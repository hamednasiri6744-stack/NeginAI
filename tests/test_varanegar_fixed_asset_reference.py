import copy,importlib.util
from pathlib import Path
P=Path(__file__).resolve().parents[1]/"scripts/windows/varanegar_fixed_asset_reference.py";S=importlib.util.spec_from_file_location("ref",P);M=importlib.util.module_from_spec(S);S.loader.exec_module(M)
def test_capitalization_and_unknown():assert M.evaluate(M.baseline())=="CAPITALIZATION_ACCEPTED_THRESHOLD_DATE_AND_LINEAGE";assert M.evaluate(dict(M.baseline(),unknown_commit=True))=="ASSET_EVENT_UNKNOWN_RECONCILIATION_REQUIRED"
def test_depreciation_and_nbv_fail_closed():assert M.evaluate(dict(M.baseline(),operation="DEPRECIATE",depreciation_inputs_current=False))=="DEPRECIATION_REJECTED_METHOD_LIFE_RESIDUAL_PERIOD_OR_ROUNDING";assert M.evaluate(dict(M.baseline(),nbv_invariants_current=False))=="ASSET_INVARIANT_REJECTED_NEGATIVE_NBV_OR_EXCESS_DEPRECIATION"
def test_impairment_and_revaluation_require_lineage_reserve():assert M.evaluate(dict(M.baseline(),operation="IMPAIR",impairment_lineage_current=False))=="IMPAIRMENT_REJECTED_TEST_LINEAGE_OR_PERIOD";assert M.evaluate(dict(M.baseline(),operation="REVALUE",revaluation_reserve_current=False))=="REVALUATION_REJECTED_RESERVE_COMPONENT_OR_PERIOD"
def test_transfer_and_disposal_fail_closed():assert M.evaluate(dict(M.baseline(),operation="TRANSFER",transfer_scope_current=False))=="TRANSFER_REJECTED_SCOPE_OWNER_OR_VERSION";assert M.evaluate(dict(M.baseline(),operation="DISPOSE",disposal_lineage_approval_current=False))=="DISPOSAL_REJECTED_PERIOD_LINEAGE_OR_APPROVAL"
def test_reconciliation():assert M.evaluate(dict(M.baseline(),operation="RECONCILE",register_gl_reconciled=False))=="ASSET_RECONCILIATION_REJECTED_REGISTER_DEPRECIATION_OR_GL"
def test_schema_exact():e=copy.deepcopy(M.baseline());e["extra"]=True;assert M.evaluate(e)=="SCHEMA_INVALID"
