"""Build an isolated target statement-parser and staging contract."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--import-boundary", required=True, type=Path)
    parser.add_argument("--parser-row", required=True, type=Path)
    parser.add_argument("--persistence-boundary", required=True, type=Path)
    parser.add_argument("--profile-target", required=True, type=Path)
    parser.add_argument("--owner-decisions", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {
        "import_boundary": args.import_boundary,
        "parser_row": args.parser_row,
        "persistence_boundary": args.persistence_boundary,
        "profile_target": args.profile_target,
        "owner_decisions": args.owner_decisions,
    }
    inputs = {name: _load(path) for name, path in paths.items()}
    invalid = sorted(name for name, value in inputs.items() if value.get("validation") != "PASS")
    row_source = inputs["parser_row"]
    decisions = inputs["owner_decisions"]
    canonical = row_source["target_contract"]["canonical_columns_are_schema_validated_before_commit"]
    decision_ids = {"BR-DEC-002", "BR-DEC-003", "BR-DEC-004"}
    relevant_decisions = [row for row in decisions["decisions"] if row["decision_id"] in decision_ids]

    entities = [
        {
            "entity": "BankStatementImportJob",
            "fields": [
                "import_job_id", "bank_account_id", "profile_id", "profile_version",
                "profile_content_sha256", "state", "expected_version", "idempotency_key",
                "source_content_sha256", "created_by_actor_id", "created_at", "expires_at",
            ],
        },
        {
            "entity": "BankStatementStagedRow",
            "fields": [
                "staged_row_id", "import_job_id", "source_row_ordinal", "voucher_date",
                "description", "debit", "credit", "voucher_no", "balance",
                "row_fingerprint", "validation_state", "expected_version",
            ],
        },
        {
            "entity": "BankStatementImportDiagnostic",
            "fields": [
                "diagnostic_id", "import_job_id", "source_row_ordinal", "stable_code",
                "severity", "canonical_field", "safe_detail", "created_at",
            ],
        },
        {
            "entity": "BankStatementSourceObject",
            "fields": [
                "source_object_id", "import_job_id", "content_sha256", "declared_format",
                "detected_format", "byte_length", "encrypted_object_reference", "retention_state",
            ],
        },
    ]
    states = [
        "UPLOADED", "PARSING", "PARSED_WITHOUT_ERRORS", "PARSED_WITH_ERRORS",
        "PREVIEWED", "COMMITTED", "REJECTED", "EXPIRED",
    ]
    pipeline = [
        "stream upload to bounded isolated object storage and compute content hash",
        "validate size, signature and allowlisted parser kind; extension alone is insufficient",
        "resolve one approved immutable profile version server-side",
        "parse in a resource-limited worker without Office automation, shell, SQL or filesystem path configuration",
        "normalize into the six canonical typed fields",
        "validate every row and persist stable diagnostics in staging only",
        "produce a read-only preview bound to job/profile/content hashes",
        "commit session header and all valid rows once in one target transaction after explicit command",
    ]
    invariants = [
        "no reconciliation session header is created before successful explicit commit",
        "parser failure leaves zero operational session or statement rows",
        "staging writes never target Varanegar or NGT operational tables",
        "raw SQL, provider, connection string, Office automation and configured filesystem paths are never executed",
        "profile id, version and content hash are identical across parse, preview and commit",
        "source content hash and scoped idempotency key prevent duplicate commit",
        "row fingerprint includes bank account, profile version, source hash, ordinal and canonical values",
        "debit and credit are independent signed decimals and malformed dual/zero rows follow recorded owner policy",
        "all six canonical fields are schema-checked before any commit",
        "diagnostics have stable codes and do not persist credentials, SQL or raw exception payloads",
        "commit uses expected version and a single application transaction owner",
        "audit and outbox append in the same commit transaction",
        "retry after an ambiguous response returns the original result",
        "source object retention and deletion are explicit auditable target policies",
    ]
    commands = [
        ["CreateImportJob", "bank_reconciliation.import_statement", None, "UPLOADED"],
        ["ParseImportJob", "bank_reconciliation.import_statement", "UPLOADED", "PARSED_*"],
        ["PreviewImportJob", "bank_reconciliation.view", "PARSED_WITHOUT_ERRORS", "PREVIEWED"],
        ["CommitImportJob", "bank_reconciliation.import_statement", "PREVIEWED", "COMMITTED"],
        ["RejectImportJob", "bank_reconciliation.import_statement", "nonterminal", "REJECTED"],
        ["ExpireImportJob", "system_retention_worker", "nonterminal expired", "EXPIRED"],
    ]
    acceptance = [
        "spoofed extension or signature mismatch is rejected before parser execution",
        "unsupported format is rejected before job can reach preview",
        "missing canonical column produces stable diagnostics and zero operational persistence",
        "invalid date or decimal produces a row-scoped stable diagnostic",
        "both debit and credit nonzero follows BR-DEC-002 and never silently drops credit",
        "both debit and credit zero follows BR-DEC-003 and is not silently committed",
        "HDR, start row, separator and text direction remain inert while BR-DEC-004 is not approved",
        "query metacharacters are treated as data and never alter a predicate",
        "mid-file parser failure leaves no operational header or partial rows",
        "mid-commit failure rolls back header, rows, audit and outbox",
        "same idempotency key and source hash commit at most once",
        "same row content in another bank account is not incorrectly suppressed",
        "profile version change after preview blocks commit",
        "closed operation date, denied account scope or disabled feature blocks commit with zero mutation",
        "expired source object cannot be committed",
        "diagnostic response contains no raw SQL, local path, credential or raw exception payload",
    ]
    errors: list[str] = []
    if invalid:
        errors.append("invalid inputs: " + ", ".join(invalid))
    if len(canonical) != 6:
        errors.append("canonical input column count changed")
    if {row["decision_id"] for row in relevant_decisions} != decision_ids:
        errors.append("required parser owner decisions missing")
    if any(row["decision_status"] != "NOT_APPROVED" for row in relevant_decisions):
        errors.append("parser owner-decision status changed and requires contract review")

    payload = {
        "artifact": "negin_erp_bank_statement_isolated_parser_and_atomic_staging_target_contract",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "status": "STAGING_CONTRACT_READY_NOT_IMPLEMENTED_OR_OWNER_APPROVED",
        "safety": {
            "mode": "OFFLINE_VALIDATED_ARTIFACT_COMPOSITION",
            "database_connections": 0,
            "live_ui_actions": 0,
            "source_or_target_commands_executed": 0,
            "business_rows_files_or_identity_values_read": 0,
            "owner_approvals_inferred": 0,
        },
        "source_facts": {
            "legacy_parser_count": row_source["summary"]["parser_count"],
            "canonical_columns": canonical,
            "legacy_profile_sql_executing_parser_count": row_source["summary"]["profile_sqlstatement_executing_parser_count"],
            "legacy_parser_consuming_hdr_count": row_source["summary"]["parser_consuming_hdr_argument_count"],
            "parser_decision_statuses": {row["decision_id"]: row["decision_status"] for row in relevant_decisions},
        },
        "summary": {
            "source_artifact_count": len(inputs),
            "entity_count": len(entities),
            "field_count": sum(len(row["fields"]) for row in entities),
            "state_count": len(states),
            "pipeline_stage_count": len(pipeline),
            "invariant_count": len(invariants),
            "command_contract_count": len(commands),
            "acceptance_obligation_count": len(acceptance),
            "approved_parser_owner_decision_count": 0,
            "implementation_execution_count": 0,
            "validation_error_count": len(errors),
        },
        "entities": entities,
        "states": states,
        "pipeline": pipeline,
        "invariants": invariants,
        "command_contracts": [
            {"command": row[0], "capability": row[1], "allowed_state": row[2], "result_state": row[3]}
            for row in commands
        ],
        "acceptance_obligations": acceptance,
        "validation_errors": errors,
        "limits": [
            "The current clone contains no real profile or statement fixture for row parity.",
            "Owner decisions BR-DEC-002/003/004 remain unapproved.",
            "No parser worker, object storage, target table or command is implemented by this artifact.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    print(json.dumps({"validation": payload["validation"], "summary": payload["summary"]}, ensure_ascii=False))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
