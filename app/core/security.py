"""Security utilities: auth, rate limiting, input sanitization."""

import hashlib
import re
from datetime import datetime, timedelta
from typing import Optional

from app.models.database import APIKey, SessionLocal
from app.core.exceptions import AuthenticationError, RateLimitError


# --- API Key Authentication ---

def hash_api_key(key: str) -> str:
    """Hash an API key using SHA-256."""
    return hashlib.sha256(key.encode()).hexdigest()


def verify_api_key(api_key: str) -> Optional[APIKey]:
    """Verify an API key against the database."""
    if not api_key:
        raise AuthenticationError("API key is required")

    key_hash = hash_api_key(api_key)
    db = SessionLocal()
    try:
        db_key = db.query(APIKey).filter(
            APIKey.key_hash == key_hash,
            APIKey.is_active == True,
        ).first()

        if not db_key:
            raise AuthenticationError("Invalid API key")

        if db_key.expires_at and db_key.expires_at < datetime.utcnow():
            raise AuthenticationError("API key has expired")

        return db_key
    finally:
        db.close()


# --- Rate Limiting (simple in-memory, use Redis in production) ---

_rate_limit_store: dict[str, list[datetime]] = {}


def check_rate_limit(api_key: str, rpm: int = 60):
    """Check if the request is within rate limits."""
    now = datetime.utcnow()
    window_start = now - timedelta(minutes=1)

    if api_key not in _rate_limit_store:
        _rate_limit_store[api_key] = []

    # Remove old entries
    _rate_limit_store[api_key] = [
        t for t in _rate_limit_store[api_key] if t > window_start
    ]

    if len(_rate_limit_store[api_key]) >= rpm:
        raise RateLimitError(f"Rate limit exceeded: {rpm} requests per minute")

    _rate_limit_store[api_key].append(now)


# --- Input Sanitization ---

PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+(all\s+)?prior\s+instructions",
    r"disregard\s+(all\s+)?previous",
    r"forget\s+(all\s+)?previous",
    r"system\s*:\s*",
    r"assistant\s*:\s*",
    r"human\s*:\s*",
    r"<\s*system\s*>",
    r"<\s*/\s*system\s*>",
    r"\[INST\]",
    r"\[/INST\]",
    r"<<SYS>>",
    r"<</SYS>>",
]


def sanitize_input(text: str) -> str:
    """Remove potential prompt injection patterns from user input."""
    sanitized = text
    for pattern in PROMPT_INJECTION_PATTERNS:
        sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE)
    return sanitized.strip()


def validate_query(query: str) -> str:
    """Validate and sanitize a user query."""
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")
    if len(query) > 2000:
        raise ValueError("Query exceeds maximum length of 2000 characters")
    return sanitize_input(query)
