"""Validate and inventory the durable Varanegar reconstruction bundle.

This tool reads only local extractor/doc/artifact files. It never connects to
Varanegar and writes only the requested machine-readable manifest.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import py_compile
import re
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "docs" / "varanegar_reconstruction" / "README_FA.md"
DISCOVERY_LOG = ROOT / "docs" / "varanegar_reconstruction" / "DISCOVERY_LOG_FA.md"
FOUR_HOUR_REPORT = ROOT / "docs" / "varanegar_reconstruction" / "FOUR_HOUR_ANALYSIS_20260826_FA.md"
THREE_MONTH_REPORT = ROOT / "docs" / "varanegar_reconstruction" / "THREE_MONTH_OPERATIONAL_ACTIVITY_20260826_FA.md"
THREE_MONTH_ARTIFACT = ROOT / "artifacts" / "varanegar_analysis" / "three_month_operational_activity_20260826.json"
THREE_MONTH_BUILDER = ROOT / "scripts" / "sql" / "build_varanegar_three_month_activity.py"
READINESS_MATRIX = ROOT / "docs" / "varanegar_reconstruction" / "RECONSTRUCTION_READINESS_MATRIX_20260826_FA.md"
CHECKPOINT = ROOT / "docs" / "varanegar_reconstruction" / "CHECKPOINT_20260826_FA.md"
EVIDENCE_TEST = ROOT / "tests" / "test_varanegar_reconstruction_evidence.py"

DOMAINS: tuple[dict[str, Any], ...] = (
    {"stage": 1, "slug": "organization_and_fiscal_year", "extractor": "extract_varanegar_org_domain.py", "artifact": "organization_and_fiscal_year_20260826.json", "doc": "01_ORGANIZATION_AND_FISCAL_YEAR_FA.md"},
    {"stage": 2, "slug": "geography_and_routes", "extractor": "extract_varanegar_geography_domain.py", "artifact": "geography_and_routes_20260826.json", "doc": "02_GEOGRAPHY_AND_ROUTES_FA.md"},
    {"stage": 3, "slug": "units_stock_and_document_types", "extractor": "extract_varanegar_units_documents_domain.py", "artifact": "units_stock_and_document_types_20260826.json", "doc": "03_UNITS_STOCK_AND_DOCUMENT_TYPES_FA.md"},
    {"stage": 4, "slug": "product_catalog", "extractor": "extract_varanegar_product_catalog_domain.py", "artifact": "product_catalog_20260826.json", "doc": "04_PRODUCT_CATALOG_FA.md"},
    {"stage": 5, "slug": "parties_customers_suppliers_personnel", "extractor": "extract_varanegar_party_domain.py", "artifact": "parties_customers_suppliers_personnel_20260826.json", "doc": "05_PARTIES_CUSTOMERS_SUPPLIERS_PERSONNEL_FA.md"},
    {"stage": 6, "slug": "pricing_discounts_prizes", "extractor": "extract_varanegar_pricing_discount_domain.py", "artifact": "pricing_discounts_prizes_20260826.json", "doc": "06_PRICING_DISCOUNTS_AND_PRIZES_FA.md"},
    {"stage": 7, "slug": "order_sale_lifecycle", "extractor": "extract_varanegar_order_sale_lifecycle_domain.py", "artifact": "order_sale_lifecycle_20260826.json", "doc": "07_ORDER_TO_SALE_LIFECYCLE_FA.md"},
    {"stage": 8, "slug": "inventory_reservation_and_exit", "extractor": "extract_varanegar_inventory_reservation_exit_domain.py", "artifact": "inventory_reservation_and_exit_20260826.json", "doc": "08_INVENTORY_RESERVATION_AND_EXIT_FA.md"},
    {"stage": 9, "slug": "distribution_delivery", "extractor": "extract_varanegar_distribution_delivery_domain.py", "artifact": "distribution_delivery_20260826.json", "doc": "09_DISTRIBUTION_AND_DELIVERY_FA.md"},
    {"stage": 10, "slug": "collections_payments_open_invoices", "extractor": "extract_varanegar_collection_payment_domain.py", "artifact": "collections_payments_open_invoices_20260826.json", "doc": "10_COLLECTIONS_PAYMENTS_OPEN_INVOICES_FA.md"},
    {"stage": 11, "slug": "sales_returns_and_settlement", "extractor": "extract_varanegar_sales_return_domain.py", "artifact": "sales_returns_and_settlement_20260826.json", "doc": "11_SALES_RETURNS_AND_SETTLEMENT_FA.md"},
    {"stage": 12, "slug": "received_cheque_lifecycle", "extractor": "extract_varanegar_received_cheque_domain.py", "artifact": "received_cheque_lifecycle_20260826.json", "doc": "12_RECEIVED_CHEQUE_LIFECYCLE_FA.md"},
    {"stage": 13, "slug": "supplier_purchase_and_payables", "extractor": "extract_varanegar_supplier_purchase_domain.py", "artifact": "supplier_purchase_and_payables_20260826.json", "doc": "13_SUPPLIER_PURCHASE_AND_PAYABLES_FA.md"},
    {"stage": 14, "slug": "supplier_disbursement_and_payable_cheques", "extractor": "extract_varanegar_supplier_disbursement_domain.py", "artifact": "supplier_disbursement_and_payable_cheques_20260826.json", "doc": "14_SUPPLIER_DISBURSEMENT_AND_PAYABLE_CHEQUES_FA.md"},
    {"stage": 15, "slug": "official_supplier_cardex_contract", "extractor": "extract_varanegar_supplier_cardex_contract.py", "artifact": "supplier_cardex_contract_20260826.json", "doc": "15_OFFICIAL_SUPPLIER_CARDEX_CONTRACT_FA.md"},
    {"stage": 16, "slug": "legacy_and_ngt_authorization", "extractor": "extract_varanegar_authorization_domain.py", "artifact": "authorization_legacy_ngt_20260826.json", "doc": "16_AUTHORIZATION_LEGACY_AND_NGT_FA.md"},
    {"stage": 17, "slug": "configuration_and_rule_flags", "extractor": "extract_varanegar_configuration_domain.py", "artifact": "configuration_and_rule_flags_20260826.json", "doc": "17_CONFIGURATION_AND_RULE_FLAGS_FA.md"},
    {"stage": 18, "slug": "general_ledger_staging_and_posting", "extractor": "extract_varanegar_general_ledger_domain.py", "artifact": "general_ledger_staging_and_posting_20260826.json", "doc": "18_GENERAL_LEDGER_STAGING_AND_POSTING_FA.md"},
)

FORBIDDEN_LITERALS = (
    "sql_password", "password=", "pwd=", "user id=", "data source=",
    "initial catalog=", "authorization: bearer", "sk-proj-", "-----begin private key-----",
)

FORBIDDEN_SQL_STATEMENT = re.compile(
    r"(?im)(?:^|;)\s*(?:INSERT|UPDATE|DELETE|MERGE|EXEC(?:UTE)?|CREATE|ALTER|DROP|TRUNCATE|GRANT|REVOKE|DENY)\b"
)

DOMAIN_FORBIDDEN_DATA_KEYS: dict[int, set[str]] = {
    5: {
        "CustomerName", "CustName", "SupplierName", "PersonnelName",
        "ContactName", "NationalCode", "NationalID", "NationalId", "Mobile",
        "Phone", "Address", "Email", "UserName", "Username", "Password",
        "PasswordHash", "Hash", "SecurityStamp", "Token",
    },
    10: {
        "CustomerName", "CustName", "ChequeNo", "ChqNo", "SayadNo",
        "AccountNo", "IBAN", "CardNo", "Comment", "Description",
    },
    12: {
        "CustomerName", "CustName", "ChequeNo", "ChqNo", "SayadNo",
        "AccountNo", "IBAN", "CardNo", "Comment", "Description",
    },
    14: {
        "SupplierName", "ChequeNo", "ChqNo", "SayadNo", "AccountNo",
        "IBAN", "CardNo", "Comment", "Description",
    },
    15: {
        "SupplierName", "ContactName", "ChequeNo", "ChqNo", "SayadNo",
        "AccountNo", "IBAN", "Comment", "Description",
    },
    16: {
        "Name", "UserName", "Username", "Password", "PasswordHash", "Hash",
        "SecurityStamp", "Token", "Email", "Phone", "Mobile",
    },
    17: {
        "KeyValue", "KeyValueOld", "Password", "PWD", "Token", "Secret",
        "Url", "URL", "Path", "HostName", "Hostname", "ApplicationName",
        "UserName", "Username", "DeviceOwner", "OwnerName",
    },
    18: {
        "VoucherComment", "VoucherItemComment", "PreVoucherComment",
        "PreVoucherItemComment", "ReferenceNo", "ReferenceName", "SLCode",
        "DLCode", "FifthLedgerCode", "SixthLedgerCode", "SeventhLedgerCode",
        "SQLUserName", "Hostname", "ApplicationName", "AppUserId",
        "ModifiedAppUserId", "ConfirmAPPUserId", "CustId", "SupplierId",
        "ContactId", "SimpleQuery", "definition_text", "sql_definition",
    },
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_safety(payload: dict[str, Any], stage: int) -> None:
    safety = payload.get("safety") or payload.get("source", {}).get("safety")
    if not safety:
        raise AssertionError(f"stage {stage}: safety block missing")
    if safety.get("updateability") != "READ_ONLY":
        raise AssertionError(f"stage {stage}: database is not recorded READ_ONLY")
    if safety.get("can_update") != 0:
        raise AssertionError(f"stage {stage}: can_update is not zero")
    if safety.get("denies_data_writes") != 1:
        raise AssertionError(f"stage {stage}: deny-data-writer evidence missing")


def _scan(text: str, label: str) -> None:
    lowered = text.lower()
    hits = [x for x in FORBIDDEN_LITERALS if x in lowered]
    if hits:
        raise AssertionError(f"{label}: forbidden credential-like literals: {hits}")


def _mapping_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        keys.update(str(key) for key in value)
        for child in value.values():
            keys.update(_mapping_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(_mapping_keys(child))
    return keys


def _validate_domain_privacy(payload: dict[str, Any], stage: int) -> None:
    forbidden = DOMAIN_FORBIDDEN_DATA_KEYS.get(stage, set())
    hits = sorted(forbidden & _mapping_keys(payload))
    if hits:
        raise AssertionError(
            f"stage {stage}: raw sensitive data keys escaped aggregate-only policy: {hits}"
        )


def _validate_extractor_is_read_only(path: Path, stage: int) -> None:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    sql_hits: list[str] = []
    forbidden_calls: list[str] = []
    def sql_literal(node: ast.AST) -> str:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.JoinedStr):
            return "".join(
                child.value if isinstance(child, ast.Constant) and isinstance(child.value, str)
                else "{expression}" for child in node.values
            )
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return sql_literal(node.left) + sql_literal(node.right)
        return ""

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr.lower() in {"commit", "executemany"}:
                forbidden_calls.append(node.func.attr)
            if node.func.attr.lower() == "execute" and node.args:
                match = FORBIDDEN_SQL_STATEMENT.search(sql_literal(node.args[0]))
                if match:
                    sql_hits.append(match.group(0).strip())
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "_rows" and len(node.args) >= 2):
            match = FORBIDDEN_SQL_STATEMENT.search(sql_literal(node.args[1]))
            if match:
                sql_hits.append(match.group(0).strip())
    if sql_hits or forbidden_calls:
        raise AssertionError(
            f"stage {stage}: extractor is not statically read-only: "
            f"sql={sorted(set(sql_hits))}, calls={sorted(set(forbidden_calls))}"
        )


def validate(output: Path) -> dict[str, Any]:
    readme = README.read_text(encoding="utf-8")
    log = DISCOVERY_LOG.read_text(encoding="utf-8")
    domain_rows: list[dict[str, Any]] = []
    seen_artifacts = set()

    for item in DOMAINS:
        extractor = ROOT / "scripts" / "sql" / item["extractor"]
        artifact = ROOT / "artifacts" / "varanegar_analysis" / "domains" / item["artifact"]
        doc = ROOT / "docs" / "varanegar_reconstruction" / "domains" / item["doc"]
        for path in (extractor, artifact, doc):
            if not path.is_file():
                raise AssertionError(f"stage {item['stage']}: missing {path}")
        if item["artifact"] in seen_artifacts:
            raise AssertionError(f"duplicate artifact mapping: {item['artifact']}")
        seen_artifacts.add(item["artifact"])
        py_compile.compile(str(extractor), doraise=True)
        _validate_extractor_is_read_only(extractor, item["stage"])
        payload = json.loads(artifact.read_text(encoding="utf-8"))
        _validate_safety(payload, item["stage"])
        _validate_domain_privacy(payload, item["stage"])
        for path in (artifact, doc):
            _scan(path.read_text(encoding="utf-8"), str(path.relative_to(ROOT)))
        doc_text = doc.read_text(encoding="utf-8")
        required_doc_markers = ("Golden Case", "ابهام", "دستور بازتولید")
        missing_markers = [marker for marker in required_doc_markers if marker not in doc_text]
        if missing_markers:
            raise AssertionError(
                f"stage {item['stage']}: incomplete domain document markers: {missing_markers}"
            )
        if "مدل مقصد" not in doc_text and "قرارداد مدل مقصد" not in doc_text:
            raise AssertionError(f"stage {item['stage']}: destination model/contract missing")
        if item["doc"] not in readme:
            raise AssertionError(f"stage {item['stage']}: README link missing")
        if item["artifact"] not in log or item["extractor"] not in log:
            raise AssertionError(f"stage {item['stage']}: discovery-log source link missing")
        domain_rows.append({
            "stage": item["stage"], "slug": item["slug"],
            "payload_domain": payload.get("domain"),
            "generated_at": payload.get("generated_at"),
            "extractor": str(extractor.relative_to(ROOT)).replace("\\", "/"),
            "artifact": str(artifact.relative_to(ROOT)).replace("\\", "/"),
            "document": str(doc.relative_to(ROOT)).replace("\\", "/"),
            "artifact_bytes": artifact.stat().st_size,
            "artifact_sha256": _sha256(artifact),
            "extractor_sha256": _sha256(extractor),
            "document_sha256": _sha256(doc),
            "table_count": len(payload.get("tables", [])),
            "formal_fk_count": len(payload.get("formal_foreign_keys", [])),
            "module_consumer_count": len(payload.get("module_consumers", [])),
            "implicit_link_count": len(payload.get("implicit_link_candidates", [])),
            "semantic_contract_count": len(payload.get("semantic_contract_sources", [])),
            "evidence_limit_count": len(payload.get("evidence_limits", [])),
            "validation": "PASS",
        })

    actual = {x.name for x in (ROOT / "artifacts" / "varanegar_analysis" / "domains").glob("*.json")}
    unexpected = sorted(actual - seen_artifacts)
    missing_from_directory = sorted(seen_artifacts - actual)
    if unexpected or missing_from_directory:
        raise AssertionError({"unexpected_artifacts": unexpected,
                              "missing_artifacts": missing_from_directory})

    for path in (FOUR_HOUR_REPORT, THREE_MONTH_REPORT, THREE_MONTH_ARTIFACT,
                 THREE_MONTH_BUILDER, EVIDENCE_TEST):
        if not path.is_file():
            raise AssertionError(f"missing cross-domain activity source: {path}")
    py_compile.compile(str(THREE_MONTH_BUILDER), doraise=True)
    py_compile.compile(str(EVIDENCE_TEST), doraise=True)
    three_month = json.loads(THREE_MONTH_ARTIFACT.read_text(encoding="utf-8"))
    if three_month.get("from") != "1405/03/01" or three_month.get("to") != "1405/05/31":
        raise AssertionError("three-month activity business-date range changed")
    if three_month.get("source_domain_count", 0) < 13 or three_month.get("window_block_count", 0) < 14:
        raise AssertionError("three-month activity lost expected source coverage")
    source_times = [source.get("source_generated_at") for source in three_month.get("sources", [])
                    if source.get("source_generated_at")]
    if not source_times or three_month.get("generated_at") != max(source_times):
        raise AssertionError("three-month derived artifact is not source-time deterministic")
    if THREE_MONTH_REPORT.name not in readme:
        raise AssertionError("three-month activity report missing from README")
    four_hour_text = FOUR_HOUR_REPORT.read_text(encoding="utf-8")
    if "۱۸ Extractor" not in four_hour_text or "۲۱ تا ۳۳ هفته" not in four_hour_text:
        raise AssertionError("four-hour report lost final scope or estimate")
    if not READINESS_MATRIX.is_file() or READINESS_MATRIX.name not in readme:
        raise AssertionError("reconstruction readiness matrix missing or unlinked")
    readiness_text = READINESS_MATRIX.read_text(encoding="utf-8")
    if "۲۱ تا ۳۳ هفته" not in readiness_text or "Definition of Done" not in readiness_text:
        raise AssertionError("readiness matrix lost estimate or definition of done")
    if not CHECKPOINT.is_file() or CHECKPOINT.name not in readme:
        raise AssertionError("continuation checkpoint missing or unlinked")
    checkpoint_text = CHECKPOINT.read_text(encoding="utf-8")
    if "domain_count=18" not in checkpoint_text or "7 passed" not in checkpoint_text:
        raise AssertionError("checkpoint lost expected verification contract")
    for path in (FOUR_HOUR_REPORT, THREE_MONTH_REPORT, THREE_MONTH_ARTIFACT,
                 READINESS_MATRIX, CHECKPOINT):
        _scan(path.read_text(encoding="utf-8"), str(path.relative_to(ROOT)))

    manifest = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "bundle": "varanegar_reconstruction_read_only_evidence",
        "workspace": str(ROOT),
        "validation": "PASS",
        "domain_count": len(domain_rows),
        "all_extractors_compile": True,
        "all_extractors_static_sql_is_read_only": True,
        "all_artifacts_parse": True,
        "all_artifacts_record_read_only_and_write_denial": True,
        "all_docs_linked_from_readme": True,
        "all_sources_registered_in_discovery_log": True,
        "all_domain_docs_have_golden_cases_open_questions_reproduction_and_target_contract": True,
        "forbidden_credential_literal_hits": 0,
        "sensitive_raw_data_key_hits": 0,
        "unexpected_domain_artifacts": [],
        "cross_domain_reports": [{
            "analysis": "four_hour_reconstruction_baseline",
            "document": str(FOUR_HOUR_REPORT.relative_to(ROOT)).replace("\\", "/"),
            "document_sha256": _sha256(FOUR_HOUR_REPORT),
            "domain_count": len(domain_rows),
            "validation": "PASS",
        }, {
            "analysis": three_month["analysis"],
            "from": three_month["from"], "to": three_month["to"],
            "source_domain_count": three_month["source_domain_count"],
            "window_block_count": three_month["window_block_count"],
            "artifact": str(THREE_MONTH_ARTIFACT.relative_to(ROOT)).replace("\\", "/"),
            "artifact_sha256": _sha256(THREE_MONTH_ARTIFACT),
            "document": str(THREE_MONTH_REPORT.relative_to(ROOT)).replace("\\", "/"),
            "document_sha256": _sha256(THREE_MONTH_REPORT),
            "builder": str(THREE_MONTH_BUILDER.relative_to(ROOT)).replace("\\", "/"),
            "builder_sha256": _sha256(THREE_MONTH_BUILDER),
            "validation": "PASS",
        }, {
            "analysis": "reconstruction_readiness_matrix",
            "document": str(READINESS_MATRIX.relative_to(ROOT)).replace("\\", "/"),
            "document_sha256": _sha256(READINESS_MATRIX),
            "domain_count": len(domain_rows),
            "validation": "PASS",
        }, {
            "analysis": "continuation_checkpoint",
            "document": str(CHECKPOINT.relative_to(ROOT)).replace("\\", "/"),
            "document_sha256": _sha256(CHECKPOINT),
            "domain_count": len(domain_rows),
            "validation": "PASS",
        }],
        "verification_tools": [{
            "path": str(EVIDENCE_TEST.relative_to(ROOT)).replace("\\", "/"),
            "sha256": _sha256(EVIDENCE_TEST),
            "expected_focused_result": "7 passed",
        }],
        "index_files": [{
            "path": str(README.relative_to(ROOT)).replace("\\", "/"),
            "sha256": _sha256(README),
        }, {
            "path": str(DISCOVERY_LOG.relative_to(ROOT)).replace("\\", "/"),
            "sha256": _sha256(DISCOVERY_LOG),
        }],
        "domains": domain_rows,
        "bundle_totals": {
            "artifact_bytes": sum(x["artifact_bytes"] for x in domain_rows),
            "recorded_table_slots": sum(x["table_count"] for x in domain_rows),
            "recorded_fk_slots": sum(x["formal_fk_count"] for x in domain_rows),
            "recorded_module_consumer_slots": sum(x["module_consumer_count"] for x in domain_rows),
            "recorded_implicit_link_slots": sum(x["implicit_link_count"] for x in domain_rows),
            "recorded_semantic_contract_slots": sum(x["semantic_contract_count"] for x in domain_rows),
        },
        "counting_note": "slot totals are per-domain evidence slots and may overlap across domains",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = validate(args.output)
    print(args.output.resolve())
    print(json.dumps({"validation": manifest["validation"],
                      "domain_count": manifest["domain_count"],
                      "bundle_totals": manifest["bundle_totals"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
