"""Social engineering tool wrappers (high-risk, default disabled)."""

from __future__ import annotations

import json
from typing import Optional

from kalimcp.auth import AuthContext, AuthError, require_scope
from kalimcp.config import get_config


def _check_high_risk(auth: AuthContext) -> Optional[str]:
    cfg = get_config().security
    if not cfg.enable_high_risk_tools:
        return json.dumps({"error": "High-risk tools are disabled."})
    try:
        require_scope(auth, "admin")
    except AuthError as e:
        return json.dumps({"error": str(e)})
    return None

# Social engineering tools (SET, GoPhish) are interactive and typically
# driven via the Terminal Manager rather than exec_tool.
# This module serves as a placeholder for future structured wrappers.
