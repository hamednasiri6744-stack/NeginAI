import copy,importlib.util
from pathlib import Path
P=Path(__file__).resolve().parents[1]/"scripts/windows/varanegar_manufacturing_reference.py";S=importlib.util.spec_from_file_location("ref",P);M=importlib.util.module_from_spec(S);S.loader.exec_module(M)
def test_plan_and_unknown():assert M.evaluate(M.baseline())=="MRP_PLAN_ACCEPTED_PEGGED_NETTED_AND_FENCED";assert M.evaluate(dict(M.baseline(),unknown_commit=True))=="MANUFACTURING_UNKNOWN_RECONCILIATION_REQUIRED"
def test_release_requires_versions_and_approval():assert M.evaluate(dict(M.baseline(),operation="RELEASE",order_version_approval_current=False))=="PRODUCTION_ORDER_REJECTED_BOM_ROUTING_VERSION_OR_APPROVAL"
def test_material_and_wip_fail_closed():assert M.evaluate(dict(M.baseline(),operation="MATERIAL",material_balance_current=False))=="MATERIAL_EXECUTION_REJECTED_SHORTAGE_BACKFLUSH_OR_WIP";assert M.evaluate(dict(M.baseline(),operation="MATERIAL",wip_transition_current=False))=="MATERIAL_EXECUTION_REJECTED_SHORTAGE_BACKFLUSH_OR_WIP"
def test_output_and_quality_require_genealogy():assert M.evaluate(dict(M.baseline(),operation="OUTPUT",genealogy_current=False))=="OUTPUT_REJECTED_YIELD_GENEALOGY_OR_QUALITY";assert M.evaluate(dict(M.baseline(),operation="QUALITY",quality_clear=False))=="QUALITY_DISPOSITION_REJECTED_GENEALOGY_HOLD_OR_APPROVAL"
def test_cost_and_reconciliation():assert M.evaluate(dict(M.baseline(),operation="COST",period_current=False))=="COSTING_REJECTED_COST_VERSION_VARIANCE_OR_PERIOD";assert M.evaluate(dict(M.baseline(),operation="RECONCILE",wip_inventory_cogs_gl_reconciled=False))=="MANUFACTURING_RECONCILIATION_REJECTED_WIP_COST_OR_GL"
def test_schema_exact():e=copy.deepcopy(M.baseline());e["extra"]=True;assert M.evaluate(e)=="SCHEMA_INVALID"
