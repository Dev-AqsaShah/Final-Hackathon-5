"""
Stage 1 - Exercise 1.4: MCP Server
Exposes Customer Success FTE capabilities as MCP tools
"""

import asyncio
import json
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    CallToolResult,
)


class Channel(str, Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    WEB_FORM = "web_form"


# In-memory store (prototype)
_tickets = {}
_customers = {}
_conversations = {}
_knowledge_base = []

# Load knowledge from product docs
import os

def _load_knowledge():
    docs_path = os.path.join(os.path.dirname(__file__), "../../context/product-docs.md")
    if os.path.exists(docs_path):
        with open(docs_path, "r") as f:
            content = f.read()
        # Split into sections
        sections = content.split("---")
        for i, section in enumerate(sections):
            if section.strip():
                lines = section.strip().split("\n")
                title = lines[0].replace("#", "").strip() if lines else f"Section {i}"
                _knowledge_base.append({
                    "id": str(i),
                    "title": title,
                    "content": section.strip()
                })

_load_knowledge()


# ─────────────────────────────────────────────
# MCP Server Setup
# ─────────────────────────────────────────────

server = Server("customer-success-fte")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_knowledge_base",
            description="Search product documentation for relevant information. Use when customer asks product questions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Max number of results to return",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="create_ticket",
            description="Create a support ticket. ALWAYS call this first at the start of every conversation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string", "description": "Customer identifier (email or phone)"},
                    "issue": {"type": "string", "description": "Description of the issue"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"], "default": "medium"},
                    "channel": {"type": "string", "enum": ["email", "whatsapp", "web_form"]},
                    "subject": {"type": "string", "description": "Ticket subject or title"}
                },
                "required": ["customer_id", "issue", "channel"]
            }
        ),
        Tool(
            name="get_customer_history",
            description="Get customer's past interactions across ALL channels. Check this before responding.",
            inputSchema={
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string", "description": "Customer identifier (email or phone)"}
                },
                "required": ["customer_id"]
            }
        ),
        Tool(
            name="escalate_to_human",
            description="Escalate conversation to human support team. Use for pricing, refunds, legal issues, angry customers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "string", "description": "The ticket ID to escalate"},
                    "reason": {"type": "string", "description": "Clear reason for escalation"},
                    "team": {
                        "type": "string",
                        "enum": ["billing", "legal", "engineering", "sales", "senior_support"],
                        "description": "Which team to escalate to"
                    },
                    "urgency": {"type": "string", "enum": ["normal", "urgent", "critical"], "default": "normal"}
                },
                "required": ["ticket_id", "reason", "team"]
            }
        ),
        Tool(
            name="send_response",
            description="Send response to customer via their channel. ALWAYS use this to reply - never respond directly.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "string", "description": "The ticket ID"},
                    "message": {"type": "string", "description": "The response message to send"},
                    "channel": {"type": "string", "enum": ["email", "whatsapp", "web_form"]}
                },
                "required": ["ticket_id", "message", "channel"]
            }
        ),
        Tool(
            name="analyze_sentiment",
            description="Analyze customer message sentiment to detect frustration or urgency.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Customer message text to analyze"}
                },
                "required": ["text"]
            }
        ),
        Tool(
            name="update_ticket_status",
            description="Update the status of an existing ticket.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "string"},
                    "status": {"type": "string", "enum": ["open", "in_progress", "resolved", "escalated", "closed"]},
                    "notes": {"type": "string", "description": "Resolution notes"}
                },
                "required": ["ticket_id", "status"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:

    if name == "search_knowledge_base":
        query = arguments.get("query", "").lower()
        max_results = arguments.get("max_results", 5)

        results = []
        for item in _knowledge_base:
            if any(word in item["content"].lower() for word in query.split()):
                results.append(item)
            if len(results) >= max_results:
                break

        if not results:
            return [TextContent(
                type="text",
                text="No relevant documentation found for this query. Consider escalating to human support."
            )]

        formatted = "\n\n---\n\n".join(
            f"**{r['title']}**\n{r['content'][:500]}" for r in results
        )
        return [TextContent(type="text", text=formatted)]

    elif name == "create_ticket":
        ticket_id = f"TKT-{str(uuid.uuid4())[:8].upper()}"
        ticket = {
            "ticket_id": ticket_id,
            "customer_id": arguments["customer_id"],
            "issue": arguments["issue"],
            "priority": arguments.get("priority", "medium"),
            "channel": arguments["channel"],
            "subject": arguments.get("subject", "Support Request"),
            "status": "open",
            "created_at": datetime.utcnow().isoformat(),
        }
        _tickets[ticket_id] = ticket

        # Add to customer history
        cid = arguments["customer_id"]
        if cid not in _customers:
            _customers[cid] = {"tickets": []}
        _customers[cid]["tickets"].append(ticket_id)

        return [TextContent(
            type="text",
            text=f"Ticket created successfully. ID: {ticket_id}, Channel: {arguments['channel']}, Priority: {ticket['priority']}"
        )]

    elif name == "get_customer_history":
        cid = arguments["customer_id"]
        customer = _customers.get(cid)

        if not customer or not customer.get("tickets"):
            return [TextContent(type="text", text="No previous interaction history found for this customer.")]

        history_items = []
        for tid in customer["tickets"][-5:]:  # last 5 tickets
            ticket = _tickets.get(tid, {})
            history_items.append(
                f"- Ticket {tid} | Channel: {ticket.get('channel', 'N/A')} | "
                f"Issue: {ticket.get('issue', 'N/A')[:100]} | "
                f"Status: {ticket.get('status', 'N/A')} | "
                f"Date: {ticket.get('created_at', 'N/A')[:10]}"
            )

        return [TextContent(
            type="text",
            text=f"Customer History ({len(history_items)} interactions):\n" + "\n".join(history_items)
        )]

    elif name == "escalate_to_human":
        ticket_id = arguments["ticket_id"]
        ticket = _tickets.get(ticket_id, {})
        ticket["status"] = "escalated"
        ticket["escalation_reason"] = arguments["reason"]
        ticket["escalation_team"] = arguments["team"]
        ticket["escalation_urgency"] = arguments.get("urgency", "normal")
        ticket["escalated_at"] = datetime.utcnow().isoformat()

        return [TextContent(
            type="text",
            text=f"Escalated to {arguments['team']} team. Reason: {arguments['reason']}. "
                 f"Urgency: {arguments.get('urgency', 'normal')}. Reference: {ticket_id}"
        )]

    elif name == "send_response":
        ticket_id = arguments["ticket_id"]
        channel = arguments["channel"]
        message = arguments["message"]

        # Format for channel
        formatted = _format_for_channel(message, channel, ticket_id)

        # In production, this would actually send via Gmail API / Twilio / etc.
        ticket = _tickets.get(ticket_id, {})
        ticket["last_response"] = formatted
        ticket["last_response_at"] = datetime.utcnow().isoformat()

        return [TextContent(
            type="text",
            text=f"Response sent via {channel}. Delivery status: sent\n\nMessage preview:\n{formatted[:200]}..."
        )]

    elif name == "analyze_sentiment":
        text = arguments.get("text", "").lower()

        # Simple keyword-based sentiment (prototype)
        negative_words = ["angry", "frustrated", "terrible", "horrible", "worst", "unacceptable",
                         "ridiculous", "useless", "broken", "disaster", "urgent", "critical",
                         "lawsuit", "lawyer", "legal", "sue", "refund", "cancel"]
        positive_words = ["great", "excellent", "thanks", "helpful", "love", "wonderful", "amazing"]
        neutral_words = ["how", "what", "where", "when", "help", "question", "need"]

        negative_count = sum(1 for w in negative_words if w in text)
        positive_count = sum(1 for w in positive_words if w in text)

        if negative_count >= 2:
            score = 0.2
            label = "negative"
        elif negative_count == 1:
            score = 0.35
            label = "neutral_negative"
        elif positive_count >= 1:
            score = 0.8
            label = "positive"
        else:
            score = 0.5
            label = "neutral"

        return [TextContent(
            type="text",
            text=f"Sentiment: {label}, Score: {score} (0=very negative, 1=very positive). "
                 f"Recommend escalation: {'Yes' if score < 0.3 else 'No'}"
        )]

    elif name == "update_ticket_status":
        ticket_id = arguments["ticket_id"]
        ticket = _tickets.get(ticket_id)
        if ticket:
            ticket["status"] = arguments["status"]
            if "notes" in arguments:
                ticket["resolution_notes"] = arguments["notes"]
            return [TextContent(type="text", text=f"Ticket {ticket_id} updated to status: {arguments['status']}")]
        return [TextContent(type="text", text=f"Ticket {ticket_id} not found")]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


def _format_for_channel(message: str, channel: str, ticket_id: str) -> str:
    if channel == "email":
        return f"Dear Customer,\n\nThank you for contacting TechNova Support.\n\n{message}\n\nBest regards,\nTechNova Support Team\nTicket: {ticket_id}"
    elif channel == "whatsapp":
        if len(message) > 300:
            message = message[:297] + "..."
        return f"{message}\n\nTicket: {ticket_id} | Type 'human' for live support 💬"
    else:
        return f"{message}\n\n---\nTicket ID: {ticket_id} | support.technova.io"


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="customer-success-fte",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities={}
                )
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
