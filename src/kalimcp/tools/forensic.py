"""Forensics tool wrappers."""

from __future__ import annotations

from typing import Optional

from kalimcp.auth import AuthContext
from kalimcp.tools.tool_engine import exec_tool


async def forensic_binwalk(target: str, extra_args: str = "", *, _auth: Optional[AuthContext] = None) -> str:
    """Analyse firmware images with binwalk."""
    return await exec_tool("binwalk", f"{extra_args} {target}", timeout=300, _auth=_auth)


async def forensic_exiftool(target: str, *, _auth: Optional[AuthContext] = None) -> str:
    """Read file metadata with exiftool."""
    return await exec_tool("exiftool", target, timeout=30, _auth=_auth)


async def forensic_steghide(target: str, passphrase: str = "", *, _auth: Optional[AuthContext] = None) -> str:
    """Extract hidden data with steghide."""
    args = f"extract -sf {target} -f"
    if passphrase:
        args += f" -p {passphrase}"
    return await exec_tool("steghide", args, timeout=60, _auth=_auth)


async def forensic_foremost(target: str, output_dir: str = "foremost_out", *, _auth: Optional[AuthContext] = None) -> str:
    """Carve files from disk images with foremost."""
    return await exec_tool("foremost", f"-i {target} -o {output_dir}", timeout=600, _auth=_auth)
