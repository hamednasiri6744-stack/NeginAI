"""Extract the static Discount SqlCondition authoring and validation boundary.

The managed binaries are parsed as PE/CLR metadata only.  They are never
loaded, reflected, imported, or executed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import dnfile

from extract_varanegar_discount_v2_engine_runtime import _method_rows


TARGETS = {
    "Application.BaseData.dll": {
        "Application.BaseData.UserSessionInfo": ["HasPersmission", "HasPermission"],
        "<>c__DisplayClass158_0": ["<HasPersmission>b__0"],
        "<>c__DisplayClass159_0": ["<HasPermission>b__0"],
    },
    "Application.BaseTemaplateV2.dll": {
        "Application.BaseTemaplateV2.UIBase.FormBaseV2": ["InitForm"],
        "Application.BaseTemaplateV2.UIBase.FormBaseWithListDataEntry": ["InternalApplyUserPermission"],
        "Application.BaseTemaplateV2.UIBase.FormBaseV2SimpleDataEntry": [
            "MenuButtonNew_Click", "MenuButtonEdit_Click", "MenuButtonDelete_Click", "MenuButtonSave_Click",
            "InternalNewCommand", "InternalEditCommand", "InternalDeleteCommand", "InternalSaveCommand",
        ],
    },
    "VN.SDS.MainData.UI.dll": {
        "VN.SDS.MainData.UI.Discount.FormDiscount": [
            "btnCondition_Click", "CopyNew_Click", "SaveCommand",
        ],
        "VN.SDS.MainData.UI.Discount.FormDiscountCondition": [
            "SetReadOnlyForm", "filterControl1_FilterStringChanged",
            "DisplayBuiltFilter", "CorrectFilterCriteria", "OKbtn_Click",
        ],
    },
    "VN.SDS.MainData.Business.dll": {
        "VN.SDS.MainData.Business.Discount.DiscountHandler": [
            "SaveCommandcustomize", "CheckDiscountValidation", "DiscountValidation",
        ],
        "VN.SDS.MainData.Business.DiscountCondition.DiscountConditionHandler": [
            "ValidateUserBuiltCondition", "GetColumnsList",
        ],
    },
    "VN.SDS.MainData.DataAccess.dll": {
        "VN.SDS.MainData.DataAccess.DataAdapter.Discount.DiscountAdapter": [
            "CheckDiscountValidation", "DiscountValidation",
        ],
        "VN.SDS.MainData.DataAccess.DataAdapter.DiscountCondition.DiscountConditionAdapter": [
            "ExecuteBuiltCondition", "AdvanceFilterControlColumnsList",
        ],
    },
}

EXPECTED_HASHES = {
    "Application.BaseData.dll": "5181e4238578698d190e9f06258c0b6fb9eac536e9c5e1eb65a7f8e37d2064cc",
    "Application.BaseTemaplateV2.dll": "0f1763c997fd6ab6cab48350184918203bdc42761199650d4bb2633657bed95e",
    "VN.SDS.MainData.UI.dll": "afd3a9d4b3e595c352ca95cb55408f3116cac48309b98ac5826412e0e7bbd75e",
    "VN.SDS.MainData.Business.dll": "9aeaecbcfc77a91107615a7b0dcb44223ca4305a14d7533f35da9f162b4ef46c",
    "VN.SDS.MainData.DataAccess.dll": "5dcb9f47a484ed5c3d04344130ea9ef1f2e5e97c4b5acd2b11b02df0a878d987",
}

AUTH_TERMS = ("permission", "persmission", "authorize", "authorization", "accesscontrol")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _find(methods: list[dict[str, Any]], type_suffix: str, name: str) -> dict[str, Any]:
    return next(row for row in methods if row["type"].endswith(type_suffix) and row["method"] == name)


def _has(row: dict[str, Any], fragment: str) -> bool:
    return any(fragment.casefold() in item["member"].casefold() for item in row["ordered_member_references"])


def collect(source_directory: Path) -> dict[str, Any]:
    sources: list[dict[str, Any]] = []
    methods: list[dict[str, Any]] = []
    errors: list[str] = []
    form_base_type = ""
    for assembly, types in TARGETS.items():
        path = source_directory / assembly
        actual_hash = _sha256(path)
        sources.append({
            "assembly_file": assembly,
            "assembly_bytes": path.stat().st_size,
            "assembly_sha256": actual_hash,
            "expected_sha256": EXPECTED_HASHES[assembly],
            "hash_matches_pinned_inventory": actual_hash == EXPECTED_HASHES[assembly],
        })
        if actual_hash != EXPECTED_HASHES[assembly]:
            errors.append(f"hash mismatch: {assembly}")
        pe = dnfile.dnPE(str(path))
        if assembly == "VN.SDS.MainData.UI.dll":
            form_type = next(row for row in pe.net.mdtables.TypeDef.rows if f"{row.TypeNamespace}.{row.TypeName}" == "VN.SDS.MainData.UI.Discount.FormDiscount")
            base_row = form_type.Extends.row
            form_base_type = f"{base_row.TypeNamespace}.{base_row.TypeName}"
        for type_name, names in types.items():
            for name in names:
                rows = _method_rows(pe, type_name, name)
                if not rows:
                    errors.append(f"method missing: {type_name}.{name}")
                methods.extend(rows)

    condition_click = _find(methods, "FormDiscount", "btnCondition_Click")
    copy_new = _find(methods, "FormDiscount", "CopyNew_Click")
    save_ui = _find(methods, "FormDiscount", "SaveCommand")
    filter_change = _find(methods, "FormDiscountCondition", "filterControl1_FilterStringChanged")
    ok_click = _find(methods, "FormDiscountCondition", "OKbtn_Click")
    save_business = _find(methods, "DiscountHandler", "SaveCommandcustomize")
    validate_business = _find(methods, "DiscountConditionHandler", "ValidateUserBuiltCondition")
    validate_adapter = _find(methods, "DiscountConditionAdapter", "ExecuteBuiltCondition")
    base_init = _find(methods, "FormBaseV2", "InitForm")
    permission_apply = _find(methods, "FormBaseWithListDataEntry", "InternalApplyUserPermission")
    button_clicks = [row for row in methods if row["method"] in {"MenuButtonNew_Click", "MenuButtonEdit_Click", "MenuButtonDelete_Click", "MenuButtonSave_Click"}]
    internal_commands = [row for row in methods if row["method"] in {"InternalNewCommand", "InternalEditCommand", "InternalDeleteCommand", "InternalSaveCommand"}]
    permission_by_key = next(row for row in methods if row["type"] == "Application.BaseData.UserSessionInfo" and row["method"] == "HasPersmission" and row["parameter_names"] == ["ClassName", "AccessNodeKey", "ignoreCheckKey"])
    permission_by_id = next(row for row in methods if row["type"] == "Application.BaseData.UserSessionInfo" and row["method"] == "HasPermission")
    permission_key_predicate = _find(methods, "<>c__DisplayClass158_0", "<HasPersmission>b__0")
    permission_id_predicate = _find(methods, "<>c__DisplayClass159_0", "<HasPermission>b__0")
    base_permission_allowlisted_keys = sorted(
        set(permission_apply.get("_literals", [])) & {"View", "New", "Edit", "Delete", "Print", "InsertToExcel", "Action"}
    )

    assertions = {
        "condition_button_opens_dedicated_dialog_and_copies_filter_condition_to_sql_condition": (
            _has(condition_click, "FormDiscountCondition..ctor")
            and _has(condition_click, "Form.ShowDialog")
            and _has(condition_click, "FormDiscountCondition.FilterCondition")
            and _has(condition_click, "DiscountEntity.set_SqlCondition")
        ),
        "copy_new_is_second_selected_sql_condition_setter": (
            _has(copy_new, "DiscountViewEntity.get_SqlConditionForSearch")
            and _has(copy_new, "DiscountEntity.set_SqlCondition")
        ),
        "visual_filter_is_compiled_to_dataset_where_clause": (
            _has(filter_change, "CriteriaToWhereClauseHelper.GetDataSetWhere")
        ),
        "dialog_validates_condition_against_evc_temp_context_before_accepting": (
            _has(ok_click, "EVCHandler.CreateEVCSqlTempTable")
            and _has(ok_click, "DiscountConditionHandler.ValidateUserBuiltCondition")
            and _has(ok_click, "FormDiscountCondition.FilterCondition")
            and _has(ok_click, "Form.set_DialogResult")
        ),
        "validation_business_layer_delegates_to_execute_built_condition": (
            _has(validate_business, "DiscountConditionAdapter.ExecuteBuiltCondition")
        ),
        "validation_adapter_executes_dynamic_sql_four_times": (
            sum("Thunderstruck.DataContext.Execute" in item["member"] for item in validate_adapter["ordered_member_references"]) == 4
            and sum(shape["contains_sp_executesql"] for shape in validate_adapter["literal_shapes"]) == 4
        ),
        "ui_save_commits_after_business_validation_and_save": (
            _has(save_ui, "DiscountHandler.CheckDiscountValidation")
            and _has(save_ui, "DiscountHandler.SaveCommandcustomize")
            and _has(save_ui, "DataContext.Commit")
        ),
        "business_save_delegates_to_generic_typespec_save": (
            sum("TypeSpecRow.SaveCommand" in item["member"] for item in save_business["ordered_member_references"]) == 2
        ),
        "discount_form_inherits_permission_aware_list_data_entry_base": form_base_type == "Application.BaseTemaplateV2.UIBase.FormBaseWithListDataEntry",
        "base_initialization_invokes_virtual_permission_application": _has(base_init, "InternalApplyUserPermission"),
        "base_permission_application_uses_session_permission_to_enable_toolbar": (
            _has(permission_apply, "UserSessionInfo.HasPersmission")
            and _has(permission_apply, "ToolStripItem.set_Enabled")
        ),
        "toolbar_clicks_require_visible_and_enabled_before_internal_command": all(
            _has(row, "ToolStripItem.get_Visible")
            and _has(row, "ToolStripItem.get_Enabled")
            and _has(row, row["method"].replace("MenuButton", "Internal").replace("_Click", "Command"))
            for row in button_clicks
        ),
        "internal_commands_do_not_recheck_session_permission": all(
            not _has(row, "UserSessionInfo.HasPersmission") for row in internal_commands
        ),
        "session_permission_lookup_reads_cached_permission_and_returns_has_access": all(
            _has(row, "UserSessionInfo.get_UserPermissionS")
            and _has(row, "TypeSpecRow.Find")
            and _has(row, "UserPermission.get_HasAccess")
            for row in (permission_by_key, permission_by_id)
        ),
        "permission_key_predicate_matches_class_and_access_node_key": (
            _has(permission_key_predicate, "UserPermission.get_ClassName")
            and _has(permission_key_predicate, "UserPermission.get_AccessNodeKey")
        ),
        "permission_id_predicate_matches_access_node_id": _has(permission_id_predicate, "UserPermission.get_AccessNodeId"),
        "session_permission_lookup_has_no_database_round_trip": all(
            not any("DataContext" in item["member"] for item in row["ordered_member_references"])
            for row in (permission_by_key, permission_by_id)
        ),
        "base_permission_keys_cover_new_edit_delete_children": {"New", "Edit", "Delete"}.issubset(base_permission_allowlisted_keys),
        "selected_list_base_permission_path_does_not_reference_view_key": "View" not in base_permission_allowlisted_keys,
    }
    if not all(assertions.values()):
        errors.extend(f"assertion failed: {name}" for name, value in assertions.items() if not value)

    method_local_auth_refs = sorted({
        item["member"]
        for method in methods
        for item in method["ordered_member_references"]
        if any(term in item["member"].casefold() for term in AUTH_TERMS)
    })
    public_methods = []
    for row in methods:
        public_methods.append({
            "type": row["type"],
            "method": row["method"],
            "occurrence": row["occurrence"],
            "parameter_names": row["parameter_names"],
            "instruction_count": row["instruction_count"],
            "member_reference_count": len(row["ordered_member_references"]),
            "data_context_execute_count": sum(
                "Thunderstruck.DataContext.Execute" in item["member"]
                for item in row["ordered_member_references"]
            ),
            "sp_executesql_literal_shape_count": sum(
                shape["contains_sp_executesql"] for shape in row["literal_shapes"]
            ),
            "sets_sql_condition": _has(row, "DiscountEntity.set_SqlCondition"),
            "calls_user_condition_validator": _has(row, "ValidateUserBuiltCondition"),
            "method_local_authorization_reference_count": sum(
                any(term in item["member"].casefold() for term in AUTH_TERMS)
                for item in row["ordered_member_references"]
            ),
        })

    return {
        "artifact": "varanegar_discount_rule_authoring_and_validation_static_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_PE_CLR_METADATA_AND_IL_ONLY",
            "assemblies_loaded_or_executed": 0,
            "database_connections": 0,
            "application_forms_opened": 0,
            "dynamic_conditions_executed": 0,
            "business_commands_executed": 0,
            "raw_sql_condition_text_persisted": False,
        },
        "summary": {
            "source_assembly_count": len(sources),
            "selected_method_count": len(methods),
            "selected_instruction_count": sum(row["instruction_count"] for row in methods),
            "selected_sql_condition_setter_method_count": sum(row["sets_sql_condition"] for row in public_methods),
            "validation_adapter_dynamic_execute_count": next(
                row["data_context_execute_count"] for row in public_methods
                if row["type"].endswith("DiscountConditionAdapter") and row["method"] == "ExecuteBuiltCondition"
            ),
            "method_local_authorization_reference_count": len(method_local_auth_refs),
            "discount_specific_method_local_authorization_reference_count": sum(
                row["method_local_authorization_reference_count"]
                for row in public_methods
                if row["type"].startswith("VN.SDS.")
            ),
            "internal_command_permission_recheck_count": sum(
                _has(row, "UserSessionInfo.HasPersmission") for row in internal_commands
            ),
            "session_permission_lookup_method_count": 2,
            "session_permission_lookup_database_call_count": sum(
                any("DataContext" in item["member"] for item in row["ordered_member_references"])
                for row in (permission_by_key, permission_by_id)
            ),
            "base_permission_allowlisted_keys": base_permission_allowlisted_keys,
            "assertion_count": len(assertions),
            "assertion_pass_count": sum(assertions.values()),
            "validation_error_count": len(errors),
        },
        "sources": sources,
        "methods": public_methods,
        "assertions": assertions,
        "method_local_authorization_references": method_local_auth_refs,
        "authorization_interpretation": {
            "method_local_guard_proven": bool(method_local_auth_refs),
            "discount_specific_method_local_guard_proven": False,
            "base_form_toolbar_permission_gate_proven": True,
            "internal_command_permission_recheck_proven": False,
            "permission_enforcement_shape": "SESSION_PERMISSION_TO_TOOLBAR_ENABLED_THEN_VISIBLE_ENABLED_CLICK_GATE",
            "permission_lookup_source": "IN_MEMORY_USER_PERMISSION_SNAPSHOT",
            "permission_lookup_key_shapes": ["ClassName+AccessNodeKey", "AccessNodeId"],
            "admin_bypass_computed_inside_selected_lookup_proven": False,
            "configured_view_child_consumed_by_selected_list_base_permission_method_proven": False,
            "separate_save_permission_key_in_selected_list_base_proven": False,
            "outer_menu_or_base_form_authorization_disproven": False,
            "conclusion": "No named authorization call is present in discount-specific authoring, validation, save, or internal command methods. The inherited base form calls UserSessionInfo.HasPersmission during initialization to set toolbar Enabled state, and click handlers require Visible plus Enabled before dispatch. HasPersmission/HasPermission search the in-memory UserPermissionS snapshot by ClassName+AccessNodeKey or AccessNodeId and return the cached HasAccess flag without a database round trip. Internal commands do not recheck permission, so the proven legacy boundary is UI-command gating over a session snapshot rather than service-layer authorization. How admin bypass and deny precedence were materialized into HasAccess is outside these selected lookup methods.",
        },
        "security_interpretation": {
            "condition_is_only_display_metadata": False,
            "visual_filter_builder_present": True,
            "user_built_condition_is_runtime_validated_by_execution": True,
            "runtime_validation_is_equivalent_to_allowlisted_dsl": False,
            "target_requirement": "Replace stored executable SQL with an allowlisted, versioned rule AST/DSL and enforce explicit author/publisher permissions plus immutable audit history.",
        },
        "validation_errors": errors,
        "limits": [
            "Static IL proves call structure, not the effective user/menu permission assigned at runtime.",
            "The selected methods do not prove every inherited BaseForm guard or every external menu authorization path.",
            "Successful execution-based validation does not make arbitrary stored SQL a safe or portable rule language.",
            "No raw condition, literal business value, rule identifier, or user identifier is retained.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    artifact = collect(args.source_directory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if artifact["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
