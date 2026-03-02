"""PTY Session — async pseudo-terminal with ring buffer output storage."""

from __future__ import annotations

import asyncio
import collections
import fcntl
import logging
import os
import pty
import re
import struct
import termios
import time
from typing import Optional

from kalimcp.terminal.ansi import clean_terminal_output

logger = logging.getLogger("kalimcp.pty_session")

# ---------------------------------------------------------------------------
# Ring buffer
# ---------------------------------------------------------------------------

DEFAULT_RING_SIZE = 10_000  # lines


class RingBuffer:
    """Thread-safe (asyncio-safe) ring buffer storing text lines."""

    def __init__(self, maxlen: int = DEFAULT_RING_SIZE):
        self._buf: collections.deque[str] = collections.deque(maxlen=maxlen)
        self._lock = asyncio.Lock()

    async def append(self, line: str) -> None:
        async with self._lock:
            self._buf.append(line)

    async def append_text(self, text: str) -> None:
        """Split *text* into lines and append each."""
        for line in text.splitlines():
            await self.append(line)

    async def get_recent(self, n: int = 50) -> list[str]:
        async with self._lock:
            items = list(self._buf)
        return items[-n:]

    async def get_all(self) -> list[str]:
        async with self._lock:
            return list(self._buf)

    @property
    def size(self) -> int:
        return len(self._buf)


# ---------------------------------------------------------------------------
# PTY Session
# ---------------------------------------------------------------------------


class PtySession:
    """Wraps a single PTY pseudo-terminal."""

    def __init__(
        self,
        session_id: str,
        name: str = "",
        shell: str = "/bin/bash",
        cols: int = 120,
        rows: int = 40,
    ):
        self.session_id = session_id
        self.name = name or session_id[:8]
        self.shell = shell
        self.cols = cols
        self.rows = rows

        self.created_at: float = time.time()
        self.last_active_at: float = time.time()

        self.buffer = RingBuffer()
        self._master_fd: Optional[int] = None
        self._pid: Optional[int] = None
        self._reader_task: Optional[asyncio.Task] = None
        self._alive = False

    async def start(self) -> None:
        """Fork a child process with a PTY."""
        pid, master_fd = pty.openpty()

        # Set terminal size
        winsize = struct.pack("HHHH", self.rows, self.cols, 0, 0)
        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)

        child_pid = os.fork()
        if child_pid == 0:
            # Child process
            os.close(master_fd)
            os.setsid()
            slave_fd = pty.slave_open(pid) if hasattr(pty, "slave_open") else os.open(os.ttyname(pid), os.O_RDWR)
            # Set slave as controlling terminal
            fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)
            os.dup2(slave_fd, 0)
            os.dup2(slave_fd, 1)
            os.dup2(slave_fd, 2)
            if slave_fd > 2:
                os.close(slave_fd)
            os.close(pid)
            os.execvp(self.shell, [self.shell])
        else:
            # Parent
            os.close(pid)
            self._master_fd = master_fd
            self._pid = child_pid
            self._alive = True

            # Make master non-blocking
            flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
            fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

            # Start background reader
            self._reader_task = asyncio.create_task(self._read_loop())

    async def _read_loop(self) -> None:
        """Continuously read from master_fd and store in ring buffer."""
        loop = asyncio.get_event_loop()
        while self._alive and self._master_fd is not None:
            try:
                data = await loop.run_in_executor(None, self._blocking_read)
                if data:
                    cleaned = clean_terminal_output(data)
                    await self.buffer.append_text(cleaned)
                    self.last_active_at = time.time()
                else:
                    await asyncio.sleep(0.05)
            except OSError:
                break
            except asyncio.CancelledError:
                break

    def _blocking_read(self) -> str:
        """Read from master fd (called in thread)."""
        try:
            data = os.read(self._master_fd, 4096)  # type: ignore[arg-type]
            return data.decode("utf-8", errors="replace")
        except (OSError, BlockingIOError):
            return ""

    async def write(self, data: str) -> None:
        """Write data to the PTY."""
        if self._master_fd is None:
            raise RuntimeError("Session not started")
        self.last_active_at = time.time()
        encoded = data.encode("utf-8")
        os.write(self._master_fd, encoded)

    async def wait_for(self, pattern: str, timeout: float = 30.0) -> str:
        """Wait until *pattern* (regex) appears in output, returning matched text."""
        regex = re.compile(pattern)
        start = time.time()
        while time.time() - start < timeout:
            recent = await self.buffer.get_recent(200)
            text = "\n".join(recent)
            m = regex.search(text)
            if m:
                return text
            await asyncio.sleep(0.2)
        return f"Timeout waiting for pattern '{pattern}' after {timeout}s"

    async def kill(self) -> None:
        """Terminate the PTY session."""
        self._alive = False
        if self._reader_task and not self._reader_task.done():
            self._reader_task.cancel()
        if self._pid:
            try:
                os.kill(self._pid, 9)
                os.waitpid(self._pid, os.WNOHANG)
            except (OSError, ChildProcessError):
                pass
        if self._master_fd is not None:
            try:
                os.close(self._master_fd)
            except OSError:
                pass
            self._master_fd = None

    @property
    def is_alive(self) -> bool:
        return self._alive
