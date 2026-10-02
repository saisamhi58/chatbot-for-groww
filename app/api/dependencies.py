"""FastAPI dependencies."""

from fastapi import Header, Request
from app.core.security import verify_api_key, check_rate_limit
from app.models.database import APIKey


async def get_current_api_key(x_api_key: str = Header(None)) -> APIKey:
    """Dependency to validate API key from header."""
    api_key = verify_api_key(x_api_key)
    check_rate_limit(x_api_key, api_key.rate_limit)
    return api_key
