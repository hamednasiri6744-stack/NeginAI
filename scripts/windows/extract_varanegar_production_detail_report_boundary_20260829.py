"""Extract the hash-pinned RPT-14 generic GetAllView-to-SQL and export boundary."""
from __future__ import annotations
import argparse,hashlib,json,sys
from datetime import datetime
from pathlib import Path
import dnfile
from dncil.cil.body.reader import read_method_body_from_bytes
from dncil.clr.token import StringToken,Token
sys.path.insert(0,str(Path(__file__).resolve().parent))
from extract_varanegar_targeted_il_contracts import _full_type_name,_owner_maps,_resolve_token,_text  # noqa:E402
FILES={"VN.SDS.Stock.UI.dll":"8b3c00aeb385656523b412352dfb1030f24d69e46c34c6c41cb88b5d8fde2713","VN.SDS.MainData.DataAccess.dll":"5dcb9f47a484ed5c3d04344130ea9ef1f2e5e97c4b5acd2b11b02df0a878d987","VN.SDS.Common.dll":"403e01ae11294457ed9ee6e8be3e8ab75eeb7c8cc5da3a57956a3c8c09d64b18","Application.BusinessLayer.dll":"3322cee4550c172c87142085c4c89bccc4bb2fd3dd583040385920b6a7ff5408"}
UI_TYPE="VN.SDS.Stock.UI.StockGoods.Reports.FormProductionDetailReport";ENTITY="VN.SDS.Common.MainData.Entity.BatchNumber.BatchNumberEntity";VIEW="VN.SDS.Common.MainData.Entity.BatchNumber.BatchNumberViewEntity";ADAPTER="VN.SDS.MainData.DataAccess.DataAdapter.BatchNumber.BatchNumberAdapter";BASE="Application.BusinessLayer.DataAdapter.BaseDataV2Adapter`4"
def sha(b):return hashlib.sha256(b).hexdigest()
def find_type(pe,name):return next((x for x in pe.net.mdtables.TypeDef.rows if _full_type_name(x)==name),None)
def method(pe,t,name):return next((x.row for x in (t.MethodList or []) if _text(x.row.Name)==name and x.row.Rva),None)
def calls_and_strings(pe,m):
 owners,fields=_owner_maps(pe);body=read_method_body_from_bytes(pe.get_data(m.Rva,65536));calls=[];strings=[]
 for i in body.instructions:
  if i.mnemonic in {"call","callvirt","newobj"} and isinstance(i.operand,Token):calls.append({"offset":i.offset,"member":_resolve_token(pe,i.operand,owners,fields)})
  if isinstance(i.operand,StringToken):
   x=pe.net.user_strings.get(i.operand.rid);v="" if x is None else _text(x);strings.append({"sha256":sha(v.encode()),"length":len(v),"safe_object_name":v if v.casefold().startswith(("usp_","gnr.")) else None,"raw_business_value_persisted":False})
 return {"instruction_count":len(body.instructions),"ordered_calls":calls,"redacted_literals":strings}
