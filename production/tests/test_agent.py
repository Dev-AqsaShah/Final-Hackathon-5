"""
Agent Tests - Transition tests from incubation discoveries
Run these before deploying to production
"""

import pytest
from unittest.mock import AsyncMock, patch


# ─────────────────────────────────────────────────────────────────────────────
# Tool Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestChannelFormatting:
    """Test channel-specific response formatting."""

    def test_whatsapp_response_truncated(self):
        """WhatsApp responses over 300 chars should be trimmed."""
        from production.agent.tools import _format_for_channel, Channel
        long_response = "A" * 400
        formatted = _format_for_channel(long_response, Channel.WHATSAPP, "TKT-001")
        assert len(formatted) < 450

    def test_email_response_has_greeting(self):
        """Email responses must have greeting and signature."""
        from production.agent.tools import _format_for_channel, Channel
        response = "Here are the steps to reset your password."
        formatted = _format_for_channel(response, Channel.EMAIL, "TKT-001")
        assert "dear" in formatted.lower()
        assert "best regards" in formatted.lower()
        assert "TKT-001" in formatted

    def test_web_form_response_has_ticket_id(self):
        """Web form responses must include ticket ID."""
        from production.agent.tools import _format_for_channel, Channel
        response = "Please go to Settings > Security to enable 2FA."
        formatted = _format_for_channel(response, Channel.WEB_FORM, "TKT-TEST999")
        assert "TKT-TEST999" in formatted

    def test_whatsapp_includes_human_hint(self):
        """WhatsApp responses should hint how to reach a human."""
        from production.agent.tools import _format_for_channel, Channel
        formatted = _format_for_channel("Your issue has been noted.", Channel.WHATSAPP, "TKT-002")
        assert "human" in formatted.lower() or "agent" in formatted.lower()


class TestEscalationTool:
    """Test escalation tool logic directly via the impl helper."""

    @pytest.mark.asyncio
    async def test_escalate_to_sales(self):
        """Pricing inquiry escalation goes to sales."""
        from production.agent.tools import _escalate_to_human_impl, EscalationInput, EscalationTeam
        with patch("production.agent.tools.escalate_ticket", new_callable=AsyncMock):
            result = await _escalate_to_human_impl(EscalationInput(
                ticket_id="TKT-TEST001",
                reason="pricing_inquiry",
                team=EscalationTeam.SALES
            ))
        assert "sales" in result.lower()
        assert "TKT-TEST001" in result

    @pytest.mark.asyncio
    async def test_escalate_to_billing(self):
        """Refund request escalation goes to billing."""
        from production.agent.tools import _escalate_to_human_impl, EscalationInput, EscalationTeam
        with patch("production.agent.tools.escalate_ticket", new_callable=AsyncMock):
            result = await _escalate_to_human_impl(EscalationInput(
                ticket_id="TKT-TEST002",
                reason="refund_request",
                team=EscalationTeam.BILLING
            ))
        assert "billing" in result.lower()

    @pytest.mark.asyncio
    async def test_escalate_legal(self):
        """Legal threat escalation is critical."""
        from production.agent.tools import _escalate_to_human_impl, EscalationInput, EscalationTeam
        with patch("production.agent.tools.escalate_ticket", new_callable=AsyncMock):
            result = await _escalate_to_human_impl(EscalationInput(
                ticket_id="TKT-TEST003",
                reason="legal_threat",
                team=EscalationTeam.LEGAL
            ))
        assert "legal" in result.lower() or "TKT-TEST003" in result


# ─────────────────────────────────────────────────────────────────────────────
# Escalation Decision Skill Tests  (from src/agent/skills.py)
# ─────────────────────────────────────────────────────────────────────────────

class TestEscalationDecisions:
    """Test escalation decision skill from incubation."""

    def test_legal_threat_escalation(self):
        """Legal keywords must trigger immediate escalation."""
        from src.agent.skills import escalation_decision_skill, sentiment_analysis_skill
        msg = "Our lawyer will be contacting you about this issue."
        sentiment = sentiment_analysis_skill(msg)
        decision = escalation_decision_skill(msg, sentiment)
        assert decision.should_escalate is True
        assert decision.reason == "legal_threat"
        assert decision.team == "legal"

    def test_pricing_inquiry_escalation(self):
        """Pricing questions must escalate to sales."""
        from src.agent.skills import escalation_decision_skill, sentiment_analysis_skill
        msg = "How much does the enterprise plan cost?"
        sentiment = sentiment_analysis_skill(msg)
        decision = escalation_decision_skill(msg, sentiment)
        assert decision.should_escalate is True
        assert decision.reason == "pricing_inquiry"
        assert decision.team == "sales"

    def test_human_request_escalation(self):
        """Explicit human requests must escalate."""
        from src.agent.skills import escalation_decision_skill, sentiment_analysis_skill
        msg = "I need to talk to a real person please"
        sentiment = sentiment_analysis_skill(msg)
        decision = escalation_decision_skill(msg, sentiment)
        assert decision.should_escalate is True
        assert decision.reason == "human_requested"

    def test_normal_question_no_escalation(self):
        """Normal product questions should not escalate."""
        from src.agent.skills import escalation_decision_skill, sentiment_analysis_skill
        msg = "How do I reset my password?"
        sentiment = sentiment_analysis_skill(msg)
        decision = escalation_decision_skill(msg, sentiment)
        assert decision.should_escalate is False


# ─────────────────────────────────────────────────────────────────────────────
# Sentiment Analysis Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestSentimentAnalysis:
    """Test sentiment analysis skill."""

    def test_angry_customer_negative(self):
        """Angry messages should get negative sentiment."""
        from src.agent.skills import sentiment_analysis_skill
        msg = "This is RIDICULOUS! Your product is completely BROKEN! Worst service ever!"
        result = sentiment_analysis_skill(msg)
        assert result.label == "negative"
        assert result.score < 0.3
        assert result.recommend_escalation is True

    def test_legal_threat_critical(self):
        """Legal threats should get very low score."""
        from src.agent.skills import sentiment_analysis_skill
        result = sentiment_analysis_skill("Our lawyer will be in touch.")
        assert result.score < 0.1
        assert result.recommend_escalation is True

    def test_happy_customer_positive(self):
        """Positive messages should get high score."""
        from src.agent.skills import sentiment_analysis_skill
        result = sentiment_analysis_skill(
            "Thank you for your help. This was very helpful and I appreciate the excellent service."
        )
        assert result.label == "positive"
        assert result.score > 0.7

    def test_neutral_question(self):
        """Simple questions should be neutral."""
        from src.agent.skills import sentiment_analysis_skill
        result = sentiment_analysis_skill("How do I export data to CSV?")
        assert result.label == "neutral"
        assert result.recommend_escalation is False
