"""Pure synthetic procure-to-pay evaluator; it reads and mutates no ERP data."""
from __future__ import annotations
FIELDS={"operation","scope_current","budget_approval_current","po_version_current","receipt_acceptance_current","service_acceptance_current","invoice_identity_unique","line_identity_current","quantity_invariants_current","quantity_tolerance_current","price_tax_freight_tolerance_current","currency_rounding_current","partial_over_under_policy_current","return_lineage_current","hold_clear","release_approved","payment_gates_current","period_current","expected_version_match","idempotency_current","unknown_commit","accrual_ap_gl_reconciled","blocking_unknown"}
BOOL=FIELDS-{"operation"};OPS={"ORDER","RECEIVE","SERVICE","MATCH","RETURN","RELEASE","PAYMENT","RECONCILE"}
def evaluate(e):
 if not isinstance(e,dict) or set(e)!=FIELDS:return "SCHEMA_INVALID"
 if e["operation"] not in OPS or any(type(e[x]) is not bool for x in BOOL):return "SCHEMA_INVALID"
 if not e["scope_current"]:return "P2P_REJECTED_SUPPLIER_ORGANIZATION_CURRENCY_SCOPE"
 if not e["expected_version_match"] or not e["idempotency_current"]:return "P2P_REJECTED_VERSION_OR_IDEMPOTENCY"
 if e["unknown_commit"]:return "P2P_UNKNOWN_RECONCILIATION_REQUIRED"
 if e["blocking_unknown"]:return "MANUAL_REVIEW_REQUIRED_BLOCKING_UNKNOWN"
 op=e["operation"]
 if op=="ORDER":return "PURCHASE_ORDER_ACCEPTED_SCOPED_VERSIONED_AND_APPROVED" if e["budget_approval_current"] and e["po_version_current"] else "PURCHASE_ORDER_REJECTED_BUDGET_VERSION_OR_APPROVAL"
 if op=="RECEIVE":return "RECEIPT_ACCEPTED_INSPECTED_AND_STOCK_LINKED" if e["receipt_acceptance_current"] and e["line_identity_current"] else "RECEIPT_REJECTED_ACCEPTANCE_SCOPE_OR_LINEAGE"
 if op=="SERVICE":return "SERVICE_ENTRY_ACCEPTED_MILESTONE_AND_EVIDENCE_LINKED" if e["service_acceptance_current"] and e["line_identity_current"] else "SERVICE_ENTRY_REJECTED_ACCEPTANCE_OR_EVIDENCE"
 if not e["invoice_identity_unique"]:return "INVOICE_REJECTED_IDENTITY_DUPLICATE_OR_SCOPE"
 if op=="MATCH":
  if not e["line_identity_current"] or not e["quantity_invariants_current"]:return "THREE_WAY_MATCH_REJECTED_LINE_IDENTITY_OR_QUANTITY"
  if not e["quantity_tolerance_current"] or not e["partial_over_under_policy_current"]:return "THREE_WAY_MATCH_HELD_QUANTITY_OR_PARTIAL_EXCEPTION"
  if not e["price_tax_freight_tolerance_current"] or not e["currency_rounding_current"]:return "THREE_WAY_MATCH_REJECTED_PRICE_TAX_FREIGHT_OR_ROUNDING"
  return "THREE_WAY_MATCH_ACCEPTED_WITHIN_TOLERANCE"
 if op=="RETURN":return "RETURN_DEBIT_NOTE_OR_REVERSAL_ACCEPTED_WITH_LINEAGE" if e["return_lineage_current"] else "RETURN_REJECTED_ORIGINAL_LINEAGE"
 if op=="RELEASE":return "HOLD_RELEASE_ACCEPTED_INDEPENDENTLY_APPROVED" if e["hold_clear"] and e["release_approved"] else "HOLD_RELEASE_REJECTED_UNRESOLVED_OR_UNAPPROVED"
 if op=="PAYMENT":return "PAYMENT_ELIGIBLE_ALL_GATES_CURRENT" if e["hold_clear"] and e["payment_gates_current"] and e["period_current"] else "PAYMENT_BLOCKED_HOLD_GATE_OR_PERIOD"
 return "P2P_RECONCILIATION_ACCEPTED_ACCRUAL_SUBLEDGER_AND_GL" if e["accrual_ap_gl_reconciled"] else "P2P_RECONCILIATION_REJECTED_ACCRUAL_SUBLEDGER_OR_GL"
def baseline():return {"operation":"ORDER","scope_current":True,"budget_approval_current":True,"po_version_current":True,"receipt_acceptance_current":True,"service_acceptance_current":True,"invoice_identity_unique":True,"line_identity_current":True,"quantity_invariants_current":True,"quantity_tolerance_current":True,"price_tax_freight_tolerance_current":True,"currency_rounding_current":True,"partial_over_under_policy_current":True,"return_lineage_current":True,"hold_clear":True,"release_approved":True,"payment_gates_current":True,"period_current":True,"expected_version_match":True,"idempotency_current":True,"unknown_commit":False,"accrual_ap_gl_reconciled":True,"blocking_unknown":False}
