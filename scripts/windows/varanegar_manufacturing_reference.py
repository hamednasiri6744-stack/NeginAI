"""Pure synthetic manufacturing evaluator; it reads and mutates no ERP data."""
from __future__ import annotations
FIELDS={"operation","scope_current","bom_routing_version_current","mrp_pegging_policy_current","order_version_approval_current","material_balance_current","labor_machine_output_current","genealogy_current","quality_clear","wip_transition_current","cost_version_variance_current","period_current","expected_version_match","idempotency_current","unknown_commit","wip_inventory_cogs_gl_reconciled","blocking_unknown"}
BOOL=FIELDS-{"operation"};OPS={"PLAN","RELEASE","MATERIAL","OUTPUT","QUALITY","COST","RECONCILE"}
def evaluate(e):
 if not isinstance(e,dict) or set(e)!=FIELDS:return "SCHEMA_INVALID"
 if e["operation"] not in OPS or any(type(e[x]) is not bool for x in BOOL):return "SCHEMA_INVALID"
 if not e["scope_current"]:return "MANUFACTURING_REJECTED_ITEM_PLANT_OR_OWNER_SCOPE"
 if not e["expected_version_match"] or not e["idempotency_current"]:return "MANUFACTURING_REJECTED_VERSION_OR_IDEMPOTENCY"
 if e["unknown_commit"]:return "MANUFACTURING_UNKNOWN_RECONCILIATION_REQUIRED"
 if e["blocking_unknown"]:return "MANUAL_REVIEW_REQUIRED_BLOCKING_UNKNOWN"
 op=e["operation"]
 if op=="PLAN":return "MRP_PLAN_ACCEPTED_PEGGED_NETTED_AND_FENCED" if e["mrp_pegging_policy_current"] and e["bom_routing_version_current"] else "MRP_PLAN_REJECTED_BOM_ROUTING_POLICY_OR_PEGGING"
 if op=="RELEASE":return "PRODUCTION_ORDER_ACCEPTED_VERSIONED_APPROVED_AND_RELEASED" if e["order_version_approval_current"] and e["bom_routing_version_current"] else "PRODUCTION_ORDER_REJECTED_BOM_ROUTING_VERSION_OR_APPROVAL"
 if op=="MATERIAL":return "MATERIAL_EXECUTION_ACCEPTED_RESERVED_ISSUED_AND_BALANCED" if e["material_balance_current"] and e["wip_transition_current"] else "MATERIAL_EXECUTION_REJECTED_SHORTAGE_BACKFLUSH_OR_WIP"
 if op=="OUTPUT":return "OUTPUT_ACCEPTED_YIELD_GENEALOGY_AND_QUALITY" if e["labor_machine_output_current"] and e["genealogy_current"] and e["quality_clear"] else "OUTPUT_REJECTED_YIELD_GENEALOGY_OR_QUALITY"
 if op=="QUALITY":return "QUALITY_DISPOSITION_ACCEPTED_INSPECTED_AND_RELEASED" if e["genealogy_current"] and e["quality_clear"] else "QUALITY_DISPOSITION_REJECTED_GENEALOGY_HOLD_OR_APPROVAL"
 if op=="COST":return "COSTING_ACCEPTED_STANDARD_ACTUAL_OVERHEAD_AND_VARIANCE" if e["cost_version_variance_current"] and e["period_current"] else "COSTING_REJECTED_COST_VERSION_VARIANCE_OR_PERIOD"
 return "MANUFACTURING_RECONCILIATION_ACCEPTED_WIP_INVENTORY_COGS_GL" if e["wip_inventory_cogs_gl_reconciled"] else "MANUFACTURING_RECONCILIATION_REJECTED_WIP_COST_OR_GL"
def baseline():return {"operation":"PLAN","scope_current":True,"bom_routing_version_current":True,"mrp_pegging_policy_current":True,"order_version_approval_current":True,"material_balance_current":True,"labor_machine_output_current":True,"genealogy_current":True,"quality_clear":True,"wip_transition_current":True,"cost_version_variance_current":True,"period_current":True,"expected_version_match":True,"idempotency_current":True,"unknown_commit":False,"wip_inventory_cogs_gl_reconciled":True,"blocking_unknown":False}
