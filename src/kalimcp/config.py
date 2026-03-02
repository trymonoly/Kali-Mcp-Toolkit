"""Configuration system — YAML → Pydantic v2 with env-var overrides."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Pydantic v2 Config Models
# ---------------------------------------------------------------------------


class ServerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    host: str = Field(default="0.0.0.0", description="Bind address")
    port: int = Field(default=8443, ge=1, le=65535, description="Listen port")
    workers: int = Field(default=4, ge=1, description="Uvicorn workers")
    reload: bool = Field(default=False, description="Auto-reload in dev mode")


class ApiKeyEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(..., min_length=1, description="API key value")
    name: str = Field(default="default", description="Human-readable key name")
    scopes: list[str] = Field(default_factory=lambda: ["read"], description="Granted scopes")


class AuthConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(default=True, description="Enable authentication")
    api_keys: list[ApiKeyEntry] = Field(default_factory=list, description="API key list")
    jwt_secret: Optional[str] = Field(default=None, description="JWT signing secret")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")


class SecurityConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_requests_per_minute: int = Field(default=60, ge=1)
    max_concurrent_processes: int = Field(default=10, ge=1)
    command_timeout: int = Field(default=300, ge=1, description="Default timeout in seconds")
    session_timeout: int = Field(default=1800, ge=60, description="Terminal session timeout (s)")
    max_sessions: int = Field(default=20, ge=1)
    max_output_bytes: int = Field(default=5_000_000, ge=1024, description="Max stdout/stderr size")
    max_argument_length: int = Field(default=4096, ge=64)
    blocked_commands: list[str] = Field(
        default_factory=lambda: [
            "rm -rf /",
            "mkfs",
            "dd if=/dev/zero",
            ":(){:|:&};:",
        ]
    )
    enable_shell_listener: bool = Field(default=False, description="Enable reverse-shell listener (high risk)")
    enable_high_risk_tools: bool = Field(default=False, description="Enable high-risk tool wrappers")
    enable_install_deps: bool = Field(default=False, description="Enable code_install_deps")
    allowed_listener_ports: list[int] = Field(default_factory=lambda: list(range(4444, 4464)))
    allowed_listener_addresses: list[str] = Field(default_factory=lambda: ["127.0.0.1", "0.0.0.0"])
    target_whitelist: list[str] = Field(default_factory=list, description="Allowed target IPs/CIDRs for high-risk tools")


class WorkspaceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    root: str = Field(default="/opt/kalimcp/workspace", description="Workspace root directory")
    max_file_size_mb: int = Field(default=50, ge=1)


class LoggingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audit_log: str = Field(default="/var/log/kalimcp/audit.log")
    level: str = Field(default="INFO")
    max_audit_size_mb: int = Field(default=100, ge=1, description="Rotate audit log at this size")


class TlsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(default=False)
    cert_file: Optional[str] = Field(default=None)
    key_file: Optional[str] = Field(default=None)


class AppConfig(BaseModel):
    """Root configuration model."""

    model_config = ConfigDict(extra="forbid")

    server: ServerConfig = Field(default_factory=ServerConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    workspace: WorkspaceConfig = Field(default_factory=WorkspaceConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    tls: TlsConfig = Field(default_factory=TlsConfig)


# ---------------------------------------------------------------------------
# YAML loading + env-var override
# ---------------------------------------------------------------------------

_ENV_PREFIX = "KALIMCP_"


def _apply_env_overrides(data: dict) -> dict:
    """Override nested config values via environment variables.

    Convention:  KALIMCP_<SECTION>__<KEY>=value   (double underscore separator)
    Example:     KALIMCP_SERVER__PORT=9090
    """
    for key, value in os.environ.items():
        if not key.startswith(_ENV_PREFIX):
            continue
        parts = key[len(_ENV_PREFIX) :].lower().split("__")
        node = data
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        # Attempt numeric coercion
        try:
            value = int(value)  # type: ignore[assignment]
        except ValueError:
            if value.lower() in ("true", "false"):
                value = value.lower() == "true"  # type: ignore[assignment]
        node[parts[-1]] = value
    return data


def load_config(path: str | Path | None = None) -> AppConfig:
    """Load configuration from YAML file with env-var overrides."""
    data: dict = {}
    if path is not None:
        p = Path(path)
        if p.exists():
            with open(p, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
    data = _apply_env_overrides(data)
    return AppConfig(**data)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_config: AppConfig | None = None


def get_config() -> AppConfig:
    """Return the global config singleton. Call ``init_config`` first."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def init_config(path: str | Path | None = None) -> AppConfig:
    """Initialise (or re-initialise) the global config."""
    global _config
    _config = load_config(path)
    return _config
