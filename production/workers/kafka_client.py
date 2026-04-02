"""
Kafka Client for multi-channel event streaming
"""

import json
import logging
import os
from datetime import datetime

try:
    from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logging.warning("aiokafka not installed - Kafka disabled, running in direct mode")

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../../production/.env"))
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:9092")

# Topic definitions for all channels
TOPICS = {
    # Incoming tickets from all channels (unified queue)
    "tickets_incoming": "fte.tickets.incoming",

    # Channel-specific inbound
    "email_inbound": "fte.channels.email.inbound",
    "whatsapp_inbound": "fte.channels.whatsapp.inbound",
    "webform_inbound": "fte.channels.webform.inbound",

    # Channel-specific outbound
    "email_outbound": "fte.channels.email.outbound",
    "whatsapp_outbound": "fte.channels.whatsapp.outbound",

    # Escalations
    "escalations": "fte.escalations",

    # Metrics and monitoring
    "metrics": "fte.metrics",

    # Dead letter queue for failed processing
    "dlq": "fte.dlq"
}


class FTEKafkaProducer:
    def __init__(self):
        self.producer = None

    async def start(self):
        if not KAFKA_AVAILABLE:
            logger.info("Kafka not available - running in mock mode")
            return
        self.producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8")
        )
        await self.producer.start()
        logger.info("Kafka producer started")

    async def stop(self):
        if self.producer:
            await self.producer.stop()

    async def publish(self, topic: str, event: dict):
        if not KAFKA_AVAILABLE or not self.producer:
            logger.info(f"[MOCK KAFKA] {topic}: {list(event.keys())}")
            return
        event["timestamp"] = datetime.utcnow().isoformat()
        await self.producer.send_and_wait(topic, event)
        logger.debug(f"Published to {topic}: {list(event.keys())}")


class FTEKafkaConsumer:
    def __init__(self, topics: list[str], group_id: str):
        self.consumer = AIOKafkaConsumer(
            *topics,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=group_id,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="earliest"
        )

    async def start(self):
        await self.consumer.start()
        logger.info(f"Kafka consumer started for group: {self.consumer._group_id}")

    async def stop(self):
        await self.consumer.stop()

    async def consume(self, handler):
        """Consume messages and call handler for each one."""
        async for msg in self.consumer:
            try:
                await handler(msg.topic, msg.value)
            except Exception as e:
                logger.error(f"Error processing message from {msg.topic}: {e}")
