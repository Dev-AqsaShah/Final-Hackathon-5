"""
Database access functions for the Customer Success FTE
All DB operations go through these functions
"""

import os
import uuid
from datetime import datetime
from typing import Optional

import asyncpg

# ─────────────────────────────────────────────
# Database Connection Pool
# ─────────────────────────────────────────────

_pool: Optional[asyncpg.Pool] = None


async def get_db_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "password"),
            database=os.getenv("POSTGRES_DB", "fte_db"),
            min_size=2,
            max_size=10
        )
    return _pool


async def close_db_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


# ─────────────────────────────────────────────
# Customer Queries
# ─────────────────────────────────────────────

async def find_customer_by_email(email: str) -> Optional[dict]:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM customers WHERE email = $1", email.lower()
        )
        return dict(row) if row else None


async def find_customer_by_phone(phone: str) -> Optional[dict]:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT c.* FROM customers c
            JOIN customer_identifiers ci ON ci.customer_id = c.id
            WHERE ci.identifier_type = 'whatsapp' AND ci.identifier_value = $1
        """, phone)
        return dict(row) if row else None


async def create_customer(email: str = None, phone: str = None, name: str = None) -> str:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        customer_id = await conn.fetchval("""
            INSERT INTO customers (email, phone, name)
            VALUES ($1, $2, $3)
            RETURNING id
        """, email, phone, name)

        if phone:
            await conn.execute("""
                INSERT INTO customer_identifiers (customer_id, identifier_type, identifier_value)
                VALUES ($1, 'whatsapp', $2)
                ON CONFLICT (identifier_type, identifier_value) DO NOTHING
            """, customer_id, phone)

        return str(customer_id)


async def get_or_create_customer(message_data: dict) -> str:
    """Resolve or create customer from incoming message data."""
    email = message_data.get("customer_email", "").lower().strip() or None
    phone = message_data.get("customer_phone", "").strip() or None
    name = message_data.get("customer_name", "")

    if email:
        customer = await find_customer_by_email(email)
        if customer:
            return str(customer["id"])

    if phone:
        customer = await find_customer_by_phone(phone)
        if customer:
            return str(customer["id"])

    return await create_customer(email=email, phone=phone, name=name)


# ─────────────────────────────────────────────
# Conversation Queries
# ─────────────────────────────────────────────

async def get_or_create_conversation(customer_id: str, channel: str) -> str:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Check for active conversation within last 24 hours
        active = await conn.fetchrow("""
            SELECT id FROM conversations
            WHERE customer_id = $1
              AND status = 'active'
              AND started_at > NOW() - INTERVAL '24 hours'
            ORDER BY started_at DESC
            LIMIT 1
        """, uuid.UUID(customer_id))

        if active:
            return str(active["id"])

        conversation_id = await conn.fetchval("""
            INSERT INTO conversations (customer_id, initial_channel, status)
            VALUES ($1, $2, 'active')
            RETURNING id
        """, uuid.UUID(customer_id), channel)

        return str(conversation_id)


async def load_conversation_history(conversation_id: str) -> list[dict]:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT role, content, channel, created_at
            FROM messages
            WHERE conversation_id = $1
            ORDER BY created_at ASC
        """, uuid.UUID(conversation_id))

        return [
            {"role": r["role"], "content": r["content"]}
            for r in rows
            if r["role"] in ("user", "assistant")
        ]


# ─────────────────────────────────────────────
# Ticket Queries
# ─────────────────────────────────────────────

async def create_ticket(
    customer_id: str,
    conversation_id: str,
    channel: str,
    subject: str = "Support Request",
    category: str = "general",
    priority: str = "medium"
) -> str:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        ticket_id = await conn.fetchval("""
            INSERT INTO tickets (customer_id, conversation_id, source_channel, subject, category, priority, status)
            VALUES ($1, $2, $3, $4, $5, $6, 'open')
            RETURNING id
        """, uuid.UUID(customer_id), uuid.UUID(conversation_id), channel, subject, category, priority)

        return str(ticket_id)


