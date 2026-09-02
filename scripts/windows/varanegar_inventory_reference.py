"""Pure synthetic inventory/costing evaluator; it reads and mutates no stock."""
from __future__ import annotations
FIELDS={"operation","scope_current","lot_serial_identity_current","date_semantics_current","stock_state_current","quantity_invariants_current","negative_stock_policy_current","expected_version_match","idempotency_current","unknown_commit","cost_method_current","cost_layer_lineage_current","cost_layer_quantity_nonnegative","landed_cost_reconciled","transfer_ownership_current","count_frozen_blind","variance_approved","expiry_recall_quarantine_clear","period_current","stock_cost_gl_reconciled","blocking_unknown"}
BOOL=FIELDS-{"operation"};OPS={"MOVEMENT","ALLOCATE","COST","TRANSFER","COUNT","REVALUE","RECONCILE"}
def evaluate(e):
 if not isinstance(e,dict) or set(e)!=FIELDS:return "SCHEMA_INVALID"
 if any(type(e[x]) is not bool for x in BOOL) or e["operation"] not in OPS:return "SCHEMA_INVALID"
 if not e["scope_current"]:return "INVENTORY_REJECTED_SCOPE_UOM_WAREHOUSE_OR_OWNER"
 if not e["lot_serial_identity_current"] or not e["date_semantics_current"]:return "LOT_SERIAL_REJECTED_IDENTITY_DATE_OR_TRACEABILITY"
 if not e["expected_version_match"] or not e["idempotency_current"]:return "STOCK_MOVEMENT_REJECTED_VERSION_OR_IDEMPOTENCY"
 if e["unknown_commit"]:return "STOCK_MOVEMENT_UNKNOWN_RECONCILIATION_REQUIRED"
 if not e["stock_state_current"] or not e["quantity_invariants_current"]:return "STOCK_MOVEMENT_REJECTED_STATE_RESERVATION_OR_ALLOCATION"
 if not e["negative_stock_policy_current"]:return "STOCK_MOVEMENT_REJECTED_NEGATIVE_BACKDATE_OR_UNKNOWN"
 if e["blocking_unknown"]:return "MANUAL_REVIEW_REQUIRED_BLOCKING_UNKNOWN"
 op=e["operation"]
 if op=="ALLOCATE":return "STOCK_REJECTED_EXPIRY_RECALL_QUARANTINE_OR_DAMAGE" if not e["expiry_recall_quarantine_clear"] else "STOCK_ALLOCATION_ACCEPTED_AVAILABLE_AND_TRACEABLE"
 if op=="COST":
  if not e["cost_method_current"] or not e["cost_layer_lineage_current"] or not e["cost_layer_quantity_nonnegative"]:return "COST_LAYER_REJECTED_METHOD_SCOPE_QUANTITY_OR_ROUNDING"
  return "COST_LAYER_ACCEPTED_METHOD_VERSION_AND_LINEAGE" if e["landed_cost_reconciled"] else "LANDED_COST_REJECTED_ALLOCATION_OR_RESIDUAL"
 if op=="TRANSFER":return "TRANSFER_ACCEPTED_IN_TRANSIT_OWNER_AND_RECEIPT_RECONCILED" if e["transfer_ownership_current"] else "TRANSFER_REJECTED_SCOPE_OWNER_OR_RECEIPT"
 if op=="COUNT":return "COUNT_ADJUSTMENT_ACCEPTED_FROZEN_BLIND_AND_APPROVED" if e["count_frozen_blind"] and e["variance_approved"] else "COUNT_ADJUSTMENT_REJECTED_VARIANCE_APPROVAL_OR_VERSION"
 if op=="REVALUE":return "PERIOD_REVALUATION_ACCEPTED_RECONCILED_AND_LINKED" if e["period_current"] and e["stock_cost_gl_reconciled"] else "PERIOD_REVALUATION_REJECTED_PERIOD_OR_RECONCILIATION"
 if op=="RECONCILE":return "INVENTORY_RECONCILIATION_ACCEPTED_QUANTITY_VALUE_AND_LEDGER" if e["stock_cost_gl_reconciled"] else "INVENTORY_RECONCILIATION_REJECTED_QUANTITY_VALUE_OR_LEDGER"
 return "STOCK_MOVEMENT_ACCEPTED_SCOPED_VERSIONED_AND_BALANCED"
def baseline():return {"operation":"MOVEMENT","scope_current":True,"lot_serial_identity_current":True,"date_semantics_current":True,"stock_state_current":True,"quantity_invariants_current":True,"negative_stock_policy_current":True,"expected_version_match":True,"idempotency_current":True,"unknown_commit":False,"cost_method_current":True,"cost_layer_lineage_current":True,"cost_layer_quantity_nonnegative":True,"landed_cost_reconciled":True,"transfer_ownership_current":True,"count_frozen_blind":True,"variance_approved":True,"expiry_recall_quarantine_clear":True,"period_current":True,"stock_cost_gl_reconciled":True,"blocking_unknown":False}
