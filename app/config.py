from __future__ import annotations

import os
import secrets
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

FROZEN = bool(getattr(sys, "frozen", False))
if FROZEN:
    executable_dir = Path(sys.executable).resolve().parent
    ROOT_DIR = (
        executable_dir.parent
        if not (executable_dir / ".env").exists() and (executable_dir.parent / ".env").exists()
        else executable_dir
    )
else:
    ROOT_DIR = Path(__file__).resolve().parent.parent
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", ROOT_DIR))
ENV_PATH = ROOT_DIR / ".env"
ENV_DEFAULTS = {
    "SQL_SERVER": "",
    "SQL_DATABASE": "NeginPakhsh",
    "SQL_USERNAME": "",
    "SQL_PASSWORD": "",
    "SQL_DRIVER": "ODBC Driver 18 for SQL Server",
    "SQL_CLIENT": "odbc",
    # Enterprise deployments must validate the SQL Server certificate and
    # hostname. Development can opt in to a local bypass explicitly.
    "SQL_TRUST_CERTIFICATE": "false",
    "SQL_QUERY_TIMEOUT": "30",
    "SQL_MAX_ROWS": "1000",
    # Allows the development server to use an isolated local state database
    # while the pilot process keeps its existing database unchanged.
    "NEGINAI_SQLITE_PATH": "",
    "NEGINAI_ENVIRONMENT": "development",
    "NEGIN_ENTERPRISE_DATABASE_URL": "",
    "NEGIN_REDIS_URL": "",
    "NEGIN_COMMAND_OUTBOX_ENABLED": "false",
    "NEGIN_OTEL_EXPORTER_OTLP_ENDPOINT": "",
    "ENTITY_SYNC_INTERVAL": "300",
    "SCHEMA_SYNC_INTERVAL": "3600",
    "OPENAI_MODEL": "gpt-5.6-sol",
    "OPENAI_REASONING_EFFORT": "high",
    # Deterministic model routing keeps light conversation inexpensive while
    # preserving the flagship model for complex, multi-source analysis.
    "MODEL_ROUTER_ENABLED": "true",
    "ROUTER_FAST_MODEL": "gpt-5.6-luna",
    "ROUTER_FAST_REASONING_EFFORT": "low",
    "ROUTER_STANDARD_MODEL": "gpt-5.6-terra",
    "ROUTER_STANDARD_REASONING_EFFORT": "medium",
    # Sellers receive a lower-latency model profile; internal users keep the
    # main reporting profile above.
    "SELLER_OPENAI_MODEL": "gpt-5.6-terra",
    "SELLER_OPENAI_REASONING_EFFORT": "low",
    "SELLER_OPENAI_MAX_TURNS": "6",
    "OPENAI_MAX_TURNS": "14",
    "OPENAI_HISTORY_LIMIT": "12",
    # The authenticated Admin workspace performs deeper, multi-source reports.
    # These limits control agent orchestration/context transport, not database
    # authorization; Admin remains read-only but may inspect every catalogued
    # table and view.
    "ADMIN_OPENAI_MAX_TURNS": "40",
    "ADMIN_OPENAI_HISTORY_LIMIT": "40",
    "ADMIN_OPENAI_MAX_TOKENS": "6000",
    "NEGIN_OAUTH_CLIENT_ID": "neginai-chatgpt",
    # OAuth callbacks are exact-match only. These two URLs preserve the
    # currently configured ChatGPT GPT callback on both official hosts.
    "NEGIN_OAUTH_REDIRECT_URIS": (
        "https://chatgpt.com/aip/g-4554e122eda78292cad88bc29ae5cf3b7cdbb3b2/oauth/callback,"
        "https://oauth.openai.com/aip/g-4554e122eda78292cad88bc29ae5cf3b7cdbb3b2/oauth/callback"
    ),
    "VAPID_SUBJECT": "mailto:admin@neginpakhsh.com",
    "PUSH_NOTIFICATION_URL": "/assistant",
    "CHATGPT_GPT_URL": "https://chatgpt.com/g/g-4554e122eda78292cad88bc29ae5cf3b7cdbb3b2-hwsh-msnw-y-ngyn-pkhsh",
    "NESHAN_WEB_API_KEY": "",
    "NESHAN_SERVICE_API_KEY": "",
    "NAVIGATION_TTS_MODEL": "gpt-4o-mini-tts",
    "NAVIGATION_TTS_VOICE": "marin",
    # NGT remains the only supported bridge for operational pre-sale writes.
    # Credentials stay server-side in .env and are never returned to a client.
    "NGT_API_BASE_URL": "",
    "NGT_API_USERNAME": "",
    "NGT_API_PASSWORD": "",
    # NGT OAuth expects OwnerKey,DataOwnerKey,DataOwnerCenterKey as scope.
    "NGT_API_SCOPE": "",
    "NGT_API_TOKEN_PATH": "/oauth/token",
    "NGT_API_CATALOG_PATH": "",
    "NGT_PILOT_SEND_ENABLED": "false",
    # Temporary pilot switch. NGT's distance rule is still read and exposed,
    # but it must not block the initial visit while the ordering flow is tested.
    "PREVISIT_START_DISTANCE_CHECK_ENABLED": "false",
    # Opt-in guard: a configured API key alone must not start scheduled model calls.
    "AUTOMATION_ENABLED": "false",
    "AUTOMATION_RUN_TIMEOUT_SECONDS": "180",
}


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def ensure_action_api_key(env_path: Path = ENV_PATH) -> None:
    """Create the internal action key once without ever logging its value."""
    env_path.parent.mkdir(parents=True, exist_ok=True)
    existing = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    if existing and not existing.endswith("\n"):
        existing += "\n"
    present_names = {
        line.split("=", 1)[0].strip()
        for line in existing.splitlines()
        if "=" in line and not line.lstrip().startswith("#")
    }
    additions = "".join(f"{name}={value}\n" for name, value in ENV_DEFAULTS.items() if name not in present_names)
    load_dotenv(env_path, override=False)
    key = os.getenv("NEGIN_ACTION_API_KEY", "").strip()
    if not key:
        key = secrets.token_urlsafe(48)
        additions += f"NEGIN_ACTION_API_KEY={key}\n"
        os.environ["NEGIN_ACTION_API_KEY"] = key
    oauth_secret = os.getenv("NEGIN_OAUTH_CLIENT_SECRET", "").strip()
    if not oauth_secret:
        oauth_secret = secrets.token_urlsafe(48)
        additions += f"NEGIN_OAUTH_CLIENT_SECRET={oauth_secret}\n"
        os.environ["NEGIN_OAUTH_CLIENT_SECRET"] = oauth_secret
    session_secret = os.getenv("NEGIN_SESSION_SIGNING_SECRET", "").strip()
    if not session_secret:
        session_secret = secrets.token_urlsafe(48)
        additions += f"NEGIN_SESSION_SIGNING_SECRET={session_secret}\n"
        os.environ["NEGIN_SESSION_SIGNING_SECRET"] = session_secret
    if additions:
        env_path.write_text(existing + additions, encoding="utf-8")


