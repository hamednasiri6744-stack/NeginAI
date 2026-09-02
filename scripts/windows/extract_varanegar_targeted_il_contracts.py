"""Read call graphs from a small allowlist of Varanegar UI types.

This tool never loads or executes an assembly. It parses PE metadata and IL for
explicitly selected form types. Non-allowlisted string literals are persisted
only as SHA-256 plus length.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any

import dnfile
from dncil.cil.body.reader import read_method_body_from_bytes
from dncil.clr.token import StringToken, Token


TARGETS = {
    "VN.SDS.Container.exe": {
        "VN.SDS.Container.MainForm",
        "VN.SDS.Container.Program",
    },
    "VN.SDS.Setting.Business.dll": {
        "VN.SDS.Setting.Business.AccessNodeInfo.AccessNodeInfoHandler",
        "VN.SDS.Setting.Business.MenuConfig.MenuConfigHandler",
    },
    "VN.SDS.Setting.DataAccess.dll": {
        "VN.SDS.Setting.DataAccess.DataAdapter.AccessNodeInfo.AccessNodeInfoAdapter",
        "VN.SDS.Setting.DataAccess.DataAdapter.MenuConfig.MenuConfigAdapter",
    },
    "TreasuryOld.DataAccess.dll": {
        "TreasuryOld.DataLayer.PChequeAdapter",
        "TreasuryOld.DataLayer.PChequeStatusAdapter",
        "TreasuryOld.DataLayer.RChequeAdapter",
        "TreasuryOld.DataLayer.RChequeStatusAdapter",
    },
    "TreasuryOld.Forms.dll": {
        "TreasuryOld.Forms.frmGuaranteeTracking",
        "TreasuryOld.Forms.frmPChequeTracking",
        "TreasuryOld.Forms.frmPChequeTrackingNew",
        "TreasuryOld.Forms.frmRBankDraftTracking",
        "TreasuryOld.Forms.frmRChequeTracking",
        "TreasuryOld.Forms.frmRChequeTrackingNew",
        "TreasuryOld.Forms.frmReportPreview",
        "TreasuryOld.Forms.frmReportPreviewMultiReport",
    },
    "VN.SDS.Stock.UI.dll": {
        "VN.SDS.Stock.UI.ProductionOrder.FormProductionOrderReport",
        "VN.SDS.Stock.UI.StockGoods.FormStockGoods",
        "VN.SDS.Stock.UI.StockGoods.FormStockGoodsDataEntry",
        "VN.SDS.Stock.UI.StockGoods.FormStockGoodsEdit",
        "VN.SDS.Stock.UI.StockGoods.FormStockGoods_Old",
        "VN.SDS.Stock.UI.StockGoods.Reports.FormProductionDetailReport",
        "VN.SDS.Stock.UI.StockGoods.Reports.FormReportResultList",
        "VN.SDS.Stock.UI.StockGoods.Reports.FormSelectGoodsType",
        "VN.SDS.Stock.UI.StockGoods.Reports.FormSelectMainReport",
        "VN.SDS.Stock.UI.VchHealthyCardex.FormVchHealthyCardex",
    },
    "VN.SDS.Stock.Business.dll": {
        "VN.SDS.Stock.Business.StockGoods.StockGoodsHandler",
        "VN.SDS.Stock.Business.StockGoods.StockGoodsValidator",
    },
    "VN.SDS.Stock.DataAccess.dll": {
        "VN.SDS.Stock.DataAccess.DataAdapter.StockGoods.StockGoodsAdapter",
    },
    "VN.SDS.Sales.UI.dll": {
        "VN.SDS.Sales.UI.CallCenterReports.FormCallCallCenterReports",
        "VN.SDS.Sales.UI.Customers.FormCurrencyCustCardex",
        "VN.SDS.Sales.UI.Customers.FormCustCardex",
        "VN.SDS.Sales.UI.DistManagement.FormChangeBatchNo",
        "VN.SDS.Sales.UI.DistManagement.FormDistManagementDataEntry",
        "VN.SDS.Sales.UI.DistManagement.FormDistManagementList",
        "VN.SDS.Sales.UI.DistManagement.FormExitExportationDataEntry",
        "VN.SDS.Sales.UI.DistManagement.FormFactorSelection",
        "VN.SDS.Sales.UI.DistManagement.FormFollowDist",
        "VN.SDS.Sales.UI.DistManagement.FormOrderToDist",
        "VN.SDS.Sales.UI.DistManagement.FormRemoveExitFromDistReason",
        "VN.SDS.Sales.UI.FinalDateManagement.FormFinalDateManagement",
        "VN.SDS.Sales.UI.Order.FormOrderPrizeInFollowVocher",
        "VN.SDS.Sales.UI.PrintBatch.FormPrintBatch",
        "VN.SDS.Sales.UI.PrintInvoice.FormPrintInvoice",
        "VN.SDS.Sales.UI.RetSale.FormReportRetSale",
        "VN.SDS.Sales.UI.Sale.FormFollowVocherDataEntry",
        "VN.SDS.Sales.UI.Sale.FormFollowVocherList",
        "VN.SDS.Sales.UI.Sale.FormReportFactor",
        "VN.SDS.Sales.UI.VocherFollowUp.FormVocherFollowUp",
    },
    "VN.SDS.Sales.Business.dll": {
        "VN.SDS.Sales.Business.Dist.DistHandler",
        "VN.SDS.Sales.Business.Dist.DistValidator",
    },
    "VN.SDS.Sales.DataAccess.dll": {
        "VN.SDS.Sales.DataAccess.DataAdapter.Dist.DistAdapter",
    },
    "VN.SDS.Treasury.UI.dll": {
        "VN.SDS.Treasury.UI.ReceiptManagment.FormReceiptManagmentTracking",
        "VN.SDS.Treasury.UI.Statement.FormStatement",
        "VN.SDS.Treasury.UI.Statement.FormStatementDataEntry",
    },
    "VN.SDS.MainData.UI.dll": {
        "VN.SDS.MainData.UI.Dashboard.PublicDashboard.FormMainDashboard",
        "VN.SDS.MainData.UI.Dashboard.PublicDashboard.MainUiDashboard.FormZoomChart",
        "VN.SDS.MainData.UI.Supplier.FormSupplierCardex",
    },
}

FORBIDDEN_LITERAL_PARTS = (
    "password=",
    "pwd=",
    "user id=",
    "data source=",
    "initial catalog=",
    "connection string",
    "authorization:",
    "bearer ",
    "http://",
    "https://",
    "sk-proj-",
)

SAFE_LITERAL = re.compile(r"^[A-Za-z0-9_ .(),=<>!%'+\-*/\[\]]{1,240}$")
SAFE_PERSIAN_UI_LITERAL = re.compile(
    r"^[\u0600-\u06ff\u200c\u200f\s:،؛؟().\-]{1,80}$"
)
BUSINESS_LITERAL = re.compile(
    r"(?:Cheque|Chq|Status|Stock|Goods|Item|Dist|Distribution|Sale|Order|"
    r"Voucher|Warehouse|DCRef|Ref|Id|Date|Type|Code|History|Permission|Menu|"
    r"Usp|usp|tbl|vw)",
    re.IGNORECASE,
)


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _full_type_name(row: Any) -> str:
    namespace = _text(getattr(row, "TypeNamespace", ""))
    name = _text(getattr(row, "TypeName", ""))
    if name:
        return f"{namespace}.{name}" if namespace else name
    return type(row).__name__


def _owner_maps(pe: dnfile.dnPE) -> tuple[dict[int, str], dict[int, str]]:
    method_owners: dict[int, str] = {}
    field_owners: dict[int, str] = {}
    table = getattr(pe.net.mdtables, "TypeDef", None)
    if not table:
        return method_owners, field_owners
    for type_row in table.rows:
        owner = _full_type_name(type_row)
        for index in type_row.MethodList or []:
            method_owners[index.row_index] = owner
        for index in type_row.FieldList or []:
            field_owners[index.row_index] = owner
    return method_owners, field_owners


def _resolve_member_ref(row: Any) -> str:
    parent = getattr(getattr(row, "Class", None), "row", None)
    parent_name = _full_type_name(parent) if parent is not None else "<unknown>"
    return f"{parent_name}.{_text(getattr(row, 'Name', ''))}"


def _resolve_token(
    pe: dnfile.dnPE,
    token: Token,
    method_owners: dict[int, str],
    field_owners: dict[int, str],
) -> str:
    table = pe.net.mdtables.tables.get(token.table)
    if table is None or token.rid <= 0 or token.rid > len(table.rows):
        return f"unresolved:{token.value:#010x}"
    row = table.rows[token.rid - 1]
    table_name = getattr(table, "name", "")
    if table_name == "MemberRef":
        return _resolve_member_ref(row)
    if table_name == "MethodDef":
        owner = method_owners.get(token.rid, "<unknown>")
        return f"{owner}.{_text(row.Name)}"
    if table_name == "Field":
        owner = field_owners.get(token.rid, "<unknown>")
        return f"{owner}.{_text(row.Name)}"
    if table_name in {"TypeDef", "TypeRef"}:
        return _full_type_name(row)
    if table_name == "MethodSpec":
        method_row = getattr(getattr(row, "Method", None), "row", None)
        if method_row is None:
            return "MethodSpec:<unknown>"
        if hasattr(method_row, "Class"):
            return _resolve_member_ref(method_row)
        return f"MethodSpec:{_text(getattr(method_row, 'Name', ''))}"
    return f"{table_name}:{_text(getattr(row, 'Name', ''))}"


def _literal_record(
    pe: dnfile.dnPE, token: StringToken, *, allow_persian_ui_text: bool = False
) -> dict[str, Any]:
    item = pe.net.user_strings.get(token.rid)
    value = "" if item is None else _text(item)
    lowered = value.casefold()
    is_safe_business = (
        bool(SAFE_LITERAL.fullmatch(value))
        and bool(BUSINESS_LITERAL.search(value))
        and not any(part in lowered for part in FORBIDDEN_LITERAL_PARTS)
        and "\\" not in value
        and "@" not in value
    )
    is_safe_ui = (
        allow_persian_ui_text
        and bool(SAFE_PERSIAN_UI_LITERAL.fullmatch(value))
        and bool(re.search(r"[\u0600-\u06ff]", value))
        and not any(part in lowered for part in FORBIDDEN_LITERAL_PARTS)
        and not any(character.isdigit() for character in value)
    )
    persisted_as = (
        "allowlisted_business_literal"
        if is_safe_business
        else "allowlisted_ui_literal"
        if is_safe_ui
        else "fingerprint_only"
    )
    record: dict[str, Any] = {
        "sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
        "length": len(value),
        "persisted_as": persisted_as,
    }
    if is_safe_business:
        record["safe_literal"] = value
    elif is_safe_ui:
        record["safe_ui_literal"] = value
    return record


def _analyze_assembly(path: Path, target_names: set[str]) -> dict[str, Any]:
    pe = dnfile.dnPE(str(path))
    method_owners, field_owners = _owner_maps(pe)
    type_table = getattr(pe.net.mdtables, "TypeDef", None)
    types_by_name = {
        _full_type_name(row): row for row in ([] if not type_table else type_table.rows)
    }

    target_types: list[dict[str, Any]] = []
    body_errors = 0
    body_error_details: list[dict[str, Any]] = []
    bodies_read = 0
    for target_name in sorted(target_names):
        type_row = types_by_name.get(target_name)
        if type_row is None:
            target_types.append({"type": target_name, "found": False, "methods": []})
            continue
        method_rows: list[dict[str, Any]] = []
        for method_index in type_row.MethodList or []:
            method = method_index.row
            if method is None or not method.Rva:
                continue
            try:
                body = read_method_body_from_bytes(pe.get_data(method.Rva, 65536))
            except Exception as exc:
                body_errors += 1
                body_error_details.append(
                    {
                        "type": target_name,
                        "method": _text(getattr(method, "Name", "")),
                        "rva": int(method.Rva),
                        "error_class": type(exc).__name__,
                    }
                )
                continue
            bodies_read += 1
            calls: set[str] = set()
            fields: set[str] = set()
            literals: list[dict[str, Any]] = []
            for instruction in body.instructions:
                operand = instruction.operand
                if instruction.mnemonic in {"call", "callvirt", "newobj"} and isinstance(
                    operand, Token
                ):
                    calls.add(
                        _resolve_token(pe, operand, method_owners, field_owners)
                    )
                elif "fld" in instruction.mnemonic and isinstance(operand, Token):
                    fields.add(
                        _resolve_token(pe, operand, method_owners, field_owners)
                    )
                elif isinstance(operand, StringToken):
                    literals.append(
                        _literal_record(
                            pe,
                            operand,
                            allow_persian_ui_text=_text(method.Name)
                            == "InitializeComponent",
                        )
                    )
            method_rows.append(
                {
                    "method": _text(method.Name),
                    "instruction_count": len(body.instructions),
                    "calls": sorted(calls),
                    "referenced_fields": sorted(fields),
                    "string_literals": literals,
                }
            )
        target_types.append(
            {
                "type": target_name,
                "found": True,
                "methods": sorted(method_rows, key=lambda row: row["method"]),
            }
        )
    return {
        "file": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "target_type_count": len(target_names),
        "found_type_count": sum(row["found"] for row in target_types),
        "method_bodies_read": bodies_read,
        "method_body_error_count": body_errors,
        "method_body_errors": body_error_details,
        "target_types": target_types,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    logging.getLogger("dnfile").setLevel(logging.ERROR)
    logging.getLogger("dnfile.stream").setLevel(logging.ERROR)

    assemblies = [
        _analyze_assembly(args.source_directory / file_name, target_names)
        for file_name, target_names in sorted(TARGETS.items())
    ]
    all_literals = [
        literal
        for assembly in assemblies
        for target_type in assembly["target_types"]
        for method in target_type["methods"]
        for literal in method["string_literals"]
    ]
    artifact = {
        "artifact": "varanegar_targeted_ui_il_contracts",
        "schema_version": 1,
        "generated_at": __import__("datetime").datetime.now().astimezone().isoformat(),
        "source": {
            "directory": str(args.source_directory),
            "target_files": sorted(TARGETS),
        },
        "safety": {
            "mode": "READ_ONLY_TARGETED_IL",
            "assemblies_loaded_or_executed": 0,
            "config_files_read": 0,
            "resource_payloads_read": 0,
            "raw_non_allowlisted_strings_persisted": 0,
            "targeted_method_bodies_read": sum(
                row["method_bodies_read"] for row in assemblies
            ),
        },
        "summary": {
            "assembly_count": len(assemblies),
            "target_type_count": sum(row["target_type_count"] for row in assemblies),
            "found_type_count": sum(row["found_type_count"] for row in assemblies),
            "method_body_error_count": sum(
                row["method_body_error_count"] for row in assemblies
            ),
            "string_literal_count": len(all_literals),
            "allowlisted_business_literal_count": sum(
                row["persisted_as"] == "allowlisted_business_literal"
                for row in all_literals
            ),
            "allowlisted_ui_literal_count": sum(
                row["persisted_as"] == "allowlisted_ui_literal"
                for row in all_literals
            ),
            "fingerprint_only_literal_count": sum(
                row["persisted_as"] == "fingerprint_only" for row in all_literals
            ),
        },
        "assemblies": assemblies,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    return 0 if artifact["summary"]["method_body_error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
