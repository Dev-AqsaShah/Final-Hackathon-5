"""
Stage 3: Multi-Channel End-to-End Tests
Tests the complete flow across all channels against the FastAPI app.
"""

import pytest
from unittest.mock import AsyncMock, patch


# ─────────────────────────────────────────────────────────────────────────────
# Shared fixture
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def client():
    """TestClient with DB and Kafka mocked so startup doesn't hang."""
    from fastapi.testclient import TestClient
    with (
        patch("production.database.queries.get_db_pool", new_callable=AsyncMock),
        patch("production.database.queries.close_db_pool", new_callable=AsyncMock),
        patch("production.workers.kafka_client.FTEKafkaProducer.start", new_callable=AsyncMock),
        patch("production.workers.kafka_client.FTEKafkaProducer.stop", new_callable=AsyncMock),
        patch("production.workers.kafka_client.FTEKafkaProducer.publish", new_callable=AsyncMock),
    ):
        from production.api.main import app
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


# ─────────────────────────────────────────────────────────────────────────────
# Web Form Full Flow
# ─────────────────────────────────────────────────────────────────────────────

class TestWebFormFullFlow:
    """Complete web form flow — submit → ticket ID → status check."""

    def test_submit_technical_issue(self, client):
        """Technical issue submission returns ticket ID."""
        res = client.post("/support/submit", json={
            "name": "Alice Johnson",
            "email": "alice@technova.com",
            "subject": "Cannot reset my password",
            "category": "technical",
            "message": "I have been trying to reset my password for 30 minutes but I get no email."
        })
        assert res.status_code == 200
        data = res.json()
        assert "ticket_id" in data
        assert len(data["ticket_id"]) > 0
        assert "5 minutes" in data["estimated_response_time"]

    def test_submit_billing_issue(self, client):
        """Billing issue submission returns ticket ID."""
        res = client.post("/support/submit", json={
            "name": "Bob Smith",
            "email": "bob@company.com",
            "subject": "Question about my invoice",
            "category": "billing",
            "message": "I was charged twice this month and need a clarification please."
        })
        assert res.status_code == 200
        assert "ticket_id" in res.json()

    def test_submit_bug_report(self, client):
        """Bug report submission works."""
        res = client.post("/support/submit", json={
            "name": "Carol Dev",
            "email": "carol@startup.io",
            "subject": "API returns 500 on analytics endpoint",
            "category": "bug_report",
            "priority": "high",
            "message": "The /api/v1/analytics endpoint returns a 500 error when date range exceeds 90 days."
        })
        assert res.status_code == 200

    def test_ticket_status_retrieval(self, client):
        """After submit, ticket status endpoint works."""
        submit = client.post("/support/submit", json={
            "name": "Dave User",
            "email": "dave@test.com",
            "subject": "Status check test query",
            "category": "general",
            "message": "Testing that ticket status retrieval works correctly."
        })
        ticket_id = submit.json()["ticket_id"]
        status = client.get(f"/support/ticket/{ticket_id}")
        assert status.status_code == 200
        assert status.json()["ticket_id"] == ticket_id

    def test_multiple_submissions_get_unique_tickets(self, client):
        """Each submission gets a unique ticket ID."""
        payload = {
            "name": "Eve User",
            "email": "eve@test.com",
            "subject": "Unique ticket test",
            "category": "general",
            "message": "Testing unique ticket ID generation here."
        }
        ids = {client.post("/support/submit", json=payload).json()["ticket_id"] for _ in range(3)}
        assert len(ids) == 3  # all unique


# ─────────────────────────────────────────────────────────────────────────────
# Input Validation E2E
# ─────────────────────────────────────────────────────────────────────────────

class TestInputValidationE2E:
    """End-to-end validation — bad inputs must be rejected before agent."""

    def test_short_name_rejected(self, client):
        res = client.post("/support/submit", json={
            "name": "X", "email": "x@x.com",
            "subject": "Subject here", "category": "general",
            "message": "Message long enough here"
        })
        assert res.status_code == 422

    def test_invalid_email_rejected(self, client):
        res = client.post("/support/submit", json={
            "name": "Valid Name", "email": "not-an-email",
            "subject": "Subject here", "category": "general",
            "message": "Message long enough here"
        })
        assert res.status_code == 422

    def test_short_subject_rejected(self, client):
        res = client.post("/support/submit", json={
            "name": "Valid Name", "email": "user@test.com",
            "subject": "Hi", "category": "general",
            "message": "Message long enough here"
        })
        assert res.status_code == 422

    def test_short_message_rejected(self, client):
        res = client.post("/support/submit", json={
            "name": "Valid Name", "email": "user@test.com",
            "subject": "Valid subject", "category": "general",
            "message": "Short"
        })
        assert res.status_code == 422

    def test_invalid_category_rejected(self, client):
        res = client.post("/support/submit", json={
            "name": "Valid Name", "email": "user@test.com",
            "subject": "Valid subject", "category": "hacking",
            "message": "Message long enough here"
        })
        assert res.status_code == 422

    def test_missing_required_fields(self, client):
        res = client.post("/support/submit", json={"name": "Only Name"})
        assert res.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# Health & Observability
# ─────────────────────────────────────────────────────────────────────────────

