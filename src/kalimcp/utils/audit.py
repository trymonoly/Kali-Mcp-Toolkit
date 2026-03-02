"""Audit logging — async JSON Lines writer with size-based rotation."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from kalimcp.config import get_config

logger = logging.getLogger("kalimcp.audit")

# ---------------------------------------------------------------------------
# Audit event model
# ---------------------------------------------------------------------------


class AuditEvent(BaseModel):
    """Structured audit event written as a single JSON line."""

    timestamp: float = Field(default_factory=time.time)
    api_key_name: str = ""
    action: str = ""
    module: str = ""  # tool / terminal / codeforge
    params_summary: str = ""
    result_summary: str = ""
    duration_ms: float = 0.0
    source_ip: str = ""
    success: bool = True
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Async writer
# ---------------------------------------------------------------------------


class AuditLogger:
    """Non-blocking audit logger that writes JSON Lines to disk."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[str] = asyncio.Queue(maxsize=10_000)
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the background writer task."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._writer_loop())

    async def stop(self) -> None:
        """Flush remaining events and stop."""
        if self._task and not self._task.done():
            await self._queue.join()
            self._task.cancel()

    async def log(self, event: AuditEvent) -> None:
        """Enqueue an audit event (non-blocking for the caller)."""
        line = event.model_dump_json()
        try:
            self._queue.put_nowait(line)
        except asyncio.QueueFull:
            logger.warning("Audit queue full — dropping event: %s", event.action)

    # convenience
    async def log_dict(self, **kwargs: Any) -> None:
        await self.log(AuditEvent(**kwargs))

    # ---- internal ----

    async def _writer_loop(self) -> None:
        cfg = get_config().logging
        path = Path(cfg.audit_log)
        path.parent.mkdir(parents=True, exist_ok=True)
        max_bytes = cfg.max_audit_size_mb * 1_048_576

        while True:
            try:
                line = await self._queue.get()
                # Rotate if needed
                if path.exists() and path.stat().st_size > max_bytes:
                    rotated = path.with_suffix(f".{int(time.time())}.log")
                    path.rename(rotated)
                async with _open_append(path) as f:
                    await f.write(line + "\n")
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Audit writer error")


class _open_append:
    """Thin async context-manager wrapper around blocking file I/O.

    Uses ``asyncio.to_thread`` so the event loop is never blocked.
    """

    def __init__(self, path: Path):
        self._path = path
        self._content: str = ""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        if self._content:
            await asyncio.to_thread(self._sync_write)

    async def write(self, data: str) -> None:
        self._content += data

    def _sync_write(self) -> None:
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(self._content)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