@dataclass(frozen=True)
class Settings:
    sql_server: str
    sql_database: str
    sql_username: str
    sql_password: str
    sql_driver: str
    sql_trust_certificate: bool
    sql_query_timeout: int
    sql_max_rows: int
    action_api_key: str
    sqlite_path: Path
    deployment_environment: str = "development"
    enterprise_database_url: str = ""
    redis_url: str = ""
    command_outbox_enabled: bool = False
    otel_exporter_otlp_endpoint: str = ""
    sql_client: str = "odbc"
    entity_sync_interval: int = 300
    schema_sync_interval: int = 3600
    metadata_sync_enabled: bool = True
    seller_data_restrictions_enabled: bool = True
    openai_api_key: str = ""
    openai_automation_api_key: str = ""
    openai_model: str = "gpt-5.6-sol"
    openai_reasoning_effort: str = "high"
    model_router_enabled: bool = True
    router_fast_model: str = "gpt-5.6-luna"
    router_fast_reasoning_effort: str = "low"
    router_standard_model: str = "gpt-5.6-terra"
    router_standard_reasoning_effort: str = "medium"
    seller_openai_model: str = "gpt-5.6-terra"
    seller_openai_reasoning_effort: str = "low"
    seller_openai_max_turns: int = 6
    openai_max_turns: int = 14
    openai_history_limit: int = 12
    admin_openai_max_turns: int = 40
    admin_openai_history_limit: int = 40
    admin_openai_max_tokens: int = 6000
    openai_transcription_model: str = "gpt-4o-transcribe"
    login_username: str = ""
    login_password_hash: str = ""
    oauth_client_id: str = "neginai-chatgpt"
    oauth_client_secret: str = ""
    oauth_redirect_uris: tuple[str, ...] = ()
    session_signing_secret: str = ""
    vapid_private_key_path: Path | None = None
    vapid_subject: str = "mailto:admin@neginpakhsh.com"
    push_notification_url: str = "/assistant"
    chatgpt_gpt_url: str = "https://chatgpt.com/g/g-4554e122eda78292cad88bc29ae5cf3b7cdbb3b2-hwsh-msnw-y-ngyn-pkhsh"
    automation_enabled: bool = True
    automation_run_timeout_seconds: int = 180
    neshan_web_api_key: str = ""
    neshan_service_api_key: str = ""
    navigation_tts_model: str = "gpt-4o-mini-tts"
    navigation_tts_voice: str = "marin"
    ngt_api_base_url: str = ""
    ngt_api_username: str = ""
    ngt_api_password: str = ""
    ngt_api_scope: str = ""
    ngt_api_token_path: str = "/oauth/token"
    ngt_api_catalog_path: str = ""
    ngt_pilot_send_enabled: bool = False
    previsit_start_distance_check_enabled: bool = False
    previsit_test_all_routes_username: str = ""
    previsit_test_all_routes_until: str = ""
    varanegar_order_bridge_enabled: bool = False
    varanegar_order_commit_enabled: bool = False
    varanegar_order_numbering_verified: bool = False
    varanegar_order_sql_server: str = ""
    varanegar_order_sql_database: str = "NeginPakhsh"
    varanegar_order_sql_username: str = ""
    varanegar_order_sql_password: str = ""
    varanegar_order_sql_driver: str = "ODBC Driver 18 for SQL Server"
    varanegar_order_sql_client: str = "odbc"
    varanegar_order_sql_trust_certificate: bool = False
    varanegar_order_procedure: str = "NeginAI.usp_SubmitValidatedOrder"
    varanegar_order_system_username: str = "VnAdmin"

    @property
    def sql_configured(self) -> bool:
        return bool(self.sql_server and self.sql_username and self.sql_password)

    @property
    def varanegar_order_sql_configured(self) -> bool:
        return bool(
            self.varanegar_order_sql_server
            and self.varanegar_order_sql_username
            and self.varanegar_order_sql_password
        )


