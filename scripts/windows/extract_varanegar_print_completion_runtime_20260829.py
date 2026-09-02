"""Extract static transaction calls for batch-print completion handlers."""
from __future__ import annotations
import argparse,hashlib,json,sys
from datetime import datetime
from pathlib import Path
import dnfile
from dncil.cil.body.reader import read_method_body_from_bytes
from dncil.clr.token import Token
sys.path.insert(0,str(Path(__file__).resolve().parent))
from extract_varanegar_targeted_il_contracts import _full_type_name,_owner_maps,_resolve_token,_text  # noqa:E402
TYPE="VN.SDS.Sales.Business.PrintInvoice.PrintInvoiceHandler";EXPECTED="7d8930f8cc7e9f43ebad7e948a97d246290c0fbe424bfbb800ab6da4233bb233"
def main():
 p=argparse.ArgumentParser();p.add_argument("--assembly",required=True,type=Path);p.add_argument("--output",required=True,type=Path);a=p.parse_args();raw=a.assembly.read_bytes();h=hashlib.sha256(raw).hexdigest();pe=dnfile.dnPE(str(a.assembly));owners,fields=_owner_maps(pe);target=next((x for x in pe.net.mdtables.TypeDef.rows if _full_type_name(x)==TYPE),None);rows=[];errors=[]
 if h!=EXPECTED:errors.append("hash_mismatch")
 if target is None:errors.append("type_missing")
 if target:
  for idx in target.MethodList or []:
   m=idx.row;name=_text(getattr(m,"Name",""))
   if not (name.startswith("SetPrintCompleated") or name.startswith("SaveCommand")) or not m.Rva:continue
   body=read_method_body_from_bytes(pe.get_data(m.Rva,65536));calls=[]
   for ins in body.instructions:
    if ins.mnemonic in {"call","callvirt","newobj"} and isinstance(ins.operand,Token):calls.append({"offset":ins.offset,"member":_resolve_token(pe,ins.operand,owners,fields)})
   rows.append({"method":name,"instruction_count":len(body.instructions),"ordered_calls":calls,"commit_offsets":[x["offset"] for x in calls if x["member"].endswith("DataContext.Commit")],"rollback_offsets":[x["offset"] for x in calls if x["member"].endswith("DataContext.RollBack")],"save_command_calls":[x for x in calls if "SaveCommand" in x["member"]],"raw_literals_persisted":False})
 rows.sort(key=lambda x:x["method"])
 required={"SetPrintCompleatedDrFact","SetPrintCompleatedReportJoze"}
 if not required.issubset({x["method"] for x in rows}):errors.append("completion_methods_missing")
 out={"artifact":"varanegar_print_completion_runtime_20260829","schema_version":1,"generated_at":datetime.now().astimezone().isoformat(),"validation":"PASS" if not errors else "FAIL","source":{"file_name":a.assembly.name,"size_bytes":a.assembly.stat().st_size,"sha256":h,"expected_sha256":EXPECTED},"safety":{"mode":"STATIC_PE_CLR_METADATA_AND_IL","assemblies_loaded_or_executed":0,"commands_or_procedures_executed":0,"database_connections":0,"raw_literals_or_business_values_persisted":0,"data_mutations":0},"summary":{"selected_method_count":len(rows),"completion_method_count":sum(x["method"].startswith("SetPrintCompleated") for x in rows),"method_with_commit_count":sum(bool(x["commit_offsets"]) for x in rows),"method_with_rollback_count":sum(bool(x["rollback_offsets"]) for x in rows),"validation_error_count":len(errors)},"methods":rows,"validation_errors":errors,"confidence":{"transaction_call_signals":"CONFIRMED_STATIC_IL","physical_transaction_outcome":"UNPROVEN"},"limits":["No assembly or completion command was executed.","Absence of a local rollback call does not exclude provider or outer-layer behavior."]};a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(a.output.resolve());print(out["validation"]);print(json.dumps(out["summary"]));return 0 if not errors else 1
if __name__=="__main__":raise SystemExit(main())
