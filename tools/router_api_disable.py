from __future__ import annotations

import json
import sys
from pathlib import Path

import routeros_api
from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    config = dotenv_values(ROOT / ".env")
    pool = routeros_api.RouterOsApiPool(
        config["MIKROTIK_HOST"],
        username=config["MIKROTIK_USERNAME"],
        password=config["MIKROTIK_PASSWORD"],
        port=8728,
        plaintext_login=True,
    )
    try:
        services = pool.get_api().get_resource("/ip/service")
        api_service = next(item for item in services.get() if item.get("name") == "api")
        services.set(id=api_service["id"], disabled="yes")
        print(json.dumps({"api_disabled": True}))
    finally:
        pool.disconnect()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"ok": False, "error_type": type(exc).__name__}), file=sys.stderr)
        raise SystemExit(1)
