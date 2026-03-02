"""Async process executor — timeout, concurrency semaphore, output limits."""

from __future__ import annotations

import asyncio
import logging
import signal
import time
from dataclasses import dataclass, field
from typing import Optional

from kalimcp.config import get_config

logger = logging.getLogger("kalimcp.process")

# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------


@dataclass
class ProcessResult:
    exit_code: int = -1
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    truncated: bool = False
    duration_ms: float = 0.0


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------


class ProcessExecutor:
    """Manages async subprocess execution with resource controls."""

    def __init__(self) -> None:
        self._semaphore: Optional[asyncio.Semaphore] = None

    @property
    def semaphore(self) -> asyncio.Semaphore:
        if self._semaphore is None:
            cfg = get_config().security
            self._semaphore = asyncio.Semaphore(cfg.max_concurrent_processes)
        return self._semaphore

    async def execute(
        self,
        cmd: list[str],
        *,
        timeout: Optional[int] = None,
        stdin_data: Optional[str] = None,
        cwd: Optional[str] = None,
    ) -> ProcessResult:
        """Run *cmd* as an async subprocess.

        * Concurrency is bounded by a semaphore.
        * ``SIGTERM → wait(5s) → SIGKILL`` on timeout.
        * stdout/stderr are capped at ``max_output_bytes``.
        """
        cfg = get_config().security
        timeout = timeout or cfg.command_timeout
        max_bytes = cfg.max_output_bytes

        acquired = self.semaphore.locked()
        try:
            # Try to acquire within 5 s — otherwise reject
            try:
                await asyncio.wait_for(self.semaphore.acquire(), timeout=5)
            except asyncio.TimeoutError:
                return ProcessResult(
                    exit_code=-1,
                    stderr="Too many concurrent processes. Please retry later.",
                )

            start = time.monotonic()
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    stdin=asyncio.subprocess.PIPE if stdin_data else asyncio.subprocess.DEVNULL,
                    cwd=cwd,
                )
            except FileNotFoundError:
                return ProcessResult(exit_code=127, stderr=f"Command not found: {cmd[0]}")
            except PermissionError:
                return ProcessResult(exit_code=126, stderr=f"Permission denied: {cmd[0]}")

            result = ProcessResult()
            try:
                raw_stdout, raw_stderr = await asyncio.wait_for(
                    proc.communicate(input=stdin_data.encode() if stdin_data else None),
                    timeout=timeout,
                )
                result.exit_code = proc.returncode or 0
            except asyncio.TimeoutError:
                result.timed_out = True
                result.exit_code = -1
                await _kill_process(proc)
                # Collect whatever output we already have
                raw_stdout = b""
                raw_stderr = f"Process timed out after {timeout}s and was killed.".encode()

            # Truncate output
            result.stdout, trunc_out = _truncate(raw_stdout, max_bytes)
            result.stderr, trunc_err = _truncate(raw_stderr, max_bytes)
            result.truncated = trunc_out or trunc_err
            result.duration_ms = (time.monotonic() - start) * 1000
            return result
        finally:
            self.semaphore.release()


async def _kill_process(proc: asyncio.subprocess.Process) -> None:
    """SIGTERM → wait 5 s → SIGKILL."""
    try:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
    except ProcessLookupError:
        pass


def _truncate(data: bytes, limit: int) -> tuple[str, bool]:
    """Decode and truncate, returning (text, was_truncated)."""
    text = data.decode("utf-8", errors="replace")
    if len(data) > limit:
        text = text[: limit] + f"\n\n... [truncated — output exceeded {limit} bytes]"
        return text, True
    return text, False


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_executor: Optional[ProcessExecutor] = None


def get_executor() -> ProcessExecutor:
    global _executor
    if _executor is None:
        _executor = ProcessExecutor()
    return _executor
