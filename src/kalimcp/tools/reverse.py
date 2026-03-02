"""Reverse engineering tool wrappers."""

from __future__ import annotations

from typing import Optional

from kalimcp.auth import AuthContext
from kalimcp.tools.tool_engine import exec_tool


async def reverse_objdump(target: str, extra_args: str = "-d", *, _auth: Optional[AuthContext] = None) -> str:
    """Disassemble a binary with objdump."""
    return await exec_tool("objdump", f"{extra_args} {target}", timeout=60, _auth=_auth)


async def reverse_strings(target: str, min_len: int = 4, *, _auth: Optional[AuthContext] = None) -> str:
    """Extract printable strings from a binary."""
    return await exec_tool("strings", f"-n {min_len} {target}", timeout=30, _auth=_auth)


async def reverse_file(target: str, *, _auth: Optional[AuthContext] = None) -> str:
    """Determine file type."""
    return await exec_tool("file", target, timeout=10, _auth=_auth)