def validate_transport_security(settings: Settings) -> None:
    """Fail closed when a production SQL connection skips certificate checks."""
    if settings.command_outbox_enabled and not settings.enterprise_database_url:
        raise RuntimeError(
            "The durable command outbox requires NEGIN_ENTERPRISE_DATABASE_URL"
        )
    if settings.command_outbox_enabled and not settings.redis_url:
        raise RuntimeError("Replica-safe enterprise mode requires NEGIN_REDIS_URL")
    environment = settings.deployment_environment.casefold()
    local_development = environment in {"development", "dev", "test", "local"}
    enterprise_runtime = bool(
        settings.enterprise_database_url
        or settings.command_outbox_enabled
        or not local_development
    )
    if enterprise_runtime and not settings.redis_url:
        raise RuntimeError(
            "Enterprise authentication rate limiting requires NEGIN_REDIS_URL"
        )
    if environment not in {"production", "prod"}:
        return
    insecure_connections: list[str] = []
    if settings.sql_configured and settings.sql_trust_certificate:
        insecure_connections.append("reporting SQL Server")
    if (
        settings.varanegar_order_sql_configured
        and settings.varanegar_order_sql_trust_certificate
    ):
        insecure_connections.append("Varanegar order SQL Server")
    if insecure_connections:
        joined = ", ".join(insecure_connections)
        raise RuntimeError(
            "Production requires certificate and hostname validation for: " + joined
        )

