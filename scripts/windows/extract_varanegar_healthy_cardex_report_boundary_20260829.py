"""Extract static query and print-command boundaries for report RPT-18."""
from __future__ import annotations
import argparse,hashlib,json,re,sys
from datetime import datetime
from pathlib import Path
import dnfile
from dncil.cil.body.reader import read_method_body_from_bytes
from dncil.clr.token import StringToken,Token
sys.path.insert(0,str(Path(__file__).resolve().parent))
from extract_varanegar_targeted_il_contracts import _full_type_name,_owner_maps,_resolve_token,_text  # noqa:E402

TARGETS={
 "VN.SDS.Stock.DataAccess.dll":("VN.SDS.Stock.DataAccess.DataAdapter.VchHealthyCardex.VchHealthyCardexAdapter",{"GetDetailsVchHealthyCardex","GetMasterVchHealthyCardex"}),
 "VN.SDS.Stock.UI.dll":("VN.SDS.Stock.UI.VchHealthyCardex.FormVchHealthyCardex",{"FilterGridList","InsertToExcelCommand","UIOnPreCommandExecute","i_Click"}),
}
EXPECTED={"VN.SDS.Stock.DataAccess.dll":"05ad31992521fe0b169fc63d5747d2f84c88e6f5b565e21879957ef40078853f","VN.SDS.Stock.UI.dll":"8b3c00aeb385656523b412352dfb1030f24d69e46c34c6c41cb88b5d8fde2713"}
EXEC_RE=re.compile(r"(?i)\bexec(?:ute)?\s+((?:\[?[A-Za-z_]\w*\]?\.){0,2}\[?[A-Za-z_]\w*\]?)");OBJECT_RE=re.compile(r"(?i)\b([A-Za-z_]\w*\.[A-Za-z_]\w*)\b");PARAM_RE=re.compile(r"@[A-Za-z_]\w*");FMT_RE=re.compile(r"\{(\d+)(?:[^}]*)\}")
def sha(b):return hashlib.sha256(b).hexdigest()
def analyze(path,type_name,methods):
 raw=path.read_bytes();pe=dnfile.dnPE(str(path));owners,fields=_owner_maps(pe);tt=pe.net.mdtables.TypeDef;target=next((x for x in tt.rows if _full_type_name(x)==type_name),None);rows=[]
 if target:
  for idx in target.MethodList or []:
   m=idx.row;name=_text(getattr(m,"Name",""))
   if name not in methods or not m.Rva:continue
   body=read_method_body_from_bytes(pe.get_data(m.Rva,65536));calls=[];literals=[]
   for ins in body.instructions:
    if ins.mnemonic in {"call","callvirt","newobj"} and isinstance(ins.operand,Token):calls.append({"offset":ins.offset,"member":_resolve_token(pe,ins.operand,owners,fields)})
    if isinstance(ins.operand,StringToken):
     item=pe.net.user_strings.get(ins.operand.rid);value="" if item is None else _text(item);objects=[]
     for x in [*EXEC_RE.findall(value),*OBJECT_RE.findall(value)]:
      x=x.replace("[","").replace("]","")
      if x.casefold().startswith(("system.","thunderstruck.")) or x in objects:continue
      objects.append(x)
     if objects or "@" in value or "{" in value:literals.append({"sha256":sha(value.encode()),"length":len(value),"object_candidates":objects,"named_parameters":sorted(set(PARAM_RE.findall(value)),key=str.casefold),"format_argument_indices":sorted({int(x) for x in FMT_RE.findall(value)}),"raw_literal_persisted":False})
   rows.append({"method":name,"instruction_count":len(body.instructions),"ordered_calls":calls,"redacted_sql_literals":literals})
 return {"file":path.name,"size_bytes":path.stat().st_size,"sha256":sha(raw),"expected_sha256":EXPECTED[path.name],"hash_matches":sha(raw)==EXPECTED[path.name],"type":type_name,"methods":sorted(rows,key=lambda x:x["method"])}
def main():
 p=argparse.ArgumentParser();p.add_argument("--source-directory",required=True,type=Path);p.add_argument("--output",required=True,type=Path);a=p.parse_args();assemblies=[analyze(a.source_directory/f,*TARGETS[f]) for f in TARGETS];errors=[]
 if any(not x["hash_matches"] for x in assemblies):errors.append("hash_mismatch")
 if sum(len(x["methods"]) for x in assemblies)!=6:errors.append("method_set_incomplete")
 da=assemblies[0]["methods"]
 if any(not m["redacted_sql_literals"] for m in da):errors.append("data_access_sql_literal_missing")
 payload={"artifact":"varanegar_healthy_cardex_report_boundary_20260829","schema_version":1,"generated_at":datetime.now().astimezone().isoformat(),"validation":"PASS" if not errors else "FAIL","safety":{"mode":"STATIC_PE_CLR_METADATA_AND_IL","database_connections":0,"queries_procedures_or_ui_actions_executed":0,"assemblies_loaded_or_executed":0,"raw_sql_or_business_values_persisted":0,"data_mutations":0},"summary":{"assembly_count":len(assemblies),"selected_method_count":sum(len(x["methods"]) for x in assemblies),"query_method_count":len(da),"redacted_sql_literal_count":sum(len(x["redacted_sql_literals"]) for x in da),"validation_error_count":len(errors)},"assemblies":assemblies,"validation_errors":errors,"confidence":{"call_order_and_query_literal":"CONFIRMED_STATIC_IL","runtime_branch_and_result_parity":"UNPROVEN"},"limits":["No assembly, UI action, SQL query or procedure was executed.","Only object/parameter names and hashes from SQL literals are persisted."]};a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(a.output.resolve());print(payload["validation"]);print(json.dumps(payload["summary"]));return 0 if not errors else 1
if __name__=="__main__":raise SystemExit(main())
