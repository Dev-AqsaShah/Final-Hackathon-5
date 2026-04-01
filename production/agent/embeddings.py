"""
Embedding generation for semantic search in knowledge base
Uses OpenAI embeddings (still needed for pgvector search)
If you want fully Anthropic-only, replace with any other embedding provider
"""

import os
import openai

_client = None


def _get_client():
    global _client
    if _client is None:
        # Use OpenAI for embeddings (Anthropic doesn't have an embeddings API)
        # Alternatively use a free model like sentence-transformers locally
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        _client = openai.AsyncOpenAI(api_key=api_key)
    return _client


async def generate_embedding(text: str) -> list[float]:
    """Generate embedding vector for semantic search."""
    client = _get_client()
    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding
