"""Pure synthetic workforce/payroll evaluator; it reads no personnel data."""
from __future__ import annotations
FIELDS={"operation","scope_current","employment_contract_current","time_leave_approved","formula_version_current","statutory_rules_current","scale_rounding_balanced","retro_lineage_current","payslip_identity_privacy_current","payment_token_approval_current","termination_settlement_revocation_current","period_current","expected_version_match","idempotency_current","unknown_commit","liability_cash_gl_reconciled","blocking_unknown"}
BOOL=FIELDS-{"operation"};OPS={"INPUT","CALCULATE","RETRO","PAYSLIP","PAYMENT","TERMINATE","RECONCILE"}
def evaluate(e):
 if not isinstance(e,dict) or set(e)!=FIELDS:return "SCHEMA_INVALID"
 if e["operation"] not in OPS or any(type(e[x]) is not bool for x in BOOL):return "SCHEMA_INVALID"
 if not e["scope_current"]:return "PAYROLL_REJECTED_WORKER_EMPLOYMENT_ORGANIZATION_SCOPE"
 if not e["expected_version_match"] or not e["idempotency_current"]:return "PAYROLL_REJECTED_VERSION_OR_IDEMPOTENCY"
 if e["unknown_commit"]:return "PAYROLL_UNKNOWN_RECONCILIATION_REQUIRED"
 if e["blocking_unknown"]:return "MANUAL_REVIEW_REQUIRED_BLOCKING_UNKNOWN"
 op=e["operation"]
 if op=="INPUT":return "PAYROLL_INPUT_ACCEPTED_SCOPED_EFFECTIVE_AND_APPROVED" if e["employment_contract_current"] and e["time_leave_approved"] else "PAYROLL_INPUT_REJECTED_CONTRACT_TIME_OR_LEAVE"
 if op=="CALCULATE":return "GROSS_TO_NET_ACCEPTED_FORMULA_VERSION_AND_BALANCED" if e["formula_version_current"] and e["statutory_rules_current"] and e["scale_rounding_balanced"] and e["period_current"] else "GROSS_TO_NET_REJECTED_FORMULA_STATUTORY_SCALE_PERIOD_OR_ROUNDING"
 if op=="RETRO":return "RETRO_OFF_CYCLE_ACCEPTED_ORIGINAL_LINEAGE_AND_PERIOD" if e["retro_lineage_current"] and e["period_current"] else "RETRO_OFF_CYCLE_REJECTED_LINEAGE_PERIOD_OR_APPROVAL"
 if op=="PAYSLIP":return "PAYSLIP_ACCEPTED_NUMBERED_REDACTED_AND_RETAINED" if e["payslip_identity_privacy_current"] else "PAYSLIP_REJECTED_IDENTITY_PRIVACY_OR_DELIVERY"
 if op=="PAYMENT":return "PAYMENT_INSTRUCTION_ACCEPTED_TOKENIZED_APPROVED_AND_VERSIONED" if e["payment_token_approval_current"] and e["period_current"] else "PAYMENT_BLOCKED_IDENTITY_APPROVAL_PERIOD_OR_UNKNOWN"
 if op=="TERMINATE":return "TERMINATION_FINAL_PAY_ACCEPTED_SETTLED_AND_REVOKED" if e["termination_settlement_revocation_current"] else "TERMINATION_FINAL_PAY_REJECTED_INCOMPLETE_OR_UNAPPROVED"
 return "PAYROLL_RECONCILIATION_ACCEPTED_CONTROL_TOTALS_AND_GL" if e["liability_cash_gl_reconciled"] else "PAYROLL_RECONCILIATION_REJECTED_LIABILITY_CASH_OR_GL"
def baseline():return {"operation":"INPUT","scope_current":True,"employment_contract_current":True,"time_leave_approved":True,"formula_version_current":True,"statutory_rules_current":True,"scale_rounding_balanced":True,"retro_lineage_current":True,"payslip_identity_privacy_current":True,"payment_token_approval_current":True,"termination_settlement_revocation_current":True,"period_current":True,"expected_version_match":True,"idempotency_current":True,"unknown_commit":False,"liability_cash_gl_reconciled":True,"blocking_unknown":False}
