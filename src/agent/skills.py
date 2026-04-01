"""
Stage 1 - Exercise 1.5: Agent Skills Manifest
Reusable capability definitions for the Customer Success FTE
"""

from dataclasses import dataclass
from typing import Any
from enum import Enum


class Channel(str, Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    WEB_FORM = "web_form"


# ─────────────────────────────────────────────
# Skill 1: Knowledge Retrieval
# ─────────────────────────────────────────────

@dataclass
class KnowledgeRetrievalResult:
    found: bool
    sections: list[str]
    confidence: float
    query_used: str


def knowledge_retrieval_skill(query: str, knowledge_base: str, max_results: int = 5) -> KnowledgeRetrievalResult:
    """
    Skill: Knowledge Retrieval
    When to use: Customer asks product questions, how-to questions, feature questions
    Inputs: query text, knowledge base content
    Outputs: relevant documentation snippets with confidence scores
    """
    query_lower = query.lower()
    query_words = set(query_lower.split())

    # Split knowledge base into sections
    sections = knowledge_base.split("---")
    scored_sections = []

    for section in sections:
        if not section.strip():
            continue
        section_lower = section.lower()
        matches = sum(1 for word in query_words if word in section_lower and len(word) > 3)
        if matches > 0:
            scored_sections.append((matches, section.strip()[:800]))

    scored_sections.sort(key=lambda x: x[0], reverse=True)
    top_sections = [s[1] for s in scored_sections[:max_results]]

    confidence = min(1.0, (scored_sections[0][0] / max(len(query_words), 1)) * 2) if scored_sections else 0.0

    return KnowledgeRetrievalResult(
        found=len(top_sections) > 0,
        sections=top_sections,
        confidence=confidence,
        query_used=query
    )


# ─────────────────────────────────────────────
# Skill 2: Sentiment Analysis
# ─────────────────────────────────────────────

@dataclass
class SentimentResult:
    label: str           # "positive", "neutral", "negative"
    score: float         # 0.0 (very negative) to 1.0 (very positive)
    confidence: float
    triggers: list[str]  # which keywords triggered
    recommend_escalation: bool


def sentiment_analysis_skill(text: str) -> SentimentResult:
    """
    Skill: Sentiment Analysis
    When to use: Every customer message (run first)
    Inputs: message text
    Outputs: sentiment label, score, escalation recommendation
    """
    text_lower = text.lower()

    CRITICAL_TRIGGERS = ["lawyer", "legal", "sue", "lawsuit", "attorney"]
    NEGATIVE_HIGH = ["unacceptable", "ridiculous", "terrible", "horrible", "worst", "disaster",
                     "furious", "outrageous", "incompetent", "useless", "garbage"]
    NEGATIVE_MED = ["frustrated", "annoyed", "disappointed", "upset", "angry", "broken",
                    "not working", "failed", "issue", "problem", "wrong"]
    POSITIVE = ["thank", "great", "excellent", "helpful", "love", "amazing", "wonderful",
                "perfect", "fantastic", "appreciate"]

    found_critical = [w for w in CRITICAL_TRIGGERS if w in text_lower]
    found_neg_high = [w for w in NEGATIVE_HIGH if w in text_lower]
    found_neg_med = [w for w in NEGATIVE_MED if w in text_lower]
    found_pos = [w for w in POSITIVE if w in text_lower]

    all_triggers = found_critical + found_neg_high + found_neg_med + found_pos

    # Caps lock = anger signal
    caps_words = sum(1 for word in text.split() if word.isupper() and len(word) > 2)
    exclamations = text.count("!")

    if found_critical:
        score = 0.05
        label = "negative"
    elif found_neg_high or caps_words >= 3:
        score = 0.15
        label = "negative"
    elif found_neg_med or exclamations >= 2:
        score = 0.35
        label = "negative"
    elif found_pos:
        score = 0.85
        label = "positive"
    else:
        score = 0.55
        label = "neutral"

    return SentimentResult(
        label=label,
        score=score,
        confidence=0.75,
        triggers=all_triggers,
        recommend_escalation=score < 0.3
    )


# ─────────────────────────────────────────────
# Skill 3: Escalation Decision
# ─────────────────────────────────────────────

@dataclass
class EscalationDecision:
    should_escalate: bool
    reason: str
    team: str | None
    urgency: str   # "normal", "urgent", "critical"


def escalation_decision_skill(
    message: str,
    sentiment: SentimentResult,
    search_attempts: int = 0,
    knowledge_found: bool = True,
    category: str = "general"
) -> EscalationDecision:
    """
    Skill: Escalation Decision
    When to use: After analyzing message and generating response
    Inputs: conversation context, sentiment result, knowledge search result
    Outputs: should_escalate boolean, reason, team, urgency
    """
    text_lower = message.lower()

    # Critical escalations - immediate
    legal_words = ["lawyer", "legal", "sue", "lawsuit", "attorney", "court"]
    if any(w in text_lower for w in legal_words):
        return EscalationDecision(
            should_escalate=True,
            reason="legal_threat",
            team="legal",
            urgency="critical"
        )

    security_words = ["hacked", "breach", "unauthorized", "stolen", "compromised"]
    if any(w in text_lower for w in security_words):
        return EscalationDecision(
            should_escalate=True,
            reason="security_incident",
            team="engineering",
            urgency="critical"
        )

    # Pricing/sales - always escalate
    pricing_words = ["price", "pricing", "cost", "enterprise plan", "discount", "quote",
                     "how much", "custom plan"]
    if any(w in text_lower for w in pricing_words):
        return EscalationDecision(
            should_escalate=True,
            reason="pricing_inquiry",
            team="sales",
            urgency="normal"
        )

    # Refunds
    refund_words = ["refund", "money back", "charge", "chargeback", "overcharged"]
    if any(w in text_lower for w in refund_words):
        return EscalationDecision(
            should_escalate=True,
            reason="refund_request",
            team="billing",
            urgency="normal"
        )

    # Human request
    human_words = ["human", "real person", "agent", "representative", "talk to someone"]
    if any(w in text_lower for w in human_words):
        return EscalationDecision(
            should_escalate=True,
            reason="human_requested",
            team="senior_support",
            urgency="normal"
        )

    # Negative sentiment
    if sentiment.score < 0.3:
        return EscalationDecision(
            should_escalate=True,
            reason="negative_sentiment",
            team="senior_support",
            urgency="urgent" if sentiment.score < 0.15 else "normal"
        )

    # Cannot find information after 2 attempts
    if search_attempts >= 2 and not knowledge_found:
        return EscalationDecision(
            should_escalate=True,
            reason="knowledge_not_found",
            team="senior_support",
            urgency="normal"
        )

    return EscalationDecision(
        should_escalate=False,
        reason="",
        team=None,
        urgency="normal"
    )


# ─────────────────────────────────────────────
# Skill 4: Channel Adaptation
# ─────────────────────────────────────────────

@dataclass
class ChannelAdaptedResponse:
    formatted_response: str
    original_length: int
    final_length: int
    truncated: bool
    channel: str


def channel_adaptation_skill(response: str, channel: Channel, ticket_id: str) -> ChannelAdaptedResponse:
    """
    Skill: Channel Adaptation
    When to use: Before sending any response
    Inputs: response text, target channel
    Outputs: properly formatted response for that channel
    """
    original_length = len(response)

    if channel == Channel.EMAIL:
        formatted = f"""Dear Customer,

Thank you for contacting TechNova Support.

{response}

If you have any further questions, please reply to this email.

Best regards,
TechNova AI Support Team
support@technova.io
Reference: {ticket_id}
This response was generated by our AI assistant. Reply for human support."""

    elif channel == Channel.WHATSAPP:
        MAX_WHATSAPP = 1600
        PREFERRED_LENGTH = 300

        if len(response) > PREFERRED_LENGTH:
            # Try to cut at sentence boundary
            cut_point = response.rfind('. ', 0, PREFERRED_LENGTH)
            if cut_point == -1:
                cut_point = PREFERRED_LENGTH - 3
            response = response[:cut_point + 1].strip()

        formatted = f"{response}\n\nRef: {ticket_id} | Type 'human' for live agent 💬"

    else:  # web_form
        formatted = f"""{response}

---
Ticket ID: {ticket_id}
Need more help? Visit support.technova.io or reply to this message."""

    return ChannelAdaptedResponse(
        formatted_response=formatted,
        original_length=original_length,
        final_length=len(formatted),
        truncated=len(formatted) < original_length + 100,
        channel=channel.value
    )


# ─────────────────────────────────────────────
# Skill 5: Customer Identification
# ─────────────────────────────────────────────

@dataclass
class CustomerIdentity:
    customer_id: str
    is_new: bool
    primary_channel: str
    known_identifiers: list[str]
    has_history: bool


def customer_identification_skill(
    message_metadata: dict,
    customer_store: dict
) -> CustomerIdentity:
    """
    Skill: Customer Identification
    When to use: On every incoming message (before anything else)
    Inputs: message metadata (email, phone, etc.)
    Outputs: unified customer_id, merged history status
    """
    import uuid

    email = message_metadata.get("customer_email", "").lower().strip()
    phone = message_metadata.get("customer_phone", "").strip()
    channel = message_metadata.get("channel", "web_form")

    identifiers = []
    existing_customer = None

    if email:
        identifiers.append(f"email:{email}")
        if f"email:{email}" in customer_store:
            existing_customer = customer_store[f"email:{email}"]

    if phone:
        identifiers.append(f"phone:{phone}")
        if f"phone:{phone}" in customer_store:
            existing_customer = customer_store[f"phone:{phone}"]

    if existing_customer:
        return CustomerIdentity(
            customer_id=existing_customer["customer_id"],
            is_new=False,
            primary_channel=existing_customer.get("primary_channel", channel),
            known_identifiers=existing_customer.get("identifiers", identifiers),
            has_history=True
        )

    # Create new customer
    customer_id = f"CUST-{str(uuid.uuid4())[:8].upper()}"
    customer_data = {
        "customer_id": customer_id,
        "primary_channel": channel,
        "identifiers": identifiers,
        "created_at": __import__("datetime").datetime.utcnow().isoformat()
    }

    for ident in identifiers:
        customer_store[ident] = customer_data

    return CustomerIdentity(
        customer_id=customer_id,
        is_new=True,
        primary_channel=channel,
        known_identifiers=identifiers,
        has_history=False
    )
