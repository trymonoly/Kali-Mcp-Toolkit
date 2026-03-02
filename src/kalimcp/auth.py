"""Authentication & authorisation — API Key, optional JWT, scope enforcement."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

import jwt

from kalimcp.config import get_config

# ---------------------------------------------------------------------------
# Auth context
# ---------------------------------------------------------------------------


@dataclass
class AuthContext:
    """Carries the authenticated caller's identity through the request."""

    key_name: str = "anonymous"
    scopes: list[str] = field(default_factory=lambda: ["read"])
    source_ip: str = ""
    is_stdio: bool = False


# ---------------------------------------------------------------------------
# Verification helpers
# ---------------------------------------------------------------------------


class AuthError(Exception):
    """Raised when authentication or authorisation fails."""

    def __init__(self, message: str, status_code: int = 401):
        super().__init__(message)
        self.status_code = status_code


def verify_api_key(authorization: str) -> AuthContext:
    """Validate ``Authorization: Bearer <key>`` header and return context.

    Raises ``AuthError`` on failure.
    """
    cfg = get_config().auth

    if not authorization.startswith("Bearer "):
        raise AuthError("Missing or malformed Authorization header. Expected 'Bearer <key>'.")

    token = authorization[7:].strip()
    if not token:
        raise AuthError("Empty bearer token.")

    # Check API keys
    for entry in cfg.api_keys:
        if entry.key == token:
            return AuthContext(key_name=entry.name, scopes=list(entry.scopes))

    # Optional JWT fallback
    if cfg.jwt_secret:
        try:
            payload = jwt.decode(token, cfg.jwt_secret, algorithms=[cfg.jwt_algorithm])
            return AuthContext(
                key_name=payload.get("sub", "jwt_user"),
                scopes=payload.get("scopes", ["read"]),
            )
        except jwt.ExpiredSignatureError:
            raise AuthError("JWT token has expired.", status_code=401)
        except jwt.InvalidTokenError:
            pass  # fall through to invalid key

    raise AuthError("Invalid API key or token.", status_code=401)


def require_scope(ctx: AuthContext, scope: str) -> None:
    """Raise ``AuthError(403)`` if the caller lacks *scope*."""
    if scope not in ctx.scopes:
        raise AuthError(
            f"Insufficient permissions. Required scope: '{scope}', available: {ctx.scopes}",
            status_code=403,
        )


def authenticate_request(
    authorization: Optional[str] = None,
    *,
    is_stdio: bool = False,
    source_ip: str = "",
) -> AuthContext:
    """Top-level entry point called by the server layer.

    * stdio mode → returns a local admin context (no auth required).
    * HTTP mode  → validates bearer token.
    """
    cfg = get_config().auth

    if is_stdio:
        return AuthContext(
            key_name="stdio_local",
            scopes=["read", "execute", "admin"],
            is_stdio=True,
        )

    if not cfg.enabled:
        return AuthContext(key_name="auth_disabled", scopes=["read", "execute", "admin"])

    if authorization is None:
        raise AuthError("Authorization header is required.", status_code=401)

    ctx = verify_api_key(authorization)
    ctx.source_ip = source_ip
    return ctx


# ---------------------------------------------------------------------------
# Rate limiting (per API key, sliding window)
# ---------------------------------------------------------------------------


class RateLimiter:
    """Simple in-memory sliding-window rate limiter keyed by API key name."""

    def __init__(self) -> None:
        self._windows: dict[str, list[float]] = {}

    def check(self, key_name: str) -> bool:
        """Return ``True`` if the request is within rate limits."""
        cfg = get_config().security
        now = time.time()
        window = self._windows.setdefault(key_name, [])
        # Prune old entries
        cutoff = now - 60.0
        self._windows[key_name] = window = [t for t in window if t > cutoff]
        if len(window) >= cfg.max_requests_per_minute:
            return False
        window.append(now)
        return True


_rate_limiter = RateLimiter()


def get_rate_limiter() -> RateLimiter:
    return _rate_limiter
