from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import routeros_api
from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[1]
TARGET_IP = "192.168.1.184"
COMMENT_PREFIX = "NeginAI public HTTPS"


def public_rule(rule: dict) -> dict:
    return {
        key: rule.get(key)
        for key in (
            ".id", "chain", "action", "protocol", "dst-port", "in-interface",
            "in-interface-list", "to-addresses", "to-ports", "comment", "disabled",
        )
        if key in rule
    }


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
        nat = pool.get_api().get_resource("/ip/firewall/nat")
        before = nat.get()
        backup_dir = ROOT / "data" / "router-backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        (backup_dir / f"nat-api-before-neginai-{stamp}.json").write_text(
            json.dumps([public_rule(rule) for rule in before], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        added: list[int] = []
        for port in (80, 443):
            port_text = str(port)
            exists = any(
                rule.get("chain") == "dstnat"
                and rule.get("action") == "dst-nat"
                and rule.get("protocol") == "tcp"
                and rule.get("dst-port") == port_text
                and rule.get("to-addresses") == TARGET_IP
                and rule.get("to-ports") == port_text
                for rule in before
            )
            if not exists:
                nat.add(
                    chain="dstnat",
                    action="dst-nat",
                    protocol="tcp",
                    dst_port=port_text,
                    in_interface_list="WAN",
                    to_addresses=TARGET_IP,
                    to_ports=port_text,
                    comment=f"{COMMENT_PREFIX} {port_text}",
                )
                added.append(port)

        after = nat.get()
        verified = {
            port: any(
                rule.get("chain") == "dstnat"
                and rule.get("action") == "dst-nat"
                and rule.get("protocol") == "tcp"
                and rule.get("dst-port") == str(port)
                and rule.get("to-addresses") == TARGET_IP
                and rule.get("to-ports") == str(port)
                and rule.get("disabled") != "true"
                for rule in after
            )
            for port in (80, 443)
        }
        (backup_dir / f"nat-api-after-neginai-{stamp}.json").write_text(
            json.dumps([public_rule(rule) for rule in after], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if not all(verified.values()):
            raise RuntimeError("NeginAI NAT verification failed")
        print(json.dumps({"added": added, "verified_ports": [80, 443]}))
    finally:
        pool.disconnect()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        message = str(exc).lower()
        category = "not_allowed" if "not allowed" in message else "authentication_or_api_error"
        print(json.dumps({"ok": False, "error_type": type(exc).__name__, "category": category}), file=sys.stderr)
        raise SystemExit(1)
