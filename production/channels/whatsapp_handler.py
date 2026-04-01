"""
WhatsApp Channel Handler via Twilio
Handles incoming WhatsApp messages and sends replies
"""

import logging
import os
from datetime import datetime

from fastapi import Request

logger = logging.getLogger(__name__)


class WhatsAppHandler:
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER")  # e.g. 'whatsapp:+14155238886'

        if self.account_sid and self.auth_token:
            from twilio.rest import Client
            from twilio.request_validator import RequestValidator
            self.client = Client(self.account_sid, self.auth_token)
            self.validator = RequestValidator(self.auth_token)
        else:
            logger.warning("Twilio credentials not set - WhatsApp handler in mock mode")
            self.client = None
            self.validator = None

    async def validate_webhook(self, request: Request) -> bool:
        """Validate incoming Twilio webhook signature."""
        if not self.validator:
            return True  # Allow in mock mode

        signature = request.headers.get("X-Twilio-Signature", "")
        url = str(request.url)
        form_data = await request.form()
        params = dict(form_data)

        return self.validator.validate(url, params, signature)

    async def process_webhook(self, form_data: dict) -> dict:
        """Process incoming WhatsApp message from Twilio webhook."""
        return {
            "channel": "whatsapp",
            "channel_message_id": form_data.get("MessageSid"),
            "customer_phone": form_data.get("From", "").replace("whatsapp:", ""),
            "customer_name": form_data.get("ProfileName", ""),
            "content": form_data.get("Body", ""),
            "received_at": datetime.utcnow().isoformat(),
            "metadata": {
                "num_media": form_data.get("NumMedia", "0"),
                "wa_id": form_data.get("WaId"),
                "status": form_data.get("SmsStatus")
            }
        }

    async def send_message(self, to_phone: str, body: str) -> dict:
        """Send WhatsApp message via Twilio."""
        if not self.client:
            logger.info(f"[MOCK] WhatsApp to {to_phone}: {body[:100]}")
            return {"channel_message_id": "mock_sid", "delivery_status": "sent"}

        try:
            if not to_phone.startswith("whatsapp:"):
                to_phone = f"whatsapp:{to_phone}"

            # Split if too long
            messages_to_send = self.format_response(body)

            last_result = None
            for msg_body in messages_to_send:
                message = self.client.messages.create(
                    body=msg_body,
                    from_=self.whatsapp_number,
                    to=to_phone
                )
                last_result = {
                    "channel_message_id": message.sid,
                    "delivery_status": message.status
                }

            return last_result or {"channel_message_id": None, "delivery_status": "failed"}

        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {e}")
            return {"channel_message_id": None, "delivery_status": "failed"}

    def format_response(self, response: str, max_length: int = 1600) -> list[str]:
        """Format and split response for WhatsApp (max 1600 chars per message)."""
        if len(response) <= max_length:
            return [response]

        messages = []
        while response:
            if len(response) <= max_length:
                messages.append(response)
                break

            break_point = response.rfind(". ", 0, max_length)
            if break_point == -1:
                break_point = response.rfind(" ", 0, max_length)
            if break_point == -1:
                break_point = max_length

            messages.append(response[:break_point + 1].strip())
            response = response[break_point + 1:].strip()

        return messages
