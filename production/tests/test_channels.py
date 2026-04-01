"""
Channel integration tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ─────────────────────────────────────────────────────────────────────────────
# Shared fixture: patch DB + Kafka so app startup doesn't hang
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def test_client():
    """FastAPI TestClient with DB and Kafka mocked out."""
    from fastapi.testclient import TestClient
    with (
        patch("production.database.queries.get_db_pool", new_callable=AsyncMock),
        patch("production.database.queries.close_db_pool", new_callable=AsyncMock),
        patch("production.workers.kafka_client.FTEKafkaProducer.start", new_callable=AsyncMock),
        patch("production.workers.kafka_client.FTEKafkaProducer.stop", new_callable=AsyncMock),
        patch("production.workers.kafka_client.FTEKafkaProducer.publish", new_callable=AsyncMock),
    ):
        from production.api.main import app
        with TestClient(app, raise_server_exceptions=True) as client:
            yield client


# ─────────────────────────────────────────────────────────────────────────────
# Web Form Channel Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestWebFormChannel:
    """Test the web support form."""

    def test_valid_form_submission(self, test_client):
        """Valid form submission should return ticket ID."""
        response = test_client.post("/support/submit", json={
            "name": "Test User",
            "email": "test@example.com",
            "subject": "Help with API auth",
            "category": "technical",
            "message": "I need help with the API authentication setup"
        })
        assert response.status_code == 200
        data = response.json()
        assert "ticket_id" in data
        assert "message" in data

    def test_form_validation_short_name(self, test_client):
        """Name too short should return 422."""
        response = test_client.post("/support/submit", json={
            "name": "A",
            "email": "test@example.com",
            "subject": "Issue here",
            "category": "general",
            "message": "Valid message here okay"
        })
        assert response.status_code == 422

    def test_form_validation_invalid_email(self, test_client):
        """Invalid email should return 422."""
        response = test_client.post("/support/submit", json={
            "name": "Test User",
            "email": "not-an-email",
            "subject": "Valid subject line",
            "category": "general",
            "message": "Valid message with enough characters"
        })
        assert response.status_code == 422

    def test_form_validation_invalid_category(self, test_client):
        """Invalid category should return 422."""
        response = test_client.post("/support/submit", json={
            "name": "Test User",
            "email": "test@example.com",
            "subject": "Valid subject line",
            "category": "invalid_category",
            "message": "Valid message with enough characters"
        })
        assert response.status_code == 422

    def test_health_endpoint(self, test_client):
        """Health check should return healthy status."""
        response = test_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


# ─────────────────────────────────────────────────────────────────────────────
# WhatsApp Handler Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestWhatsAppHandler:
    """Test WhatsApp channel handler."""

    def test_process_webhook_extracts_data(self):
        """Webhook processing should extract correct fields."""
        import asyncio
        from production.channels.whatsapp_handler import WhatsAppHandler

        with patch.dict("os.environ", {
            "TWILIO_ACCOUNT_SID": "",
            "TWILIO_AUTH_TOKEN": "",
        }):
            handler = WhatsAppHandler()
            form_data = {
                "MessageSid": "SM123456",
                "From": "whatsapp:+14155550001",
                "Body": "Hello, I need help",
                "ProfileName": "John Doe",
                "WaId": "14155550001"
            }
            message = asyncio.run(handler.process_webhook(form_data))

            assert message["channel"] == "whatsapp"
            assert message["channel_message_id"] == "SM123456"
            assert message["customer_phone"] == "+14155550001"
            assert message["content"] == "Hello, I need help"
            assert message["customer_name"] == "John Doe"

    def test_format_response_short(self):
        """Short responses should not be split."""
        from production.channels.whatsapp_handler import WhatsAppHandler
        handler = WhatsAppHandler()
        result = handler.format_response("Short response.")
        assert len(result) == 1
        assert result[0] == "Short response."

    def test_format_response_long_splits(self):
        """Long responses should be split into multiple messages."""
        from production.channels.whatsapp_handler import WhatsAppHandler
        handler = WhatsAppHandler()
        long_text = ("This is a sentence. " * 100)
        result = handler.format_response(long_text)
        assert len(result) > 1
        for msg in result:
            assert len(msg) <= 1600


# ─────────────────────────────────────────────────────────────────────────────
# Gmail Handler Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestGmailHandler:
    """Test Gmail channel handler."""

    def test_extract_email_from_header(self):
        """Should extract email from 'Name <email>' format."""
        from production.channels.gmail_handler import GmailHandler
        with patch.dict("os.environ", {"GMAIL_CREDENTIALS": ""}):
            handler = GmailHandler()
            assert handler._extract_email("John Doe <john@example.com>") == "john@example.com"
            assert handler._extract_email("jane@example.com") == "jane@example.com"

    def test_extract_name_from_header(self):
        """Should extract name from 'Name <email>' format."""
        from production.channels.gmail_handler import GmailHandler
        with patch.dict("os.environ", {"GMAIL_CREDENTIALS": ""}):
            handler = GmailHandler()
            assert handler._extract_name("John Doe <john@example.com>") == "John Doe"
            assert handler._extract_name('"Jane Smith" <jane@example.com>') == "Jane Smith"
