"""Cryptography tool wrappers."""

from __future__ import annotations

from typing import Optional

from kalimcp.auth import AuthContext
from kalimcp.tools.tool_engine import exec_tool


async def crypto_hashid(hash_value: str, *, _auth: Optional[AuthContext] = None) -> str:
    """Identify hash type with hashid."""
    return await exec_tool("hashid", hash_value, timeout=15, _auth=_auth)
