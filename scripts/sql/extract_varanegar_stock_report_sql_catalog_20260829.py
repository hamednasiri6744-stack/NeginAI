"""Resolve RPT-15 static report bindings against the approved read-only clone."""
from __future__ import annotations
import argparse, hashlib, json, re, sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_varanegar_org_domain import _assert_safe_target, _connect, _rows  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]

def sha(value: str) -> str: return hashlib.sha256(value.encode("utf-8")).hexdigest()

def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--bindings",required=True,type=Path); parser.add_argument("--output",required=True,type=Path); args=parser.parse_args()
    binding=json.loads(args.bindings.read_text(encoding="utf-8-sig")); errors=[]; modules=[]
    connection=_connect()
    try:
        cursor=connection.cursor(); context=_assert_safe_target(cursor)
        for method in binding["methods"]:
            static_name=method["redacted_sql_literals"][0]["object_candidates"][0]
            if "." in static_name:
                schema,name=static_name.split(".",1)
                rows=_rows(cursor,"""SELECT o.object_id,s.name schema_name,o.name,o.type_desc,m.definition,o.modify_date FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id WHERE s.name=%s AND o.name=%s""",(schema,name))
            else:
                rows=_rows(cursor,"""SELECT o.object_id,s.name schema_name,o.name,o.type_desc,m.definition,o.modify_date FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id WHERE o.name=%s ORDER BY CASE WHEN s.name='dbo' THEN 0 ELSE 1 END,s.name""",(static_name,))
            if len(rows)!=1:
                errors.append(f"catalog_resolution_{method['method']}_{len(rows)}"); continue
            row=rows[0]; qualified=f"{row['schema_name']}.{row['name']}"; definition=row["definition"] or ""
            parameters=_rows(cursor,"""SELECT parameter_id,name parameter_name,TYPE_NAME(user_type_id) data_type,max_length,precision,scale,is_output,has_default_value FROM sys.parameters WHERE object_id=%s ORDER BY parameter_id""",(row["object_id"],))
            dependencies=_rows(cursor,"""SELECT DISTINCT COALESCE(referenced_schema_name,'?') referenced_schema,referenced_entity_name FROM sys.sql_expression_dependencies WHERE referencing_id=%s AND referenced_entity_name IS NOT NULL ORDER BY referenced_schema,referenced_entity_name""",(row["object_id"],))
            normalized=" ".join(definition.replace("[","").replace("]","").split()).casefold()
            semantic={"select_token_count":len(re.findall(r"\bselect\b",normalized)),"sum_token_count":len(re.findall(r"\bsum\s*\(",normalized)),"group_by_count":len(re.findall(r"\bgroup\s+by\b",normalized)),"date_parameter_reference_count":len(re.findall(r"@(date1|date2|accyear)\b",normalized)),"scope_parameter_reference_count":len(re.findall(r"@(dcref|stockdcref|stockdccode|goodsref|goodscode1|goodscode2)\b",normalized)),"status_or_cancel_term_count":len(re.findall(r"\b(status|isdeleted|iscanceled|iscancelled|cancel)\w*\b",normalized)),"uses_nolock":bool(re.search(r"\bwith\s*\(\s*nolock\s*\)|\bnolock\b",normalized)),"uses_dynamic_sql":bool(re.search(r"\bsp_executesql\b|\bexec\s*\(@",normalized)),"uses_temp_table":bool(re.search(r"#[a-z_]\w*",normalized)),"write_dml_token_count":len(re.findall(r"\b(insert|update|delete|merge)\b",normalized))}
            modules.append({"method":method["method"],"static_object_name":static_name,"catalog_qualified_name":qualified,"static_name_matches_catalog":static_name.casefold()==qualified.casefold() or ("." not in static_name and static_name.casefold()==row["name"].casefold()),"type_desc":row["type_desc"],"modify_date":row["modify_date"],"definition_sha256":sha(definition),"definition_character_count":len(definition),"catalog_parameters":parameters,"static_named_parameters":method["redacted_sql_literals"][0]["named_parameters"],"referenced_objects":[f"{x['referenced_schema']}.{x['referenced_entity_name']}" for x in dependencies],"semantic_profile":semantic,"definition_text_persisted":False})
        safe=context["updateability"]=="READ_ONLY" and context["can_update"]==0 and context["denies_data_writes"]==1
        if not safe: errors.append("unsafe_database_context")
        if len(modules)!=10: errors.append("resolved_module_count_not_ten")
        if any(not m["static_name_matches_catalog"] for m in modules): errors.append("static_catalog_name_mismatch")
        payload={"artifact":"varanegar_stock_report_sql_catalog_20260829","schema_version":1,"generated_at":datetime.now().astimezone().isoformat(),"validation":"PASS" if not errors else "FAIL","source":{"server_class":"LOCAL_READ_ONLY_CLONE","database":context["database_name"],"login":context["login_name"],"binding_artifact_sha256":hashlib.sha256(args.bindings.read_bytes()).hexdigest()},"safety":{"database_updateability":context["updateability"],"can_update":context["can_update"],"denies_data_writes":context["denies_data_writes"],"catalog_queries_only":True,"operational_report_or_procedure_executions":0,"raw_definitions_or_business_values_persisted":0,"source_state_changes":0},"summary":{"static_binding_count":len(binding["methods"]),"catalog_resolved_count":len(modules),"exact_static_catalog_name_match_count":sum(m["static_name_matches_catalog"] for m in modules),"catalog_parameter_count":sum(len(m["catalog_parameters"]) for m in modules),"dependency_count":sum(len(m["referenced_objects"]) for m in modules),"validation_error_count":len(errors)},"modules":modules,"validation_errors":errors,"confidence":{"method_to_sql_object":"CONFIRMED_STATIC_IL_PLUS_CATALOG","parameter_runtime_values":"UNPROVEN","result_parity":"UNPROVEN"},"limits":["Catalog identity, signatures and declared dependencies are proven; procedure bodies and report results were not executed.","Dynamic dependencies may be absent from sys.sql_expression_dependencies."]}
        args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(payload,ensure_ascii=False,indent=2,default=str)+"\n",encoding="utf-8"); print(args.output.resolve()); print(payload["validation"]); print(json.dumps(payload["summary"])); return 0 if payload["validation"]=="PASS" else 1
    finally: connection.close()
if __name__=="__main__": raise SystemExit(main())
