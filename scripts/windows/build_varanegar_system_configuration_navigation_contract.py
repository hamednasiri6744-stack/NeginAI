"""Join static settings navigation with redacted configuration-domain evidence."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _caption(route: dict) -> str:
    value = route.get("menu_caption") or {}
    return value.get("value", "") if isinstance(value, dict) else ""


def _area(caption: str) -> str:
    if "تاریخ قطعی" in caption:
        return "close_date_management"
    if "سال مالی" in caption or "بستن عملیات" in caption or "بستن اسناد" in caption or "برگشت عملیات" in caption:
        return "fiscal_period_close_reopen"
    if "تنظیمات" in caption or "تغییرات سیستم" in caption or "ارسال و دریافت" in caption:
        return "configuration_publication_and_integration"
    if "کاربر" in caption or "دسترسی" in caption or "اختیارات ویژه" in caption:
        return "privileged_access_and_maintenance"
    if "نسخه" in caption or "شابلون" in caption:
        return "template_and_version_management"
    if "گزارش" in caption:
        return "settings_scoped_reporting"
    return "other_system_setting"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--navigation", required=True, type=Path)
    parser.add_argument("--configuration-domain", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    navigation = _load(args.navigation)
    domain = _load(args.configuration_domain)
    errors: list[str] = []
    if navigation.get("validation") != "PASS":
        errors.append("navigation source is not PASS")
    if domain.get("domain") != "configuration_and_rule_flags":
        errors.append("unexpected configuration domain source")
    if domain.get("safety", {}).get("can_update") != 0:
        errors.append("configuration source is not read-only")

    routes = [row for row in navigation.get("routes", []) if row.get("root_menu_id") == 900]
    configured = []
    for route in routes:
        if route.get("form_info_id") is None:
            continue
        caption = _caption(route)
        configured.append(
            {
                "menu_id": route.get("menu_id"),
                "parent_menu_id": route.get("parent_menu_id"),
                "static_caption": caption,
                "form_info_id": route.get("form_info_id"),
                "access_node_id": route.get("access_node_id"),
                "runtime_coverage_classification": route.get("route_runtime_coverage_classification"),
                "matched_form_type": route.get("matched_form_type"),
                "target_configuration_area": _area(caption),
                "runtime_effective_value_or_precedence_proven": False,
                "runtime_save_close_or_publish_effect_proven": False,
            }
        )
    configured.sort(key=lambda row: row["menu_id"])

    classifications = Counter(row["runtime_coverage_classification"] for row in configured)
    areas = Counter(row["target_configuration_area"] for row in configured)
    key_values = domain.get("key_value_configs", {})
    general = key_values.get("general_config_without_values", {})
    server = key_values.get("server_config_without_values", {})
    history_integrity = key_values.get("history_key_integrity", {})
    dc = domain.get("dc_and_customer_configs", {})
    ngt = domain.get("ngt_configuration", {}).get("catalog_and_setting_population", {})

    if len(routes) != 50:
        errors.append("settings route count drift")
    if len(configured) != 15:
        errors.append("configured settings route count drift")

    artifact = {
        "artifact": "varanegar_system_configuration_navigation_and_effective_setting_contract",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_JOIN_OF_REDACTED_STATIC_NAVIGATION_AND_READ_ONLY_AGGREGATE_CONFIGURATION_EVIDENCE",
            "database_connections": 0,
            "network_reads": 0,
            "live_ui_actions": 0,
            "application_or_configuration_commands_executed": 0,
            "configuration_or_history_values_read_or_persisted": 0,
            "credentials_urls_paths_hosts_or_device_owners_persisted": 0,
        },
        "summary": {
            "settings_root_route_count": len(routes),
            "configured_form_route_count": len(configured),
            "runtime_matched_configured_route_count": sum(bool(row["matched_form_type"]) for row in configured),
            "runtime_unmatched_configured_route_count": sum(not row["matched_form_type"] for row in configured),
            "runtime_coverage_classification_counts": dict(sorted(classifications.items())),
            "target_configuration_area_counts": dict(sorted(areas.items())),
            "configuration_table_count": len(domain.get("tables", [])),
            "general_config_key_count": general.get("distinct_keys"),
            "server_config_key_count": server.get("distinct_keys"),
            "history_only_key_count": (history_integrity.get("general_history_only_keys", 0) + history_integrity.get("server_history_only_keys", 0)),
            "reviewed_cross_module_rule_key_count": len(domain.get("reviewed_rule_key_usage", [])),
            "dc_config_row_count": dc.get("dc_config_population", {}).get("rows"),
            "customer_field_config_field_count": dc.get("customer_field_config", {}).get("fields"),
            "ngt_device_setting_count": ngt.get("device_settings"),
            "removed_ngt_device_setting_count": ngt.get("removed_device_settings"),
            "runtime_effective_value_or_precedence_proven_count": 0,
            "runtime_mutation_effect_proven_count": 0,
            "validation_error_count": len(errors),
        },
        "target_contract": {
            "scope_precedence_to_make_explicit": ["global", "server", "dc", "device", "app", "user_exception"],
            "effective_setting_explain_fields": ["key", "effective_scope", "version", "non_secret_value_hash", "source_policy", "evaluated_at"],
            "publication_invariants": [
                "draft and published configuration versions are separate",
                "close-date and fiscal-close commands are distinct from ordinary setting edits",
                "every publication is authorized, reasoned, audited and reversible by a compensating version",
                "secret-bearing web-service settings live only in a secret store",
                "history-only keys are quarantined until retained, renamed or retired by an owner",
                "runtime consumers read a versioned effective snapshot rather than mutable nullable rows",
            ],
            "first_allowed_slice": "read_only_effective_setting_catalog_and_explain_without_values_or_secrets",
            "write_gate": "owner-reviewed precedence, exact consumer mapping, authenticated UAT, rollback and reconciliation on an isolated target",
        },
        "configured_routes": configured,
        "evidence_limits": list(domain.get("evidence_limits", [])) + [
            "Only four of fifteen configured system-setting routes map to a runtime form in the captured package.",
            "A static route, key name or SQL dependency does not prove the runtime effective value or precedence.",
            "No close, reopen, publish, apply-system-change, send/receive or settings save command was executed.",
        ],
        "source_paths": {
            "navigation": args.navigation.as_posix(),
            "configuration_domain": args.configuration_domain.as_posix(),
        },
        "validation_errors": errors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if artifact["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
