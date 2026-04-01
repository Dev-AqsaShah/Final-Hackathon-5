"""
Multi-channel End-to-End Tests
"""

import pytest
from unittest.mock import AsyncMock, patch


BASE_URL = "http://localhost:8000"


class TestMultiChannelE2E:
    """Test full flow across all channels."""

    @pytest.mark.asyncio
    async def test_web_form_full_flow(self):
        """Web form submission should create ticket and return confirmation."""
        from fastapi.testclient import TestClient
        from production.api.main import app

        with patch("production.channels.web_form_handler.FTEKafkaProducer") as mock_kafka:
            mock_kafka.return_value.start = AsyncMock()
            mock_kafka.return_value.publish = AsyncMock()
            mock_kafka.return_value.stop = AsyncMock()

            client = TestClient(app)
            response = client.post("/support/submit", json={
                "name": "Alice Johnson",
                "email": "alice@example.com",
                "subject": "Cannot reset password",
                "category": "technical",
                "message": "I have been trying to reset my password for 30 minutes but I get no email."
            })

            assert response.status_code == 200
            data = response.json()
            assert "ticket_id" in data
            assert data["ticket_id"] is not None
            assert "5 minutes" in data["estimated_response_time"]

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Health endpoint should return all channels active."""
        from fastapi.testclient import TestClient
        from production.api.main import app

        with patch("production.api.main.kafka_producer") as mock_kafka:
            mock_kafka.start = AsyncMock()
            client = TestClient(app)
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "channels" in data

    @pytest.mark.asyncio
    async def test_cross_channel_customer_lookup(self):
        """Customer lookup should work by email."""
        from fastapi.testclient import TestClient
        from production.api.main import app

        with patch("production.database.queries.find_customer_by_email", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = {
                "id": "cust-123",
                "email": "bob@example.com",
                "name": "Bob Smith"
            }

            client = TestClient(app)
            response = client.get("/customers/lookup", params={"email": "bob@example.com"})
            assert response.status_code == 200
            assert response.json()["email"] == "bob@example.com"

    @pytest.mark.asyncio
    async def test_customer_not_found(self):
        """Non-existent customer should return 404."""
        from fastapi.testclient import TestClient
        from production.api.main import app

        with patch("production.database.queries.find_customer_by_email", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = None

            client = TestClient(app)
            response = client.get("/customers/lookup", params={"email": "notexist@example.com"})
            assert response.status_code == 404

    def test_customer_lookup_no_params(self):
        """Lookup without params should return 400."""
        from fastapi.testclient import TestClient
        from production.api.main import app

        client = TestClient(app)
        response = client.get("/customers/lookup")
        assert response.status_code == 400


class TestChannelMetrics:
    """Test channel-specific metrics endpoint."""

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self):
        """Metrics endpoint should return channel breakdown."""
        from fastapi.testclient import TestClient
        from production.api.main import app

        with patch("production.database.queries.get_channel_metrics", new_callable=AsyncMock) as mock_metrics:
            mock_metrics.return_value = {
                "email":    {"channel": "email",    "total_conversations": 10, "escalations": 2},
                "whatsapp": {"channel": "whatsapp", "total_conversations": 25, "escalations": 3},
                "web_form": {"channel": "web_form", "total_conversations": 15, "escalations": 1},
            }

            client = TestClient(app)
            response = client.get("/metrics/channels")
            assert response.status_code == 200
            data = response.json()
            assert "email" in data or "whatsapp" in data or "web_form" in data
