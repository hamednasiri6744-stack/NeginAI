"""Extract the hash-pinned RPT-16/RPT-17 selector and routing boundary."""
from __future__ import annotations
import argparse,hashlib,json,sys
from datetime import datetime
from pathlib import Path
import dnfile
from dncil.cil.body.reader import read_method_body_from_bytes
from dncil.clr.token import StringToken,Token
sys.path.insert(0,str(Path(__file__).resolve().parent))
from extract_varanegar_targeted_il_contracts import _full_type_name,_owner_maps,_resolve_token,_text  # noqa:E402
FILE="VN.SDS.Stock.UI.dll";EXPECTED="8b3c00aeb385656523b412352dfb1030f24d69e46c34c6c41cb88b5d8fde2713"
TARGETS={"VN.SDS.Stock.UI.StockGoods.Reports.FormSelectGoodsType":{"MenuButtonSelect_Click","MenuButtonCancel_Click"},"VN.SDS.Stock.UI.StockGoods.Reports.FormSelectMainReport":{"GetReports","MenuButtonSelect_Click","gwSelectReport_SelectionChanged","MenuButtonCancel_Click"}}
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--source-directory",required=True,type=Path);p.add_argument("--output",required=True,type=Path);a=p.parse_args();path=a.source_directory/FILE;raw=path.read_bytes();pe=dnfile.dnPE(str(path));owners,fields=_owner_maps(pe);types={_full_type_name(x):x for x in pe.net.mdtables.TypeDef.rows};rows=[];errors=[]
 for type_name,names in TARGETS.items():
  t=types.get(type_name)
  if not t:errors.append(f"type_{type_name}");continue
  for idx in t.MethodList or []:
   m=idx.row;name=_text(getattr(m,"Name",""))
   if name not in names or not m.Rva:continue
   body=read_method_body_from_bytes(pe.get_data(m.Rva,65536));calls=[];field_refs=[];literal_fingerprints=[]
   for ins in body.instructions:
    if isinstance(ins.operand,Token):
     value=_resolve_token(pe,ins.operand,owners,fields)
     if ins.mnemonic in {"call","callvirt","newobj"}:calls.append({"offset":ins.offset,"member":value})
     elif ins.mnemonic in {"ldfld","ldsfld","stfld","stsfld"}:field_refs.append(value)
    if isinstance(ins.operand,StringToken):
     x=pe.net.user_strings.get(ins.operand.rid);v="" if x is None else _text(x);literal_fingerprints.append({"sha256":sha(v.encode()),"length":len(v),"raw_literal_persisted":False})
   rows.append({"type":type_name,"method":name,"instruction_count":len(body.instructions),"ordered_calls":calls,"referenced_fields":sorted(set(field_refs)),"literal_fingerprints":literal_fingerprints,"uses_data_query":any("DataContext.Query" in x["member"] or "DataContext.All" in x["member"] for x in calls),"sets_dialog_result":any("set_DialogResult" in x["member"] for x in calls),"reads_radio_state":any("RadioButton.get_Checked" in x["member"] for x in calls),"enumerates_report_enum":any("System.Enum.GetValues" in x["member"] for x in calls),"routes_to_production_detail":any("FormProductionDetailReport..ctor" in x["member"] for x in calls),"routes_to_report_result_list":any("FormReportResultList..ctor" in x["member"] for x in calls)})
 if sha(raw)!=EXPECTED:errors.append("hash_mismatch")
 if len(rows)!=6:errors.append("method_count")
 goods=next((x for x in rows if x["type"].endswith("FormSelectGoodsType") and x["method"]=="MenuButtonSelect_Click"),{});main=next((x for x in rows if x["type"].endswith("FormSelectMainReport") and x["method"]=="MenuButtonSelect_Click"),{});get_reports=next((x for x in rows if x["method"]=="GetReports"),{})
 checks={"no_query_in_selected_methods":not any(x["uses_data_query"] for x in rows),"goods_type_returns_dialog_result":goods.get("sets_dialog_result",False),"main_reads_goods_type_choice":main.get("reads_radio_state",False),"enum_resource_catalog":get_reports.get("enumerates_report_enum",False),"routes_to_rpt14":main.get("routes_to_production_detail",False),"routes_to_rpt15":main.get("routes_to_report_result_list",False)};errors.extend(k for k,v in checks.items() if not v)
 out={"artifact":"varanegar_stock_report_selector_boundary_20260829","schema_version":1,"generated_at":datetime.now().astimezone().isoformat(),"validation":"PASS" if not errors else "FAIL","source":{"file":FILE,"size_bytes":len(raw),"sha256":sha(raw),"expected_sha256":EXPECTED,"hash_matches":sha(raw)==EXPECTED},"safety":{"mode":"STATIC_PE_CLR_METADATA_AND_IL","database_connections":0,"queries_forms_or_dialogs_executed":0,"assemblies_loaded_or_executed":0,"raw_business_values_or_identities_persisted":0,"data_mutations":0},"summary":{"selector_type_count":2,"selected_method_count":len(rows),"query_method_count":sum(x["uses_data_query"] for x in rows),"dialog_result_method_count":sum(x["sets_dialog_result"] for x in rows),"report_routing_target_count":sum((main.get("routes_to_production_detail",False),main.get("routes_to_report_result_list",False))),"validation_error_count":len(errors)},"selectors":[{"contract_id":"RPT-16","type":"VN.SDS.Stock.UI.StockGoods.Reports.FormSelectGoodsType","role":"MODAL_GOODS_TYPE_SELECTOR","data_result_owned":False},{"contract_id":"RPT-17","type":"VN.SDS.Stock.UI.StockGoods.Reports.FormSelectMainReport","role":"REPORT_ENUM_AND_ROUTE_ORCHESTRATOR","data_result_owned":False,"routes_to":["RPT-14","RPT-15"]}],"methods":sorted(rows,key=lambda x:(x["type"],x["method"])),"checks":checks,"validation_errors":errors,"confidence":{"selector_and_routing_roles":"CONFIRMED_STATIC_IL","runtime_branch_choice_and_downstream_results":"UNPROVEN"},"limits":["No selector dialog, report or query was executed.","Enum values, localized report names and selected business values are not persisted.","Static constructor calls prove possible routes, not observed runtime choices."]};a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(a.output.resolve());print(out["validation"]);print(json.dumps(out["summary"]));return 0 if not errors else 1
if __name__=="__main__":raise SystemExit(main())
