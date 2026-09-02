"""Extract redacted static SQL bindings for supplier/customer cardex reports."""
from __future__ import annotations
import argparse,hashlib,json,re,sys
from datetime import datetime
from pathlib import Path
import dnfile
from dncil.cil.body.reader import read_method_body_from_bytes
from dncil.clr.token import StringToken,Token
sys.path.insert(0,str(Path(__file__).resolve().parent))
from extract_varanegar_targeted_il_contracts import _full_type_name,_owner_maps,_resolve_token,_text  # noqa:E402
TARGETS={"VN.SDS.MainData.DataAccess.dll":{"hash":"5dcb9f47a484ed5c3d04344130ea9ef1f2e5e97c4b5acd2b11b02df0a878d987","types":{"VN.SDS.MainData.DataAccess.DataAdapter.Supplier.SupplierAdapter":{"SupplierCardex"},"VN.SDS.MainData.DataAccess.DataAdapter.Customer.CustomerAdapter":{"CustomerCardex","CustomerCardexCentralized","CustomerCurrencyCardex","GetCustomerType"}}},"VN.SDS.Sales.DataAccess.dll":{"hash":"ad1df171f9243f596ca2791580b2cdb474388e33523ffbb38fd54dd55010d3f5","types":{"VN.SDS.Sales.DataAccess.DataAdapter.FreeInvoice.FreeInvoiceAdapter":{"GetTSaleNo"}}}}
OBJ=re.compile(r"(?i)\b([A-Za-z_]\w*\.[A-Za-z_]\w*)\b");EXEC=re.compile(r"(?i)\bexec(?:ute)?\s+((?:\[?[A-Za-z_]\w*\]?\.){0,2}\[?[A-Za-z_]\w*\]?)");PARAM=re.compile(r"@[A-Za-z_]\w*");FMT=re.compile(r"\{(\d+)(?:[^}]*)\}")
def h(b):return hashlib.sha256(b).hexdigest()
def analyze(path,spec):
 raw=path.read_bytes();pe=dnfile.dnPE(str(path));owners,fields=_owner_maps(pe);types={_full_type_name(x):x for x in pe.net.mdtables.TypeDef.rows};rows=[]
 for type_name,names in spec["types"].items():
  target=types.get(type_name)
  if not target:continue
  for idx in target.MethodList or []:
   m=idx.row;name=_text(getattr(m,"Name",""))
   if name not in names or not m.Rva:continue
   body=read_method_body_from_bytes(pe.get_data(m.Rva,65536));calls=[];lits=[]
   for ins in body.instructions:
    if ins.mnemonic in {"call","callvirt","newobj"} and isinstance(ins.operand,Token):calls.append(_resolve_token(pe,ins.operand,owners,fields))
    if isinstance(ins.operand,StringToken):
     item=pe.net.user_strings.get(ins.operand.rid);value="" if item is None else _text(item);objects=[]
     for x in [*EXEC.findall(value),*OBJ.findall(value)]:
      x=x.replace("[","").replace("]","")
      if x.casefold().startswith(("system.","thunderstruck.")) or x in objects:continue
      objects.append(x)
     if objects or "@" in value or "{" in value:lits.append({"sha256":h(value.encode()),"length":len(value),"object_candidates":objects,"named_parameters":sorted(set(PARAM.findall(value)),key=str.casefold),"format_argument_indices":sorted({int(x) for x in FMT.findall(value)}),"raw_literal_persisted":False})
   rows.append({"type":type_name,"method":name,"instruction_count":len(body.instructions),"calls":calls,"uses_query":any("DataContext.Query" in x for x in calls),"uses_data_access":any(any(k in x for k in ("DataContext.Query","DataContext.ExecuteQuery","DataContext.ExecuteCommand")) for x in calls),"uses_string_format":"System.String.Format" in calls,"redacted_sql_literals":lits})
 return {"file":path.name,"size_bytes":path.stat().st_size,"sha256":h(raw),"expected_sha256":spec["hash"],"hash_matches":h(raw)==spec["hash"],"methods":sorted(rows,key=lambda x:(x["type"],x["method"]))}
def main():
 p=argparse.ArgumentParser();p.add_argument("--source-directory",required=True,type=Path);p.add_argument("--output",required=True,type=Path);a=p.parse_args();assemblies=[analyze(a.source_directory/f,s) for f,s in TARGETS.items()];methods=[m for x in assemblies for m in x["methods"]];errors=[]
 if any(not x["hash_matches"] for x in assemblies):errors.append("hash_mismatch")
 if len(methods)!=6:errors.append("method_set_incomplete")
 if any(not (m["uses_data_access"] and m["redacted_sql_literals"]) and not m["calls"] for m in methods):errors.append("binding_evidence_missing")
 out={"artifact":"varanegar_party_cardex_query_bindings_20260829","schema_version":1,"generated_at":datetime.now().astimezone().isoformat(),"validation":"PASS" if not errors else "FAIL","safety":{"mode":"STATIC_PE_CLR_METADATA_AND_IL","database_connections":0,"queries_procedures_or_ui_actions_executed":0,"assemblies_loaded_or_executed":0,"raw_sql_business_values_or_identities_persisted":0,"data_mutations":0},"summary":{"assembly_count":len(assemblies),"selected_method_count":len(methods),"query_method_count":sum(m["uses_query"] for m in methods),"redacted_sql_literal_count":sum(len(m["redacted_sql_literals"]) for m in methods),"method_with_object_candidate_count":sum(any(l["object_candidates"] for l in m["redacted_sql_literals"]) for m in methods),"validation_error_count":len(errors)},"assemblies":assemblies,"validation_errors":errors,"confidence":{"method_literal_binding":"CONFIRMED_STATIC_IL","runtime_result_parity":"UNPROVEN"},"limits":["No assembly or SQL was executed.","Only object/parameter names and hashes are persisted from literals."]};a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(a.output.resolve());print(out["validation"]);print(json.dumps(out["summary"]));return 0 if not errors else 1
if __name__=="__main__":raise SystemExit(main())
