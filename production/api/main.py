"""
FastAPI Application - Main API service
Handles all channel webhooks and REST endpoints
"""

import logging
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Response
from fastapi.middleware.cors import CORSMiddleware

import uuid
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator

from production.workers.kafka_client import FTEKafkaProducer, TOPICS
from production.database.queries import (
    load_conversation_history,
    get_channel_metrics,
    find_customer_by_email,
    find_customer_by_phone,
    get_db_pool,
    close_db_pool,
)

# Gmail and WhatsApp handlers (optional)
try:
    from production.channels.gmail_handler import GmailHandler
    gmail_handler = GmailHandler()
except Exception as e:
    logging.warning(f"Gmail handler not available: {e}")
    gmail_handler = None

try:
    from production.channels.whatsapp_handler import WhatsAppHandler
    whatsapp_handler = WhatsAppHandler()
except Exception as e:
    logging.warning(f"WhatsApp handler not available: {e}")
    whatsapp_handler = None

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# App Setup
# ─────────────────────────────────────────────

app = FastAPI(
    title="Customer Success FTE API",
    description="24/7 AI-powered customer support across Email, WhatsApp, and Web",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

kafka_producer = FTEKafkaProducer()

# ─────────────────────────────────────────────
# Web Support Form Models
# ─────────────────────────────────────────────

class SupportFormSubmission(BaseModel):
    name: str
    email: EmailStr
    subject: str
    category: str
    message: str
    priority: Optional[str] = "medium"

    @field_validator("name")
    @classmethod
    def name_valid(cls, v):
        if len(v.strip()) < 2:
            raise ValueError("Name must be at least 2 characters")
        return v.strip()

    @field_validator("message")
    @classmethod
    def message_valid(cls, v):
        if len(v.strip()) < 10:
            raise ValueError("Message must be at least 10 characters")
        return v.strip()

    @field_validator("subject")
    @classmethod
    def subject_valid(cls, v):
        if len(v.strip()) < 5:
            raise ValueError("Subject must be at least 5 characters")
        return v.strip()

    @field_validator("category")
    @classmethod
    def category_valid(cls, v):
        valid = ["general", "technical", "billing", "feedback", "bug_report"]
        if v not in valid:
            raise ValueError(f"Category must be one of: {valid}")
        return v


class SupportFormResponse(BaseModel):
    ticket_id: str
    message: str
    estimated_response_time: str


# ─────────────────────────────────────────────
# Lifecycle
# ─────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    try:
        await kafka_producer.start()
    except Exception as e:
        logger.warning(f"Kafka not available: {e} - continuing without Kafka")
    try:
        await get_db_pool()
        logger.info("Database connected")
    except Exception as e:
        logger.warning(f"Database not available: {e}")
    logger.info("API service started")


@app.on_event("shutdown")
async def shutdown():
    await kafka_producer.stop()
    await close_db_pool()
    logger.info("API service shutting down")


# ─────────────────────────────────────────────
# Web Support Form Endpoints
# ─────────────────────────────────────────────

@app.post("/support/submit", response_model=SupportFormResponse)
async def submit_support_form(submission: SupportFormSubmission):
    """Handle web support form submission."""
    ticket_id = str(uuid.uuid4())
    message_data = {
        "channel": "web_form",
        "channel_message_id": ticket_id,
        "customer_email": submission.email,
        "customer_name": submission.name,
        "subject": submission.subject,
        "content": submission.message,
        "category": submission.category,
        "priority": submission.priority,
        "received_at": datetime.utcnow().isoformat(),
    }
    try:
        await kafka_producer.publish(TOPICS["tickets_incoming"], message_data)
    except Exception as e:
        logger.warning(f"Kafka publish failed (continuing): {e}")

    return SupportFormResponse(
        ticket_id=ticket_id,
        message="Thank you! Our AI assistant will respond shortly.",
        estimated_response_time="Usually within 5 minutes"
    )


@app.get("/support/ticket/{ticket_id}")
async def get_ticket_status(ticket_id: str):
    """Get ticket status."""
    return {"ticket_id": ticket_id, "status": "open"}


# ─────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "channels": {
            "email": "active",
            "whatsapp": "active",
            "web_form": "active"
        }
    }


# ─────────────────────────────────────────────
# Gmail Webhook
# ─────────────────────────────────────────────

@app.post("/webhooks/gmail")
async def gmail_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Handle Gmail push notifications via Google Cloud Pub/Sub.
    Gmail sends a Pub/Sub notification when new email arrives.
    """
    try:
        body = await request.json()
        messages = await gmail_handler.process_notification(body)

        for message in messages:
            background_tasks.add_task(
                kafka_producer.publish,
                TOPICS["tickets_incoming"],
                message
            )

        return {"status": "processed", "count": len(messages)}

    except Exception as e:
        logger.error(f"Gmail webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
# WhatsApp Webhook (Twilio)
# ─────────────────────────────────────────────

@app.post("/webhooks/whatsapp")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Handle incoming WhatsApp messages via Twilio webhook.
    Twilio sends a POST with form data for each incoming message.
    """
    # Validate Twilio signature
    if not await whatsapp_handler.validate_webhook(request):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    form_data = await request.form()
    message = await whatsapp_handler.process_webhook(dict(form_data))

    background_tasks.add_task(
        kafka_producer.publish,
        TOPICS["tickets_incoming"],
        message
    )

    # Return empty TwiML - agent will respond asynchronously
    return Response(
        content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
        media_type="application/xml"
    )


@app.post("/webhooks/whatsapp/status")
async def whatsapp_status_webhook(request: Request):
    """Handle WhatsApp message delivery status callbacks from Twilio."""
    form_data = await request.form()
    logger.info(f"WhatsApp status update: {dict(form_data)}")
    return {"status": "received"}


# ─────────────────────────────────────────────
# Conversation & Customer Endpoints
# ─────────────────────────────────────────────

@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get full conversation history with cross-channel context."""
    history = await load_conversation_history(conversation_id)
    if not history:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"conversation_id": conversation_id, "messages": history}


@app.get("/customers/lookup")
async def lookup_customer(email: str = None, phone: str = None):
    """Look up customer by email or phone across all channels."""
    if not email and not phone:
        raise HTTPException(status_code=400, detail="Provide email or phone")

    customer = None
    if email:
        customer = await find_customer_by_email(email)
    if not customer and phone:
        customer = await find_customer_by_phone(phone)

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    return customer


# ─────────────────────────────────────────────
# Metrics Endpoints
# ─────────────────────────────────────────────

@app.get("/metrics/channels")
async def get_metrics():
    """Get performance metrics broken down by channel."""
    return await get_channel_metrics()
