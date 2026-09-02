"""Extract static RPT-03 dashboard-host and RPT-04 zoom-shell ownership boundaries."""
from __future__ import annotations
import argparse,hashlib,json,sys
from datetime import datetime
from pathlib import Path
import dnfile
from dncil.cil.body.reader import read_method_body_from_bytes
from dncil.clr.token import StringToken,Token
sys.path.insert(0,str(Path(__file__).resolve().parent))
from extract_varanegar_targeted_il_contracts import _full_type_name,_owner_maps,_resolve_token,_text  # noqa:E402
FILE="VN.SDS.MainData.UI.dll";EXPECTED="afd3a9d4b3e595c352ca95cb55408f3116cac48309b98ac5826412e0e7bbd75e";TARGETS={"VN.SDS.MainData.UI.Dashboard.PublicDashboard.FormMainDashboard":{"ApplyUserPermission","CheckPermisianDashbord","InsertDefualtDashboards","inSertDashboardControl","RefreshAll","ZoomInAndZoomOutMainSpaceDashboardUserControl"},"VN.SDS.MainData.UI.Dashboard.PublicDashboard.MainUiDashboard.FormZoomChart":{"CopyOfControl","CloseChart","FormZoomChart_DragDrop","FormZoomChart_DragOver"}}
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--source-directory",required=True,type=Path);p.add_argument("--output",required=True,type=Path);a=p.parse_args();path=a.source_directory/FILE;raw=path.read_bytes();pe=dnfile.dnPE(str(path));owners,fields=_owner_maps(pe);types={_full_type_name(x):x for x in pe.net.mdtables.TypeDef.rows};rows=[];errors=[]
 for type_name,names in TARGETS.items():
  t=types.get(type_name)
  if not t:errors.append(f"type_{type_name}");continue
  for idx in t.MethodList or []:
   m=idx.row;name=_text(getattr(m,"Name",""))
   if name not in names or not m.Rva:continue
   body=read_method_body_from_bytes(pe.get_data(m.Rva,65536));calls=[];literal_count=0
   for ins in body.instructions:
    if ins.mnemonic in {"call","callvirt","newobj"} and isinstance(ins.operand,Token):calls.append({"offset":ins.offset,"member":_resolve_token(pe,ins.operand,owners,fields)})
    if isinstance(ins.operand,StringToken):literal_count+=1
   rows.append({"type":type_name,"method":name,"instruction_count":len(body.instructions),"ordered_calls":calls,"literal_fingerprint_count":literal_count,"raw_literals_persisted":False,"uses_data_query":any("DataContext.Query" in x["member"] or "DataContext.All" in x["member"] for x in calls),"checks_permission":any("HasPersmission" in x["member"] for x in calls),"refreshes_widget_data":any("RefreshData" in x["member"] for x in calls),"copies_or_drags_control":any(any(k in x["member"] for k in ("DoDragDrop","IDataObject","DragEventArgs")) for x in calls)})
 if sha(raw)!=EXPECTED:errors.append("hash_mismatch")
 host=[x for x in rows if x["type"].endswith("FormMainDashboard")];zoom=[x for x in rows if x["type"].endswith("FormZoomChart")];constructors=sorted({x["member"].rsplit(".",1)[0] for m in host for x in m["ordered_calls"] if "ChartReport" in x["member"] and x["member"].endswith("..ctor")});checks={"ten_selected_methods":len(rows)==10,"host_permission_boundary":any(x["checks_permission"] for x in host),"host_refreshes_widgets":any(x["refreshes_widget_data"] for x in host),"five_widget_types":len(constructors)==5,"zoom_is_control_transform":any(x["copies_or_drags_control"] for x in zoom),"no_query_in_shell_methods":not any(x["uses_data_query"] for x in rows)};errors.extend(k for k,v in checks.items() if not v)
 out={"artifact":"varanegar_dashboard_shell_boundary_20260829","schema_version":1,"generated_at":datetime.now().astimezone().isoformat(),"validation":"PASS" if not errors else "FAIL","source":{"file":FILE,"size_bytes":len(raw),"sha256":sha(raw),"expected_sha256":EXPECTED,"hash_matches":sha(raw)==EXPECTED},"safety":{"mode":"STATIC_PE_CLR_METADATA_AND_IL","database_connections":0,"queries_forms_dashboards_or_controls_executed":0,"assemblies_loaded_or_executed":0,"raw_business_values_or_identities_persisted":0,"data_mutations":0},"summary":{"shell_type_count":2,"selected_method_count":len(rows),"widget_type_count":len(constructors),"query_method_count":sum(x["uses_data_query"] for x in rows),"validation_error_count":len(errors)},"ownership":{"RPT-03":{"role":"PERMISSIONED_MULTI_WIDGET_HOST","owns_widget_layout_refresh_and_visibility":True,"owns_widget_query_formula":False,"widget_types":constructors},"RPT-04":{"role":"CONTROL_ZOOM_AND_DRAG_DROP_SHELL","owns_query_or_formula":False,"changes_data_scope":False}},"methods":sorted(rows,key=lambda x:(x["type"],x["method"])),"checks":checks,"validation_errors":errors,"confidence":{"host_widget_and_zoom_roles":"CONFIRMED_STATIC_IL","widget_query_formulas_and_runtime_results":"UNPROVEN"},"limits":["No dashboard, widget, control or query was executed.","Shell method absence of queries does not imply child widgets have no queries.","Permission check presence does not prove complete per-widget resource authorization."]};a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(a.output.resolve());print(out["validation"]);print(json.dumps(out["summary"]));return 0 if not errors else 1
if __name__=="__main__":raise SystemExit(main())
