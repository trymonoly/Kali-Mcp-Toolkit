"""Terminal Manager — multi-session lifecycle, timeout reaper."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Optional

from kalimcp.config import get_config
from kalimcp.terminal.pty_session import PtySession
from kalimcp.utils.audit import AuditEvent, get_audit_logger

logger = logging.getLogger("kalimcp.terminal.manager")


class TerminalManager:
    """Manages multiple PTY sessions with limits and auto-reaping."""

    def __init__(self) -> None:
        self._sessions: dict[str, PtySession] = {}
        self._reaper_task: Optional[asyncio.Task] = None

    # ----- lifecycle -----

    async def create(
        self,
        name: str = "",
        shell: str = "/bin/bash",
        cols: int = 120,
        rows: int = 40,
    ) -> str:
        """Create a new PTY session. Returns JSON with session info."""
        cfg = get_config().security
        if len(self._sessions) >= cfg.max_sessions:
            return json.dumps({"error": f"Maximum sessions ({cfg.max_sessions}) reached. Kill an existing session first."})

        session_id = uuid.uuid4().hex[:12]
        session = PtySession(session_id=session_id, name=name, shell=shell, cols=cols, rows=rows)
        await session.start()
        self._sessions[session_id] = session

        # Ensure reaper is running
        self._ensure_reaper()

        await get_audit_logger().log(AuditEvent(
            action="terminal_create",
            module="terminal",
            params_summary=f"id={session_id} name={name} shell={shell}",
        ))

        return json.dumps({
            "session_id": session_id,
            "name": session.name,
            "shell": shell,
            "cols": cols,
            "rows": rows,
        })

    async def kill(self, session_id: str) -> str:
        session = self._sessions.pop(session_id, None)
        if session is None:
            return json.dumps({"error": f"Session '{session_id}' not found."})
        await session.kill()

        await get_audit_logger().log(AuditEvent(
            action="terminal_kill",
            module="terminal",
            params_summary=f"id={session_id}",
        ))
        return json.dumps({"status": "killed", "session_id": session_id})

    async def list_sessions(self) -> str:
        sessions = []
        for sid, s in self._sessions.items():
            sessions.append({
                "session_id": sid,
                "name": s.name,
                "shell": s.shell,
                "created_at": s.created_at,
                "last_active_at": s.last_active_at,
                "alive": s.is_alive,
                "buffer_lines": s.buffer.size,
            })
        return json.dumps(sessions, indent=2)

    # ----- I/O -----

    async def exec_command(
        self,
        session_id: str,
        command: str,
        wait_for: str = "",
        timeout: int = 30,
    ) -> str:
        session = self._sessions.get(session_id)
        if session is None:
            return json.dumps({"error": f"Session '{session_id}' not found."})

        await session.write(command + "\n")
        await asyncio.sleep(0.3)

        if wait_for:
            output = await session.wait_for(wait_for, timeout=timeout)
        else:
            await asyncio.sleep(min(timeout, 2))
            lines = await session.buffer.get_recent(100)
            output = "\n".join(lines)

        return output

    async def read_output(self, session_id: str, lines: int = 50) -> str:
        session = self._sessions.get(session_id)
        if session is None:
            return json.dumps({"error": f"Session '{session_id}' not found."})
        recent = await session.buffer.get_recent(lines)
        return "\n".join(recent)

    async def send_input(self, session_id: str, data: str, press_enter: bool = True) -> str:
        session = self._sessions.get(session_id)
        if session is None:
            return json.dumps({"error": f"Session '{session_id}' not found."})
        payload = data + ("\n" if press_enter else "")
        await session.write(payload)
        await asyncio.sleep(0.3)
        recent = await session.buffer.get_recent(20)
        return "\n".join(recent)

    # ----- timeout reaper -----

    def _ensure_reaper(self) -> None:
        if self._reaper_task is None or self._reaper_task.done():
            self._reaper_task = asyncio.create_task(self._reaper_loop())

    async def _reaper_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(60)
                await self._reap_stale()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Reaper error")

    async def _reap_stale(self) -> None:
        cfg = get_config().security
        now = time.time()
        to_kill = [
            sid
            for sid, s in self._sessions.items()
            if (now - s.last_active_at) > cfg.session_timeout
        ]
        for sid in to_kill:
            logger.info("Reaping stale session %s", sid)
            await self.kill(sid)
            await get_audit_logger().log(AuditEvent(
                action="terminal_timeout_reap",
                module="terminal",
                params_summary=f"id={sid}",
            ))


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_manager: Optional[TerminalManager] = None


def get_terminal_manager() -> TerminalManager:
    global _manager
    if _manager is None:
        _manager = TerminalManager()
    return _manager
