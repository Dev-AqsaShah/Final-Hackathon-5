"""
Production Customer Success FTE Agent
Built with OpenAI Agents SDK - channel-aware, 24/7 autonomous operation
"""

from agents import Agent
from agents.extensions.models.litellm_model import LitellmModel

from production.agent.prompts import CUSTOMER_SUCCESS_SYSTEM_PROMPT
from production.agent.tools import (
    search_knowledge_base,
    create_ticket,
    get_customer_history,
    escalate_to_human,
    send_response,
)


# ─────────────────────────────────────────────
# The Production Agent (using Claude via LiteLLM)
# ─────────────────────────────────────────────

customer_success_agent = Agent(
    name="Customer Success FTE",
    model=LitellmModel(model="anthropic/claude-sonnet-4-6"),
    instructions=CUSTOMER_SUCCESS_SYSTEM_PROMPT,
    tools=[
        search_knowledge_base,
        create_ticket,
        get_customer_history,
        escalate_to_human,
        send_response,
    ],
)
