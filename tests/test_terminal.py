"""Terminal module tests — ANSI cleaning, ring buffer."""

from __future__ import annotations

import asyncio

import pytest

from kalimcp.terminal.ansi import clean_terminal_output, strip_ansi


# ── ANSI strip ──────────────────────────────────────────────────────


class TestAnsiStrip:
    def test_colour_codes(self):
        text = "\x1b[31mERROR\x1b[0m: something happened"
        assert strip_ansi(text) == "ERROR: something happened"

    def test_cursor_movement(self):
        text = "\x1b[2J\x1b[H\x1b[1;1HHello World"
        assert strip_ansi(text) == "Hello World"

    def test_osc_sequences(self):
        text = "\x1b]0;title\x07Some output"
        assert strip_ansi(text) == "Some output"

    def test_preserves_newlines(self):
        text = "line1\nline2\n\x1b[32mline3\x1b[0m"
        result = strip_ansi(text)
        assert "line1\nline2\nline3" == result

    def test_clean_terminal_output(self):
        text = "\x1b[31mfoo\x1b[0m\n\n\n\n\n\nbar"
        result = clean_terminal_output(text)
        # Should collapse excessive blank lines
        assert result.count("\n\n\n") == 0
        assert "foo" in result
        assert "bar" in result

    def test_metasploit_style_output(self):
        text = "\x1b[4m\x1b[34mmsf6\x1b[0m > use exploit/multi/handler\n"
        result = strip_ansi(text)
        assert "msf6" in result
        assert "\x1b" not in result


# ── Ring buffer ─────────────────────────────────────────────────────


class TestRingBuffer:
    @pytest.mark.asyncio
    async def test_basic_append_and_read(self):
        from kalimcp.terminal.pty_session import RingBuffer

        buf = RingBuffer(maxlen=100)
        await buf.append("line1")
        await buf.append("line2")
        recent = await buf.get_recent(10)
        assert recent == ["line1", "line2"]

    @pytest.mark.asyncio
    async def test_overflow(self):
        from kalimcp.terminal.pty_session import RingBuffer

        buf = RingBuffer(maxlen=5)
        for i in range(10):
            await buf.append(f"line{i}")
        recent = await buf.get_all()
        assert len(recent) == 5
        assert recent[0] == "line5"
        assert recent[-1] == "line9"

    @pytest.mark.asyncio
    async def test_append_text(self):
        from kalimcp.terminal.pty_session import RingBuffer

        buf = RingBuffer(maxlen=100)
        await buf.append_text("a\nb\nc")
        recent = await buf.get_recent(10)
        assert recent == ["a", "b", "c"]
