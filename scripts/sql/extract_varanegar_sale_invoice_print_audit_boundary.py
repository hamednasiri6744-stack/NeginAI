"""Extract read-only sale-invoice template and physical-print audit semantics."""
from __future__ import annotations
import argparse, hashlib, json, re
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_org_domain import _assert_safe_target, _connect, _json_default, _rows

MODULES=(("dbo","USP_SDSNET_PrintedDoc_GetList"),("SLE","usp_SetPrintedDoc"))
RECENT_FROM="20260522"; RECENT_TO="20260823"

def _profiles(cur:Any):
 rows=[]
 for schema,name in MODULES:
  found=_rows(cur,"""select s.name schema_name,o.name object_name,o.type_desc,o.create_date,o.modify_date,sm.definition from sys.objects o join sys.schemas s on s.schema_id=o.schema_id join sys.sql_modules sm on sm.object_id=o.object_id where s.name=%s and o.name=%s""",(schema,name))
  if len(found)!=1:raise AssertionError(f"expected one module {schema}.{name}")
  row=found[0];d=row.pop("definition") or "";compact=re.sub(r"\s+"," ",d)
  callers=_rows(cur,"""select distinct object_schema_name(referencing_id) caller_schema,object_name(referencing_id) caller_name from sys.sql_expression_dependencies where referenced_id=object_id(%s) order by caller_schema,caller_name""",(f"{schema}.{name}",))
  row.update({"qualified_name":f"{schema}.{name}","definition_sha256":hashlib.sha256(d.encode()).hexdigest(),"definition_character_count":len(d),"static_sql_caller_count":len(callers),"static_sql_callers":[f"{x['caller_schema']}.{x['caller_name']}" for x in callers],"begin_transaction_signal_count":len(re.findall(r"(?i)\bbegin\s+tran(?:saction)?\b",compact)),"commit_signal_count":len(re.findall(r"(?i)\bcommit(?:\s+tran(?:saction)?)?\b",compact)),"rollback_signal_count":len(re.findall(r"(?i)\brollback(?:\s+tran(?:saction)?)?\b",compact)),"dynamic_sql_signal":bool(re.search(r"(?i)\bsp_executesql\b|\bexec\s*\(",compact)),"reads_print_audit_signal":bool(re.search(r"(?i)\bfrom\s+GNR\.tblPrintedDoc\b",compact)),"inserts_print_audit_signal":bool(re.search(r"(?i)\binsert\s+into\s+GNR\.tblPrintedDoc\b",compact)),"kind0_range_reuses_lower_bound_signal":bool(re.search(r"(?i)Between\s+@DistNo1\s+And\s+@DistNo1",compact)),"kind0_contains_hardcoded_scope_literals_signal":name=="usp_SetPrintedDoc" and bool(re.search(r"(?i)IF\s+@KindPrint\s*=\s*0[\s\S]{0,1000}where\s+SM\.DcRef\s*=\s*\d+",d)),"definition_error_or_business_values_persisted":False})
  rows.append(row)
 return rows

def _template_inventory(cur:Any,source:Path):
 configured=_rows(cur,"""select Id,FileName,ReportType,IsDefault,generalConfigId from GNR.tblReportFile order by ReportType,IsDefault desc,Id""")
 files=[]
 for folder in ("Report","Rep","CustomReps"):
  root=source/folder
  if root.is_dir():
   for p in root.rglob("*"):
    if p.is_file() and p.suffix.casefold() in {".rpt",".mrt"}:
     files.append({"root":folder,"name_casefold":p.name.casefold(),"size":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()})
 names={x["name_casefold"] for x in files}
 safe=[]
 for x in configured:
  name=str(x.pop("FileName") or "")
  safe.append({**x,"file_name_sha256":hashlib.sha256(name.encode()).hexdigest(),"file_name_length":len(name),"extension":Path(name).suffix.casefold(),"matched_in_scanned_deployment_roots":name.casefold() in names,"raw_name_persisted":False})
 return {"configured_templates":safe,"configured_template_count":len(safe),"configured_default_count":sum(int(x["IsDefault"] or 0)==1 for x in safe),"configured_distinct_filename_hash_count":len({x["file_name_sha256"] for x in safe}),"scanned_template_file_count":len(files),"scanned_root_counts":[{"root":r,"file_count":sum(x["root"]==r for x in files)} for r in ("Report","Rep","CustomReps")],"configured_template_deployment_match_count":sum(x["matched_in_scanned_deployment_roots"] for x in safe),"scanned_file_names_or_paths_persisted":0}

