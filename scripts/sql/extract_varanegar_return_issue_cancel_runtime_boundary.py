"""Extract hash-pinned managed official-return issue/cancel call boundaries."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import dnfile
from dncil.cil.body.reader import read_method_body_from_bytes
from dncil.clr.token import StringToken, Token

WINDOWS_SCRIPTS = Path(__file__).resolve().parents[1] / "windows"
sys.path.insert(0, str(WINDOWS_SCRIPTS))
from extract_varanegar_targeted_il_contracts import _full_type_name, _owner_maps, _resolve_token  # noqa: E402

TARGETS = {
    "VN.SDS.Sales.UI.dll": {"VN.SDS.Sales.UI.RetSale.FormRetSaleList": {"CancelCommand"}},
    "VN.SDS.Sales.Business.dll": {"VN.SDS.Sales.Business.RetSale.RetSaleHandler": {
        "CancelRetSaleAndGenerateCancelRetSaleVocher", "GenerateRetSaleVocher"}},
    "VN.SDS.Sales.DataAccess.dll": {"VN.SDS.Sales.DataAccess.DataAdapter.RetSale.RetSaleAdapter": {
        "CancelRetSaleAndGenerateCancelRetSaleVocher", "GenerateRetSaleVocher"}},
}

SAFE_MEMBERS = {
    "Thunderstruck.DataContext..ctor", "Thunderstruck.DataContext.Execute", "Thunderstruck.DataContext.Query",
    "Thunderstruck.DataContext.Commit", "Thunderstruck.DataContext.RollBack", "Thunderstruck.DataContext.Dispose",
    "VN.SDS.Sales.Business.RetSale.RetSaleHandler.CancelRetSaleAndGenerateCancelRetSaleVocher",
    "VN.SDS.Sales.Business.RetSale.RetSaleHandler.GenerateRetSaleVocher",
    "VN.SDS.Sales.DataAccess.DataAdapter.RetSale.RetSaleAdapter.CancelRetSaleAndGenerateCancelRetSaleVocher",
    "VN.SDS.Sales.DataAccess.DataAdapter.RetSale.RetSaleAdapter.GenerateRetSaleVocher",
    "VN.SDS.MainData.IBusiness.OprDate.IOprDateHandler.CheckSetOprDate",
}
PROCEDURES = {"dbo.USP_SDSNET_GenerateRetSaleVocher", "dbo.usp_Sdsnet_RetSale_Save",
              "dbo.USP_SDSNET_GenerateCancelRetSaleVocher", "SLE.USP_SDSNET_CancelRetSaleHdr"}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _method(pe: dnfile.dnPE, assembly: str, owner: str, index: Any,
            method_owners: dict[int, str], field_owners: dict[int, str]) -> dict[str, Any]:
    body = read_method_body_from_bytes(pe.get_data(index.row.Rva, 524288))
    events, literals, procedures = [], [], set()
    for ins in body.instructions:
        operand = ins.operand
        if isinstance(operand, StringToken):
            item = pe.net.user_strings.get(operand.rid); value = "" if item is None else str(item.value)
            compact = " ".join(value.replace("[", "").replace("]", "").split())
            for procedure in PROCEDURES:
                if procedure.casefold() in compact.casefold(): procedures.add(procedure)
            literals.append({"sha256": hashlib.sha256(value.encode()).hexdigest(), "length": len(value),
                             "raw_value_persisted": False})
        elif isinstance(operand, Token):
            member = _resolve_token(pe, operand, method_owners, field_owners)
            if member in SAFE_MEMBERS:
                events.append({"offset": int(ins.offset), "opcode": ins.mnemonic, "member": member})
    return {"assembly_file": assembly, "type": owner, "method": str(index.row.Name),
            "instruction_count": len(body.instructions), "has_exception_regions": bool(body.exception_handlers),
            "event_ledger": events, "procedure_name_signals": sorted(procedures), "literal_fingerprints": literals}


def collect(source_directory: Path, binary_inventory: Path) -> dict[str, Any]:
    expected = {x["name"]: x["sha256"] for x in _load(binary_inventory)["files"]}
    sources, methods, errors = [], [], []
    for assembly, type_targets in TARGETS.items():
        path = source_directory / assembly; actual = hashlib.sha256(path.read_bytes()).hexdigest()
        match = actual == expected.get(assembly)
        sources.append({"assembly_file": assembly, "assembly_bytes": path.stat().st_size,
                        "assembly_sha256": actual, "inventory_sha256_match": match})
        if not match: errors.append({"assembly_file": assembly, "error": "inventory hash mismatch"})
        pe = dnfile.dnPE(str(path)); method_owners, field_owners = _owner_maps(pe)
        types = {_full_type_name(row): row for row in pe.net.mdtables.TypeDef.rows}
        for owner, selected in type_targets.items():
            type_row = types.get(owner)
            if type_row is None:
                errors.append({"assembly_file": assembly, "type": owner, "error": "type absent"}); continue
            found = set()
            for index in type_row.MethodList or []:
                row = index.row
                if row is None or not row.Rva or str(row.Name) not in selected: continue
                found.add(str(row.Name))
                try: methods.append(_method(pe, assembly, owner, index, method_owners, field_owners))
                except Exception as exc: errors.append({"assembly_file": assembly, "type": owner,
                                                        "method": str(row.Name), "error": type(exc).__name__})
            for missing in selected - found:
                errors.append({"assembly_file": assembly, "type": owner, "method": missing, "error": "method absent"})

    def chosen(owner: str, name: str) -> list[dict[str, Any]]:
        return [x for x in methods if x["type"] == owner and x["method"] == name]

    def offsets(method: dict[str, Any] | None, member: str) -> list[int]:
        return [] if method is None else [x["offset"] for x in method["event_ledger"] if x["member"] == member]

    ui_type = "VN.SDS.Sales.UI.RetSale.FormRetSaleList"
    business_type = "VN.SDS.Sales.Business.RetSale.RetSaleHandler"
    adapter_type = "VN.SDS.Sales.DataAccess.DataAdapter.RetSale.RetSaleAdapter"
    keys = [(ui_type,"CancelCommand"),(business_type,"CancelRetSaleAndGenerateCancelRetSaleVocher"),
            (business_type,"GenerateRetSaleVocher"),(adapter_type,"CancelRetSaleAndGenerateCancelRetSaleVocher"),
            (adapter_type,"GenerateRetSaleVocher")]
    selections = {(owner,name): chosen(owner,name) for owner,name in keys}
    if not all(len(rows) == 1 for rows in selections.values()): errors.append({"error": "selected runtime coverage incomplete"})
    get = lambda owner,name: selections[(owner,name)][0] if len(selections[(owner,name)]) == 1 else None
    ui, bc, bg, ac, ag = [get(*key) for key in keys]
    context, commit, rollback = "Thunderstruck.DataContext..ctor", "Thunderstruck.DataContext.Commit", "Thunderstruck.DataContext.RollBack"
    bc_call = "VN.SDS.Sales.Business.RetSale.RetSaleHandler.CancelRetSaleAndGenerateCancelRetSaleVocher"
    ac_call = "VN.SDS.Sales.DataAccess.DataAdapter.RetSale.RetSaleAdapter.CancelRetSaleAndGenerateCancelRetSaleVocher"
    ag_call = "VN.SDS.Sales.DataAccess.DataAdapter.RetSale.RetSaleAdapter.GenerateRetSaleVocher"
    contract = {
        "ui_cancel_calls_business_without_explicit_context_commit_or_rollback": bool(offsets(ui,bc_call) and not offsets(ui,context) and not offsets(ui,commit) and not offsets(ui,rollback)),
        "business_cancel_is_thin_adapter_delegate": bool(offsets(bc,ac_call) and not offsets(bc,context) and not offsets(bc,commit) and not offsets(bc,rollback)),
        "business_generate_is_thin_adapter_delegate": bool(offsets(bg,ag_call) and not offsets(bg,context) and not offsets(bg,commit) and not offsets(bg,rollback)),
        "adapter_cancel_uses_named_save_or_cancel_procedures": bool(ac and set(ac["procedure_name_signals"]) & {"dbo.usp_Sdsnet_RetSale_Save","dbo.USP_SDSNET_GenerateCancelRetSaleVocher","SLE.USP_SDSNET_CancelRetSaleHdr"}),
        "adapter_generate_uses_named_generator": bool(ag and "dbo.USP_SDSNET_GenerateRetSaleVocher" in ag["procedure_name_signals"]),
        "adapter_cancel_context_query_or_execute": bool(offsets(ac,context) and (offsets(ac,"Thunderstruck.DataContext.Query") or offsets(ac,"Thunderstruck.DataContext.Execute"))),
        "adapter_generate_queries_named_generator_without_explicit_context_commit_or_rollback": bool(
            ag and offsets(ag,"Thunderstruck.DataContext.Query") and not offsets(ag,context)
            and not offsets(ag,commit) and not offsets(ag,rollback)
        ),
        "adapter_cancel_has_explicit_commit": bool(offsets(ac,commit)), "adapter_cancel_has_explicit_rollback": bool(offsets(ac,rollback)),
        "adapter_generate_has_explicit_commit": bool(offsets(ag,commit)), "adapter_generate_has_explicit_rollback": bool(offsets(ag,rollback)),
        "managed_to_sql_physical_transaction_enlistment_proven": False,
    }
    return {"artifact": "varanegar_return_issue_cancel_runtime_boundary", "schema_version": 1,
            "generated_at": datetime.now().astimezone().isoformat(), "validation": "PASS" if not errors else "FAIL",
            "source": sources,
            "safety": {"mode": "STATIC_HASH_PINNED_PE_METADATA_AND_IL_ONLY", "assembly_loads_or_executions": 0,
                       "application_form_or_command_executions": 0, "database_connections": 0,
                       "configuration_return_sale_customer_user_or_host_values_read": 0,
                       "raw_string_sql_or_identifier_literals_persisted": 0, "source_or_target_state_changed": 0},
            "summary": {"assembly_count": len(sources), "selected_method_count": len(methods),
                        "selected_instruction_count": sum(x["instruction_count"] for x in methods),
                        "source_hash_mismatch_count": sum(not x["inventory_sha256_match"] for x in sources),
                        "method_or_coverage_error_count": len(errors)},
            "managed_return_contract": contract, "method_contracts": methods, "errors": errors,
            "evidence_limits": ["Linear IL proves call presence, not branch execution or successful effects.",
                                "SQL-local transaction enlistment with managed DataContext is not inferred.",
                                "Only allowlisted procedure names are retained; raw literals and business identifiers are not persisted.",
                                "Assemblies were never loaded or executed."]}


def main() -> int:
    logging.getLogger("dnfile").setLevel(logging.CRITICAL); p=argparse.ArgumentParser()
    p.add_argument("--source-directory",required=True,type=Path);p.add_argument("--binary-inventory",required=True,type=Path);p.add_argument("--output",required=True,type=Path);a=p.parse_args()
    payload=collect(a.source_directory,a.binary_inventory);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(a.output.resolve());print(json.dumps(payload["summary"],ensure_ascii=False));print(json.dumps(payload["managed_return_contract"],ensure_ascii=False));return 0 if payload["validation"]=="PASS" else 1


if __name__ == "__main__": raise SystemExit(main())
