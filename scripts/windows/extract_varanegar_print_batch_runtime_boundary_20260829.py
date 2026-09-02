"""Extract ordered static call boundaries for the legacy batch-print form."""
from __future__ import annotations
import argparse,hashlib,json,sys
from datetime import datetime
from pathlib import Path
import dnfile
from dncil.cil.body.reader import read_method_body_from_bytes
from dncil.clr.token import Token
sys.path.insert(0,str(Path(__file__).resolve().parent))
from extract_varanegar_targeted_il_contracts import _full_type_name,_owner_maps,_resolve_token,_text  # noqa:E402
TYPE="VN.SDS.Sales.UI.PrintBatch.FormPrintBatch";EXPECTED="be1feb2307bef7c676ea0a58b1aa00ef1ab895a562c376698fc33827ebd2c280"
INCLUDE={"AcceptCommand","CheckCanPrint","GetReportPathName","PrintCommand"}
def main():
 p=argparse.ArgumentParser();p.add_argument("--assembly",required=True,type=Path);p.add_argument("--output",required=True,type=Path);a=p.parse_args();raw=a.assembly.read_bytes();h=hashlib.sha256(raw).hexdigest();pe=dnfile.dnPE(str(a.assembly));owners,fields=_owner_maps(pe);target=next((x for x in pe.net.mdtables.TypeDef.rows if _full_type_name(x)==TYPE),None);rows=[];errors=[]
 if h!=EXPECTED:errors.append("hash_mismatch")
 if target is None:errors.append("type_missing")
 if target:
  for idx in target.MethodList or []:
   m=idx.row;name=_text(getattr(m,"Name",""))
   if not (name in INCLUDE or (name.startswith("Print") and name not in {"Print"})) or not m.Rva:continue
   body=read_method_body_from_bytes(pe.get_data(m.Rva,65536));calls=[]
   for ins in body.instructions:
    if ins.mnemonic in {"call","callvirt","newobj"} and isinstance(ins.operand,Token):calls.append({"offset":ins.offset,"member":_resolve_token(pe,ins.operand,owners,fields)})
   rows.append({"method":name,"instruction_count":len(body.instructions),"ordered_calls":calls,"has_thread_sleep":any(x["member"]=="System.Threading.Thread.Sleep" for x in calls),"has_report_render":any(x["member"].endswith("ShowReportFact") for x in calls),"has_printed_completed_read":any(x["member"].endswith("get_PrintedCompleted") for x in calls),"completion_command_calls":[x for x in calls if ".SetPrintCompleated" in x["member"]],"raw_literals_persisted":False})
 rows.sort(key=lambda x:x["method"])
 if not any(x["method"]=="PrintCommand" for x in rows):errors.append("print_command_missing")
 out={"artifact":"varanegar_print_batch_runtime_boundary_20260829","schema_version":1,"generated_at":datetime.now().astimezone().isoformat(),"validation":"PASS" if not errors else "FAIL","source":{"file_name":a.assembly.name,"size_bytes":a.assembly.stat().st_size,"sha256":h,"expected_sha256":EXPECTED},"safety":{"mode":"STATIC_PE_CLR_METADATA_AND_IL","assemblies_loaded_or_executed":0,"ui_report_or_operational_commands_executed":0,"database_connections":0,"raw_literals_business_values_or_identities_persisted":0,"data_mutations":0},"summary":{"selected_method_count":len(rows),"render_method_count":sum(x["has_report_render"] for x in rows),"printed_completed_reader_method_count":sum(x["has_printed_completed_read"] for x in rows),"completion_command_method_count":sum(bool(x["completion_command_calls"]) for x in rows),"thread_sleep_method_count":sum(x["has_thread_sleep"] for x in rows),"validation_error_count":len(errors)},"methods":rows,"validation_errors":errors,"confidence":{"ordered_call_offsets":"CONFIRMED_STATIC_IL","runtime_branch_outcome":"UNPROVEN"},"limits":["No form, report, assembly or command was executed.","Call offsets establish static order, not that every branch reaches every call."]};a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(a.output.resolve());print(out["validation"]);print(json.dumps(out["summary"]));return 0 if not errors else 1
if __name__=="__main__":raise SystemExit(main())
