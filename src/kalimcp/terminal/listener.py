"""Shell Listener — reverse-shell listener (default disabled, admin scope required)."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Optional

from kalimcp.auth import AuthContext, AuthError, require_scope
from kalimcp.config import get_config
from kalimcp.utils.audit import AuditEvent, get_audit_logger

logger = logging.getLogger("kalimcp.terminal.listener")


class ConnectionInfo:
    """Represents a single reverse-shell connection."""

    def __init__(self, conn_id: str, addr: str, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.conn_id = conn_id
        self.addr = addr
        self.reader = reader
        self.writer = writer
        self.connected_at = time.time()
        self._output_buffer: list[str] = []
        self._read_task: Optional[asyncio.Task] = None

    async def start_reading(self) -> None:
        """Background task: continuously read from the reverse shell."""
        self._read_task = asyncio.current_task() or asyncio.ensure_future(self._read_loop())
        if asyncio.current_task() is None:
            return
        await self._read_loop()

    async def _read_loop(self) -> None:
        try:
            while True:
                data = await asyncio.wait_for(self.reader.read(8192), timeout=1.0)
                if not data:
                    self._output_buffer.append("\n[Connection closed by remote]\n")
                    break
                self._output_buffer.append(data.decode("utf-8", errors="replace"))
                # Keep buffer bounded
                if len(self._output_buffer) > 5000:
                    self._output_buffer = self._output_buffer[-2500:]
        except asyncio.TimeoutError:
            pass  # will be re-called
        except Exception as e:
            self._output_buffer.append(f"\n[Read error: {e}]\n")

    def get_output(self, lines: int = 100) -> str:
        full = "".join(self._output_buffer)
        all_lines = full.splitlines(keepends=True)
        return "".join(all_lines[-lines:])

    def to_dict(self) -> dict:
        return {
            "conn_id": self.conn_id,
            "addr": self.addr,
            "connected_at": self.connected_at,
        }


class ListenerInfo:
    def __init__(self, listener_id: str, port: int, protocol: str, handler: str):
        self.listener_id = listener_id
        self.port = port
        self.protocol = protocol
        self.handler = handler
        self.started_at = time.time()
        self.connections: list[str] = []
        self._server: Optional[asyncio.AbstractServer] = None

    def to_dict(self) -> dict:
        return {
            "listener_id": self.listener_id,
            "port": self.port,
            "protocol": self.protocol,
            "handler": self.handler,
            "started_at": self.started_at,
            "connections": self.connections,
        }


class ListenerManager:
    """Manages reverse-shell listeners."""

    def __init__(self) -> None:
        self._listeners: dict[str, ListenerInfo] = {}
        self._connections: dict[str, ConnectionInfo] = {}

    async def start_listener(
        self,
        port: int,
        protocol: str = "tcp",
        handler: str = "raw",
        auth: Optional[AuthContext] = None,
    ) -> str:
        cfg = get_config().security
        audit = get_audit_logger()

        # Feature gate
        if not cfg.enable_shell_listener:
            return json.dumps({"error": "Shell listener is disabled in configuration. Set security.enable_shell_listener=true to enable."})

        # Auth
        if auth:
            try:
                require_scope(auth, "admin")
            except AuthError as e:
                return json.dumps({"error": str(e)})

        # Port validation
        if port not in cfg.allowed_listener_ports:
            return json.dumps({"error": f"Port {port} is not in allowed list: {cfg.allowed_listener_ports}"})

        # Check for duplicate
        for info in self._listeners.values():
            if info.port == port:
                return json.dumps({"error": f"Port {port} already has an active listener."})

        listener_id = uuid.uuid4().hex[:8]
        info = ListenerInfo(listener_id=listener_id, port=port, protocol=protocol, handler=handler)

        try:
            if protocol == "tcp":
                server = await asyncio.start_server(
                    lambda r, w: self._handle_connection(info, r, w),
                    host="0.0.0.0",
                    port=port,
                )
                info._server = server
            else:
                return json.dumps({"error": f"Protocol '{protocol}' not yet supported."})
        except OSError as e:
            return json.dumps({"error": f"Failed to bind port {port}: {e}"})

        self._listeners[listener_id] = info

        await audit.log(AuditEvent(
            action="shell_listener_start",
            module="terminal",
            params_summary=f"port={port} proto={protocol} handler={handler}",
            api_key_name=auth.key_name if auth else "",
        ))

        return json.dumps(info.to_dict())

    async def _handle_connection(
        self,
        info: ListenerInfo,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        peername = writer.get_extra_info("peername")
        addr = f"{peername[0]}:{peername[1]}" if peername else "unknown"
        conn_id = uuid.uuid4().hex[:8]
        conn = ConnectionInfo(conn_id=conn_id, addr=addr, reader=reader, writer=writer)
        self._connections[conn_id] = conn
        info.connections.append(f"{addr} (conn={conn_id})")
        logger.info("Listener %s received connection from %s (conn=%s)", info.listener_id, addr, conn_id)

        await get_audit_logger().log(AuditEvent(
            action="shell_listener_connection",
            module="terminal",
            params_summary=f"listener={info.listener_id} from={addr} conn={conn_id}",
        ))

        # Start background reader
        asyncio.create_task(conn._read_loop())

    # ------------------------------------------------------------------
    # Connection interaction
    # ------------------------------------------------------------------

    async def exec_on_connection(
        self,
        conn_id: str,
        command: str,
        timeout: int = 15,
        auth: Optional[AuthContext] = None,
    ) -> str:
        """Send a command to a reverse-shell connection and return output."""
        cfg = get_config().security
        if not cfg.enable_shell_listener:
            return json.dumps({"error": "Shell listener is disabled."})
        if auth:
            try:
                require_scope(auth, "admin")
            except AuthError as e:
                return json.dumps({"error": str(e)})

        conn = self._connections.get(conn_id)
        if conn is None:
            return json.dumps({"error": f"Connection '{conn_id}' not found.", "available": list(self._connections.keys())})

        # Clear buffer before command
        conn._output_buffer.clear()

        # Send command
        try:
            conn.writer.write((command + "\n").encode())
            await conn.writer.drain()
        except Exception as e:
            return json.dumps({"error": f"Failed to send command: {e}"})

        # Wait for output
        await asyncio.sleep(min(timeout, 2))
        # Keep reading until timeout or no new data
        deadline = time.time() + timeout
        while time.time() < deadline:
            await asyncio.sleep(0.5)
            # Check if we got some output
            if conn._output_buffer:
                # Wait a bit more for output to stabilize
                await asyncio.sleep(0.5)
                break

        await get_audit_logger().log(AuditEvent(
            action="shell_connection_exec",
            module="terminal",
            params_summary=f"conn={conn_id} cmd={command[:80]}",
            api_key_name=auth.key_name if auth else "",
        ))

        output = conn.get_output()
        return json.dumps({"conn_id": conn_id, "command": command, "output": output})

    async def read_connection(self, conn_id: str, lines: int = 100, auth: Optional[AuthContext] = None) -> str:
        """Read the output buffer of a reverse-shell connection."""
        if auth:
            try:
                require_scope(auth, "admin")
            except AuthError as e:
                return json.dumps({"error": str(e)})
        conn = self._connections.get(conn_id)
        if conn is None:
            return json.dumps({"error": f"Connection '{conn_id}' not found."})
        return json.dumps({"conn_id": conn_id, "output": conn.get_output(lines)})

    async def list_connections(self, auth: Optional[AuthContext] = None) -> str:
        """List all active reverse-shell connections."""
        if auth:
            try:
                require_scope(auth, "admin")
            except AuthError as e:
                return json.dumps({"error": str(e)})
        return json.dumps([c.to_dict() for c in self._connections.values()], indent=2)

    async def list_listeners(self, auth: Optional[AuthContext] = None) -> str:
        cfg = get_config().security
        if not cfg.enable_shell_listener:
            return json.dumps({"error": "Shell listener is disabled."})
        if auth:
            try:
                require_scope(auth, "admin")
            except AuthError as e:
                return json.dumps({"error": str(e)})

        return json.dumps([info.to_dict() for info in self._listeners.values()], indent=2)

    async def stop_listener(self, listener_id: str) -> str:
        info = self._listeners.pop(listener_id, None)
        if info is None:
            return json.dumps({"error": f"Listener '{listener_id}' not found."})
        if info._server:
            info._server.close()
            await info._server.wait_closed()

        await get_audit_logger().log(AuditEvent(
            action="shell_listener_stop",
            module="terminal",
            params_summary=f"listener={listener_id} port={info.port}",
        ))
        return json.dumps({"status": "stopped", "listener_id": listener_id})


# Singleton
_listener_manager: Optional[ListenerManager] = None


def get_listener_manager() -> ListenerManager:
    global _listener_manager
    if _listener_manager is None:
        _listener_manager = ListenerManager()
    return _listener_manager
