"""Extract hash-pinned Crystal invoice-print and print-audit runtime routes."""
from __future__ import annotations
import argparse,hashlib,json,logging,sys
from datetime import datetime
from pathlib import Path
from typing import Any
import dnfile
from dncil.cil.body.reader import read_method_body_from_bytes
from dncil.clr.token import StringToken,Token
WINDOWS=Path(__file__).resolve().parents[1]/"windows";sys.path.insert(0,str(WINDOWS))
from extract_varanegar_targeted_il_contracts import _full_type_name,_owner_maps,_resolve_token  # noqa:E402

TARGETS={
 "VN.SDS.Sales.UI.dll":{"VN.SDS.Sales.UI.Sale.FormReportFactor":{"GetReportPathName","PrintDrfact","PrintDrfactColl","PrintCommand"}},
 "VN.SDS.Sales.Business.dll":{"VN.SDS.Sales.Business.PrintInvoice.PrintInvoiceHandler":{"SetLoginDrFactForVocherOrFactor","SaveCommandDRFact"}},
 "Application.ReportEngine.dll":{"Application.ReportEngine.frmPreviewPrint":{"GetReportRunningPath","ShowReportFact","RefreshReport"}},
}
SAFE={
 "VN.SDS.Common.MainData.Entity.ReportFile.ReportFileEntity.get_FileName",
 "VN.SDS.Sales.UI.Sale.FormReportFactor.GetReportPathName","VN.SDS.Sales.UI.Sale.FormReportFactor.PrintDrfact","VN.SDS.Sales.UI.Sale.FormReportFactor.PrintDrfactColl",
 "Application.ReportEngine.frmPreviewPrint..ctor","Application.ReportEngine.frmPreviewPrint.ShowReportFact","Application.ReportEngine.frmPreviewPrint.get_PrintedCompleted","Application.ReportEngine.frmPreviewPrint.GetReportRunningPath","Application.ReportEngine.frmPreviewPrint.RefreshReport",
 "CrystalDecisions.CrystalReports.Engine.ReportDocument..ctor","CrystalDecisions.CrystalReports.Engine.ReportDocument.Load","CrystalDecisions.CrystalReports.Engine.ReportDocument.SetParameterValue","CrystalDecisions.CrystalReports.Engine.ReportDocument.PrintToPrinter","CrystalDecisions.CrystalReports.Engine.Table.ApplyLogOnInfo","CrystalDecisions.Windows.Forms.CrystalReportViewer.set_ReportSource",
 "System.IO.File.Exists","Application.DataLayer.DBConnector.get_ConnectionString","Application.DataLayer.DBConnector.get_Connection",
 "VN.SDS.Sales.Business.PrintInvoice.PrintInvoiceHandler.SetLoginDrFactForVocherOrFactor","VN.SDS.Sales.Business.PrintInvoice.PrintInvoiceHandler.SaveCommandDRFact",
 "Thunderstruck.DataContext..ctor","Thunderstruck.DataContext.Commit","Thunderstruck.DataContext.RollBack","Thunderstruck.DataContext.Dispose","TypeSpecRow.SaveCommand","VN.SDS.Common.Sales.Entity.PrintedDoc.PrintedDocEntity.set_DocType",
}
def _load(p):return json.loads(p.read_text(encoding="utf-8-sig"))
def _method(pe,assembly,owner,index,mo,fo):
 body=read_method_body_from_bytes(pe.get_data(index.row.Rva,524288));events=[];literals=[];const2=[]
 for ins in body.instructions:
  o=ins.operand
  if isinstance(o,StringToken):
   item=pe.net.user_strings.get(o.rid);value="" if item is None else str(item.value);low=value.casefold()
   literals.append({"sha256":hashlib.sha256(value.encode()).hexdigest(),"length":len(value),"report_or_rep_path_marker":("\\report\\" in low or "\\rep\\" in low),"custom_override_marker":"\\customreps\\" in low,"raw_value_persisted":False})
  elif isinstance(o,Token):
   m=_resolve_token(pe,o,mo,fo)
   if m in SAFE:events.append({"offset":int(ins.offset),"opcode":ins.mnemonic,"member":m})
  if ins.mnemonic=="ldc.i4.2":const2.append(int(ins.offset))
 return {"assembly_file":assembly,"type":owner,"method":str(index.row.Name),"instruction_count":len(body.instructions),"has_exception_regions":bool(body.exception_handlers),"event_ledger":events,"integer_constant_two_offsets":const2,"literal_fingerprints":literals}
