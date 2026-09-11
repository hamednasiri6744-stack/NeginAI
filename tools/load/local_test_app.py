"""Isolated app instance used only for localhost capacity verification."""

from __future__ import annotations

import tempfile
from dataclasses import replace
from pathlib import Path

from app import main as main_module
from app.config import get_settings

_root = Path(tempfile.mkdtemp(prefix="neginai-load-"))
_settings = replace(
    get_settings(),
    sqlite_path=_root / "load.db",
    vapid_private_key_path=_root / "vapid.pem",
    metadata_sync_enabled=False,
    automation_enabled=False,
    enterprise_database_url="",
    redis_url="",
    command_outbox_enabled=False,
    otel_exporter_otlp_endpoint="",
    varanegar_order_bridge_enabled=False,
    varanegar_order_commit_enabled=False,
)

# The load process must not alter the workspace .env. Secrets are irrelevant to
# the public liveness endpoint exercised by this isolated application instance.
main_module.ensure_action_api_key = lambda: None
main_module.get_settings = lambda: _settings
app = main_module.app
