"""Extract the static runtime persistence boundary of Discount V2 order-to-sale EVC preparation."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import dnfile
from dncil.cil.body.reader import read_method_body_from_bytes
from dncil.clr.token import StringToken, Token

from extract_varanegar_targeted_il_contracts import _full_type_name, _owner_maps, _resolve_token


TARGETS: dict[str, dict[str, list[str]]] = {
    "VN.SDS.Sales.UI.dll": {
        "VN.SDS.Sales.UI.OrderToSale.FormOrderToSale": [
            "AcceptCommandDiscountV2",
            "AddCustomControlToToolTip",
            "CheckboxSaveTestDada_CheckedChanged",
            "SodorFactor_BackgroundWorker_DoWork",
        ],
    },
    "VN.SDS.Common.dll": {
        "VN.SDS.Common.Sales.EntityHelper.OrderToSale.CreateSaleByOrderHelper": [
            ".ctor",
            "get_CalcForDiscountV2",
            "set_CalcForDiscountV2",
        ],
    },
    "VN.SDS.Sales.Business.dll": {
        "VN.SDS.Sales.Business.EVC.EVCHandler": [
            "FillEVCUsingDiscountV2",
            "InitialCalcData",
            "ExtractCalcDataFromDB",
            "FillEVCByOrder",
            "GenerateOldSDSData",
            "ConvertCalcDataToEVCViewEntitis",
            "SaveEvcPackage",
            "GenerateZipPack",
            "CreateEVCSqlTempTableV2",
            "GetInstance",
        ],
        "VN.SDS.Sales.Business.Sale.SaleItemPaymentUsanceHandler": [
            "SaveSharpSaleSaleItemPaymentUsanceV2"
        ],
    },
    "VN.SDS.Sales.DataAccess.dll": {
        "VN.SDS.Sales.DataAccess.DataAdapter.EVC.EVCAdapter": [
            "CreateEVCSqlTempTableV2",
            "CreateEVCSqlTempTable",
            "CreateEVCItemFullV2SqlTempTable",
            "CreateSharpSaleItemPaymentUsance",
        ],
        "VN.SDS.Sales.DataAccess.DataAdapter.Sale.SaleItemPaymentUsanceAdapter": [
            "SaveSharpSaleSaleItemPaymentUsanceV2",
        ],
        "VN.SDS.Sales.DataAccess.DataAdapter.Order.OrderAdapter": [
            "CreateSaleByOrder",
        ],
    },
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_literal(value: str) -> str | None:
    compact = " ".join(value.split())
    lowered = compact.casefold()
    if any(
        token in lowered
        for token in (
            "exec ", "usp_", "tbl", "#", "temp", "evc", "vn.sds.container",
            "testdatadiscountv2", "orderno_", "oprdate_", "محاسبات تخفیف",
        )
    ):
        return compact
    return None


def _methods(pe: dnfile.dnPE, type_name: str, method_name: str) -> list[dict[str, Any]]:
    method_owners, field_owners = _owner_maps(pe)
    type_row = next(row for row in pe.net.mdtables.TypeDef.rows if _full_type_name(row) == type_name)
    result: list[dict[str, Any]] = []
    for occurrence, index in enumerate(
        item for item in (type_row.MethodList or []) if str(item.row.Name) == method_name and item.row.Rva
    ):
        row = index.row
        body = read_method_body_from_bytes(pe.get_data(row.Rva, 524288))
        members: list[str] = []
        member_call_counts: dict[str, int] = {}
        member_reference_offsets: dict[str, list[int]] = {}
        field_accesses: list[dict[str, Any]] = []
        literals: list[dict[str, Any]] = []
        numeric_constants: list[int] = []
        for instruction in body.instructions:
            operand = instruction.operand
            if isinstance(operand, StringToken):
                found = pe.net.user_strings.get(operand.rid)
                value = "" if found is None else str(found.value)
                entry: dict[str, Any] = {
                    "sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
                    "length": len(value),
                }
                safe = _safe_literal(value)
                if safe is not None:
                    entry["safe_literal"] = safe
                literals.append(entry)
            elif isinstance(operand, Token):
                member = _resolve_token(pe, operand, method_owners, field_owners)
                members.append(member)
                member_call_counts[member] = member_call_counts.get(member, 0) + 1
                member_reference_offsets.setdefault(member, []).append(int(instruction.offset))
                if member.endswith("EVCHandler.globalCalcData"):
                    field_accesses.append({"offset": int(instruction.offset), "opcode": instruction.mnemonic})
            if instruction.mnemonic.startswith("ldc.i4"):
                map_value = {f"ldc.i4.{n}": n for n in range(9)} | {"ldc.i4.m1": -1}
                if instruction.mnemonic in map_value:
                    numeric_constants.append(map_value[instruction.mnemonic])
                elif isinstance(operand, int):
                    numeric_constants.append(operand)
        result.append(
            {
                "type": type_name,
                "method": method_name,
                "occurrence": occurrence,
                "method_metadata_token": 0x06000000 | int(index.row_index),
                "parameter_names": [str(item.row.Name) for item in row.ParamList or []],
                "instruction_count": len(body.instructions),
                "called_members": sorted(set(members)),
                "member_reference_counts": dict(sorted(member_call_counts.items())),
                "member_reference_offsets": dict(sorted(member_reference_offsets.items())),
                "string_literals": literals,
                "numeric_constants": numeric_constants,
                "global_calc_data_field_accesses": field_accesses,
            }
        )
    return result


def collect(source_directory: Path, binary_inventory: Path) -> dict[str, Any]:
    inventory = json.loads(binary_inventory.read_text(encoding="utf-8-sig"))
    expected = {row["name"]: row["sha256"] for row in inventory["files"]}
    sources: list[dict[str, Any]] = []
    methods: list[dict[str, Any]] = []
    for assembly_name, types in TARGETS.items():
        path = source_directory / assembly_name
        actual = _sha256(path)
        sources.append(
            {
                "assembly_file": assembly_name,
                "assembly_bytes": path.stat().st_size,
                "assembly_sha256": actual,
                "inventory_sha256_match": actual == expected.get(assembly_name),
            }
        )
        pe = dnfile.dnPE(str(path))
        for type_name, method_names in types.items():
            for method_name in method_names:
                methods.extend(_methods(pe, type_name, method_name))

    scan_members = {
        "calc_flag_setter": "VN.SDS.Common.Sales.EntityHelper.OrderToSale.CreateSaleByOrderHelper.set_CalcForDiscountV2",
        "helper_constructor": "VN.SDS.Common.Sales.EntityHelper.OrderToSale.CreateSaleByOrderHelper..ctor",
        "discount_v2_entry": "VN.SDS.Sales.Business.Order.OrderHandler.CreateSaleByOrderUsingDiscountV2",
    }
    member_callsites: dict[str, list[dict[str, Any]]] = {key: [] for key in scan_members}
    double_temp_literal_files: list[str] = []
    double_temp_create_literal_files: list[str] = []
    single_temp_create_literal_files: list[str] = []
    managed_scan_count = 0
    managed_parse_error_count = 0
    for item in inventory["files"]:
        path = source_directory / item["name"]
        if not path.is_file() or path.suffix.casefold() != ".dll":
            continue
        try:
            raw_bytes = path.read_bytes()
            if "#SaleSaleItemPaymentUsance".encode("utf-16le") in raw_bytes:
                double_temp_literal_files.append(item["name"])
            if "CREATE TABLE #SaleSaleItemPaymentUsance".upper().encode("utf-16le") in raw_bytes.upper():
                double_temp_create_literal_files.append(item["name"])
            if "CREATE TABLE #SaleItemPaymentUsance".upper().encode("utf-16le") in raw_bytes.upper():
                single_temp_create_literal_files.append(item["name"])
            pe = dnfile.dnPE(str(path))
            if not pe.net or not pe.net.mdtables.TypeDef:
                continue
            managed_scan_count += 1
            method_owners, field_owners = _owner_maps(pe)
            for type_row in pe.net.mdtables.TypeDef.rows:
                owner = _full_type_name(type_row)
                for index in type_row.MethodList or []:
                    row = index.row
                    if row is None or not row.Rva:
                        continue
                    try:
                        body = read_method_body_from_bytes(pe.get_data(row.Rva, 524288))
                    except Exception:
                        continue
                    resolved = {
                        _resolve_token(pe, instruction.operand, method_owners, field_owners)
                        for instruction in body.instructions
                        if isinstance(instruction.operand, Token)
                        and not isinstance(instruction.operand, StringToken)
                    }
                    for key, member in scan_members.items():
                        if member in resolved:
                            member_callsites[key].append(
                                {"assembly_file": item["name"], "type": owner, "method": str(row.Name)}
                            )
        except Exception:
            managed_parse_error_count += 1

    by_name = {(row["type"], row["method"]): row for row in methods}
    fill = by_name[("VN.SDS.Sales.Business.EVC.EVCHandler", "FillEVCUsingDiscountV2")]
    extract = by_name[("VN.SDS.Sales.Business.EVC.EVCHandler", "ExtractCalcDataFromDB")]
    initial = by_name[("VN.SDS.Sales.Business.EVC.EVCHandler", "InitialCalcData")]
    fill_order = by_name[("VN.SDS.Sales.Business.EVC.EVCHandler", "FillEVCByOrder")]
    generate_old = by_name[("VN.SDS.Sales.Business.EVC.EVCHandler", "GenerateOldSDSData")]
    get_instance = by_name[("VN.SDS.Sales.Business.EVC.EVCHandler", "GetInstance")]
    ui_accept_v2 = by_name[("VN.SDS.Sales.UI.OrderToSale.FormOrderToSale", "AcceptCommandDiscountV2")]
    ui_worker = by_name[("VN.SDS.Sales.UI.OrderToSale.FormOrderToSale", "SodorFactor_BackgroundWorker_DoWork")]
    ui_add_controls = by_name[("VN.SDS.Sales.UI.OrderToSale.FormOrderToSale", "AddCustomControlToToolTip")]
    generate_zip = by_name[("VN.SDS.Sales.Business.EVC.EVCHandler", "GenerateZipPack")]
    usance = by_name[(
        "VN.SDS.Sales.Business.Sale.SaleItemPaymentUsanceHandler",
        "SaveSharpSaleSaleItemPaymentUsanceV2",
    )]
    usance_adapter = by_name[(
        "VN.SDS.Sales.DataAccess.DataAdapter.Sale.SaleItemPaymentUsanceAdapter",
        "SaveSharpSaleSaleItemPaymentUsanceV2",
    )]
    assertions = {
        "source_hashes_match_inventory": all(row["inventory_sha256_match"] for row in sources),
        "all_selected_methods_found_once": len(methods) == sum(
            len(names) for types in TARGETS.values() for names in types.values()
        ),
        "fill_uses_entity_save_command": "TypeSpecRow.SaveCommand" in fill["called_members"],
        "fill_persists_sharp_payment_usances": any(
            member.endswith("SaleItemPaymentUsanceHandler.SaveSharpSaleSaleItemPaymentUsanceV2")
            for member in fill["called_members"]
        ),
        "extract_creates_and_fills_evc_sql_staging": all(
            any(member.endswith(suffix) for member in extract["called_members"])
            for suffix in ("EVCHandler.CreateEVCSqlTempTableV2", "EVCHandler.FillEVCByOrder")
        ),
        "fill_order_executes_sql": "Thunderstruck.DataContext.Execute" in fill_order["called_members"],
        "old_path_calls_do_evc": any(
            literal.get("safe_literal", "").casefold().startswith("exec sle.usp_doevc")
            for literal in generate_old["string_literals"]
        ),
        "payment_usance_delegates_with_passed_context": any(
            member.endswith("SaleItemPaymentUsanceAdapter.SaveSharpSaleSaleItemPaymentUsanceV2")
            for member in usance["called_members"]
        )
        and any(
            member in {"Thunderstruck.DataContext.Execute", "Thunderstruck.DataContext.GetValue"}
            for member in usance_adapter["called_members"]
        ),
        "calc_flag_has_no_typed_setter_after_constructor": member_callsites["calc_flag_setter"]
        == [
            {
                "assembly_file": "VN.SDS.Common.dll",
                "type": "VN.SDS.Common.Sales.EntityHelper.OrderToSale.CreateSaleByOrderHelper",
                "method": ".ctor",
            }
        ],
        "discount_v2_entry_is_reached_from_order_to_sale_form": any(
            row["type"] == "VN.SDS.Sales.UI.OrderToSale.FormOrderToSale"
            for row in member_callsites["discount_v2_entry"]
        ),
        "no_managed_create_literal_for_double_temp_name": len(double_temp_create_literal_files) == 0,
        "global_calc_data_is_instance_not_static_field_access": all(
            access["opcode"] in {"ldfld", "stfld"}
            for method in methods
            for access in method["global_calc_data_field_accesses"]
        )
        and any(
            access["opcode"] == "stfld"
            for method in methods
            for access in method["global_calc_data_field_accesses"]
        ),
        "get_instance_constructs_fresh_evc_handler": (
            "VN.SDS.Sales.Business.EVC.EVCHandler..ctor" in get_instance["called_members"]
        ),
        "selected_v2_load_path_has_35_direct_context_reads": (
            initial["member_reference_counts"].get("Thunderstruck.DataContext.AllRawEntity", 0) == 17
            and initial["member_reference_counts"].get("Thunderstruck.DataContext.GetValue", 0) == 1
            and extract["member_reference_counts"].get("Thunderstruck.DataContext.AllRawEntity", 0) == 17
        ),
        "selected_v2_load_paths_inject_sds_advanced_condition_helper_into_calcdata": (
            initial["member_reference_offsets"].get(
                "DicountV2SqlServerSDS.AdvanceConditionSqlHelper..ctor"
            ) == [32]
            and initial["member_reference_offsets"].get(
                "DiscountV2.Entity.Internal.CalcData..ctor"
            ) == [37]
            and extract["member_reference_offsets"].get(
                "DicountV2SqlServerSDS.AdvanceConditionSqlHelper..ctor"
            ) == [29]
            and extract["member_reference_offsets"].get(
                "DiscountV2.Entity.Internal.CalcData..ctor"
            ) == [34]
            and not any(
                "DicountV2SqlServer.AdvanceConditionSqlHelper" in member
                for row in (initial, extract)
                for member in row["called_members"]
            )
        ),
        "desktop_v2_accept_runs_inside_background_worker": (
            "VN.SDS.Sales.Business.Order.OrderHandler.CreateSaleByOrderUsingDiscountV2"
            in ui_accept_v2["called_members"]
            and "System.ComponentModel.BackgroundWorker.ReportProgress" in ui_accept_v2["called_members"]
            and "VN.SDS.Sales.UI.OrderToSale.FormOrderToSale.AcceptCommandDiscountV2"
            in ui_worker["called_members"]
        ),
        "discount_v2_toolbar_exposes_unpermissioned_test_data_checkbox": (
            "VN.SDS.Common.MainData.Entity.ServerConfig.ServerConfigEntity.get_IsDiscountV2Active"
            in ui_add_controls["called_members"]
            and "System.Windows.Forms.CheckBox.set_Checked" in ui_add_controls["called_members"]
            and not any(
                "Permission" in member or "Authorize" in member
                for member in ui_add_controls["called_members"]
            )
        ),
        "test_data_export_serializes_full_calcdata_to_gzip_bytes": all(
            member in generate_zip["called_members"]
            for member in (
                "Newtonsoft.Json.JsonConvert.SerializeObject",
                "System.IO.Compression.GZipStream..ctor",
                "System.IO.File.WriteAllBytes",
                "System.IO.Directory.CreateDirectory",
            )
        ),
        "test_data_export_has_no_named_encryption_call": not any(
            "Cryptography" in member or "Encrypt" in member
            for member in generate_zip["called_members"]
        ),
        "batch_cancellation_is_checked_before_each_selected_conversion_not_inside_db_call": (
            ui_accept_v2["member_reference_offsets"].get(
                "System.ComponentModel.BackgroundWorker.get_CancellationPending"
            )
            == [190]
            and ui_accept_v2["member_reference_offsets"].get(
                "VN.SDS.Sales.Business.Order.OrderHandler.CreateSaleByOrderUsingDiscountV2"
            )
            == [917]
            and not any(
                "DbCommand.Cancel" in member or "CancellationToken" in member
                for member in ui_accept_v2["called_members"]
            )
        ),
        "diagnostic_export_executes_legacy_do_evc_before_managed_promotion": (
            fill["member_reference_offsets"].get(
                "VN.SDS.Sales.Business.EVC.EVCHandler.GenerateOldSDSData"
            )
            == [392]
            and fill["member_reference_offsets"].get(
                "VN.SDS.Sales.Business.EVC.EVCHandler.CalcOrderPromotion"
            )
            == [542]
            and any(
                literal.get("safe_literal", "").casefold().startswith("exec sle.usp_doevc")
                for literal in generate_old["string_literals"]
            )
        ),
        "assemblies_were_not_loaded_or_executed": True,
    }
    diagnostic_directory = source_directory / "TestDataDiscountV2"
    diagnostic_files = (
        [path for path in diagnostic_directory.iterdir() if path.is_file()]
        if diagnostic_directory.is_dir()
        else []
    )
    return {
        "artifact": "varanegar_order_sale_evc_runtime_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if all(assertions.values()) else "FAIL",
        "source": sources,
        "safety": {
            "mode": "STATIC_HASH_PINNED_PE_METADATA_AND_IL_ONLY",
            "assembly_loads_or_executions": 0,
            "database_connections": 0,
            "application_commands_executed": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "assembly_count": len(sources),
            "selected_method_count": len(methods),
            "selected_instruction_count": sum(row["instruction_count"] for row in methods),
            "safe_sql_literal_count": sum(
                1 for row in methods for literal in row["string_literals"] if "safe_literal" in literal
            ),
            "managed_inventory_assembly_scan_count": managed_scan_count,
            "managed_inventory_parse_error_count": managed_parse_error_count,
            "calc_for_discount_v2_setter_callsite_count": len(member_callsites["calc_flag_setter"]),
            "discount_v2_entry_callsite_count": len(member_callsites["discount_v2_entry"]),
            "global_calc_data_field_access_count": sum(
                len(method["global_calc_data_field_accesses"]) for method in methods
            ),
            "selected_sds_advanced_condition_helper_injection_count": sum(
                row["member_reference_counts"].get(
                    "DicountV2SqlServerSDS.AdvanceConditionSqlHelper..ctor", 0
                )
                for row in (initial, extract)
            ),
            "runtime_share_diagnostic_directory_exists": diagnostic_directory.is_dir(),
            "runtime_share_diagnostic_file_count": len(diagnostic_files),
            "runtime_share_diagnostic_total_bytes": sum(path.stat().st_size for path in diagnostic_files),
        },
        "methods": methods,
        "inventory_member_callsites": member_callsites,
        "inventory_temp_table_literal_scan": {
            "double_temp_name_literal_files": sorted(double_temp_literal_files),
            "double_temp_create_literal_files": sorted(double_temp_create_literal_files),
            "single_temp_create_literal_files": sorted(single_temp_create_literal_files),
        },
        "runtime_share_diagnostic_export_snapshot": {
            "relative_directory": "TestDataDiscountV2",
            "directory_exists": diagnostic_directory.is_dir(),
            "file_count": len(diagnostic_files),
            "total_bytes": sum(path.stat().st_size for path in diagnostic_files),
            "file_names_or_contents_persisted": 0,
        },
        "assertions": assertions,
        "limits": [
            "TypeSpec generic ownership is represented by the metadata resolver as TypeSpecRow; entity metadata and SQL inspection are required to name its target tables.",
            "Static IL proves reachable persistence calls, not that every branch ran in a historical conversion.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--binary-inventory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    logging.getLogger("dnfile").setLevel(logging.CRITICAL)
    logging.getLogger("dnfile.stream").setLevel(logging.CRITICAL)
    artifact = collect(args.source_directory, args.binary_inventory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    print(json.dumps(artifact["assertions"], ensure_ascii=False))
    print(artifact["validation"])
    return 0 if artifact["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
