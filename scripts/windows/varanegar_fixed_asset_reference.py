"""Pure synthetic fixed-asset evaluator; it reads and mutates no asset data."""
from __future__ import annotations
FIELDS={"operation","scope_current","acquisition_cip_lineage_current","book_method_policy_current","component_identity_current","depreciation_inputs_current","nbv_invariants_current","impairment_lineage_current","revaluation_reserve_current","transfer_scope_current","disposal_lineage_approval_current","period_current","expected_version_match","idempotency_current","unknown_commit","register_gl_reconciled","blocking_unknown"}
BOOL=FIELDS-{"operation"};OPS={"CAPITALIZE","DEPRECIATE","IMPAIR","REVALUE","TRANSFER","DISPOSE","RECONCILE"}
def evaluate(e):
 if not isinstance(e,dict) or set(e)!=FIELDS:return "SCHEMA_INVALID"
 if e["operation"] not in OPS or any(type(e[x]) is not bool for x in BOOL):return "SCHEMA_INVALID"
 if not e["scope_current"] or not e["component_identity_current"]:return "ASSET_EVENT_REJECTED_IDENTITY_SCOPE_OR_COMPONENT"
 if not e["expected_version_match"] or not e["idempotency_current"]:return "ASSET_EVENT_REJECTED_VERSION_OR_IDEMPOTENCY"
 if e["unknown_commit"]:return "ASSET_EVENT_UNKNOWN_RECONCILIATION_REQUIRED"
 if e["blocking_unknown"]:return "MANUAL_REVIEW_REQUIRED_BLOCKING_UNKNOWN"
 if not e["nbv_invariants_current"]:return "ASSET_INVARIANT_REJECTED_NEGATIVE_NBV_OR_EXCESS_DEPRECIATION"
 op=e["operation"]
 if op=="CAPITALIZE":return "CAPITALIZATION_ACCEPTED_THRESHOLD_DATE_AND_LINEAGE" if e["acquisition_cip_lineage_current"] and e["book_method_policy_current"] and e["period_current"] else "CAPITALIZATION_REJECTED_THRESHOLD_CIP_POLICY_OR_PERIOD"
 if op=="DEPRECIATE":return "DEPRECIATION_ACCEPTED_METHOD_PERIOD_PRORATION_AND_BALANCED" if e["book_method_policy_current"] and e["depreciation_inputs_current"] and e["period_current"] else "DEPRECIATION_REJECTED_METHOD_LIFE_RESIDUAL_PERIOD_OR_ROUNDING"
 if op=="IMPAIR":return "IMPAIRMENT_ACCEPTED_TEST_AMOUNT_AND_LINEAGE" if e["impairment_lineage_current"] and e["period_current"] else "IMPAIRMENT_REJECTED_TEST_LINEAGE_OR_PERIOD"
 if op=="REVALUE":return "REVALUATION_ACCEPTED_RESERVE_AND_COMPONENT_ALLOCATION" if e["revaluation_reserve_current"] and e["period_current"] else "REVALUATION_REJECTED_RESERVE_COMPONENT_OR_PERIOD"
 if op=="TRANSFER":return "TRANSFER_ACCEPTED_SCOPE_OWNER_AND_VERSION" if e["transfer_scope_current"] else "TRANSFER_REJECTED_SCOPE_OWNER_OR_VERSION"
 if op=="DISPOSE":return "DISPOSAL_ACCEPTED_PROCEEDS_GAIN_LOSS_AND_DERECOGNITION" if e["disposal_lineage_approval_current"] and e["period_current"] else "DISPOSAL_REJECTED_PERIOD_LINEAGE_OR_APPROVAL"
 return "ASSET_RECONCILIATION_ACCEPTED_REGISTER_SUBLEDGER_AND_GL" if e["register_gl_reconciled"] else "ASSET_RECONCILIATION_REJECTED_REGISTER_DEPRECIATION_OR_GL"
def baseline():return {"operation":"CAPITALIZE","scope_current":True,"acquisition_cip_lineage_current":True,"book_method_policy_current":True,"component_identity_current":True,"depreciation_inputs_current":True,"nbv_invariants_current":True,"impairment_lineage_current":True,"revaluation_reserve_current":True,"transfer_scope_current":True,"disposal_lineage_approval_current":True,"period_current":True,"expected_version_match":True,"idempotency_current":True,"unknown_commit":False,"register_gl_reconciled":True,"blocking_unknown":False}