def collect(source:Path,binary_inventory:Path):
 con=_connect()
 try:
  cur=con.cursor();ctx=_assert_safe_target(cur)
  if str(ctx["updateability"]).upper()!="READ_ONLY" or int(ctx["can_update"] or 0)!=0:raise RuntimeError("analysis database not read-only")
  profiles=_profiles(cur);templates=_template_inventory(cur,source)
  by_type=_rows(cur,f"""select DocType,count_big(*) print_event_count,count(distinct DocRef) document_count,min(PrintDate) minimum_print_time,max(PrintDate) maximum_print_time,sum(case when PrintDate>='{RECENT_FROM}' and PrintDate<'{RECENT_TO}' then 1 else 0 end) recent_print_event_count from GNR.tblPrintedDoc group by DocType order by DocType""")
  duplicate=_rows(cur,"""with x as(select DocType,DocRef,count_big(*) n from GNR.tblPrintedDoc group by DocType,DocRef)select count_big(*) document_key_count,sum(case when n>1 then 1 else 0 end) repeated_document_key_count,max(n) maximum_prints_per_document,sum(n) print_event_count from x""")[0]
  type2=_rows(cur,f"""with d as(select distinct DocRef from GNR.tblPrintedDoc where DocType=2) select count_big(*) document_count,sum(case when s.ID is null then 1 else 0 end) absent_sale_count,sum(case when s.CancelFlag=1 then 1 else 0 end) cancelled_sale_count,sum(case when s.CancelFlag=0 then 1 else 0 end) active_sale_count from d left join SLE.tblSaleHdr s on s.ID=d.DocRef""")[0]
  type2_events=_rows(cur,f"""select count_big(*) print_event_count,count(distinct DocRef) document_count,sum(case when PrintDate>='{RECENT_FROM}' and PrintDate<'{RECENT_TO}' then 1 else 0 end) recent_print_event_count from GNR.tblPrintedDoc where DocType=2""")[0]
  type2_repeat=_rows(cur,"""with x as(select DocRef,count_big(*) n from GNR.tblPrintedDoc where DocType=2 group by DocRef)select count_big(*) document_count,sum(case when n>1 then 1 else 0 end) repeated_document_count,max(n) maximum_prints_per_document,sum(n) print_event_count from x""")[0]
  after_cancel=_rows(cur,f"""with c as(select HdrRef,ModifiedDate,row_number()over(partition by HdrRef order by ModifiedDate desc,ID desc) rn from SLE.tblSaleHdrDetail),x as(select p.DocRef,p.PrintDate,datediff(second,c.ModifiedDate,p.PrintDate) lag_seconds from GNR.tblPrintedDoc p join SLE.tblSaleHdr s on s.ID=p.DocRef and s.CancelFlag=1 join c on c.HdrRef=s.ID and c.rn=1 where p.DocType=2 and p.PrintDate>c.ModifiedDate)select count_big(*) print_event_count,count(distinct DocRef) document_count,sum(case when lag_seconds<=300 then 1 else 0 end) within_five_minutes_count,sum(case when lag_seconds>300 and lag_seconds<=86400 then 1 else 0 end) after_five_minutes_within_day_count,sum(case when lag_seconds>86400 then 1 else 0 end) after_day_count,max(lag_seconds) maximum_lag_seconds,sum(case when PrintDate>='{RECENT_FROM}' and PrintDate<'{RECENT_TO}' then 1 else 0 end) recent_print_event_count from x""")[0]
  inventory=json.loads(binary_inventory.read_text(encoding="utf-8-sig"));needle="usp_SetPrintedDoc";literal_hits=[]
  for item in inventory["files"]:
   name=item["name"]
   if not name.casefold().endswith((".dll",".exe")):continue
   p=source/name
   if not p.is_file():continue
   b=p.read_bytes()
   if needle.encode() in b or needle.encode("utf-16le") in b:literal_hits.append(name)
  p={x["qualified_name"]:x for x in profiles}
  contract={"get_list_reads_audit_and_uses_dynamic_sql":p["dbo.USP_SDSNET_PrintedDoc_GetList"]["reads_print_audit_signal"] and p["dbo.USP_SDSNET_PrintedDoc_GetList"]["dynamic_sql_signal"],"get_list_kind0_reuses_lower_bound_as_upper_bound":p["dbo.USP_SDSNET_PrintedDoc_GetList"]["kind0_range_reuses_lower_bound_signal"],"alternate_set_procedure_inserts_audit_without_local_transaction":p["SLE.usp_SetPrintedDoc"]["inserts_print_audit_signal"] and p["SLE.usp_SetPrintedDoc"]["begin_transaction_signal_count"]==0,"alternate_set_procedure_kind0_contains_hardcoded_scope_literals":p["SLE.usp_SetPrintedDoc"]["kind0_contains_hardcoded_scope_literals_signal"],"alternate_set_procedure_has_no_static_sql_caller":p["SLE.usp_SetPrintedDoc"]["static_sql_caller_count"]==0,"alternate_set_procedure_has_no_exact_deployed_binary_literal":len(literal_hits)==0}
  summary={"selected_sql_module_count":len(profiles),"configured_template_count":templates["configured_template_count"],"configured_template_deployment_match_count":templates["configured_template_deployment_match_count"],"scanned_template_file_count":templates["scanned_template_file_count"],"print_event_count":int(duplicate["print_event_count"]),"printed_document_key_count":int(duplicate["document_key_count"]),"repeated_printed_document_key_count":int(duplicate["repeated_document_key_count"]),"maximum_prints_per_document":int(duplicate["maximum_prints_per_document"]),"sale_print_event_count":int(type2_events["print_event_count"]),"sale_printed_document_count":int(type2["document_count"]),"repeated_sale_printed_document_count":int(type2_repeat["repeated_document_count"]),"maximum_sale_prints_per_document":int(type2_repeat["maximum_prints_per_document"]),"sale_printed_absent_current_sale_count":int(type2["absent_sale_count"]),"post_terminal_cancel_sale_print_event_count":int(after_cancel["print_event_count"]),"post_terminal_cancel_sale_document_count":int(after_cancel["document_count"]),"recent_post_terminal_cancel_sale_print_event_count":int(after_cancel["recent_print_event_count"])}
  return {"artifact":"varanegar_sale_invoice_print_audit_boundary","schema_version":1,"generated_at":datetime.now().astimezone().isoformat(),"validation":"PASS" if all(contract.values()) else "FAIL","scope":{"server":"127.0.0.1","database":"NeginPakhsh_WebDev","deployment_root":"HASH_PINNED_VN_SDS_CONTAINER"},"safety":{"mode":"READ_ONLY_CLONE_STATIC_DEPLOYMENT_AND_ANONYMOUS_PRINT_AUDIT_AGGREGATES","database_updateability":ctx["updateability"],"can_select":ctx["can_select"],"can_view_definition":ctx["can_view_definition"],"can_update":ctx["can_update"],"denies_data_writes":1,"report_procedure_view_form_print_or_application_command_executions":0,"assemblies_loaded_or_executed":0,"report_sale_customer_user_host_template_name_or_raw_values_persisted":0,"sql_definitions_error_texts_connection_strings_or_business_identifiers_persisted":0,"source_or_target_state_changed":0},"summary":summary,"sql_module_profiles":profiles,"static_print_sql_contract":contract,"report_template_inventory":templates,"print_audit_by_document_type":by_type,"print_audit_key_repetition":duplicate,"sale_print_document_integrity":type2,"sale_print_event_profile":type2_events,"sale_print_repetition":type2_repeat,"sale_print_after_current_terminal_cancel_time":after_cancel,"exact_alternate_procedure_literal_hit_count":len(literal_hits),"evidence_limits":["Configured template absence from the scanned deployment roots does not prove a runtime load failure; another current directory, cache or external distribution source may exist.","Post-terminal print timestamps prove audit ordering, not whether the output was operational use, archive copy or an approved VOID reprint.","The hard-coded alternate procedure is capability only: no SQL dependency or exact deployed binary literal was found and invocation is not attributed.","No report, template, procedure, view, form or print command was executed and no raw template, sale, user, host, connection or report result was persisted."]}
 finally:con.close()

def main():
 p=argparse.ArgumentParser();p.add_argument("--source-directory",required=True,type=Path);p.add_argument("--binary-inventory",required=True,type=Path);p.add_argument("--output",required=True,type=Path);a=p.parse_args();x=collect(a.source_directory,a.binary_inventory);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(x,ensure_ascii=False,indent=2,default=_json_default)+"\n",encoding="utf-8");print(a.output.resolve());print(json.dumps(x["summary"],ensure_ascii=False));print(json.dumps(x["static_print_sql_contract"],ensure_ascii=False));return 0 if x["validation"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
