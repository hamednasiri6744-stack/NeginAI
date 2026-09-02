"""Extract hash-pinned managed sale-to-voucher reversal route."""
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

TARGETS={"VN.SDS.Sales.UI.dll":{"VN.SDS.Sales.UI.Sale.FormSaleList":{"ConvertSaleToVocher"}},
 "VN.SDS.Sales.Business.dll":{"VN.SDS.Sales.Business.Sale.SaleHandler":{"ConvertSale2Vocher"}},
 "VN.SDS.Sales.DataAccess.dll":{"VN.SDS.Sales.DataAccess.DataAdapter.Sale.SaleAdapter":{"ConvertSaleToVocher","IsvalidSaleForConvertToVocher"}}}
SAFE={"Thunderstruck.DataContext..ctor","Thunderstruck.DataContext.Execute","Thunderstruck.DataContext.Query","Thunderstruck.DataContext.Commit","Thunderstruck.DataContext.RollBack","Thunderstruck.DataContext.Dispose",
 "VN.SDS.Sales.Business.Sale.SaleHandler.ConvertSale2Vocher","VN.SDS.Sales.DataAccess.DataAdapter.Sale.SaleAdapter.ConvertSaleToVocher","VN.SDS.Sales.DataAccess.DataAdapter.Sale.SaleAdapter.IsvalidSaleForConvertToVocher",
 "VN.SDS.MainData.IBusiness.OprDate.IOprDateHandler.CheckSetOprDate"}
PROCS={"usp_sdsnet_ConvertSaleToVocher"}
def _load(p):return json.loads(p.read_text(encoding="utf-8-sig"))
def _method(pe,assembly,owner,index,mo,fo):
 body=read_method_body_from_bytes(pe.get_data(index.row.Rva,524288));events=[];literals=[];procs=set()
 for ins in body.instructions:
  o=ins.operand
  if isinstance(o,StringToken):
   item=pe.net.user_strings.get(o.rid);value="" if item is None else str(item.value);compact=" ".join(value.replace("[","").replace("]","").split())
   for p in PROCS:
    if p.casefold() in compact.casefold():procs.add(p)
   literals.append({"sha256":hashlib.sha256(value.encode()).hexdigest(),"length":len(value),"raw_value_persisted":False})
  elif isinstance(o,Token):
   m=_resolve_token(pe,o,mo,fo)
   if m in SAFE:events.append({"offset":int(ins.offset),"opcode":ins.mnemonic,"member":m})
 return {"assembly_file":assembly,"type":owner,"method":str(index.row.Name),"instruction_count":len(body.instructions),"has_exception_regions":bool(body.exception_handlers),"event_ledger":events,"procedure_name_signals":sorted(procs),"literal_fingerprints":literals}

def collect(source_directory:Path,binary_inventory:Path):
 expected={x["name"]:x["sha256"] for x in _load(binary_inventory)["files"]};sources=[];methods=[];errors=[]
 for assembly,targets in TARGETS.items():
  path=source_directory/assembly;actual=hashlib.sha256(path.read_bytes()).hexdigest();match=actual==expected.get(assembly);sources.append({"assembly_file":assembly,"assembly_bytes":path.stat().st_size,"assembly_sha256":actual,"inventory_sha256_match":match})
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
 ui=one("VN.SDS.Sales.UI.Sale.FormSaleList","ConvertSaleToVocher");business=one("VN.SDS.Sales.Business.Sale.SaleHandler","ConvertSale2Vocher");adapter=one("VN.SDS.Sales.DataAccess.DataAdapter.Sale.SaleAdapter","ConvertSaleToVocher");valid=one("VN.SDS.Sales.DataAccess.DataAdapter.Sale.SaleAdapter","IsvalidSaleForConvertToVocher")
 if any(x is None for x in(ui,business,adapter,valid)):errors.append({"error":"selected runtime coverage incomplete"})
 ctx="Thunderstruck.DataContext..ctor";commit="Thunderstruck.DataContext.Commit";rollback="Thunderstruck.DataContext.RollBack";bcall="VN.SDS.Sales.Business.Sale.SaleHandler.ConvertSale2Vocher";acall="VN.SDS.Sales.DataAccess.DataAdapter.Sale.SaleAdapter.ConvertSaleToVocher";vcall="VN.SDS.Sales.DataAccess.DataAdapter.Sale.SaleAdapter.IsvalidSaleForConvertToVocher"
 contract={"ui_calls_business_without_explicit_context_commit_or_rollback":bool(off(ui,bcall) and not off(ui,ctx) and not off(ui,commit) and not off(ui,rollback)),
 "business_constructs_context_validates_then_calls_adapter":bool(off(business,ctx) and off(business,vcall) and off(business,acall) and min(off(business,vcall))<max(off(business,acall))),
 "business_has_explicit_commit":bool(off(business,commit)),"business_has_explicit_rollback":bool(off(business,rollback)),
 "adapter_uses_named_conversion_procedure":bool(adapter and "usp_sdsnet_ConvertSaleToVocher" in adapter["procedure_name_signals"]),
 "adapter_queries_or_executes":bool(off(adapter,"Thunderstruck.DataContext.Query") or off(adapter,"Thunderstruck.DataContext.Execute")),
 "adapter_has_explicit_context":bool(off(adapter,ctx)),"adapter_has_explicit_commit":bool(off(adapter,commit)),"adapter_has_explicit_rollback":bool(off(adapter,rollback)),
 "managed_to_sql_physical_transaction_enlistment_proven":False}
 return {"artifact":"varanegar_sale_voucher_snapshot_runtime_boundary","schema_version":1,"generated_at":datetime.now().astimezone().isoformat(),"validation":"PASS" if not errors else "FAIL","source":sources,
 "safety":{"mode":"STATIC_HASH_PINNED_PE_METADATA_AND_IL_ONLY","assembly_loads_or_executions":0,"application_form_or_command_executions":0,"database_connections":0,"configuration_sale_order_customer_user_or_host_values_read":0,"raw_string_sql_or_identifier_literals_persisted":0,"source_or_target_state_changed":0},
 "summary":{"assembly_count":len(sources),"selected_method_count":len(methods),"selected_instruction_count":sum(x["instruction_count"] for x in methods),"source_hash_mismatch_count":sum(not x["inventory_sha256_match"] for x in sources),"method_or_coverage_error_count":len(errors)},"managed_snapshot_conversion_contract":contract,"method_contracts":methods,"errors":errors,
 "evidence_limits":["Linear IL proves call presence and ordering, not branch execution or successful effects.","Physical transaction enlistment between managed contexts and the SQL-local transaction is not inferred.","Only an allowlisted procedure name is retained; raw literals are fingerprints.","Assemblies were never loaded or executed."]}
def main():
 logging.getLogger("dnfile").setLevel(logging.CRITICAL);p=argparse.ArgumentParser();p.add_argument("--source-directory",required=True,type=Path);p.add_argument("--binary-inventory",required=True,type=Path);p.add_argument("--output",required=True,type=Path);a=p.parse_args();x=collect(a.source_directory,a.binary_inventory);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(a.output.resolve());print(json.dumps(x["summary"],ensure_ascii=False));print(json.dumps(x["managed_snapshot_conversion_contract"],ensure_ascii=False));return 0 if x["validation"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
