"""
AI Client setup.
Initialises boto3 for Titan Embeddings v2 (AWS) and httpx for Nemotron-3 (OpenRouter).
"""

import json
import asyncio
import logging

import boto3
from botocore.config import Config
import httpx
from functools import lru_cache
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import get_settings

logger = logging.getLogger(__name__)

# Model IDs
TITAN_EMBED_MODEL = "amazon.titan-embed-text-v2:0"
CHAT_MODEL = "anthropic/claude-3.7-sonnet"


@lru_cache()
def get_bedrock_runtime():
    """Cached boto3 Bedrock Runtime client."""
    settings = get_settings()
    return boto3.client(
        "bedrock-runtime",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id or None,
        aws_secret_access_key=settings.aws_secret_access_key or None,
        config=Config(
            retries={"max_attempts": 3, "mode": "adaptive"},
            connect_timeout=10,
            read_timeout=60,
        ),
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def _invoke_titan_embed_sync(text: str) -> list[float]:
    """Synchronous Titan Embeddings v2 call (runs in thread pool)."""
    client = get_bedrock_runtime()
    body = json.dumps({
        "inputText": text[:8000],   # Titan v2 max context
        "dimensions": 1024,
        "normalize": True,
    })
    response = client.invoke_model(
        modelId=TITAN_EMBED_MODEL,
        body=body,
        contentType="application/json",
        accept="application/json",
    )
    result = json.loads(response["body"].read())
    return result["embedding"]


async def embed_text(text: str) -> list[float]:
    """
    Async wrapper: calls Titan v2 in a thread pool so we don't block the FastAPI event loop.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _invoke_titan_embed_sync, text)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(httpx.HTTPStatusError),
    reraise=True,
)
async def call_claude(system_prompt: str, user_message: str, max_tokens: int = 2048) -> str:
    """
    Async wrapper for OpenRouter Chat API (Nemotron 3).
    """
    settings = get_settings()
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "DevLens",
    }
    
    payload = {
        "model": CHAT_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "max_tokens": max_tokens,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        
    return data["choices"][0]["message"]["content"]
