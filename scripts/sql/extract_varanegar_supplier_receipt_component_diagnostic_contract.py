"""Diagnose supplier-invoice/type-20 receipt reconciliation at relation-component scope.

The clone is read only. Source invoice/voucher/goods identifiers are processed
only in memory to build anonymous connected-component aggregates and are never
persisted in the output artifact. No business command or stored procedure runs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import dnfile
from dncil.cil.body.reader import read_method_body_from_bytes
from dncil.clr.token import StringToken, Token

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "windows"))
from extract_varanegar_targeted_il_contracts import (  # noqa: E402
    _full_type_name,
    _owner_maps,
    _resolve_token,
)

from extract_varanegar_org_domain import (
    DATABASE,
    SERVER,
    _assert_safe_target,
    _connect,
    _json_default,
    _rows,
)


class UnionFind:
    def __init__(self) -> None:
        self.parent: dict[tuple[str, int], tuple[str, int]] = {}

    def find(self, node: tuple[str, int]) -> tuple[str, int]:
        self.parent.setdefault(node, node)
        if self.parent[node] != node:
            self.parent[node] = self.find(self.parent[node])
        return self.parent[node]

    def union(self, left: tuple[str, int], right: tuple[str, int]) -> None:
        a, b = self.find(left), self.find(right)
        if a != b:
            self.parent[max(a, b)] = min(a, b)


def _classify(left: float, right: float) -> str:
    if abs(left) < 0.0001:
        return "receipt_only"
    if abs(right) < 0.0001:
        return "invoice_only"
    if abs(left - right) < 0.0001:
        return "exact"
    return "mismatch"


def _read_module(cursor: Any, schema: str, name: str) -> tuple[dict[str, Any], str]:
    row = _rows(
        cursor,
        f"""
        SELECT s.name schema_name,o.name object_name,o.type_desc,o.modify_date,
               DATALENGTH(m.definition) definition_bytes,m.definition
        FROM sys.sql_modules m
        JOIN sys.objects o ON o.object_id=m.object_id
        JOIN sys.schemas s ON s.schema_id=o.schema_id
        WHERE s.name='{schema}' AND o.name='{name}'
        """,
    )[0]
    definition = row.pop("definition")
    return row, definition


def _module_contract(cursor: Any) -> dict[str, Any]:
    row, definition = _read_module(cursor, "ICA", "usp_ApplySupInvoice")
    normalized = re.sub(r"\s+", " ", definition).casefold()
    return {
        **row,
        "qualified_name": "ICA.usp_ApplySupInvoice",
        "definition_sha256": hashlib.sha256(definition.encode("utf-8")).hexdigest(),
        "aggregates_supplied_invoice_list_by_goods": (
            "from ica.tblsupinvoiceitm" in normalized
            and "@supinvoiceidlisttype" in normalized
            and "group by i.goodsref" in normalized
        ),
        "aggregates_supplied_voucher_list_by_goods": (
            "from #tempicanetcardex" in normalized
            and "@invvocheridlisttype" in normalized
            and "group by goodsref" in normalized
        ),
        "compares_aggregate_goods_quantities": (
            "full join #ica i on s.goodsref=i.goodsref" in normalized
            and "isnull(s.supqty, -1) <> isnull(i.icaqty, -1)" in normalized
        ),
        "has_line_level_invoice_to_voucher_item_crosswalk": False,
        "writes_voucher_item_price": "insert into inv.tblvocheritmprice" in normalized,
    }


def _supplier_return_validation_contract(cursor: Any) -> dict[str, Any]:
    module_names = [
        ("SLE", "usp_CheckRetSupInvoice"),
        ("dbo", "usp_sdsnet_RetSupInvoice_BeforeSave"),
        ("dbo", "usp_sdsnet_RetSupInvoice_Save"),
        ("ICA", "UspRetSupInvoiceHdrBeforeInsert"),
        ("ICA", "UspRetSupInvoiceHdrBeforeUpdate"),
        ("ICA", "UspRetSupInvoiceItmBeforeInsert"),
        ("ICA", "UspRetSupInvoiceItmBeforeUpdate"),
        ("ICA", "TblRetSupInvoiceItmTolls"),
        ("dbo", "usp_sdsnet_RetSupInvoice_CheckUserRights"),
        ("dbo", "usp_Convert_RetSupInvoice2"),
        ("ICA", "UspRetSupInvoiceItmInsert"),
        ("ICA", "UspRetSupInvoiceItmUpdate"),
    ]
    modules: list[dict[str, Any]] = []
    definitions: dict[str, str] = {}
    for schema, name in module_names:
        row, definition = _read_module(cursor, schema, name)
        qualified_name = f"{schema}.{name}"
        definitions[qualified_name] = re.sub(r"\s+", " ", definition).casefold()
        modules.append({
            **row,
            "qualified_name": qualified_name,
            "definition_sha256": hashlib.sha256(definition.encode("utf-8")).hexdigest(),
        })

    check = definitions["SLE.usp_CheckRetSupInvoice"]
    before = definitions["dbo.usp_sdsnet_RetSupInvoice_BeforeSave"]
    save = definitions["dbo.usp_sdsnet_RetSupInvoice_Save"]
    hdr_insert = definitions["ICA.UspRetSupInvoiceHdrBeforeInsert"]
    hdr_update = definitions["ICA.UspRetSupInvoiceHdrBeforeUpdate"]
    compatibility_view = definitions["ICA.TblRetSupInvoiceItmTolls"]
    rights = definitions["dbo.usp_sdsnet_RetSupInvoice_CheckUserRights"]
    convert = definitions["dbo.usp_Convert_RetSupInvoice2"]
    item_insert = definitions["ICA.UspRetSupInvoiceItmInsert"]
    item_update = definitions["ICA.UspRetSupInvoiceItmUpdate"]
    final_date_slice = before.split("select top 1 @lastdate", 1)[-1].split("begin try", 1)[0]
    insert_branch = save.split("else if @savemode= 'update'", 1)[0]
    update_branch = save.split("else if @savemode= 'update'", 1)[-1].split("else if @savemode= 'delete'", 1)[0]
    call_marker = "exec sle.usp_checkretsupinvoice"
    after_call = insert_branch.split(call_marker, 1)[-1] if call_marker in insert_branch else ""

    return {
        "modules": modules,
        "sup_invoice_ref_is_optional_in_before_save_required_field_check": (
            "currencyref is null or dcref is null or supplierref is null" in before
            and "supinvoiceref is null" not in before
        ),
        "legacy_header_insert_requires_sup_invoice_ref": (
            "when (@supinvoiceref is null)" in hdr_insert or "isnull(@supinvoiceref" in hdr_insert
        ),
        "legacy_header_update_requires_sup_invoice_ref": (
            "when (@supinvoiceref is null)" in hdr_update or "isnull(@supinvoiceref" in hdr_update
        ),
        "validator_returns_immediately_when_sup_invoice_ref_is_null": (
            "if @supinvoiceref is null return" in check
        ),
        "validator_quantity_check_uses_inner_join_on_goods": (
            "inner join" in check and "on ret.goodsref=sup.goodsref" in check
        ),
        "validator_aggregates_all_return_headers_sharing_source_invoice": (
            "where h.supinvoiceref=@supinvoiceref" in check
        ),
        "validator_scopes_return_items_to_current_return_header": (
            "where h.id=@retsupinvoiceid" in check
        ),
        "validator_has_explicit_unmatched_return_goods_check": (
            "not exists" in check and "tblsupinvoiceitm" in check and "tblretsupinvoiceitm" in check
        ),
        "validator_toll_integrity_filter_compares_item_ref_to_header_id": (
            "xt.retsupinvoiceitmref = @retsupinvoiceid" in check
        ),
        "insert_branch_calls_validator": call_marker in insert_branch,
        "update_branch_calls_validator": call_marker in update_branch,
        "insert_branch_captures_validator_return_code": (
            "exec @" in insert_branch.split(call_marker, 1)[0][-100:] if call_marker in insert_branch else False
        ),
        "insert_branch_raises_after_validator_call": "raiserror" in after_call,
        "save_has_explicit_transaction_and_catch_rollback": (
            "begin transaction" in save and "save transaction retsupinvoice" in save
            and "rollback transaction retsupinvoice" in save
        ),
        "update_branch_uses_hdrid_for_new_item_tolls": "where si.hdrref=@hdrid" in update_branch,
        "update_branch_assigns_hdrid": (
            "set @hdrid" in update_branch or "select @hdrid" in update_branch
        ),
        "update_branch_retargets_existing_item_toll_header_ref": (
            "set retsupinvoicetollsref" in update_branch
        ),
        "compatibility_view_resolves_item_toll_by_same_header_and_toll_code": (
            "st.retinvoiceref=si.hdrref" in compatibility_view
            and "st.tollref=xt.tollref" in compatibility_view
        ),
        "compatibility_view_uses_stored_explicit_item_toll_header_ref": (
            "xt.retsupinvoicetollsref" in compatibility_view
        ),
        "stale_toll_ref_root_cause_candidate": (
            "the SDSNET UPDATE branch can replace toll-header identity without retargeting existing "
            "item-toll refs, and its new allocation insert filters on @HdrId although only the INSERT "
            "branch assigns @HdrId; the compatibility view deliberately resolves by header plus TollRef"
        ),
        "price_provenance_contract": {
            "sdsnet_save_copies_staged_price_and_amount": (
                "select @itmid + row_number()" in save and "goodsref, qty, unitref, price, amount" in save
            ),
            "official_import_maps_unit_price_to_price": (
                "unitprice" in convert and ", price" in convert
            ),
            "official_import_calculates_amount_from_qty_times_unit_price": (
                "round(tmp.qty * tmp.unitprice, 0)" in convert
            ),
            "legacy_insert_accepts_and_persists_price_parameter": (
                "@price money" in item_insert
                and "insert into ica.tblretsupinvoiceitm" in item_insert
                and "@price" in item_insert.split("insert into ica.tblretsupinvoiceitm", 1)[-1]
            ),
            "legacy_update_accepts_and_persists_price_parameter": (
                "@price money" in item_update and "price = @price" in item_update
            ),
            "current_row_creation_path_marker_available": False,
            "conclusion": (
                "nonzero price can come from desktop/legacy input, SDSNET staged input or the official "
                "conversion import UnitPrice; current rows lack an authoritative creation-path marker"
            ),
        },
        "access_operation_date_and_required_goods_contract": {
            "insert_access_node_id": 826001,
            "update_access_node_id": 826002,
            "delete_access_node_id": 826003,
            "uses_access_node_authorizer": "usp_checkuserrightsbyaccessnodeid" in rights,
            "forwards_accyear_or_dcref_to_access_node_authorizer": any(
                marker in rights
                for marker in (
                    "usp_checkuserrightsbyaccessnodeid @userref, @accyear",
                    "usp_checkuserrightsbyaccessnodeid @userref, @dcref",
                )
            ),
            "purchase_final_date_sysref": 5,
            "final_date_lookup_filters_accyear": "accyear=@accyear" in final_date_slice,
            "final_date_lookup_filters_dcref": "dcref=@dcref" in final_date_slice,
            "before_save_required_goods_check_reads_global_persisted_item_table": (
                "from ica.tblretsupinvoiceitm where isnull(goodsref,0) =0" in before
            ),
            "before_save_required_goods_check_scoped_to_current_parent_or_temp_items": (
                "from #tblretsupinvoiceitm where isnull(goodsref,0) =0" in before
                or "where hdrref=@id and isnull(goodsref,0) =0" in before
            ),
            "target_rule": (
                "authorization must be command plus effective DC/fiscal scope; final-date and required-item "
                "validation must be scoped to the current command aggregate, never the whole table"
            ),
        },
        "persistence_effect_conclusion": (
            "the INSERT path calls the validator after writing rows but neither captures its return code "
            "nor raises from the output message before COMMIT; the UPDATE path does not call it"
        ),
    }


def _desktop_save_boundary(source_directory: Path, binary_inventory_path: Path) -> dict[str, Any]:
    assembly_name = "VN.SDS.Stock.UI.dll"
    target_type = "VN.SDS.Stock.UI.RetSupInvoice.FormRetSupInvoiceDataEntry"
    target_method = "SaveCommand"
    inventory = json.loads(binary_inventory_path.read_text(encoding="utf-8-sig"))
    expected_hashes = {row["name"]: row["sha256"] for row in inventory["files"]}
    expected_sha = expected_hashes[assembly_name]
    assembly_path = source_directory / assembly_name
    actual_sha = hashlib.sha256(assembly_path.read_bytes()).hexdigest()
    if actual_sha != expected_sha:
        raise RuntimeError(f"Runtime assembly hash mismatch: {assembly_name}")

    pe = dnfile.dnPE(str(assembly_path))
    method_owners, field_owners = _owner_maps(pe)
    type_row = next(
        row for row in pe.net.mdtables.TypeDef.rows if _full_type_name(row) == target_type
    )
    method_row = next(
        index.row for index in type_row.MethodList if str(index.row.Name) == target_method
    )
    body = read_method_body_from_bytes(pe.get_data(method_row.Rva, 65536))
    ordered_calls: list[dict[str, Any]] = []
    branch_rows: list[dict[str, Any]] = []
    for instruction_index, instruction in enumerate(body.instructions):
        operand = instruction.operand
        if instruction.mnemonic in {"call", "callvirt", "newobj"} and isinstance(operand, Token):
            call = _resolve_token(pe, operand, method_owners, field_owners)
            if any(marker in call for marker in (
                "ValidationResult.get_IsValid",
                "TypeSpecRow.SaveCommand",
                "RetSupInvoiceHdrHandler.CheckRetSupInvoice",
                "String.IsNullOrWhiteSpace",
                "ValidationFailure..ctor",
                "DataContext.Dispose",
                "DataContext.Commit",
            )):
                ordered_calls.append({
                    "instruction_index": instruction_index,
                    "il_offset": int(instruction.offset),
                    "opcode": instruction.mnemonic,
                    "call": call,
                })
        elif instruction.mnemonic.startswith(("brtrue", "brfalse", "leave")):
            branch_rows.append({
                "instruction_index": instruction_index,
                "il_offset": int(instruction.offset),
                "opcode": instruction.mnemonic,
                "target_offset": int(operand) if isinstance(operand, int) else str(operand),
            })
        elif isinstance(operand, StringToken):
            continue

    positions = {row["call"]: row["instruction_index"] for row in ordered_calls}
    save_position = next(v for k, v in positions.items() if k.endswith("TypeSpecRow.SaveCommand"))
    check_position = next(v for k, v in positions.items() if k.endswith("RetSupInvoiceHdrHandler.CheckRetSupInvoice"))
    empty_position = next(v for k, v in positions.items() if k.endswith("String.IsNullOrWhiteSpace"))
    failure_position = next(
        row["instruction_index"]
        for row in ordered_calls
        if row["instruction_index"] > empty_position
        and row["call"].endswith("ValidationFailure..ctor")
    )
    commit_position = next(v for k, v in positions.items() if k.endswith("DataContext.Commit"))
    dispose_positions = [
        row["instruction_index"]
        for row in ordered_calls
        if row["call"].endswith("DataContext.Dispose")
    ]
    empty_branch = next(row for row in branch_rows if row["instruction_index"] == empty_position + 1)

    def _ui_method(name: str) -> tuple[Any, list[str]]:
        row = next(index.row for index in type_row.MethodList if str(index.row.Name) == name)
        method_body = read_method_body_from_bytes(pe.get_data(row.Rva, 65536))
        method_calls: list[str] = []
        for instruction in method_body.instructions:
            if instruction.mnemonic in {"call", "callvirt", "newobj"} and isinstance(instruction.operand, Token):
                method_calls.append(
                    _resolve_token(pe, instruction.operand, method_owners, field_owners)
                )
        return method_body, method_calls

    fill_items_body, fill_items_calls = _ui_method("FillRetSupInvoiceItmGrid")
    source_change_body, source_change_calls = _ui_method("SupInvoiceRefTextEdit_EditValueChanged")
    voucher_change_body, voucher_change_calls = _ui_method("InvVocherRefTextEdit_EditValueChanged")
    grid_validation_body, grid_validation_calls = _ui_method("GridList_ValidatingEditor")
    source_instructions = list(source_change_body.instructions)
    unmatched_zero_price_branch = any(
        instruction.mnemonic == "ldc.i4.0"
        and any(
            later.mnemonic in {"call", "callvirt"}
            and isinstance(later.operand, Token)
            and _resolve_token(pe, later.operand, method_owners, field_owners).endswith(
                "ColumnView.SetRowCellValue"
            )
            for later in source_instructions[index + 1:index + 4]
        )
        for index, instruction in enumerate(source_instructions)
    )
    voucher_instructions = list(voucher_change_body.instructions)
    clears_source_invoice_on_voucher_change = any(
        instruction.mnemonic == "ldnull"
        and any(
            later.mnemonic in {"call", "callvirt"}
            and isinstance(later.operand, Token)
            and _resolve_token(pe, later.operand, method_owners, field_owners).endswith(
                "BaseEdit.set_EditValue"
            )
            for later in voucher_instructions[index + 1:index + 3]
        )
        for index, instruction in enumerate(voucher_instructions)
    ) and any(call.endswith("RetSupInvoiceHdrEntity.set_SupInvoiceRef") for call in voucher_change_calls)
    grid_validation_columns: list[str] = []
    for instruction in grid_validation_body.instructions:
        if isinstance(instruction.operand, StringToken):
            value = pe.net.user_strings.get(instruction.operand.rid)
            value_text = "" if value is None else str(value)
            if value_text in {"Price", "Amount"}:
                grid_validation_columns.append(value_text)

    layered_targets = [
        (
            "VN.SDS.Stock.Business.dll",
            "VN.SDS.Stock.Business.RetSupInvoice.RetSupInvoiceHdrHandler",
            "CheckRetSupInvoice",
        ),
        (
            "VN.SDS.Stock.DataAccess.dll",
            "VN.SDS.Stock.DataAccess.DataAdapter.RetSupInvoice.RetSupInvoiceHdrAdapter",
            "CheckRetSupInvoice",
        ),
    ]
    layered_methods: list[dict[str, Any]] = []
    for layer_assembly, layer_type, layer_method in layered_targets:
        layer_path = source_directory / layer_assembly
        layer_sha = hashlib.sha256(layer_path.read_bytes()).hexdigest()
        if layer_sha != expected_hashes[layer_assembly]:
            raise RuntimeError(f"Runtime assembly hash mismatch: {layer_assembly}")
        layer_pe = dnfile.dnPE(str(layer_path))
        layer_method_owners, layer_field_owners = _owner_maps(layer_pe)
        layer_type_row = next(
            row for row in layer_pe.net.mdtables.TypeDef.rows
            if _full_type_name(row) == layer_type
        )
        layer_method_row = next(
            index.row for index in layer_type_row.MethodList
            if str(index.row.Name) == layer_method
        )
        layer_body = read_method_body_from_bytes(
            layer_pe.get_data(layer_method_row.Rva, 65536)
        )
        calls: list[str] = []
        safe_sql_literals: list[str] = []
        for instruction in layer_body.instructions:
            operand = instruction.operand
            if isinstance(operand, StringToken):
                value = layer_pe.net.user_strings.get(operand.rid)
                value_text = "" if value is None else str(value)
                if re.fullmatch(r"[A-Za-z0-9_.]+", value_text) and value_text.startswith("SLE.usp_"):
                    safe_sql_literals.append(value_text)
            elif instruction.mnemonic in {"call", "callvirt", "newobj"} and isinstance(operand, Token):
                calls.append(
                    _resolve_token(
                        layer_pe,
                        operand,
                        layer_method_owners,
                        layer_field_owners,
                    )
                )
        layered_methods.append({
            "assembly": layer_assembly,
            "assembly_sha256": layer_sha,
            "binary_inventory_sha256_match": True,
            "type": layer_type,
            "method": layer_method,
            "instruction_count": len(layer_body.instructions),
            "ordered_calls": calls,
            "allowlisted_sql_module_literals": safe_sql_literals,
        })

    business_method, data_access_method = layered_methods
    exact_sql_name = "SLE.usp_CheckRetSupInvoice"

    return {
        "assembly": assembly_name,
        "assembly_sha256": actual_sha,
        "binary_inventory_sha256_match": True,
        "target_type": target_type,
        "target_method": target_method,
        "method_instruction_count": len(body.instructions),
        "ordered_control_calls": ordered_calls,
        "selected_branches": branch_rows,
        "calls_buffered_row_save_before_return_validator": save_position < check_position,
        "calls_return_validator_before_data_context_commit": check_position < commit_position,
        "tests_validator_message_for_null_or_whitespace": empty_position < failure_position,
        "nonempty_validator_message_builds_validation_failure_before_commit": failure_position < commit_position,
        "nonempty_validator_message_has_dispose_before_commit": any(
            empty_position < position < commit_position for position in dispose_positions
        ),
        "empty_message_branch_targets_commit_block": (
            empty_branch["opcode"].startswith("brtrue")
            and int(empty_branch["target_offset"]) <= next(
                row["il_offset"] for row in ordered_calls if row["instruction_index"] == commit_position
            )
        ),
        "desktop_persistence_effect_conclusion": (
            "the desktop SaveCommand treats a non-empty validator message as a ValidationFailure, "
            "disposes the DataContext and leaves before Commit; this differs from the SDSNET SQL save path"
        ),
        "layered_binding": {
            "methods": layered_methods,
            "business_calls_data_access_adapter": any(
                call.endswith("RetSupInvoiceHdrAdapter.CheckRetSupInvoice")
                for call in business_method["ordered_calls"]
            ),
            "data_access_calls_data_context_execute": any(
                call.endswith("DataContext.Execute")
                for call in data_access_method["ordered_calls"]
            ),
            "data_access_exact_sql_module_literal": exact_sql_name,
            "data_access_exact_sql_module_literal_observed": (
                exact_sql_name in data_access_method["allowlisted_sql_module_literals"]
            ),
            "proven_chain": (
                "FormRetSupInvoiceDataEntry.SaveCommand -> RetSupInvoiceHdrHandler.CheckRetSupInvoice "
                "-> RetSupInvoiceHdrAdapter.CheckRetSupInvoice -> SLE.usp_CheckRetSupInvoice"
            ),
        },
        "source_selection_contract": {
            "fill_item_grid_instruction_count": len(fill_items_body.instructions),
            "source_invoice_change_instruction_count": len(source_change_body.instructions),
            "inventory_voucher_change_instruction_count": len(voucher_change_body.instructions),
            "grid_validation_instruction_count": len(grid_validation_body.instructions),
            "item_grid_loads_through_inventory_voucher_ref": (
                any(call.endswith("RetSupInvoiceItmViewEntityHelper.set_InvVocherRef") for call in fill_items_calls)
                and any(call.endswith("TypeSpecRow.GetAllView") for call in fill_items_calls)
            ),
            "source_invoice_change_fetches_invoice_items": (
                any(call.endswith("SupInvoiceItmViewEntityHelper.set_HdrRef") for call in source_change_calls)
                and any(call.endswith("SupInvoiceItmHandler.GetInstance") for call in source_change_calls)
            ),
            "matched_goods_copy_source_invoice_price_to_grid": (
                any(call.endswith("SupInvoiceItmEntity.get_Price") for call in source_change_calls)
                and any(call.endswith("ColumnView.SetRowCellValue") for call in source_change_calls)
            ),
            "unmatched_goods_set_grid_price_to_zero": unmatched_zero_price_branch,
            "inventory_voucher_change_clears_source_invoice_selection": clears_source_invoice_on_voucher_change,
            "grid_numeric_validation_columns": sorted(set(grid_validation_columns)),
            "grid_price_or_amount_validation_calls_numeric_only_helper": (
                any(call.endswith("FormRetSupInvoiceDataEntry.IsNumeric") for call in grid_validation_calls)
            ),
            "authority_conclusion": (
                "the inventory voucher supplies the return item set; the optional supplier invoice is a "
                "pricing/source hint, matching goods copy its price and unmatched goods receive zero price; "
                "the grid exposes Price/Amount numeric validation, so nonzero historical values cannot be "
                "attributed to a prior invoice without audit evidence"
            ),
        },
    }


def collect(source_directory: Path, binary_inventory_path: Path) -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        safety = _assert_safe_target(cursor)
        relations = _rows(cursor, "SELECT SupInvoiceHdrRef invoice_id,InvVchHdrRef voucher_id FROM ICA.tblSupInvInvoiceRelation")
        invoice_rows = _rows(cursor, "SELECT HdrRef invoice_id,GoodsRef goods_id,SUM(CONVERT(float,ISNULL(Qty,0))) qty FROM ICA.TblSupInvoiceItm GROUP BY HdrRef,GoodsRef")
        voucher_rows = _rows(cursor, "SELECT HdrRef voucher_id,GoodsRef goods_id,SUM(CONVERT(float,ISNULL(TotalQty,0))) qty FROM Inv.tblVocherItm WHERE HdrRef IN (SELECT InvVchHdrRef FROM ICA.tblSupInvInvoiceRelation) GROUP BY HdrRef,GoodsRef")
        return_rows = _rows(cursor, "SELECT h.ID return_id,h.SupInvoiceRef invoice_id,i.GoodsRef goods_id,SUM(CONVERT(float,ISNULL(i.Qty,0))) qty FROM ICA.tblRetSupInvoiceHdr h JOIN ICA.tblRetSupInvoiceItm i ON i.HdrRef=h.ID WHERE h.SupInvoiceRef IS NOT NULL GROUP BY h.ID,h.SupInvoiceRef,i.GoodsRef")
        return_missing_profile = _rows(cursor, """
            WITH r AS (
              SELECT h.ID return_id,h.SupInvoiceRef,h.InvVocherRef,h.SupplierRef,h.DCRef,h.AccYear,
                     h.RetInvoiceDate,h.IsNew,i.GoodsRef,SUM(i.Qty) qty,
                     MAX(ABS(CONVERT(float,ISNULL(i.Price,0)))) max_abs_price,
                     MAX(ABS(CONVERT(float,ISNULL(i.TotalAmount,0)))) max_abs_total_amount
              FROM ICA.tblRetSupInvoiceHdr h
              JOIN ICA.tblRetSupInvoiceItm i ON i.HdrRef=h.ID
              WHERE h.SupInvoiceRef IS NOT NULL
              GROUP BY h.ID,h.SupInvoiceRef,h.InvVocherRef,h.SupplierRef,h.DCRef,h.AccYear,h.RetInvoiceDate,h.IsNew,i.GoodsRef
            ), missing AS (
              SELECT r.* FROM r
              WHERE NOT EXISTS (
                SELECT 1 FROM ICA.TblSupInvoiceItm s
                WHERE s.HdrRef=r.SupInvoiceRef AND s.GoodsRef=r.GoodsRef
              )
            )
            SELECT COUNT_BIG(*) goods_groups,COUNT(DISTINCT return_id) return_headers,
                   COUNT(DISTINCT GoodsRef) goods,
                   SUM(CASE WHEN IsNew=1 THEN 1 ELSE 0 END) new_path_groups,
                   SUM(ISNULL(other_invoice.found,0)) goods_seen_on_other_supplier_invoice,
                   SUM(ISNULL(prior_invoice.found,0)) goods_seen_on_prior_same_scope_supplier_invoice,
                   SUM(ISNULL(source_relation.found,0)) source_invoice_has_receipt_relation,
                   SUM(CASE WHEN max_abs_price=0 THEN 1 ELSE 0 END) zero_price_goods_groups,
                   SUM(CASE WHEN max_abs_price<>0 THEN 1 ELSE 0 END) nonzero_price_goods_groups,
                   SUM(CASE WHEN IsNew=1 AND max_abs_price<>0 THEN 1 ELSE 0 END) new_path_nonzero_price_goods_groups,
                   SUM(CASE WHEN ISNULL(IsNew,0)=0 AND max_abs_price<>0 THEN 1 ELSE 0 END) legacy_path_nonzero_price_goods_groups,
                   SUM(CASE WHEN max_abs_total_amount=0 THEN 1 ELSE 0 END) zero_total_amount_goods_groups,
                   SUM(CASE WHEN max_abs_total_amount<>0 THEN 1 ELSE 0 END) nonzero_total_amount_goods_groups,
                   SUM(ISNULL(exact_inventory_exit.found,0)) exact_linked_type55_inventory_exit_goods_groups
            FROM missing m
            OUTER APPLY (
              SELECT TOP 1 1 found FROM ICA.TblSupInvoiceHdr h2
              JOIN ICA.TblSupInvoiceItm i2 ON i2.HdrRef=h2.ID
              WHERE h2.SupplierRef=m.SupplierRef AND i2.GoodsRef=m.GoodsRef
                AND h2.ID<>m.SupInvoiceRef
            ) other_invoice
            OUTER APPLY (
              SELECT TOP 1 1 found FROM ICA.TblSupInvoiceHdr h2
              JOIN ICA.TblSupInvoiceItm i2 ON i2.HdrRef=h2.ID
              WHERE h2.SupplierRef=m.SupplierRef AND h2.DCRef=m.DCRef
                AND h2.AccYear=m.AccYear AND i2.GoodsRef=m.GoodsRef
                AND h2.SupInvoiceDate<=m.RetInvoiceDate AND h2.ID<>m.SupInvoiceRef
            ) prior_invoice
            OUTER APPLY (
              SELECT TOP 1 1 found FROM ICA.tblSupInvInvoiceRelation x
              WHERE x.SupInvoiceHdrRef=m.SupInvoiceRef
            ) source_relation
            OUTER APPLY (
              SELECT TOP 1 1 found
              FROM Inv.tblVocherHdr vh
              JOIN Inv.tblVocherItm vi ON vi.HdrRef=vh.ID AND vi.GoodsRef=m.GoodsRef
              WHERE vh.ID=m.InvVocherRef AND vh.VocherTypeCode=55
              GROUP BY vh.ID
              HAVING ABS(CONVERT(float,SUM(ISNULL(vi.TotalQty,0))-m.qty))<0.0001
            ) exact_inventory_exit
        """)[0]
        module = _module_contract(cursor)
        supplier_return_validation = _supplier_return_validation_contract(cursor)
        supplier_return_validator_data_profile = _rows(cursor, """
            WITH sup AS (
              SELECT HdrRef SupInvoiceRef,GoodsRef,
                     SUM(CONVERT(float,ISNULL(Qty,0))) SupQty,
                     SUM(CONVERT(float,ISNULL(PrizeQty,0))) SupPrizeQty,
                     SUM(CONVERT(float,ISNULL(TotalAmount,0))) SupTotalAmount
              FROM ICA.TblSupInvoiceItm
              GROUP BY HdrRef,GoodsRef
            ), ret_doc AS (
              SELECT h.ID RetSupInvoiceRef,h.SupInvoiceRef,i.GoodsRef,
                     SUM(CONVERT(float,ISNULL(i.Qty,0))) RetQty,
                     SUM(CONVERT(float,ISNULL(i.PrizeQty,0))) RetPrizeQty,
                     SUM(CONVERT(float,ISNULL(i.TotalAmount,0))) RetTotalAmount
              FROM ICA.tblRetSupInvoiceHdr h
              JOIN ICA.tblRetSupInvoiceItm i ON i.HdrRef=h.ID
              WHERE h.SupInvoiceRef IS NOT NULL
              GROUP BY h.ID,h.SupInvoiceRef,i.GoodsRef
            ), ret AS (
              SELECT SupInvoiceRef,GoodsRef,
                     SUM(RetQty) RetQty,SUM(RetPrizeQty) RetPrizeQty,
                     SUM(RetTotalAmount) RetTotalAmount
              FROM ret_doc
              GROUP BY SupInvoiceRef,GoodsRef
            ), doc_eval AS (
              SELECT d.*,s.GoodsRef matched_source_goods
              FROM ret_doc d
              LEFT JOIN sup s ON s.SupInvoiceRef=d.SupInvoiceRef AND s.GoodsRef=d.GoodsRef
            )
            SELECT
              COUNT_BIG(*) sourced_return_goods_group_count,
              (SELECT COUNT_BIG(*) FROM ret_doc) return_document_goods_group_count,
              (SELECT SUM(CASE WHEN matched_source_goods IS NULL THEN 1 ELSE 0 END) FROM doc_eval) unmatched_return_document_goods_group_count,
              SUM(CASE WHEN s.GoodsRef IS NULL THEN 1 ELSE 0 END) unmatched_return_goods_group_count,
              SUM(CASE WHEN s.GoodsRef IS NOT NULL AND (r.RetQty>s.SupQty OR r.RetPrizeQty>s.SupPrizeQty) THEN 1 ELSE 0 END) matched_over_return_goods_group_count,
              SUM(CASE WHEN s.GoodsRef IS NOT NULL AND r.RetQty=s.SupQty AND r.RetTotalAmount<>s.SupTotalAmount THEN 1 ELSE 0 END) matched_full_quantity_amount_mismatch_group_count
            FROM ret r
            LEFT JOIN sup s ON s.SupInvoiceRef=r.SupInvoiceRef AND s.GoodsRef=r.GoodsRef
        """)[0]
        supplier_return_toll_integrity_profile = _rows(cursor, """
            SELECT COUNT_BIG(*) item_toll_row_count,
                   COUNT(DISTINCT CASE WHEN st.ID IS NULL THEN si.HdrRef END) affected_return_header_count,
                   COUNT(DISTINCT CASE WHEN st.ID IS NULL AND h.IsNew=1 THEN si.HdrRef END) affected_new_path_return_header_count,
                   SUM(CASE WHEN st.ID IS NULL THEN 1 ELSE 0 END) correct_scope_missing_header_toll_row_count,
                   SUM(CASE WHEN any_toll.ID IS NULL THEN 1 ELSE 0 END) referenced_toll_row_missing_globally_count,
                   SUM(CASE WHEN any_toll.ID IS NOT NULL AND any_toll.RetInvoiceRef<>si.HdrRef THEN 1 ELSE 0 END) referenced_toll_belongs_to_other_return_header_count,
                   SUM(CASE WHEN st.ID IS NULL AND code_match.match_count=1 THEN 1 ELSE 0 END) stale_explicit_ref_resolved_by_same_header_toll_code_count,
                   SUM(CASE WHEN st.ID IS NULL AND code_match.match_count=0 THEN 1 ELSE 0 END) unresolved_by_explicit_ref_or_same_header_toll_code_count,
                   SUM(CASE WHEN st.ID IS NULL AND code_match.match_count>1 THEN 1 ELSE 0 END) ambiguous_same_header_toll_code_match_count,
                   SUM(CASE WHEN ISNULL(compatibility_view.found,0)=0 THEN 1 ELSE 0 END) omitted_from_deployed_compatibility_view_count,
                   SUM(CASE WHEN st.ID IS NOT NULL AND st.TollRef<>xt.TollRef THEN 1 ELSE 0 END) same_header_toll_code_mismatch_count,
                   SUM(CASE WHEN si.ID=si.HdrRef THEN 1 ELSE 0 END) deployed_validator_scope_candidate_row_count,
                   SUM(CASE WHEN si.ID=si.HdrRef AND st.ID IS NULL THEN 1 ELSE 0 END) deployed_validator_detectable_missing_toll_row_count,
                   SUM(CASE WHEN si.ID<>si.HdrRef AND st.ID IS NULL THEN 1 ELSE 0 END) deployed_validator_missed_missing_toll_row_count
            FROM ICA.tblRetSupInvoiceItmXToll xt
            JOIN ICA.tblRetSupInvoiceItm si ON si.ID=xt.RetSupInvoiceItmRef
            JOIN ICA.tblRetSupInvoiceHdr h ON h.ID=si.HdrRef
            LEFT JOIN ICA.tblRetSupInvoiceTolls any_toll ON any_toll.ID=xt.RetSupInvoiceTollsRef
            LEFT JOIN ICA.tblRetSupInvoiceTolls st
              ON st.RetInvoiceRef=si.HdrRef AND st.ID=xt.RetSupInvoiceTollsRef
            OUTER APPLY (
              SELECT COUNT_BIG(*) match_count
              FROM ICA.tblRetSupInvoiceTolls by_code
              WHERE by_code.RetInvoiceRef=si.HdrRef AND by_code.TollRef=xt.TollRef
            ) code_match
            OUTER APPLY (
              SELECT TOP 1 1 found
              FROM ICA.TblRetSupInvoiceItmTolls compatibility_view
              WHERE compatibility_view.RetSupInvoiceItmTollsId=xt.ID
            ) compatibility_view
        """)[0]
        supplier_return_required_goods_guard_profile = _rows(cursor, """
            SELECT COUNT_BIG(*) zero_or_null_goods_item_count,
                   COUNT(DISTINCT HdrRef) affected_return_header_count
            FROM ICA.tblRetSupInvoiceItm
            WHERE ISNULL(GoodsRef,0)=0
        """)[0]
        supplier_invoice_item_uniqueness_profile = _rows(cursor, """
            SELECT
              (SELECT COUNT_BIG(*) FROM (
                 SELECT HdrRef,GoodsRef FROM ICA.TblSupInvoiceItm
                 GROUP BY HdrRef,GoodsRef HAVING COUNT_BIG(*)>1
               ) d) duplicate_header_goods_group_count,
              (SELECT COUNT_BIG(*)
               FROM sys.indexes i
               WHERE i.object_id=OBJECT_ID('ICA.TblSupInvoiceItm')
                 AND i.is_unique=1
                 AND EXISTS (
                   SELECT 1 FROM sys.index_columns ic JOIN sys.columns c
                     ON c.object_id=ic.object_id AND c.column_id=ic.column_id
                   WHERE ic.object_id=i.object_id AND ic.index_id=i.index_id
                     AND ic.key_ordinal=1 AND c.name='HdrRef'
                 )
                 AND EXISTS (
                   SELECT 1 FROM sys.index_columns ic JOIN sys.columns c
                     ON c.object_id=ic.object_id AND c.column_id=ic.column_id
                   WHERE ic.object_id=i.object_id AND ic.index_id=i.index_id
                     AND ic.key_ordinal=2 AND c.name='GoodsRef'
                 )
              ) unique_header_goods_index_count
        """)[0]
        three_month_supplier_return_profile = _rows(cursor, """
            WITH window_headers AS (
              SELECT ID,IsNew,SupInvoiceRef,InvVocherRef
              FROM ICA.tblRetSupInvoiceHdr
              WHERE RetInvoiceDate BETWEEN '1405/03/01' AND '1405/05/31'
            ), window_missing_source AS (
              SELECT h.ID,i.GoodsRef
              FROM window_headers h
              JOIN ICA.tblRetSupInvoiceItm i ON i.HdrRef=h.ID
              WHERE h.SupInvoiceRef IS NOT NULL
                AND NOT EXISTS (
                  SELECT 1 FROM ICA.TblSupInvoiceItm s
                  WHERE s.HdrRef=h.SupInvoiceRef AND s.GoodsRef=i.GoodsRef
                )
              GROUP BY h.ID,i.GoodsRef
            ), window_stale_toll AS (
              SELECT xt.ID
              FROM window_headers h
              JOIN ICA.tblRetSupInvoiceItm i ON i.HdrRef=h.ID
              JOIN ICA.tblRetSupInvoiceItmXToll xt ON xt.RetSupInvoiceItmRef=i.ID
              LEFT JOIN ICA.tblRetSupInvoiceTolls st
                ON st.RetInvoiceRef=h.ID AND st.ID=xt.RetSupInvoiceTollsRef
              WHERE st.ID IS NULL
            )
            SELECT COUNT_BIG(*) return_header_count,
                   SUM(CASE WHEN IsNew=1 THEN 1 ELSE 0 END) new_path_header_count,
                   SUM(CASE WHEN ISNULL(IsNew,0)=0 THEN 1 ELSE 0 END) legacy_path_header_count,
                   SUM(CASE WHEN SupInvoiceRef IS NOT NULL THEN 1 ELSE 0 END) optional_source_invoice_present_header_count,
                   (SELECT COUNT_BIG(*) FROM ICA.tblRetSupInvoiceItm i JOIN window_headers x ON x.ID=i.HdrRef) return_item_count,
                   (SELECT COUNT_BIG(*) FROM window_missing_source) optional_source_item_absent_goods_group_count,
                   (SELECT COUNT_BIG(*) FROM window_stale_toll) stale_explicit_toll_ref_row_count
            FROM window_headers
        """)[0]
    finally:
        connection.close()

    uf = UnionFind()
    invoice_to_vouchers: dict[int, set[int]] = defaultdict(set)
    voucher_to_invoices: dict[int, set[int]] = defaultdict(set)
    for row in relations:
        invoice_id, voucher_id = int(row["invoice_id"]), int(row["voucher_id"])
        uf.union(("I", invoice_id), ("V", voucher_id))
        invoice_to_vouchers[invoice_id].add(voucher_id)
        voucher_to_invoices[voucher_id].add(invoice_id)

    invoice_qty = {(int(r["invoice_id"]), int(r["goods_id"])): float(r["qty"] or 0) for r in invoice_rows}
    voucher_qty = {(int(r["voucher_id"]), int(r["goods_id"])): float(r["qty"] or 0) for r in voucher_rows}

    naive_counts: dict[str, int] = defaultdict(int)
    naive_receipt_only: list[tuple[int, int]] = []
    for invoice_id, voucher_ids in invoice_to_vouchers.items():
        goods = {g for i, g in invoice_qty if i == invoice_id}
        goods |= {g for v, g in voucher_qty if v in voucher_ids}
        for goods_id in goods:
            left = invoice_qty.get((invoice_id, goods_id), 0.0)
            right = sum(voucher_qty.get((v, goods_id), 0.0) for v in voucher_ids)
            result = _classify(left, right)
            naive_counts[result] += 1
            if result == "receipt_only":
                naive_receipt_only.append((invoice_id, goods_id))

    component_invoices: dict[tuple[str, int], set[int]] = defaultdict(set)
    component_vouchers: dict[tuple[str, int], set[int]] = defaultdict(set)
    for invoice_id in invoice_to_vouchers:
        component_invoices[uf.find(("I", invoice_id))].add(invoice_id)
    for voucher_id in voucher_to_invoices:
        component_vouchers[uf.find(("V", voucher_id))].add(voucher_id)

    component_counts: dict[str, int] = defaultdict(int)
    component_with_multiple_invoices = 0
    component_with_shared_voucher = 0
    component_invoice_counts: list[int] = []
    component_voucher_counts: list[int] = []
    for root, invoices in component_invoices.items():
        vouchers = component_vouchers[root]
        component_invoice_counts.append(len(invoices))
        component_voucher_counts.append(len(vouchers))
        component_with_multiple_invoices += int(len(invoices) > 1)
        component_with_shared_voucher += int(any(len(voucher_to_invoices[v]) > 1 for v in vouchers))
        goods = {g for i, g in invoice_qty if i in invoices}
        goods |= {g for v, g in voucher_qty if v in vouchers}
        for goods_id in goods:
            left = sum(invoice_qty.get((i, goods_id), 0.0) for i in invoices)
            right = sum(voucher_qty.get((v, goods_id), 0.0) for v in vouchers)
            component_counts[_classify(left, right)] += 1

    explained_naive_receipt_only = 0
    for invoice_id, goods_id in naive_receipt_only:
        root = uf.find(("I", invoice_id))
        if any(invoice_qty.get((other, goods_id), 0.0) for other in component_invoices[root] if other != invoice_id):
            explained_naive_receipt_only += 1

    return_missing_source = 0
    return_missing_with_goods_in_component_invoice = 0
    return_missing_with_goods_in_component_receipt = 0
    return_missing_within_component_invoice_qty = 0
    for row in return_rows:
        invoice_id = int(row["invoice_id"])
        goods_id = int(row["goods_id"])
        qty = float(row["qty"] or 0)
        if (invoice_id, goods_id) in invoice_qty:
            continue
        return_missing_source += 1
        if invoice_id not in invoice_to_vouchers:
            continue
        root = uf.find(("I", invoice_id))
        component_invoice_qty = sum(
            invoice_qty.get((other, goods_id), 0.0)
            for other in component_invoices[root]
        )
        component_receipt_qty = sum(
            voucher_qty.get((voucher, goods_id), 0.0)
            for voucher in component_vouchers[root]
        )
        return_missing_with_goods_in_component_invoice += int(component_invoice_qty > 0)
        return_missing_with_goods_in_component_receipt += int(component_receipt_qty > 0)
        return_missing_within_component_invoice_qty += int(component_invoice_qty + 0.0001 >= qty)

    summary = {
        "relation_count": len(relations),
        "relation_component_count": len(component_invoices),
        "component_with_multiple_invoices_count": component_with_multiple_invoices,
        "component_with_shared_voucher_count": component_with_shared_voucher,
        "maximum_invoices_per_component": max(component_invoice_counts, default=0),
        "maximum_vouchers_per_component": max(component_voucher_counts, default=0),
        "naive_per_invoice_receipt_only_goods_group_count": naive_counts["receipt_only"],
        "naive_receipt_only_explained_by_other_invoice_in_component_count": explained_naive_receipt_only,
        "component_scope_receipt_only_goods_group_count": component_counts["receipt_only"],
        "component_scope_invoice_only_goods_group_count": component_counts["invoice_only"],
        "component_scope_quantity_mismatch_goods_group_count": component_counts["mismatch"],
        "component_scope_exact_goods_group_count": component_counts["exact"],
        "supplier_return_missing_direct_source_goods_group_count": return_missing_source,
        "supplier_return_missing_source_goods_found_in_component_invoice_count": return_missing_with_goods_in_component_invoice,
        "supplier_return_missing_source_goods_found_in_component_receipt_count": return_missing_with_goods_in_component_receipt,
        "supplier_return_missing_source_qty_within_component_invoice_qty_count": return_missing_within_component_invoice_qty,
    }
    if summary["naive_per_invoice_receipt_only_goods_group_count"] != 5:
        raise RuntimeError("Expected the previously reported five per-invoice receipt-only groups")
    if any(summary[key] for key in (
        "component_scope_receipt_only_goods_group_count",
        "component_scope_invoice_only_goods_group_count",
        "component_scope_quantity_mismatch_goods_group_count",
    )):
        raise RuntimeError("Supplier invoice/receipt component reconciliation has unexplained residual")

    return {
        "artifact": "varanegar_supplier_invoice_receipt_relation_component_diagnostic_contract",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone(),
        "validation": "PASS",
        "scope": {"server": SERVER, "database": DATABASE},
        "safety": {
            "mode": "READ_ONLY_CLONE_IN_MEMORY_RECONCILIATION_CATALOG_DEFINITION_AND_STATIC_PE_IL",
            "database_updateability": safety["updateability"],
            "can_select": safety["can_select"],
            "can_view_definition": safety["can_view_definition"],
            "can_update": safety["can_update"],
            "denies_data_writes": safety["denies_data_writes"],
            "stored_procedure_or_application_command_executions": 0,
            "assemblies_loaded_or_executed": 0,
            "raw_non_allowlisted_strings_persisted": 0,
            "raw_invoice_voucher_goods_ids_or_quantities_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": summary,
        "semantic_correction": {
            "previous_model": "each invoice must independently contain every goods row from every related receipt",
            "evidenced_model": "ICA.usp_ApplySupInvoice validates the complete supplied invoice list against the complete supplied voucher list, aggregated by GoodsRef",
            "previous_false_positive_count": 5,
            "remaining_unexplained_component_residual_count": 0,
            "migration_rule": "preserve the N:M header relation and reconcile each connected invoice-receipt component; never synthesize financial lines for per-invoice receipt-only groups that reconcile inside the component",
        },
        "official_apply_contract": module,
        "supplier_return_missing_direct_source_profile": return_missing_profile,
        "supplier_return_validator_data_profile": supplier_return_validator_data_profile,
        "supplier_return_toll_integrity_profile": supplier_return_toll_integrity_profile,
        "supplier_return_required_goods_guard_profile": supplier_return_required_goods_guard_profile,
        "supplier_invoice_item_uniqueness_profile": supplier_invoice_item_uniqueness_profile,
        "three_month_supplier_return_profile": {
            "business_date_field": "ICA.tblRetSupInvoiceHdr.RetInvoiceDate",
            "window": "1405/03/01..1405/05/31",
            **three_month_supplier_return_profile,
        },
        "supplier_return_validation_contract": supplier_return_validation,
        "desktop_save_boundary": _desktop_save_boundary(source_directory, binary_inventory_path),
        "supplier_return_semantic_correction": {
            "previous_model": "every return goods row must exist on SupInvoiceRef and a missing row is an inventory-source anomaly",
            "evidenced_model": "InvVocherRef type-55 is item and quantity authority; SupInvoiceRef is optional source/pricing provenance",
            "source_item_absent_goods_group_count": int(return_missing_profile["goods_groups"]),
            "exact_type55_inventory_exit_goods_group_count": int(return_missing_profile["exact_linked_type55_inventory_exit_goods_groups"]),
            "nonzero_historical_price_goods_group_count": int(return_missing_profile["nonzero_price_goods_groups"]),
            "migration_state": "OPTIONAL_SOURCE_ITEM_ABSENT_NOT_AN_INVENTORY_ERROR",
            "migration_rule": "preserve the exact type-55 exit plus historical price/amount; never reassign or reprice from a prior invoice candidate",
        },
        "diagnostic_order": [
            "build the bipartite invoice-to-type20-receipt relation graph",
            "identify connected components before comparing goods quantities",
            "aggregate every invoice and receipt in the same component by GoodsRef",
            "quarantine only component-level receipt-only, invoice-only or quantity residuals",
            "apply effective price only through the versioned idempotent supplier-invoice command",
        ],
        "evidence_limits": [
            "The clone proves current connected-component reconciliation, not the user intent behind the one shared receipt.",
            "The relation table has header granularity; no authoritative line-allocation crosswalk was found.",
            "Static SQL proves the deployed aggregate validation shape, not every historical UI selection batch.",
            "A non-blocking persistence conclusion is based on stored-procedure control flow; no save command was executed.",
            "Desktop blocking behavior is proven from ordered static IL, not from executing the form or command.",
            "No raw source identifier, quantity row, stored procedure, form, assembly or mutation was persisted or executed.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--binary-inventory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = collect(args.source_directory, args.binary_inventory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(payload["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
