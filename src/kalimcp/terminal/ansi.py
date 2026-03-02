"""ANSI escape code cleaner — strips colours, cursor movement, screen control."""

from __future__ import annotations

import re

# CSI (Control Sequence Introducer) sequences:  ESC [ ... final_byte
_CSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")

# OSC (Operating System Command):  ESC ] ... BEL/ST
_OSC_RE = re.compile(r"\x1b\].*?(?:\x07|\x1b\\)")

# Single-character escape sequences:  ESC (char)
_ESC_SINGLE = re.compile(r"\x1b[()][A-Za-z0-9]")

# Other escape sequences:  ESC followed by one char
_ESC_OTHER = re.compile(r"\x1b[^[\]()]")

# Raw control characters (BEL, BS, etc.) except \n \r \t
_CTRL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def strip_ansi(text: str) -> str:
    """Remove all ANSI escape sequences and stray control characters.

    Preserves meaningful whitespace (newlines, tabs).
    """
    text = _CSI_RE.sub("", text)
    text = _OSC_RE.sub("", text)
    text = _ESC_SINGLE.sub("", text)
    text = _ESC_OTHER.sub("", text)
    text = _CTRL_CHARS.sub("", text)
    return text


def clean_terminal_output(text: str) -> str:
    """Strip ANSI codes and normalise whitespace for AI consumption."""
    text = strip_ansi(text)
    # Collapse runs of blank lines
    lines = text.splitlines()
    cleaned: list[str] = []
    blank_run = 0
    for line in lines:
        if not line.strip():
            blank_run += 1
            if blank_run <= 2:
                cleaned.append("")
        else:
            blank_run = 0
            cleaned.append(line)
    return "\n".join(cleaned)
