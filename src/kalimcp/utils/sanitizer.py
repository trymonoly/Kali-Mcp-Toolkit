"""Input sanitisation — whitelist enforcement, command injection defense, path traversal prevention."""

from __future__ import annotations

import os
import re
import shlex
from pathlib import Path

from kalimcp.config import get_config
from kalimcp.tools import get_catalog

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SanitisationError(Exception):
    """Raised when an input fails security checks."""

    def __init__(self, message: str, code: str = "sanitisation_error"):
        super().__init__(message)
        self.code = code


# ---------------------------------------------------------------------------
# Tool whitelist
# ---------------------------------------------------------------------------


def validate_tool_name(tool_name: str) -> None:
    """Ensure *tool_name* exists in the catalog and is allowed."""
    catalog = get_catalog()
    tool = catalog.get_tool(tool_name)
    if tool is None:
        raise SanitisationError(
            f"Tool '{tool_name}' is not registered in the catalog. "
            "Use list_kali_tools() to see available tools.",
            code="tool_not_found",
        )
    if not tool.allowed:
        raise SanitisationError(
            f"Tool '{tool_name}' is currently disabled in the catalog.",
            code="tool_disabled",
        )


# ---------------------------------------------------------------------------
# Dangerous command patterns
# ---------------------------------------------------------------------------

_DANGEROUS_PATTERNS: list[re.Pattern] = [
    re.compile(r"rm\s+(-\w*\s+)*-\w*r\w*\s+/"),   # rm -rf /
    re.compile(r"mkfs"),
    re.compile(r"dd\s+if=/dev/zero"),
    re.compile(r":\(\)\s*\{.*\|.*&\s*\}\s*;\s*:"),  # fork bomb
    re.compile(r">\s*/dev/sd[a-z]"),                  # overwrite disk
    re.compile(r"chmod\s+(-\w+\s+)*777\s+/"),         # chmod 777 /
    re.compile(r"wget\s+.*\|\s*sh"),                   # wget | sh
    re.compile(r"curl\s+.*\|\s*sh"),                   # curl | sh
    re.compile(r"mv\s+/"),                             # mv /
]

_SHELL_META_CHARS = re.compile(r"[;&|`$\(\)\{\}<>]")


def validate_arguments(arguments: str) -> list[str]:
    """Sanitise *arguments* string and return a safe token list.

    1. Reject if it matches any dangerous pattern.
    2. Reject shell meta-characters that could enable injection.
    3. Enforce max length.
    4. Split into tokens via ``shlex.split`` (no ``shell=True``).

    Returns a list of argument tokens safe for ``subprocess`` exec mode.
    """
    cfg = get_config().security

    # Length check
    if len(arguments) > cfg.max_argument_length:
        raise SanitisationError(
            f"Argument string exceeds maximum length ({cfg.max_argument_length}).",
            code="argument_too_long",
        )

    # Blocked commands from config
    lower = arguments.lower()
    for blocked in cfg.blocked_commands:
        if blocked.lower() in lower:
            raise SanitisationError(
                f"Blocked command pattern detected: '{blocked}'",
                code="blocked_command",
            )

    # Regex-based dangerous patterns
    for pat in _DANGEROUS_PATTERNS:
        if pat.search(arguments):
            raise SanitisationError(
                f"Dangerous command pattern detected (matched: {pat.pattern}).",
                code="dangerous_pattern",
            )

    # Shell metacharacter injection
    if _SHELL_META_CHARS.search(arguments):
        raise SanitisationError(
            "Shell metacharacters (;, &, |, `, $, etc.) are not allowed in arguments. "
            "Compose commands using structured tool parameters instead.",
            code="shell_injection",
        )

    # Parse tokens
    try:
        tokens = shlex.split(arguments)
    except ValueError as e:
        raise SanitisationError(f"Malformed argument string: {e}", code="parse_error")

    return tokens


# ---------------------------------------------------------------------------
# Path traversal prevention
# ---------------------------------------------------------------------------


def validate_workspace_path(file_path: str) -> Path:
    """Resolve *file_path* and ensure it stays inside the workspace root.

    Handles ``../`` sequences and symbolic links (``realpath``).
    """
    cfg = get_config().workspace
    root = Path(cfg.root).resolve()

    target = (root / file_path).resolve()
    # Resolve symlinks
    try:
        real_target = target.resolve(strict=False)
    except OSError:
        real_target = target

    if not str(real_target).startswith(str(root)):
        raise SanitisationError(
            f"Path traversal detected — resolved path '{real_target}' is outside workspace root '{root}'.",
            code="path_traversal",
        )

    return real_target


def validate_package_name(name: str) -> None:
    """Reject package names that look like shell injection attempts."""
    if not re.match(r"^[a-zA-Z0-9_\-\.]+[a-zA-Z0-9_\-\.>=<,\[\]]*$", name):
        raise SanitisationError(
            f"Invalid package name: '{name}'. Only alphanumerics, hyphens, underscores, and dots are allowed.",
            code="invalid_package_name",
        )
