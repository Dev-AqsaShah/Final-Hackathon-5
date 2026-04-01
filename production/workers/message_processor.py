"""
Unified Message Processor
Kafka consumer that processes messages from ALL channels through the FTE agent
"""

import asyncio
import logging
from datetime import datetime

from agents import Runner

from production.agent.customer_success_agent import customer_success_agent
from production.channels.gmail_handler import GmailHandler
from production.channels.whatsapp_handler import WhatsAppHandler
from production.database.queries import (
    get_or_create_customer,
    get_or_create_conversation,
    load_conversation_history,
    save_message,
    record_metric,
)
from production.workers.kafka_client import FTEKafkaProducer, FTEKafkaConsumer, TOPICS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class UnifiedMessageProcessor:
    """Process incoming messages from all channels through the FTE agent."""

    def __init__(self):
        self.gmail = GmailHandler()
        self.whatsapp = WhatsAppHandler()
        self.producer = FTEKafkaProducer()

    async def start(self):
        await self.producer.start()

        consumer = FTEKafkaConsumer(
            topics=[TOPICS["tickets_incoming"]],
            group_id="fte-message-processor"
        )
        await consumer.start()

        logger.info("Message processor started - listening for tickets...")
        await consumer.consume(self.process_message)

    async def process_message(self, topic: str, message: dict):
        """Process a single incoming message from any channel."""
        start_time = datetime.utcnow()

        try:
            channel = message.get("channel", "web_form")
            logger.info(f"Processing {channel} message from {message.get('customer_email') or message.get('customer_phone')}")

            # 1. Resolve or create customer
            customer_id = await get_or_create_customer(message)

            # 2. Get or create conversation
            conversation_id = await get_or_create_conversation(customer_id, channel)

            # 3. Save incoming message
            await save_message(
                conversation_id=conversation_id,
                channel=channel,
                direction="inbound",
                role="user",
                content=message["content"],
                channel_message_id=message.get("channel_message_id")
            )

            # 4. Load conversation history for context
            history = await load_conversation_history(conversation_id)

            # 5. Build context for agent
            context = {
                "customer_id": customer_id,
                "conversation_id": conversation_id,
                "channel": channel,
                "ticket_subject": message.get("subject", "Support Request"),
                "customer_email": message.get("customer_email"),
                "customer_phone": message.get("customer_phone"),
                "metadata": message.get("metadata", {})
            }

            # 6. Format input for agent
            agent_input = self._build_agent_input(message, context)

            # Append context to history
            history.append({"role": "user", "content": agent_input})

            # 7. Run the agent
            result = await Runner.run(
                customer_success_agent,
                input=history,
            )

            # 8. Calculate metrics
            latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # 9. Save agent response
            await save_message(
                conversation_id=conversation_id,
                channel=channel,
                direction="outbound",
                role="assistant",
                content=result.final_output,
                latency_ms=latency_ms,
            )

            # 10. Publish metrics
            await self.producer.publish(TOPICS["metrics"], {
                "event_type": "message_processed",
                "channel": channel,
                "latency_ms": latency_ms,
                "customer_id": customer_id,
            })

            logger.info(f"Processed {channel} message in {latency_ms}ms")

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            await self._handle_error(message, e)

    def _build_agent_input(self, message: dict, context: dict) -> str:
        """Build the input string for the agent with full context."""
        channel = message.get("channel", "web_form")
        subject = message.get("subject", "Support Request")
        content = message.get("content", "")
        customer_email = message.get("customer_email", "")
        customer_phone = message.get("customer_phone", "")
        customer_name = message.get("customer_name", "Customer")

        identifier = customer_email or customer_phone or "unknown"

        return (
            f"[Channel: {channel}] "
            f"[Customer: {customer_name} ({identifier})] "
            f"[CustomerID: {context['customer_id']}] "
            f"[ConversationID: {context['conversation_id']}] "
            f"[Subject: {subject}]\n\n"
            f"Message: {content}"
        )

    async def _handle_error(self, message: dict, error: Exception):
        """Send an apology when processing fails."""
        channel = message.get("channel", "web_form")
        apology = (
            "I'm sorry, I'm having trouble processing your request right now. "
            "A human agent will follow up with you shortly."
        )

        try:
            if channel == "email" and message.get("customer_email"):
                await self.gmail.send_reply(
                    to_email=message["customer_email"],
                    subject=message.get("subject", "Support Request"),
                    body=apology
                )
            elif channel == "whatsapp" and message.get("customer_phone"):
                await self.whatsapp.send_message(
                    to_phone=message["customer_phone"],
                    body=apology
                )
        except Exception as send_err:
            logger.error(f"Failed to send error response: {send_err}")

        # Publish to human escalation queue
        await self.producer.publish(TOPICS["escalations"], {
            "event_type": "processing_error",
            "channel": channel,
            "original_message": message,
            "error": str(error),
            "requires_human": True
        })


async def main():
    processor = UnifiedMessageProcessor()
    await processor.start()


if __name__ == "__main__":
    asyncio.run(main())
