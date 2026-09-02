"""Build target report/read/export/print contracts and synthetic Golden cases."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def _case(case_id: str, surface: str, category: str, setup: str, action: str, expected: list[str]) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "surface": surface,
        "category": category,
        "setup": setup,
        "action": action,
        "expected": expected,
        "execution_target": "NEGIN_ERP_REPORT_TEST_HARNESS_ONLY",
        "legacy_execution_allowed": False,
        "target_module": "reporting_documents",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    source = json.loads(args.reports.read_text(encoding="utf-8-sig"))
    errors = []
    contracts = []
    cases = []

    for ordinal, report in enumerate(source["surfaces"], start=1):
        type_name = report["type"]
        slug = _slug(type_name)
        prefix = f"RPT-{ordinal:02d}"
        flags = report["execution_flags"]
        query_surface = f"report.{slug}.read"
        commands = []
        if flags["has_export_to_file"]:
            commands.append(f"report.{slug}.export_file")
        if flags["has_print_completion_write"]:
            commands.append(f"document.{slug}.mark_print_completed")
        if flags["has_save_command"]:
            commands.append(f"statement.{slug}.create_or_update")

        contracts.append(
            {
                "contract_id": prefix,
                "legacy_type": type_name,
                "primary_domain_id": report["primary_domain_id"],
                "legacy_classification": report["classification"],
                "query_surface": query_surface,
                "command_surfaces": commands,
                "permissions": report["recommended_atomic_permissions"],
                "source_filter_contract_call_count": len(report["filter_contract_calls"]),
                "source_query_contract_call_count": len(report["query_contract_calls"]),
                "source_query_semantics_status": "STATIC_CALL_AND_LITERAL_EVIDENCE_ONLY_NOT_RESULT_PARITY",
                "query_contract": {
                    "required_context": ["tenant_id", "actor_id", "allowed_scope", "business_date_basis"],
                    "required_bounds": ["page_size_max", "date_range_max", "sort_allowlist", "filter_allowlist"],
                    "response_metadata": ["query_id", "filter_hash", "source_watermark", "generated_at", "row_count", "next_cursor", "privacy_class"],
                    "read_only": True,
                    "result_parity_requires_owner_golden_values": True,
                },
                "export_contract": {
                    "enabled": bool(flags["has_export_to_file"]),
                    "external_file_event_only": True,
                    "erp_state_mutation_allowed": False,
                    "required_receipt": ["export_job_id", "query_id", "filter_hash", "row_count", "content_sha256", "expires_at"],
                },
                "print_contract": {
                    "preview_is_read_only": True,
                    "mark_print_completed_command": bool(flags["has_print_completion_write"]),
                    "mark_command_requires_idempotency_and_expected_version": bool(flags["has_print_completion_write"]),
                    "preview_or_export_may_mark_completed": False,
                },
                "statement_contract": {
                    "legacy_save_signal": bool(flags["has_save_command"]),
                    "read_and_write_split_required": bool(flags["has_save_command"]),
                    "write_requires_idempotency_expected_version_audit_outbox": bool(flags["has_save_command"]),
                },
                "readiness": "SYNTHETIC_TARGET_CONTRACT_ONLY_NO_RESULT_PARITY_OR_UAT",
            }
        )

        common = [
            ("READ_HAPPY", "happy_path", "authorized actor, valid bounded filters and allowed scope", "run first page", ["only scoped rows returned", "query/filter/watermark provenance returned", "zero ERP writes"]),
            ("AUTH_DENIED", "authorization", "actor lacks report.read", "submit same query", ["AUTH_DENIED", "zero rows and zero writes", "denial audit contains no sensitive values"]),
            ("SCOPE", "scope", "authorized actor requests another DC/office/customer scope", "submit query", ["out-of-scope request denied or intersected explicitly", "zero leaked rows", "effective scope returned"]),
            ("PAGINATION", "pagination", "result exceeds page size", "walk cursor pages and replay one cursor", ["stable deterministic ordering", "no missing or duplicate row identity", "page size cap enforced"]),
            ("FRESHNESS", "freshness", "source watermark is older than accepted threshold", "request report", ["staleness is explicit", "no silent current label", "refresh or owner decision required"]),
            ("PRIVACY", "privacy", "actor has report access but lacks sensitive-field permission", "read/export response", ["sensitive fields masked or omitted", "aggregate totals preserve allowed semantics", "no raw value in logs"]),
        ]
        for suffix, category, setup, action, expected in common:
            cases.append(_case(f"{prefix}-{suffix}", query_surface, category, setup, action, expected))

        if report["filter_contract_calls"]:
            cases.append(_case(f"{prefix}-FILTER_BOUNDARY", query_surface, "filter_boundary", "minimum/maximum business date and invalid filter values", "execute boundary matrix", ["business-date inclusion is deterministic", "invalid fields/operators rejected", "created/import timestamp is not substituted"] ))
        if flags["has_export_to_file"]:
            export_surface = f"report.{slug}.export_file"
            for suffix, category, setup, action, expected in (
                ("EXPORT_HAPPY", "export", "authorized bounded query", "request export", ["immutable export receipt returned", "file hash and row count match query", "zero ERP writes"]),
                ("EXPORT_AUTH", "authorization", "actor lacks report.export_file", "request export", ["AUTH_DENIED", "no file/job created", "zero ERP writes"]),
                ("EXPORT_REPLAY", "idempotency", "same export job key and filter hash", "submit twice", ["one artifact or original receipt returned", "no duplicate job effect", "same content hash"]),
                ("EXPORT_FAILURE", "fault_injection", "failure after file creation before response", "retry same job key", ["one recoverable result", "partial file quarantined or replaced", "ERP state unchanged"]),
            ):
                cases.append(_case(f"{prefix}-{suffix}", export_surface, category, setup, action, expected))
        if flags["has_print_completion_write"]:
            mark_surface = f"document.{slug}.mark_print_completed"
            for suffix, category, setup, action, expected in (
                ("PREVIEW_NO_MUTATION", "read_only", "document is not print-completed", "preview or export", ["document status/version unchanged", "no print history appended", "preview provenance returned"]),
                ("MARK_SUCCESS", "happy_path", "authorized print receipt and current expected_version", "mark completed once", ["status/history advances once", "audit and outbox recorded", "new version returned"]),
                ("MARK_REPLAY", "idempotency", "same command_id and print receipt", "submit twice", ["original result returned", "one history/outbox effect", "version advances once"]),
                ("MARK_AUTH", "authorization", "actor may preview but lacks document.mark_print_completed", "submit mark command", ["AUTH_DENIED", "document unchanged", "denial audited"]),
                ("MARK_FAILURE", "fault_injection", "crash after commit before response", "retry same command_id", ["original committed result recovered", "no duplicate history/outbox", "result never silently unknown"]),
            ):
                cases.append(_case(f"{prefix}-{suffix}", mark_surface, category, setup, action, expected))
        if flags["has_save_command"]:
            statement_surface = f"statement.{slug}.create_or_update"
            for suffix, category, setup, action, expected in (
                ("STATEMENT_READ_ONLY", "read_only", "existing statement", "open/read report view", ["statement/version unchanged", "zero audit/outbox mutation", "read permission independent from write"]),
                ("STATEMENT_SAVE", "happy_path", "authorized valid payload and expected_version", "save once", ["one aggregate version committed", "audit/outbox recorded", "reconciliation status explicit"]),
                ("STATEMENT_REPLAY", "idempotency", "same command_id and payload hash", "submit twice", ["original result returned", "one aggregate/audit/outbox effect", "version advances once"]),
                ("STATEMENT_CONCURRENCY", "concurrency", "stale expected_version", "submit update", ["VERSION_CONFLICT", "no overwrite", "current version returned"]),
                ("STATEMENT_AUTH", "authorization", "actor has statement.read but lacks write permission", "submit save", ["AUTH_DENIED", "statement unchanged", "denial audited"]),
                ("STATEMENT_FAILURE", "fault_injection", "failure before and after commit", "retry same command_id", ["rollback or original committed result", "no duplicate ledger/audit/outbox", "unknown outcome blocks acceptance"]),
            ):
                cases.append(_case(f"{prefix}-{suffix}", statement_surface, category, setup, action, expected))

    case_ids = [case["case_id"] for case in cases]
    if len(case_ids) != len(set(case_ids)):
        errors.append("duplicate case ids")
    if len(contracts) != source["summary"]["surface_count"]:
        errors.append("report contract count mismatch")
    if any(case["legacy_execution_allowed"] for case in cases):
        errors.append("legacy execution allowed")

    artifact = {
        "artifact": "negin_personal_erp_report_target_contracts_and_synthetic_golden_cases",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_TARGET_DESIGN_FROM_REDACTED_STATIC_REPORT_EVIDENCE",
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "live_ui_actions": 0,
            "source_or_target_commands_executed": 0,
            "business_rows_or_values_read_or_persisted": 0,
            "legacy_report_or_print_execution_allowed": 0,
            "result_parity_uat_or_release_readiness_inferred": 0,
        },
        "source": {"path": args.reports.as_posix(), "sha256": hashlib.sha256(args.reports.read_bytes()).hexdigest()},
        "summary": {
            "report_contract_count": len(contracts),
            "query_surface_count": len(contracts),
            "export_surface_count": sum(contract["export_contract"]["enabled"] for contract in contracts),
            "print_completion_command_count": sum(contract["print_contract"]["mark_print_completed_command"] for contract in contracts),
            "statement_command_count": sum(contract["statement_contract"]["legacy_save_signal"] for contract in contracts),
            "golden_case_count": len(cases),
            "golden_case_category_counts": dict(sorted(Counter(case["category"] for case in cases).items())),
            "legacy_execution_allowed_count": sum(case["legacy_execution_allowed"] for case in cases),
            "result_parity_proven_contract_count": 0,
            "validation_error_count": len(errors),
        },
        "contracts": contracts,
        "golden_cases": cases,
        "acceptance_gate": [
            "Every query enforces identity/context scope, bounded filters, stable pagination and provenance.",
            "Preview/export never marks a document printed or mutates ERP state.",
            "Print-completed and statement writes use separate authorized idempotent commands with expected_version.",
            "Owner-approved Golden values prove calculations and totals before parity or release claims.",
        ],
        "validation_errors": errors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

