"""
Production Agent Tools - OpenAI Agents SDK function_tool definitions
Converted from MCP server tools with proper validation and error handling
"""

import logging
from enum import Enum
from typing import Optional

from agents import function_tool
from pydantic import BaseModel

from production.database.queries import (
    get_db_pool,
    get_customer_history as db_get_customer_history,
    search_knowledge_base as db_search_knowledge_base,
    create_ticket as db_create_ticket,
    update_ticket_status,
    escalate_ticket,
    save_message,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Enums & Input Schemas
# ─────────────────────────────────────────────

class Channel(str, Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    WEB_FORM = "web_form"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EscalationTeam(str, Enum):
    BILLING = "billing"
    LEGAL = "legal"
    ENGINEERING = "engineering"
    SALES = "sales"
    SENIOR_SUPPORT = "senior_support"


class KnowledgeSearchInput(BaseModel):
    query: str
    max_results: int = 5
    category: Optional[str] = None


class TicketInput(BaseModel):
    customer_id: str
    conversation_id: str
    issue: str
    channel: Channel
    subject: Optional[str] = "Support Request"
    priority: Priority = Priority.MEDIUM
    category: Optional[str] = "general"


class EscalationInput(BaseModel):
    ticket_id: str
    reason: str
    team: EscalationTeam
    urgency: str = "normal"


class ResponseInput(BaseModel):
    ticket_id: str
    conversation_id: str
    message: str
    channel: Channel
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None


# ─────────────────────────────────────────────
# Tool Implementations
# ─────────────────────────────────────────────

@function_tool
async def search_knowledge_base(input: KnowledgeSearchInput) -> str:
    """Search product documentation for relevant information.

    Use this when the customer asks questions about product features,
    how to use something, or needs technical information.

    Args:
        input: Search parameters including query and optional filters

    Returns:
        Formatted search results with relevance scores
    """
    try:
        from production.agent.embeddings import generate_embedding
        embedding = await generate_embedding(input.query)

        results = await db_search_knowledge_base(
            query_embedding=embedding,
            max_results=input.max_results,
            category=input.category
        )

        if not results:
            return "No relevant documentation found. Consider escalating to human support."

        formatted = []
        for r in results:
            formatted.append(
                f"**{r['title']}** (relevance: {r.get('similarity', 0):.2f})\n{r['content'][:500]}"
            )

        return "\n\n---\n\n".join(formatted)

    except Exception as e:
        logger.error(f"Knowledge base search failed: {e}")
        return "Knowledge base temporarily unavailable. Please try again or escalate."


@function_tool
async def create_ticket(input: TicketInput) -> str:
    """Create a support ticket for tracking.

    ALWAYS create a ticket at the start of every conversation.
    Include the source channel for proper tracking and reporting.

    Args:
        input: Ticket details including customer, issue, and channel

    Returns:
        Ticket ID confirmation
    """
    try:
        ticket_id = await db_create_ticket(
            customer_id=input.customer_id,
            conversation_id=input.conversation_id,
            channel=input.channel.value,
            subject=input.subject,
            category=input.category,
            priority=input.priority.value
        )

        logger.info(f"Created ticket {ticket_id} for customer {input.customer_id} via {input.channel.value}")
        return f"Ticket created successfully. ID: {ticket_id}, Channel: {input.channel.value}, Priority: {input.priority.value}"

    except Exception as e:
        logger.error(f"Failed to create ticket: {e}")
        return f"Ticket creation failed: {str(e)}"


@function_tool
async def get_customer_history(customer_id: str) -> str:
    """Get customer's complete interaction history across ALL channels.

    Use this to understand context from previous conversations,
    even if they happened on a different channel (email vs WhatsApp vs web).

    Args:
        customer_id: The unified customer ID

    Returns:
        Formatted history of past interactions
    """
    try:
        history = await db_get_customer_history(customer_id)

        if not history:
            return "No previous interaction history found for this customer."

        formatted = [f"Customer History ({len(history)} recent interactions):"]
        for item in history[:10]:
            formatted.append(
                f"- [{item['channel']}] {item['role']}: {str(item['content'])[:150]}... "
                f"({str(item['created_at'])[:10]})"
            )

        return "\n".join(formatted)

    except Exception as e:
        logger.error(f"Failed to get customer history: {e}")
        return "Customer history temporarily unavailable."


async def _escalate_to_human_impl(input: EscalationInput) -> str:
    """Underlying escalation logic (testable directly)."""
    try:
        await escalate_ticket(
            ticket_id=input.ticket_id,
            reason=input.reason,
            team=input.team.value,
            urgency=input.urgency
        )
        logger.info(f"Escalated ticket {input.ticket_id} to {input.team.value}: {input.reason}")
        return (
            f"Escalated to {input.team.value} team. "
            f"Reason: {input.reason}. "
            f"Urgency: {input.urgency}. "
            f"Reference: {input.ticket_id}"
        )
    except Exception as e:
        logger.error(f"Escalation failed: {e}")
        return f"Escalation failed: {str(e)}"


@function_tool
async def escalate_to_human(input: EscalationInput) -> str:
    """Escalate conversation to human support.

    Use this when:
    - Customer asks about pricing or refunds
    - Customer sentiment is negative (frustrated/angry)
    - You cannot find relevant information after 2 searches
    - Customer explicitly requests human help
    - Legal threats or security incidents

    Args:
        input: Escalation details including ticket, reason, and team

    Returns:
        Confirmation of escalation
    """
    return await _escalate_to_human_impl(input)


@function_tool
async def send_response(input: ResponseInput) -> str:
    """Send response to customer via their preferred channel.

    The response will be automatically formatted for the channel.
    - Email: Formal with greeting/signature
    - WhatsApp: Concise and conversational (< 300 chars preferred)
    - Web: Semi-formal

    ALWAYS use this tool to reply - never respond directly to customer.

    Args:
        input: Response details including message and channel

    Returns:
        Delivery confirmation
    """
    try:
        formatted = _format_for_channel(input.message, input.channel, input.ticket_id)

        # Send via appropriate channel
        delivery_status = "sent"
        channel_message_id = None

        if input.channel == Channel.EMAIL and input.customer_email:
            from production.channels.gmail_handler import GmailHandler
            gmail = GmailHandler()
            result = await gmail.send_reply(
                to_email=input.customer_email,
                subject="Re: Support Request",
                body=formatted
            )
            delivery_status = result.get("delivery_status", "sent")
            channel_message_id = result.get("channel_message_id")

        elif input.channel == Channel.WHATSAPP and input.customer_phone:
            from production.channels.whatsapp_handler import WhatsAppHandler
            whatsapp = WhatsAppHandler()
            result = await whatsapp.send_message(
                to_phone=input.customer_phone,
                body=formatted
            )
            delivery_status = result.get("delivery_status", "sent")
            channel_message_id = result.get("channel_message_id")

        # Save outbound message to DB
        await save_message(
            conversation_id=input.conversation_id,
            channel=input.channel.value,
            direction="outbound",
            role="agent",
            content=formatted,
            channel_message_id=channel_message_id,
            delivery_status=delivery_status
        )

        return f"Response sent via {input.channel.value}. Status: {delivery_status}"

    except Exception as e:
        logger.error(f"Failed to send response: {e}")
        return f"Response delivery failed: {str(e)}"


# ─────────────────────────────────────────────
# Channel Formatting Helper
# ─────────────────────────────────────────────

def _format_for_channel(response: str, channel: Channel, ticket_id: str) -> str:
    if channel == Channel.EMAIL:
        return f"""Dear Customer,

Thank you for reaching out to TechNova Support.

{response}

If you have any further questions, please don't hesitate to reply to this email.

Best regards,
TechNova AI Support Team
support@technova.io
---
Ticket Reference: {ticket_id}
This response was generated by our AI assistant. For complex issues, you can request human support."""

    elif channel == Channel.WHATSAPP:
        if len(response) > 300:
            cut = response.rfind('. ', 0, 297)
            if cut == -1:
                cut = 297
            response = response[:cut + 1].strip()
        return f"{response}\n\n📱 Ref: {ticket_id} | Reply or type 'human' for live support."

    else:  # web_form
        return f"""{response}

---
Need more help? Reply to this message or visit support.technova.io
Ticket ID: {ticket_id}"""
