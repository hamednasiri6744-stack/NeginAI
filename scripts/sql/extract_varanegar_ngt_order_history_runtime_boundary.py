"""Fingerprint managed Type=1 order crosswalk write-back from static IL."""

from __future__ import annotations

import argparse, hashlib, json, logging, re, sys
from datetime import datetime
from pathlib import Path
from typing import Any
import dnfile
from dncil.cil.body.reader import read_method_body_from_bytes
from dncil.clr.token import Token

WINDOWS_SCRIPTS=Path(__file__).resolve().parents[1]/"windows"; sys.path.insert(0,str(WINDOWS_SCRIPTS))
from extract_varanegar_ngt_authorization_runtime_boundary import _owner_maps,_parameter_count,_resolve_token,_signature_bytes  # noqa:E402

FILES=("NGT.Business.dll","NGT.DataAccess.dll","NGT.WebApi.dll")
OWNER=re.compile(r"(?:TourDomain\+<ReplicateTour>|StockLevelDomain\+<AddConflictVoucherToCustomerCall>)d__",re.I)
SIGNAL=re.compile(r"(?:CustomerCallOrderLine\.set_BackOfficeOrder|NewReplicateTour|BeginTransaction|DbContextTransaction\.(?:Commit|Rollback)|SaveChanges|UpdateBatch)",re.I)
def _text(v:Any)->str:return "" if v is None else str(v)

def collect(root:Path)->dict[str,Any]:
    methods=[]; errors=[]; sources=[]
    for file in FILES:
        path=root/file; pe=dnfile.dnPE(str(path)); mo,fo,tn=_owner_maps(pe)
        sources.append({"assembly_file":file,"assembly_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"assembly_bytes":path.stat().st_size})
        for ti,tr in enumerate(pe.net.mdtables.TypeDef.rows,start=1):
            owner=tn[ti]
            if not OWNER.search(owner):continue
            for mi in tr.MethodList or []:
                m=mi.row
                if m is None or not m.Rva or _text(m.Name)!="MoveNext":continue
                try: body=read_method_body_from_bytes(pe.get_data(m.Rva,131072))
                except Exception as exc: errors.append({"file":file,"owner":owner,"error_type":type(exc).__name__}); continue
                events=[]
                for ins in body.instructions:
                    if not isinstance(ins.operand,Token):continue
                    value=_text(_resolve_token(pe,ins.operand,mo,fo,tn))
                    if SIGNAL.search(value):events.append({"offset":ins.offset,"opcode":ins.mnemonic,"operand":value})
                methods.append({"file":file,"owner":owner,"method":_text(m.Name),"method_metadata_token":f"0x06{mi.row_index:06x}","parameter_count":_parameter_count(m),"signature_hex":_signature_bytes(m).hex(),"instruction_count":len(body.instructions),"has_exception_regions":bool(body.exception_handlers),"event_ledger":events})
    rep=next((x for x in methods if "TourDomain+<ReplicateTour>" in x["owner"]),None); ev=[] if rep is None else rep["event_ledger"]
    setters=[x for x in ev if "CustomerCallOrderLine.set_BackOfficeOrder" in x["operand"]]
    new=[x["offset"] for x in ev if x["operand"].endswith("TourDomain.NewReplicateTour")]
    begin=[x["offset"] for x in ev if x["operand"].endswith("Database.BeginTransaction")]
    commits=[x["offset"] for x in ev if x["operand"].endswith("DbContextTransaction.Commit")]
    contract={"replicate_tour_present":rep is not None,"new_replication_call_count":len(new),"order_line_crosswalk_setter_count":len(setters),"order_line_crosswalk_setter_members":sorted({x["operand"] for x in setters}),"new_replication_precedes_managed_transaction_in_linear_il":bool(new and begin and min(new)<min(begin)),"new_replication_precedes_order_crosswalk_setters_in_linear_il":bool(new and setters and min(new)<min(x["offset"] for x in setters)),"managed_commit_exists_before_order_crosswalk_setters_in_linear_il":bool(commits and setters and any(x<min(y["offset"] for y in setters) for x in commits)),"managed_commit_exists_after_order_crosswalk_setters_in_linear_il":bool(commits and setters and any(x>max(y["offset"] for y in setters) for x in commits))}
    return {"artifact":"varanegar_ngt_order_history_runtime_boundary","schema_version":1,"generated_at":datetime.now().astimezone(),"validation":"PASS" if rep is not None and not errors else "FAIL","source":sources,"safety":{"mode":"STATIC_PE_METADATA_AND_IL_ONLY","assembly_loads_or_execution":0,"application_endpoint_or_command_executions":0,"database_connections":0,"configuration_or_business_data_reads":0,"raw_string_or_sql_literals_persisted":0,"guid_literals_persisted":0,"source_or_target_state_changed":0},"summary":{"assembly_count":len(sources),"selected_method_count":len(methods),"selected_instruction_count":sum(x["instruction_count"] for x in methods),"method_body_error_count":len(errors),"order_line_crosswalk_setter_count":len(setters)},"order_history_runtime_contract":contract,"method_contracts":methods,"body_errors":errors,"evidence_limits":["Linear IL order does not prove branch execution frequency.","Static setters prove write-back shape, not the cause of missing current targets.","Assemblies were never loaded or executed."]}

def main()->int:
    logging.getLogger("dnfile").setLevel(logging.CRITICAL); p=argparse.ArgumentParser(); p.add_argument("--source-directory",required=True,type=Path); p.add_argument("--output",required=True,type=Path); a=p.parse_args(); x=collect(a.source_directory); a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(x,ensure_ascii=False,indent=2,default=str)+"\n",encoding="utf-8"); print(a.output.resolve()); print(json.dumps(x["summary"],ensure_ascii=False)); print(json.dumps(x["order_history_runtime_contract"],ensure_ascii=False)); return 0 if x["validation"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
