"""
Gmail Channel Handler
Handles incoming emails via Gmail API + Pub/Sub and sends replies
"""

import base64
import json
import logging
import os
import re
from datetime import datetime
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


class GmailHandler:
    def __init__(self):
        creds_json = os.getenv("GMAIL_CREDENTIALS")
        if creds_json:
            import json as _json
            creds_data = _json.loads(creds_json)
            self.credentials = Credentials.from_authorized_user_info(creds_data)
            self.service = build("gmail", "v1", credentials=self.credentials)
        else:
            logger.warning("GMAIL_CREDENTIALS not set - Gmail handler in mock mode")
            self.service = None

    async def setup_push_notifications(self, topic_name: str) -> dict:
        """Set up Gmail push notifications via Google Cloud Pub/Sub."""
        if not self.service:
            return {"mock": True}
        request = {
            "labelIds": ["INBOX"],
            "topicName": topic_name,
            "labelFilterAction": "include"
        }
        return self.service.users().watch(userId="me", body=request).execute()

    async def process_notification(self, pubsub_message: dict) -> list[dict]:
        """Process incoming Pub/Sub notification from Gmail."""
        if not self.service:
            return []

        history_id = pubsub_message.get("historyId")

        history = self.service.users().history().list(
            userId="me",
            startHistoryId=history_id,
            historyTypes=["messageAdded"]
        ).execute()

        messages = []
        for record in history.get("history", []):
            for msg_added in record.get("messagesAdded", []):
                msg_id = msg_added["message"]["id"]
                message = await self.get_message(msg_id)
                if message:
                    messages.append(message)

        return messages

    async def get_message(self, message_id: str) -> dict | None:
        """Fetch and parse a Gmail message."""
        if not self.service:
            return None
        try:
            msg = self.service.users().messages().get(
                userId="me",
                id=message_id,
                format="full"
            ).execute()

            headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
            body = self._extract_body(msg["payload"])

            return {
                "channel": "email",
                "channel_message_id": message_id,
                "customer_email": self._extract_email(headers.get("From", "")),
                "customer_name": self._extract_name(headers.get("From", "")),
                "subject": headers.get("Subject", ""),
                "content": body,
                "received_at": datetime.utcnow().isoformat(),
                "thread_id": msg.get("threadId"),
                "metadata": {
                    "headers": headers,
                    "labels": msg.get("labelIds", [])
                }
            }
        except Exception as e:
            logger.error(f"Failed to get Gmail message {message_id}: {e}")
            return None

    async def send_reply(
        self,
        to_email: str,
        subject: str,
        body: str,
        thread_id: str = None
    ) -> dict:
        """Send email reply via Gmail API."""
        if not self.service:
            logger.info(f"[MOCK] Email to {to_email}: {body[:100]}")
            return {"channel_message_id": "mock_id", "delivery_status": "sent"}

        try:
            message = MIMEText(body)
            message["to"] = to_email
            message["subject"] = f"Re: {subject}" if not subject.startswith("Re:") else subject

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

            send_request = {"raw": raw}
            if thread_id:
                send_request["threadId"] = thread_id

            result = self.service.users().messages().send(
                userId="me",
                body=send_request
            ).execute()

            return {
                "channel_message_id": result["id"],
                "delivery_status": "sent"
            }
        except Exception as e:
            logger.error(f"Failed to send Gmail reply: {e}")
            return {"channel_message_id": None, "delivery_status": "failed"}

    def _extract_body(self, payload: dict) -> str:
        if "body" in payload and payload["body"].get("data"):
            return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
        return ""

    def _extract_email(self, from_header: str) -> str:
        match = re.search(r"<(.+?)>", from_header)
        return match.group(1) if match else from_header

    def _extract_name(self, from_header: str) -> str:
        match = re.search(r"^(.+?)\s*<", from_header)
        return match.group(1).strip().strip('"') if match else ""