def get_settings() -> Settings:
    load_dotenv(ENV_PATH, override=False)
    sqlite_path_override = os.getenv("NEGINAI_SQLITE_PATH", "").strip()
    return Settings(
        sql_server=os.getenv("SQL_SERVER", "").strip(),
        sql_database=os.getenv("SQL_DATABASE", "NeginPakhsh").strip(),
        sql_username=os.getenv("SQL_USERNAME", "").strip(),
        sql_password=os.getenv("SQL_PASSWORD", ""),
        sql_driver=os.getenv("SQL_DRIVER", "ODBC Driver 18 for SQL Server").strip(),
        sql_trust_certificate=_as_bool(os.getenv("SQL_TRUST_CERTIFICATE"), False),
        sql_query_timeout=max(1, int(os.getenv("SQL_QUERY_TIMEOUT", "30"))),
        sql_max_rows=max(1, int(os.getenv("SQL_MAX_ROWS", "1000"))),
        action_api_key=os.getenv("NEGIN_ACTION_API_KEY", "").strip(),
        sqlite_path=(
            Path(sqlite_path_override).expanduser()
            if sqlite_path_override
            else ROOT_DIR / "data" / "neginai.db"
        ),
        deployment_environment=(
            os.getenv("NEGINAI_ENVIRONMENT", "development").strip().lower()
            or "development"
        ),
        enterprise_database_url=os.getenv("NEGIN_ENTERPRISE_DATABASE_URL", "").strip(),
        redis_url=os.getenv("NEGIN_REDIS_URL", "").strip(),
        command_outbox_enabled=_as_bool(os.getenv("NEGIN_COMMAND_OUTBOX_ENABLED"), False),
        otel_exporter_otlp_endpoint=os.getenv(
            "NEGIN_OTEL_EXPORTER_OTLP_ENDPOINT", ""
        ).strip(),
        sql_client=(os.getenv("SQL_CLIENT", "odbc").strip().lower() or "odbc"),
        entity_sync_interval=max(30, int(os.getenv("ENTITY_SYNC_INTERVAL", "300"))),
        schema_sync_interval=max(300, int(os.getenv("SCHEMA_SYNC_INTERVAL", "3600"))),
        metadata_sync_enabled=_as_bool(os.getenv("METADATA_SYNC_ENABLED"), True),
        seller_data_restrictions_enabled=_as_bool(
            os.getenv("SELLER_DATA_RESTRICTIONS_ENABLED"), True
        ),
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        openai_automation_api_key=os.getenv("OPENAI_AUTOMATION_API_KEY", "").strip(),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5.6-sol").strip() or "gpt-5.6-sol",
        openai_reasoning_effort=(
            os.getenv("OPENAI_REASONING_EFFORT", "high").strip().lower() or "high"
        ),
        model_router_enabled=_as_bool(os.getenv("MODEL_ROUTER_ENABLED"), True),
        router_fast_model=(
            os.getenv("ROUTER_FAST_MODEL", "gpt-5.6-luna").strip()
            or "gpt-5.6-luna"
        ),
        router_fast_reasoning_effort=(
            os.getenv("ROUTER_FAST_REASONING_EFFORT", "low").strip().lower()
            or "low"
        ),
        router_standard_model=(
            os.getenv("ROUTER_STANDARD_MODEL", "gpt-5.6-terra").strip()
            or "gpt-5.6-terra"
        ),
        router_standard_reasoning_effort=(
            os.getenv("ROUTER_STANDARD_REASONING_EFFORT", "medium").strip().lower()
            or "medium"
        ),
        seller_openai_model=(
            os.getenv("SELLER_OPENAI_MODEL", "gpt-5.6-terra").strip()
            or "gpt-5.6-terra"
        ),
        seller_openai_reasoning_effort=(
            os.getenv("SELLER_OPENAI_REASONING_EFFORT", "low").strip().lower()
            or "low"
        ),
        seller_openai_max_turns=max(
            2, int(os.getenv("SELLER_OPENAI_MAX_TURNS", "6"))
        ),
        openai_max_turns=max(6, int(os.getenv("OPENAI_MAX_TURNS", "14"))),
        openai_history_limit=max(2, int(os.getenv("OPENAI_HISTORY_LIMIT", "12"))),
        admin_openai_max_turns=max(
            14, int(os.getenv("ADMIN_OPENAI_MAX_TURNS", "40"))
        ),
        admin_openai_history_limit=max(
            12, int(os.getenv("ADMIN_OPENAI_HISTORY_LIMIT", "40"))
        ),
        admin_openai_max_tokens=max(
            2200, int(os.getenv("ADMIN_OPENAI_MAX_TOKENS", "6000"))
        ),
        openai_transcription_model=(
            os.getenv("OPENAI_TRANSCRIPTION_MODEL", "gpt-4o-transcribe").strip()
            or "gpt-transcribe"
        ),
        login_username=os.getenv("NEGIN_LOGIN_USERNAME", "").strip(),
        login_password_hash=os.getenv("NEGIN_LOGIN_PASSWORD_HASH", "").strip(),
        oauth_client_id=(
            os.getenv("NEGIN_OAUTH_CLIENT_ID", "neginai-chatgpt").strip()
            or "neginai-chatgpt"
        ),
        oauth_client_secret=os.getenv("NEGIN_OAUTH_CLIENT_SECRET", "").strip(),
        oauth_redirect_uris=tuple(
            uri.strip()
            for uri in os.getenv(
                "NEGIN_OAUTH_REDIRECT_URIS",
                ENV_DEFAULTS["NEGIN_OAUTH_REDIRECT_URIS"],
            ).split(",")
            if uri.strip()
        ),
        session_signing_secret=os.getenv("NEGIN_SESSION_SIGNING_SECRET", "").strip(),
        vapid_private_key_path=Path(
            os.getenv("VAPID_PRIVATE_KEY_PATH", str(ROOT_DIR / "data" / "vapid_private.pem"))
        ),
        vapid_subject=(
            os.getenv("VAPID_SUBJECT", "mailto:admin@neginpakhsh.com").strip()
            or "mailto:admin@neginpakhsh.com"
        ),
        push_notification_url=(
            os.getenv("PUSH_NOTIFICATION_URL", "/assistant").strip()
            or "/assistant"
        ),
        chatgpt_gpt_url=(
            os.getenv(
                "CHATGPT_GPT_URL",
                "https://chatgpt.com/g/g-4554e122eda78292cad88bc29ae5cf3b7cdbb3b2-hwsh-msnw-y-ngyn-pkhsh",
            ).strip()
            or "https://chatgpt.com/g/g-4554e122eda78292cad88bc29ae5cf3b7cdbb3b2-hwsh-msnw-y-ngyn-pkhsh"
        ),
        automation_enabled=_as_bool(os.getenv("AUTOMATION_ENABLED"), False),
        automation_run_timeout_seconds=max(
            30, int(os.getenv("AUTOMATION_RUN_TIMEOUT_SECONDS", "180"))
        ),
        neshan_web_api_key=os.getenv("NESHAN_WEB_API_KEY", "").strip(),
        neshan_service_api_key=os.getenv("NESHAN_SERVICE_API_KEY", "").strip(),
        navigation_tts_model=(
            os.getenv("NAVIGATION_TTS_MODEL", "gpt-4o-mini-tts").strip()
            or "gpt-4o-mini-tts"
        ),
        navigation_tts_voice=(
            os.getenv("NAVIGATION_TTS_VOICE", "marin").strip() or "marin"
        ),
        ngt_api_base_url=os.getenv("NGT_API_BASE_URL", "").strip().rstrip("/"),
        ngt_api_username=os.getenv("NGT_API_USERNAME", "").strip(),
        ngt_api_password=os.getenv("NGT_API_PASSWORD", ""),
        ngt_api_scope=os.getenv("NGT_API_SCOPE", "").strip(),
        ngt_api_token_path=(
            os.getenv("NGT_API_TOKEN_PATH", "/oauth/token").strip()
            or "/oauth/token"
        ),
        ngt_api_catalog_path=os.getenv("NGT_API_CATALOG_PATH", "").strip(),
        ngt_pilot_send_enabled=_as_bool(os.getenv("NGT_PILOT_SEND_ENABLED"), False),
        previsit_start_distance_check_enabled=_as_bool(
            os.getenv("PREVISIT_START_DISTANCE_CHECK_ENABLED"), False
        ),
        previsit_test_all_routes_username=os.getenv(
            "PREVISIT_TEST_ALL_ROUTES_USERNAME", ""
        ).strip(),
        previsit_test_all_routes_until=os.getenv(
            "PREVISIT_TEST_ALL_ROUTES_UNTIL", ""
        ).strip(),
        varanegar_order_bridge_enabled=_as_bool(
            os.getenv("VARANEGAR_ORDER_BRIDGE_ENABLED"), False
        ),
        varanegar_order_commit_enabled=_as_bool(
            os.getenv("VARANEGAR_ORDER_COMMIT_ENABLED"), False
        ),
        varanegar_order_numbering_verified=_as_bool(
            os.getenv("VARANEGAR_ORDER_NUMBERING_VERIFIED"), False
        ),
        varanegar_order_sql_server=os.getenv(
            "VARANEGAR_ORDER_SQL_SERVER", os.getenv("SQL_SERVER", "")
        ).strip(),
        varanegar_order_sql_database=(
            os.getenv(
                "VARANEGAR_ORDER_SQL_DATABASE",
                os.getenv("SQL_DATABASE", "NeginPakhsh"),
            ).strip()
            or "NeginPakhsh"
        ),
        varanegar_order_sql_username=os.getenv("VARANEGAR_ORDER_SQL_USERNAME", "").strip(),
        varanegar_order_sql_password=os.getenv("VARANEGAR_ORDER_SQL_PASSWORD", ""),
        varanegar_order_sql_driver=(
            os.getenv("VARANEGAR_ORDER_SQL_DRIVER", "ODBC Driver 18 for SQL Server").strip()
            or "ODBC Driver 18 for SQL Server"
        ),
        varanegar_order_sql_client=(
            os.getenv("VARANEGAR_ORDER_SQL_CLIENT", "odbc").strip().lower() or "odbc"
        ),
        varanegar_order_sql_trust_certificate=_as_bool(
            os.getenv("VARANEGAR_ORDER_SQL_TRUST_CERTIFICATE"), False
        ),
        varanegar_order_procedure=(
            os.getenv("VARANEGAR_ORDER_PROCEDURE", "NeginAI.usp_SubmitValidatedOrder").strip()
            or "NeginAI.usp_SubmitValidatedOrder"
        ),
        varanegar_order_system_username=(
            os.getenv("VARANEGAR_ORDER_SYSTEM_USERNAME", "VnAdmin").strip() or "VnAdmin"
        ),
    )
