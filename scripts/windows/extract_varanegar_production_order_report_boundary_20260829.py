"""Extract the hash-pinned static RPT-13 production-order report query boundary."""
from __future__ import annotations
import argparse,hashlib,json,re,sys
from datetime import datetime
from pathlib import Path
import dnfile
from dncil.cil.body.reader import read_method_body_from_bytes
from dncil.clr.token import StringToken,Token
sys.path.insert(0,str(Path(__file__).resolve().parent))
from extract_varanegar_targeted_il_contracts import _full_type_name,_owner_maps,_resolve_token,_text  # noqa:E402
FILE="VN.SDS.Stock.UI.dll";EXPECTED="8b3c00aeb385656523b412352dfb1030f24d69e46c34c6c41cb88b5d8fde2713";TYPE="VN.SDS.Stock.UI.ProductionOrder.FormProductionOrderReport";METHODS={"InternalConfirmCommand","FormProductionOrderReport_Load","MenuButtonInsertToExcel_Click"};OBJ=re.compile(r"(?i)\b(?:exec(?:ute)?\s+)?((?:\[?[A-Za-z_]\w*\]?\.){0,2}\[?(?:usp|USP)_[A-Za-z_]\w*\]?)");FMT=re.compile(r"\{(\d+)(?:[^}]*)\}")
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--source-directory",required=True,type=Path);p.add_argument("--output",required=True,type=Path);a=p.parse_args();path=a.source_directory/FILE;raw=path.read_bytes();pe=dnfile.dnPE(str(path));owners,fields=_owner_maps(pe);target=next((x for x in pe.net.mdtables.TypeDef.rows if _full_type_name(x)==TYPE),None);rows=[];errors=[]
 if not target:errors.append("type_missing")
 else:
  for idx in target.MethodList or []:
   m=idx.row;name=_text(getattr(m,"Name",""))
   if name not in METHODS or not m.Rva:continue
   body=read_method_body_from_bytes(pe.get_data(m.Rva,65536));calls=[];literals=[]
   for ins in body.instructions:
    if ins.mnemonic in {"call","callvirt","newobj"} and isinstance(ins.operand,Token):calls.append({"offset":ins.offset,"member":_resolve_token(pe,ins.operand,owners,fields)})
    if isinstance(ins.operand,StringToken):
     item=pe.net.user_strings.get(ins.operand.rid);value="" if item is None else _text(item);objects=sorted({x.replace("[","").replace("]","") for x in OBJ.findall(value)},key=str.casefold)
     if objects or "{" in value:literals.append({"sha256":sha(value.encode()),"length":len(value),"object_candidates":objects,"format_argument_indices":sorted({int(x) for x in FMT.findall(value)}),"raw_literal_persisted":False})
   rows.append({"method":name,"instruction_count":len(body.instructions),"ordered_calls":calls,"uses_query":any("DataContext.Query" in x["member"] for x in calls),"uses_excel_export":any("InsertToExcelCommand" in x["member"] for x in calls),"redacted_literals":literals})
 if sha(raw)!=EXPECTED:errors.append("hash_mismatch")
 if len(rows)!=3:errors.append("method_set_incomplete")
 confirm=next((x for x in rows if x["method"]=="InternalConfirmCommand"),{})
 if not confirm.get("uses_query") or not any(x["object_candidates"] for x in confirm.get("redacted_literals",[])):errors.append("confirm_query_binding_missing")
 out={"artifact":"varanegar_production_order_report_boundary_20260829","schema_version":1,"generated_at":datetime.now().astimezone().isoformat(),"validation":"PASS" if not errors else "FAIL","source":{"file":FILE,"sha256":sha(raw),"expected_sha256":EXPECTED,"hash_matches":sha(raw)==EXPECTED},"safety":{"mode":"STATIC_PE_CLR_METADATA_AND_IL","database_connections":0,"queries_forms_or_exports_executed":0,"assemblies_loaded_or_executed":0,"raw_sql_business_values_or_identities_persisted":0,"data_mutations":0},"summary":{"selected_method_count":len(rows),"query_method_count":sum(x["uses_query"] for x in rows),"export_delegation_method_count":sum(x["uses_excel_export"] for x in rows),"validation_error_count":len(errors)},"type":TYPE,"methods":sorted(rows,key=lambda x:x["method"]),"validation_errors":errors,"confidence":{"query_identity_and_input_call_surface":"CONFIRMED_STATIC_IL","runtime_results":"UNPROVEN"},"limits":["No UI, query or export was executed.","Format argument positions do not by themselves prove business meaning or result parity."]};a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(a.output.resolve());print(out["validation"]);print(json.dumps(out["summary"]));return 0 if not errors else 1
if __name__=="__main__":raise SystemExit(main())
