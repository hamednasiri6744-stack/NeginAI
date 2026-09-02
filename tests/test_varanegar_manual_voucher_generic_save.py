import ast,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];E=ROOT/"scripts/windows/extract_varanegar_manual_voucher_generic_save_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_manual_voucher_generic_save_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_extractor_contract_is_offline_and_static():
 source=E.read_text(encoding="utf-8");assert ast.parse(source) and "dnfile.dnPE" in source and "Assembly.Load" not in source and "LoadFrom" not in source
def test_all_five_hashes_match():assert len(load()["source"])==5 and all(x["hash_match"] for x in load()["source"])
def test_manual_adapter_binding_exact():assert load()["resolved_chain"]["ui_generic_binding"]["arguments"][0]=="VN.SDS.Treasury.DataAccess.DataAdapter.ManualVoucher.ManualVoucherAdapter"
def test_ui_opens_begin_context():assert load()["resolved_chain"]["ui_transaction_mode_operand"]=="ldc.i4.0"
def test_generic_crud_overloads_commit():
 x=load();assert x["summary"]["context_crud_overload_count"]==x["summary"]["context_crud_overload_with_commit_count"]==3;assert all(len(v["commit_offsets"])==1 for v in x["context_crud_methods"].values())
def test_no_false_named_procedure():assert load()["resolved_chain"]["exact_named_procedure"]=="NONE_GENERIC_ENTITY_METADATA_PERSISTENCE"
def test_no_explicit_rollback_signal():assert load()["summary"]["selected_method_with_explicit_rollback_count"]==0
def test_safety_zero():assert set(v for k,v in load()["safety"].items() if k!="mode")=={0}
