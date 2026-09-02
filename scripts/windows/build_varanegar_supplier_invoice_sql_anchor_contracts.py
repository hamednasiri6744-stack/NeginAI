"""Resolve allowlisted supplier-invoice inline SQL into catalog target anchors."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path


DELETE_RE = re.compile(r"^\s*delete\s+from\s+([A-Za-z_][\w]*)\.([A-Za-z_][\w]*)\b", re.I)
TRIGGER_RE = re.compile(r"\b(?:enable|disable)\s+trigger\s+([A-Za-z_][\w]*)\b", re.I)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--supplier-contract", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    source = json.loads(args.supplier_contract.read_text(encoding="utf-8-sig"))
    targets: set[str] = set()
    triggers: set[str] = set()
    provenance = []
    for row in source["static_sql_literals"]:
        literal = row["safe_literal"]
        delete = DELETE_RE.search(literal)
        trigger = TRIGGER_RE.search(literal)
        if delete:
            targets.add(f"{delete.group(1)}.{delete.group(2)}")
        if trigger:
            triggers.add(trigger.group(1))
        provenance.append({
            "data_access_type": row["data_access_type"],
            "method": row["method"],
            "literal_sha256": row["sha256"],
            "resolved_delete_target": f"{delete.group(1)}.{delete.group(2)}" if delete else None,
            "resolved_trigger_name": trigger.group(1) if trigger else None,
        })
    errors = []
    if targets != {"ica.tblSupInvInvoiceRelation"}:
        errors.append(f"unexpected delete targets: {sorted(targets)}")
    if triggers != {"tr_VN_PreventDeletetblSupInvInvoiceRelation"}:
        errors.append(f"unexpected trigger names: {sorted(triggers)}")
    modules = [{
        "object": "STATIC_INLINE_SUPPLIER_INVOICE_RELATION_DELETE_AND_TRIGGER_GUARD",
        "durable_mutation_targets": sorted(targets, key=str.casefold),
        "trigger_names": sorted(triggers, key=str.casefold),
        "runtime_executed": False,
    }]
    artifact = {
        "artifact": "varanegar_supplier_invoice_relation_inline_sql_catalog_anchor_contracts",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_PARSE_OF_ALLOWLISTED_STATIC_SQL_LITERALS",
            "database_connections": 0,
            "sql_statements_executed": 0,
            "row_values_read_or_persisted": 0,
        },
        "summary": {
            "source_literal_count": len(source["static_sql_literals"]),
            "resolved_durable_mutation_target_count": len(targets),
            "resolved_trigger_name_count": len(triggers),
            "runtime_executed_count": 0,
            "validation_error_count": len(errors),
        },
        "modules": modules,
        "provenance": provenance,
        "validation_errors": errors,
        "limits": [
            "The target and trigger name are static literal evidence; branch selection and runtime effects were not observed.",
            "Trigger enable/disable text is evidence to replace safely and was never executed.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