def main():
 p=argparse.ArgumentParser();p.add_argument("--source-directory",required=True,type=Path);p.add_argument("--output",required=True,type=Path);a=p.parse_args();pes={};sources=[];errors=[]
 for f,h in FILES.items():
  path=a.source_directory/f;raw=path.read_bytes();sources.append({"file":f,"size_bytes":len(raw),"sha256":sha(raw),"expected_sha256":h,"hash_matches":sha(raw)==h});pes[f]=dnfile.dnPE(str(path))
  if sha(raw)!=h:errors.append(f"hash_{f}")
 ui=find_type(pes["VN.SDS.Stock.UI.dll"],UI_TYPE);entity=find_type(pes["VN.SDS.Common.dll"],ENTITY);view=find_type(pes["VN.SDS.Common.dll"],VIEW);adapter=find_type(pes["VN.SDS.MainData.DataAccess.dll"],ADAPTER);base=find_type(pes["Application.BusinessLayer.dll"],BASE)
 if not all((ui,entity,view,adapter,base)):errors.append("type_chain_missing")
 rows={}
 if ui:
  for n in ("GetBatchWithStock","GetBatchWithoutStock","FillTotalQty","menubuttonExportToExcell_Click"):
   m=method(pes["VN.SDS.Stock.UI.dll"],ui,n)
   if m:rows[n]=calls_and_strings(pes["VN.SDS.Stock.UI.dll"],m)
 if entity:
  for n in ("GetDataSPName","GetTableName"):
   m=method(pes["VN.SDS.Common.dll"],entity,n)
   if m:rows[n]=calls_and_strings(pes["VN.SDS.Common.dll"],m)
 if base:
  candidates=[x.row for x in (base.MethodList or []) if _text(x.row.Name)=="GetAllView" and x.row.Rva];chosen=max(candidates,key=lambda m:calls_and_strings(pes["Application.BusinessLayer.dll"],m)["instruction_count"]);rows["BaseDataV2Adapter.GetAllView"]=calls_and_strings(pes["Application.BusinessLayer.dll"],chosen)
 view_extends_entity=bool(view and getattr(view,"Extends",None) and view.Extends.row is entity);sp=next((x["safe_object_name"] for x in rows.get("GetDataSPName",{}).get("redacted_literals",[]) if x["safe_object_name"]),None);table=next((x["safe_object_name"] for x in rows.get("GetTableName",{}).get("redacted_literals",[]) if x["safe_object_name"]),None);base_calls=[x["member"] for x in rows.get("BaseDataV2Adapter.GetAllView",{}).get("ordered_calls",[])];ui_get_calls=[x["member"] for n in ("GetBatchWithStock","GetBatchWithoutStock") for x in rows.get(n,{}).get("ordered_calls",[])];export_calls=[x["member"] for x in rows.get("menubuttonExportToExcell_Click",{}).get("ordered_calls",[])]
 checks={"four_hashes":all(x["hash_matches"] for x in sources),"view_extends_entity":view_extends_entity,"sp_override":sp=="usp_sdsnet_BatchNo_GetList","table_override":table.casefold()=="gnr.tblbatchno" if table else False,"ui_two_generic_reads":sum("GetAllView" in x for x in ui_get_calls)==2,"base_resolves_sp_and_executes_read":any("GetDataSPName" in x for x in base_calls) and any("DataContext.AllFast" in x for x in base_calls),"file_export":any("ExportToXls" in x for x in export_calls)}
 errors.extend(k for k,v in checks.items() if not v)
 out={"artifact":"varanegar_production_detail_report_boundary_20260829","schema_version":1,"generated_at":datetime.now().astimezone().isoformat(),"validation":"PASS" if not errors else "FAIL","sources":sources,"safety":{"mode":"STATIC_PE_CLR_METADATA_AND_IL","database_connections":0,"queries_forms_or_exports_executed":0,"assemblies_loaded_or_executed":0,"raw_sql_business_values_or_identities_persisted":0,"data_mutations":0},"summary":{"assembly_count":len(sources),"selected_method_count":len(rows),"generic_read_path_count":2,"exact_sql_binding_count":1 if sp else 0,"file_export_path_count":1 if checks["file_export"] else 0,"validation_error_count":len(errors)},"chain":{"ui_type":UI_TYPE,"read_methods":["GetBatchWithStock","GetBatchWithoutStock"],"adapter_type":ADAPTER,"generic_base_type":BASE,"view_type":VIEW,"view_extends_entity":view_extends_entity,"entity_type":ENTITY,"sql_object_candidate":sp,"table_name":table,"binding":"CONFIRMED_STATIC_INHERITANCE_AND_IL_CHAIN"},"methods":rows,"checks":checks,"validation_errors":errors,"confidence":{"generic_query_identity_and_export":"CONFIRMED_STATIC_IL","with_vs_without_stock_filter_formula_and_results":"UNPROVEN"},"limits":["No assembly, query, form or export was executed.","The adapter generic TypeSpec is corroborated by type references; raw TypeSpec bytes are not persisted.","With/without-stock distinction is expressed through FetchReason and requires result parity evidence."]};a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(a.output.resolve());print(out["validation"]);print(json.dumps(out["summary"]));return 0 if not errors else 1
if __name__=="__main__":raise SystemExit(main())
