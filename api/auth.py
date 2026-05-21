"""API key authentication middleware."""

import os
from typing import Optional

from fastapi import Request, HTTPException, status
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

_API_KEYS: Optional[set[str]] = None


def get_api_keys() -> set[str]:
    global _API_KEYS
    if _API_KEYS is None:
        raw = os.getenv("API_KEYS", "")
        _API_KEYS = {k.strip() for k in raw.split(",") if k.strip()}
    return _API_KEYS


async def verify_api_key(request: Request, api_key: Optional[str] = None) -> None:
    if not get_api_keys():
        return

    if api_key is None:
        api_key = request.headers.get("X-API-Key")

    if not api_key or api_key not in get_api_keys():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