def collect(source:Path,inventory:Path):
 expected={x["name"]:x["sha256"] for x in _load(inventory)["files"]};sources=[];methods=[];errors=[]
 for assembly,targets in TARGETS.items():
  path=source/assembly;actual=hashlib.sha256(path.read_bytes()).hexdigest();match=actual==expected.get(assembly);sources.append({"assembly_file":assembly,"assembly_bytes":path.stat().st_size,"assembly_sha256":actual,"inventory_sha256_match":match})
  if not match:errors.append({"assembly_file":assembly,"error":"inventory hash mismatch"})
  pe=dnfile.dnPE(str(path));mo,fo=_owner_maps(pe);types={_full_type_name(x):x for x in pe.net.mdtables.TypeDef.rows}
  for owner,selected in targets.items():
   tr=types.get(owner)
   if tr is None:errors.append({"assembly_file":assembly,"type":owner,"error":"type absent"});continue
   found=set()
   for index in tr.MethodList or []:
    row=index.row
    if row is None or not row.Rva or str(row.Name) not in selected:continue
    found.add(str(row.Name))
    try:methods.append(_method(pe,assembly,owner,index,mo,fo))
    except Exception as e:errors.append({"assembly_file":assembly,"type":owner,"method":str(row.Name),"error":type(e).__name__})
   for missing in selected-found:errors.append({"assembly_file":assembly,"type":owner,"method":missing,"error":"method absent"})
 def one(owner,name):
  rows=[x for x in methods if x["type"]==owner and x["method"]==name];return rows[0] if len(rows)==1 else None
 def off(m,member):return [] if m is None else [x["offset"] for x in m["event_ledger"] if x["member"]==member]
 ui="VN.SDS.Sales.UI.Sale.FormReportFactor";be="VN.SDS.Sales.Business.PrintInvoice.PrintInvoiceHandler";eng="Application.ReportEngine.frmPreviewPrint"
 path=one(ui,"GetReportPathName");single=one(ui,"PrintDrfact");multi=one(ui,"PrintDrfactColl");mark=one(be,"SetLoginDrFactForVocherOrFactor");save=one(be,"SaveCommandDRFact");resolve=one(eng,"GetReportRunningPath");show=one(eng,"ShowReportFact");refresh=one(eng,"RefreshReport")
 if any(x is None for x in(path,single,multi,mark,save,resolve,show,refresh)):errors.append({"error":"selected runtime coverage incomplete"})
 getter="VN.SDS.Common.MainData.Entity.ReportFile.ReportFileEntity.get_FileName";showcall="Application.ReportEngine.frmPreviewPrint.ShowReportFact";printed="Application.ReportEngine.frmPreviewPrint.get_PrintedCompleted";markcall="VN.SDS.Sales.Business.PrintInvoice.PrintInvoiceHandler.SetLoginDrFactForVocherOrFactor";ctx="Thunderstruck.DataContext..ctor";commit="Thunderstruck.DataContext.Commit";rollback="Thunderstruck.DataContext.RollBack";savecall="TypeSpecRow.SaveCommand";doctype="VN.SDS.Common.Sales.Entity.PrintedDoc.PrintedDocEntity.set_DocType"
 def ordered_ui(m):return bool(off(m,showcall) and off(m,printed) and off(m,markcall) and min(off(m,showcall))<min(off(m,printed))<max(off(m,markcall)))
 doctype2=bool(save and off(save,doctype) and any(x<min(off(save,doctype)) and min(off(save,doctype))-x<=2 for x in save["integer_constant_two_offsets"]))
 contract={"ui_resolves_configured_report_filename":bool(off(path,getter)),"single_print_calls_report_then_marks_only_after_printed_completed":ordered_ui(single),"collection_print_calls_report_then_marks_only_after_printed_completed":ordered_ui(multi),"report_engine_loads_crystal_template_and_sets_parameters":bool(off(show,"CrystalDecisions.CrystalReports.Engine.ReportDocument.Load") and off(show,"CrystalDecisions.CrystalReports.Engine.ReportDocument.SetParameterValue")),"report_engine_refresh_applies_current_connection_to_report_tables":bool(off(refresh,"Application.DataLayer.DBConnector.get_Connection") and off(refresh,"CrystalDecisions.CrystalReports.Engine.Table.ApplyLogOnInfo") and off(refresh,"CrystalDecisions.Windows.Forms.CrystalReportViewer.set_ReportSource")),"report_engine_supports_custom_override_when_file_exists":bool(off(resolve,"System.IO.File.Exists") and any(x["report_or_rep_path_marker"] for x in resolve["literal_fingerprints"]) and any(x["custom_override_marker"] for x in resolve["literal_fingerprints"])),"print_completion_builds_type2_audit_rows":doctype2,"print_completion_uses_context_save_then_commit":bool(off(save,ctx) and off(save,savecall) and off(save,commit) and min(off(save,savecall))<max(off(save,commit))),"print_completion_has_no_explicit_rollback":not bool(off(save,rollback)),"template_embedded_query_identity_and_result_parity_proven":False}
 return {"artifact":"varanegar_sale_invoice_print_runtime_boundary","schema_version":1,"generated_at":datetime.now().astimezone().isoformat(),"validation":"PASS" if not errors else "FAIL","source":sources,"safety":{"mode":"STATIC_HASH_PINNED_PE_METADATA_AND_IL_ONLY","assembly_loads_or_executions":0,"report_template_form_print_or_application_command_executions":0,"database_connections":0,"configuration_sale_user_host_connection_or_report_values_read":0,"raw_string_literals_persisted":0,"source_or_target_state_changed":0},"summary":{"assembly_count":len(sources),"selected_method_count":len(methods),"selected_instruction_count":sum(x["instruction_count"] for x in methods),"source_hash_mismatch_count":sum(not x["inventory_sha256_match"] for x in sources),"method_or_coverage_error_count":len(errors)},"managed_invoice_print_contract":contract,"method_contracts":methods,"errors":errors,"evidence_limits":["Static IL proves call presence and linear ordering, not successful physical printing or branch execution.","Crystal template embedded tables, commands and formulas are outside the inspected assemblies and remain unresolved when the configured files are unavailable.","Dispose behavior and physical transaction enlistment are not upgraded into an explicit rollback guarantee.","Assemblies were never loaded or executed and raw literals were fingerprinted only."]}
def main():
 logging.getLogger("dnfile").setLevel(logging.CRITICAL);p=argparse.ArgumentParser();p.add_argument("--source-directory",required=True,type=Path);p.add_argument("--binary-inventory",required=True,type=Path);p.add_argument("--output",required=True,type=Path);a=p.parse_args();x=collect(a.source_directory,a.binary_inventory);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(a.output.resolve());print(json.dumps(x["summary"],ensure_ascii=False));print(json.dumps(x["managed_invoice_print_contract"],ensure_ascii=False));return 0 if x["validation"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
