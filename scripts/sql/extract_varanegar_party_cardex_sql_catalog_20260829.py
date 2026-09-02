"""Resolve party-cardex objects in the approved read-only clone catalog."""
from __future__ import annotations
import argparse,hashlib,json,re,sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from extract_varanegar_org_domain import _assert_safe_target,_connect,_rows  # noqa:E402

def sha(value:str)->str:return hashlib.sha256(value.encode()).hexdigest()

def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--boundary",required=True,type=Path);p.add_argument("--output",required=True,type=Path);a=p.parse_args()
 b=json.loads(a.boundary.read_text(encoding="utf-8-sig"));candidates=[]
 for assembly in b["assemblies"]:
  for method in assembly["methods"]:
   for literal in method["redacted_sql_literals"]:
    for obj in literal["object_candidates"]:
     candidates.append({"method":method["method"],"candidate":obj})
 modules=[];errors=[];con=_connect()
 try:
  cur=con.cursor();ctx=_assert_safe_target(cur)
  for item in candidates:
   parts=item["candidate"].split(".",1);schema,name=(parts if len(parts)==2 else (None,parts[0]))
   rows=_rows(cur,"""SELECT o.object_id,s.name schema_name,o.name,o.type_desc,m.definition,o.modify_date
FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
WHERE o.name=%s AND (%s IS NULL OR s.name=%s)""",(name,schema,schema))
   if len(rows)!=1:errors.append(f"resolution_{item['method']}_{len(rows)}");continue
   row=rows[0];definition=row["definition"] or "";normalized=" ".join(definition.replace("[","").replace("]","").split()).casefold()
   params=_rows(cur,"SELECT parameter_id,name parameter_name,TYPE_NAME(user_type_id) data_type,max_length,precision,scale,is_output FROM sys.parameters WHERE object_id=%s ORDER BY parameter_id",(row["object_id"],))
   deps=_rows(cur,"SELECT DISTINCT COALESCE(referenced_schema_name,'?') referenced_schema,referenced_entity_name FROM sys.sql_expression_dependencies WHERE referencing_id=%s AND referenced_entity_name IS NOT NULL ORDER BY referenced_schema,referenced_entity_name",(row["object_id"],))
   tokens={key:len(re.findall(pattern,normalized)) for key,pattern in {"acc_year":r"accyear|acc_year","dc_scope":r"dcref|dc_ref","party_scope":r"cust(ref|code)|supplierref","date_scope":r"startdate|enddate|filterdate","currency_scope":r"currency(ref|code)|exchangerate","summary_scope":r"summarytype|showjustremainamount","amount_terms":r"debit|credit|remain|amount","aggregation":r"\bsum\s*\(|\bgroup\s+by\b"}.items()}
   semantic={"uses_dynamic_sql":bool(re.search(r"\bsp_executesql\b|\bexec\s*\(@",normalized)),"write_dml_token_count":len(re.findall(r"\b(insert|update|delete|merge)\b",normalized)),"semantic_token_counts":tokens}
   modules.append({"method":item["method"],"literal_candidate":item["candidate"],"sql_object":f"{row['schema_name']}.{row['name']}","type_desc":row["type_desc"],"modify_date":row["modify_date"],"definition_sha256":sha(definition),"definition_character_count":len(definition),"parameters":params,"referenced_objects":[f"{x['referenced_schema']}.{x['referenced_entity_name']}" for x in deps],"semantic_profile":semantic,"definition_persisted":False})
  safe=ctx["updateability"]=="READ_ONLY" and ctx["can_update"]==0 and ctx["denies_data_writes"]==1
  if not safe:errors.append("unsafe_context")
  if len(modules)!=5:errors.append("module_count")
  out={"artifact":"varanegar_party_cardex_sql_catalog_20260829","schema_version":1,"generated_at":datetime.now().astimezone().isoformat(),"validation":"PASS" if not errors else "FAIL","source":{"server_class":"LOCAL_READ_ONLY_CLONE","database":ctx["database_name"],"login":ctx["login_name"],"boundary_sha256":hashlib.sha256(a.boundary.read_bytes()).hexdigest()},"safety":{"database_updateability":ctx["updateability"],"can_update":ctx["can_update"],"denies_data_writes":ctx["denies_data_writes"],"catalog_queries_only":True,"report_or_operational_procedure_executions":0,"raw_definitions_or_business_values_persisted":0,"source_state_changes":0},"summary":{"resolved_object_count":len(modules),"parameter_count":sum(len(x["parameters"]) for x in modules),"dependency_count":sum(len(x["referenced_objects"]) for x in modules),"validation_error_count":len(errors)},"modules":modules,"validation_errors":errors,"confidence":{"identity_signature_dependencies":"CONFIRMED","formula_and_runtime_results":"UNPROVEN"},"limits":["Objects were resolved from catalog only; no view or procedure was executed.","Dynamic dependencies and result-set formulas may not be fully visible in catalog metadata."]}
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2,default=str)+"\n",encoding="utf-8");print(a.output.resolve());print(out["validation"]);print(json.dumps(out["summary"]));return 0 if not errors else 1
 finally:con.close()

if __name__=="__main__":raise SystemExit(main())
