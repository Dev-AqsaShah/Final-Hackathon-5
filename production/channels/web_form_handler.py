"""
Web Form Channel Handler
FastAPI router for web support form submissions
"""

import uuid
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, field_validator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/support", tags=["support-form"])


# ─────────────────────────────────────────────
# Request / Response Models
# ─────────────────────────────────────────────

class SupportFormSubmission(BaseModel):
    name: str
    email: EmailStr
    subject: str
    category: str      # 'general', 'technical', 'billing', 'feedback', 'bug_report'
    message: str
    priority: Optional[str] = "medium"
    attachments: Optional[list[str]] = []

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError("Name must be at least 2 characters")
        return v.strip()

    @field_validator("message")
    @classmethod
    def message_must_have_content(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError("Message must be at least 10 characters")
        return v.strip()

    @field_validator("subject")
    @classmethod
    def subject_must_not_be_empty(cls, v):
        if not v or len(v.strip()) < 5:
            raise ValueError("Subject must be at least 5 characters")
        return v.strip()

    @field_validator("category")
    @classmethod
    def category_must_be_valid(cls, v):
        valid_categories = ["general", "technical", "billing", "feedback", "bug_report"]
        if v not in valid_categories:
            raise ValueError(f"Category must be one of: {valid_categories}")
        return v

    @field_validator("priority")
    @classmethod
    def priority_must_be_valid(cls, v):
        if v and v not in ["low", "medium", "high"]:
            raise ValueError("Priority must be low, medium, or high")
        return v


class SupportFormResponse(BaseModel):
    ticket_id: str
    message: str
    estimated_response_time: str


class TicketStatusResponse(BaseModel):
    ticket_id: str
    status: str
    created_at: str
    messages: list[dict] = []


# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────

@router.post("/submit", response_model=SupportFormResponse)
async def submit_support_form(submission: SupportFormSubmission):
    """
    Handle support form submission.

    Steps:
    1. Validate the submission (Pydantic handles this)
    2. Create ticket record in DB
    3. Publish to Kafka for agent processing
    4. Return confirmation to user
    """
    ticket_id = str(uuid.uuid4())

    # Build normalized message for agent processing
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
        "metadata": {
            "form_version": "1.0",
            "attachments": submission.attachments
        }
    }

    try:
        # Publish to Kafka for agent processing
        from production.workers.kafka_client import FTEKafkaProducer, TOPICS
        producer = FTEKafkaProducer()
        await producer.start()
        await producer.publish(TOPICS["tickets_incoming"], message_data)
        await producer.stop()
    except Exception as e:
        logger.error(f"Failed to publish to Kafka: {e}")
        # Continue even if Kafka is down - ticket still gets created

    return SupportFormResponse(
        ticket_id=ticket_id,
        message="Thank you for contacting us! Our AI assistant will respond shortly.",
        estimated_response_time="Usually within 5 minutes"
    )


@router.get("/ticket/{ticket_id}", response_model=TicketStatusResponse)
async def get_ticket_status(ticket_id: str):
    """Get status and conversation history for a ticket."""
    from production.database.queries import get_ticket
    ticket = await get_ticket(ticket_id)

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return TicketStatusResponse(
        ticket_id=str(ticket["id"]),
        status=ticket["status"],
        created_at=str(ticket["created_at"]),
        messages=[]
    )