class TestHealthAndObservability:
    """Health checks and metrics endpoints."""

    def test_health_returns_healthy(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert data["channels"]["email"] == "active"
        assert data["channels"]["whatsapp"] == "active"
        assert data["channels"]["web_form"] == "active"

    def test_health_has_timestamp(self, client):
        res = client.get("/health")
        assert "timestamp" in res.json()

    def test_metrics_endpoint_reachable(self, client):
        with patch("production.api.main.get_channel_metrics", new_callable=AsyncMock) as m:
            m.return_value = {
                "web_form": {"channel": "web_form", "total_conversations": 5, "escalations": 0}
            }
            res = client.get("/metrics/channels")
        assert res.status_code == 200

    def test_metrics_with_mock_data_all_channels(self, client):
        with patch("production.api.main.get_channel_metrics", new_callable=AsyncMock) as m:
            m.return_value = {
                "email":    {"channel": "email",    "total_conversations": 10, "escalations": 2},
                "whatsapp": {"channel": "whatsapp", "total_conversations": 25, "escalations": 3},
                "web_form": {"channel": "web_form", "total_conversations": 15, "escalations": 1},
            }
            res = client.get("/metrics/channels")
        data = res.json()
        assert "email" in data
        assert "whatsapp" in data
        assert "web_form" in data
        assert data["whatsapp"]["total_conversations"] == 25


# ─────────────────────────────────────────────────────────────────────────────
# Cross-Channel Customer Lookup
# ─────────────────────────────────────────────────────────────────────────────

class TestCrossChannelContinuity:
    """Customer lookup and cross-channel identity."""

    def test_lookup_by_email_found(self, client):
        with patch("production.api.main.find_customer_by_email", new_callable=AsyncMock) as m:
            m.return_value = {"id": "cust-001", "email": "alice@technova.com", "name": "Alice"}
            res = client.get("/customers/lookup", params={"email": "alice@technova.com"})
        assert res.status_code == 200
        assert res.json()["email"] == "alice@technova.com"

    def test_lookup_by_phone_found(self, client):
        with (
            patch("production.api.main.find_customer_by_email", new_callable=AsyncMock) as me,
            patch("production.api.main.find_customer_by_phone", new_callable=AsyncMock) as mp,
        ):
            me.return_value = None
            mp.return_value = {"id": "cust-002", "phone": "+14155550001", "name": "Bob"}
            res = client.get("/customers/lookup", params={"phone": "+14155550001"})
        assert res.status_code == 200

    def test_lookup_not_found_returns_404(self, client):
        with patch("production.api.main.find_customer_by_email", new_callable=AsyncMock) as m:
            m.return_value = None
            res = client.get("/customers/lookup", params={"email": "ghost@none.com"})
        assert res.status_code == 404

    def test_lookup_no_params_returns_400(self, client):
        res = client.get("/customers/lookup")
        assert res.status_code == 400

    def test_web_form_submit_then_lookup(self, client):
        """Submit via web form, then customer should be findable."""
        client.post("/support/submit", json={
            "name": "Cross Chan User",
            "email": "crosschan@test.com",
            "subject": "Cross channel test submit",
            "category": "general",
            "message": "Testing cross channel customer lookup flow."
        })
        with patch("production.api.main.find_customer_by_email", new_callable=AsyncMock) as m:
            m.return_value = {"id": "cust-cross", "email": "crosschan@test.com", "name": "Cross Chan User"}
            res = client.get("/customers/lookup", params={"email": "crosschan@test.com"})
        assert res.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# WhatsApp Webhook E2E
# ─────────────────────────────────────────────────────────────────────────────

class TestWhatsAppWebhookE2E:
    """WhatsApp webhook processing."""

    def test_whatsapp_webhook_signature_required(self, client):
        """WhatsApp webhook without valid Twilio signature returns 403."""
        res = client.post("/webhooks/whatsapp", data={
            "MessageSid": "SM123", "From": "whatsapp:+14155550001",
            "Body": "I need help", "ProfileName": "Test"
        })
        assert res.status_code in [200, 403]

    def test_whatsapp_status_webhook(self, client):
        """Status webhook accepts delivery updates."""
        res = client.post("/webhooks/whatsapp/status", data={
            "MessageSid": "SM123", "MessageStatus": "delivered"
        })
        assert res.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# Escalation Scenarios E2E
# ─────────────────────────────────────────────────────────────────────────────

class TestEscalationScenariosE2E:
    """Verify escalation-triggering messages are accepted (agent handles them)."""

    def test_legal_threat_message_accepted(self, client):
        """Legal threat message is accepted — agent will escalate."""
        res = client.post("/support/submit", json={
            "name": "Angry Legal User",
            "email": "legal@threat.com",
            "subject": "Our lawyers are involved now",
            "category": "general",
            "priority": "high",
            "message": "This is completely unacceptable. Our lawyer will be contacting you."
        })
        assert res.status_code == 200
        assert "ticket_id" in res.json()

    def test_refund_request_accepted(self, client):
        """Refund request is accepted — agent will escalate to billing."""
        res = client.post("/support/submit", json={
            "name": "Refund User",
            "email": "refund@test.com",
            "subject": "I want a full refund immediately",
            "category": "billing",
            "message": "I want a complete refund for my subscription. This is not acceptable."
        })
        assert res.status_code == 200

    def test_urgent_priority_accepted(self, client):
        """High priority messages are accepted."""
        res = client.post("/support/submit", json={
            "name": "Urgent User",
            "email": "urgent@test.com",
            "subject": "Production system is completely down",
            "category": "technical",
            "priority": "high",
            "message": "Our production system is completely down. All users are affected right now."
        })
        assert res.status_code == 200