async def get_ticket(ticket_id: str) -> Optional[dict]:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM tickets WHERE id = $1", uuid.UUID(ticket_id)
        )
        return dict(row) if row else None


async def update_ticket_status(ticket_id: str, status: str, notes: str = None):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE tickets
            SET status = $1,
                resolution_notes = COALESCE($2, resolution_notes),
                resolved_at = CASE WHEN $1 = 'resolved' THEN NOW() ELSE resolved_at END,
                updated_at = NOW()
            WHERE id = $3
        """, status, notes, uuid.UUID(ticket_id))


async def escalate_ticket(ticket_id: str, reason: str, team: str, urgency: str = "normal"):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("""
                UPDATE tickets
                SET status = 'escalated',
                    escalation_reason = $1,
                    escalation_team = $2,
                    escalated_at = NOW(),
                    updated_at = NOW()
                WHERE id = $3
            """, reason, team, uuid.UUID(ticket_id))

            await conn.execute("""
                INSERT INTO escalations (ticket_id, reason, team, urgency)
                VALUES ($1, $2, $3, $4)
            """, uuid.UUID(ticket_id), reason, team, urgency)


# ─────────────────────────────────────────────
# Message Queries
# ─────────────────────────────────────────────

async def save_message(
    conversation_id: str,
    channel: str,
    direction: str,
    role: str,
    content: str,
    tokens_used: int = None,
    latency_ms: int = None,
    tool_calls: list = None,
    channel_message_id: str = None,
    delivery_status: str = "sent"
) -> str:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        msg_id = await conn.fetchval("""
            INSERT INTO messages
                (conversation_id, channel, direction, role, content,
                 tokens_used, latency_ms, tool_calls, channel_message_id, delivery_status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9, $10)
            RETURNING id
        """,
            uuid.UUID(conversation_id), channel, direction, role, content,
            tokens_used, latency_ms,
            __import__("json").dumps(tool_calls or []),
            channel_message_id, delivery_status
        )
        return str(msg_id)


# ─────────────────────────────────────────────
# Knowledge Base Queries
# ─────────────────────────────────────────────

async def search_knowledge_base(query_embedding: list[float], max_results: int = 5, category: str = None) -> list[dict]:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        if category:
            rows = await conn.fetch("""
                SELECT title, content, category,
                       1 - (embedding <=> $1::vector) as similarity
                FROM knowledge_base
                WHERE category = $2
                ORDER BY embedding <=> $1::vector
                LIMIT $3
            """, query_embedding, category, max_results)
        else:
            rows = await conn.fetch("""
                SELECT title, content, category,
                       1 - (embedding <=> $1::vector) as similarity
                FROM knowledge_base
                ORDER BY embedding <=> $1::vector
                LIMIT $2
            """, query_embedding, max_results)

        return [dict(row) for row in rows]


async def get_customer_history(customer_id: str) -> list[dict]:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT c.initial_channel, c.started_at, c.status,
                   m.content, m.role, m.channel, m.created_at
            FROM conversations c
            JOIN messages m ON m.conversation_id = c.id
            WHERE c.customer_id = $1
            ORDER BY m.created_at DESC
            LIMIT 20
        """, uuid.UUID(customer_id))
        return [dict(row) for row in rows]


# ─────────────────────────────────────────────
# Metrics Queries
# ─────────────────────────────────────────────

async def record_metric(name: str, value: float, channel: str = None, dimensions: dict = None):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO agent_metrics (metric_name, metric_value, channel, dimensions)
            VALUES ($1, $2, $3, $4::jsonb)
        """, name, value, channel, __import__("json").dumps(dimensions or {}))


async def get_channel_metrics() -> dict:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                initial_channel as channel,
                COUNT(*) as total_conversations,
                AVG(sentiment_score) as avg_sentiment,
                COUNT(*) FILTER (WHERE status = 'escalated') as escalations,
                COUNT(*) FILTER (WHERE status = 'resolved') as resolved
            FROM conversations
            WHERE started_at > NOW() - INTERVAL '24 hours'
            GROUP BY initial_channel
        """)
        return {row["channel"]: dict(row) for row in rows}
