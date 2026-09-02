"""Pure synthetic order-to-cash evaluator; it reads and mutates no ERP data."""
from __future__ import annotations
FIELDS={"operation","scope_current","order_version_pricing_approved","credit_current","allocation_delivery_current","invoice_identity_lineage_current","return_lineage_current","cash_identity_custody_current","cash_allocation_balanced","dispute_collection_approved","aging_ecl_current","revenue_obligation_period_current","expected_version_match","idempotency_current","unknown_commit","ar_cash_revenue_gl_reconciled","blocking_unknown"}
BOOL=FIELDS-{"operation"};OPS={"ORDER","FULFILL","INVOICE","RETURN","CASH","ALLOCATE","COLLECT","REVENUE","RECONCILE"}
def evaluate(e):
 if not isinstance(e,dict) or set(e)!=FIELDS:return "SCHEMA_INVALID"
 if e["operation"] not in OPS or any(type(e[x]) is not bool for x in BOOL):return "SCHEMA_INVALID"
 if not e["scope_current"]:return "O2C_REJECTED_CUSTOMER_ORGANIZATION_CURRENCY_SCOPE"
 if not e["expected_version_match"] or not e["idempotency_current"]:return "O2C_REJECTED_VERSION_OR_IDEMPOTENCY"
 if e["unknown_commit"]:return "O2C_UNKNOWN_RECONCILIATION_REQUIRED"
 if e["blocking_unknown"]:return "MANUAL_REVIEW_REQUIRED_BLOCKING_UNKNOWN"
 op=e["operation"]
 if op=="ORDER":
  if not e["order_version_pricing_approved"]:return "SALES_ORDER_REJECTED_VERSION_PRICE_OR_APPROVAL"
  return "SALES_ORDER_ACCEPTED_SCOPED_PRICED_CREDIT_APPROVED" if e["credit_current"] else "CREDIT_REJECTED_LIMIT_EXPOSURE_OR_OVERRIDE"
 if op=="FULFILL":return "FULFILLMENT_ACCEPTED_ALLOCATED_SHIPPED_AND_DELIVERED" if e["allocation_delivery_current"] and e["credit_current"] else "FULFILLMENT_REJECTED_ALLOCATION_DELIVERY_OR_CREDIT"
 if op=="INVOICE":return "INVOICE_ACCEPTED_SCHEDULE_TAX_AND_LINEAGE" if e["invoice_identity_lineage_current"] else "INVOICE_REJECTED_IDENTITY_SCHEDULE_TAX_OR_LINEAGE"
 if op=="RETURN":return "RETURN_CREDIT_REFUND_ACCEPTED_WITH_ORIGINAL_LINEAGE" if e["return_lineage_current"] else "RETURN_CREDIT_REFUND_REJECTED_LINEAGE"
 if op=="CASH":return "CASH_RECEIPT_ACCEPTED_IDENTIFIED_AND_CUSTODIED" if e["cash_identity_custody_current"] else "CASH_RECEIPT_REJECTED_IDENTITY_OR_CUSTODY"
 if op=="ALLOCATE":
  if not e["cash_identity_custody_current"]:return "CASH_RECEIPT_REJECTED_IDENTITY_OR_CUSTODY"
  return "CASH_ALLOCATION_ACCEPTED_BALANCED_AND_VERSIONED" if e["cash_allocation_balanced"] else "CASH_ALLOCATION_REJECTED_AMOUNT_IDENTITY_OR_REVERSAL"
 if op=="COLLECT":return "DISPUTE_COLLECTION_ACTION_ACCEPTED_APPROVED_AND_EVIDENCED" if e["dispute_collection_approved"] else "DISPUTE_COLLECTION_REJECTED_UNAPPROVED_OR_UNEVIDENCED"
 if op=="REVENUE":return "REVENUE_RECOGNITION_ACCEPTED_OBLIGATION_AND_PERIOD" if e["aging_ecl_current"] and e["revenue_obligation_period_current"] else "REVENUE_OR_ECL_REJECTED_CUTOFF_OBLIGATION_OR_PERIOD"
 return "O2C_RECONCILIATION_ACCEPTED_AR_CASH_REVENUE_AND_GL" if e["ar_cash_revenue_gl_reconciled"] else "O2C_RECONCILIATION_REJECTED_AR_CASH_REVENUE_OR_GL"
def baseline():return {"operation":"ORDER","scope_current":True,"order_version_pricing_approved":True,"credit_current":True,"allocation_delivery_current":True,"invoice_identity_lineage_current":True,"return_lineage_current":True,"cash_identity_custody_current":True,"cash_allocation_balanced":True,"dispute_collection_approved":True,"aging_ecl_current":True,"revenue_obligation_period_current":True,"expected_version_match":True,"idempotency_current":True,"unknown_commit":False,"ar_cash_revenue_gl_reconciled":True,"blocking_unknown":False}
