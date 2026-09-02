"""Pure synthetic tax-fiscalization evaluator; it performs no fiscal submission."""
from __future__ import annotations
FIELDS={"regime_current","registration_current","schema_current","identifiers_current","classification_current","tax_calculation_current","rounding_currency_current","fiscal_identity_current","digest_signature_current","certificate_current","submission_state","idempotency_current","unknown_reconciled","contingency_scope_current","contingency_expiry_current","original_lineage_current","period_state_current","provider_state_current","human_machine_parity","archive_current","control_totals_reconciled","blocking_unknown"}
BOOL=FIELDS-{"submission_state"};STATES={"DRAFT","ACK","WARNING","REJECT","UNKNOWN","CONTINGENCY","CORRECT","CANCEL"}
def evaluate(e):
 if not isinstance(e,dict) or set(e)!=FIELDS:return "SCHEMA_INVALID"
 if any(type(e[x]) is not bool for x in BOOL) or e["submission_state"] not in STATES:return "SCHEMA_INVALID"
 if not e["regime_current"] or not e["registration_current"]:return "FISCAL_DOCUMENT_REJECTED_REGIME_REGISTRATION_OR_SCOPE"
 if not e["schema_current"] or not e["identifiers_current"] or not e["classification_current"]:return "FISCAL_DOCUMENT_REJECTED_SCHEMA_IDENTIFIER_OR_CLASSIFICATION"
 if not e["tax_calculation_current"] or not e["rounding_currency_current"]:return "FISCAL_DOCUMENT_REJECTED_TAX_CALCULATION_OR_ROUNDING"
 if not e["fiscal_identity_current"]:return "FISCAL_DOCUMENT_REJECTED_NUMBER_UUID_TIMESTAMP_OR_DUPLICATE"
 if not e["digest_signature_current"] or not e["certificate_current"]:return "FISCAL_DOCUMENT_REJECTED_DIGEST_SIGNATURE_OR_CERTIFICATE"
 if not e["idempotency_current"]:return "SUBMISSION_REJECTED_IDEMPOTENCY_OR_PAYLOAD_IDENTITY"
 if not e["human_machine_parity"] or not e["archive_current"]:return "OUTPUT_REJECTED_HUMAN_MACHINE_OR_ARCHIVAL_PARITY"
 if e["blocking_unknown"]:return "MANUAL_REVIEW_REQUIRED_BLOCKING_UNKNOWN"
 state=e["submission_state"]
 if state=="ACK":return "SUBMISSION_CLEARED_ACKNOWLEDGED_AND_RECONCILED" if e["control_totals_reconciled"] else "SUBMISSION_REJECTED_CONTROL_TOTAL_RECONCILIATION"
 if state=="WARNING":return "SUBMISSION_WARNING_REVIEW_REQUIRED"
 if state=="REJECT":return "SUBMISSION_REJECTED_PROVIDER_CODE_PRESERVED"
 if state=="UNKNOWN":return "SUBMISSION_UNKNOWN_RECONCILIATION_REQUIRED" if not e["unknown_reconciled"] else "SUBMISSION_UNKNOWN_RECONCILED_NO_BLIND_RETRY"
 if state=="CONTINGENCY":return "CONTINGENCY_ACCEPTED_SCOPED_EXPIRING_AND_RECONCILABLE" if e["contingency_scope_current"] and e["contingency_expiry_current"] else "CONTINGENCY_REJECTED_SCOPE_EXPIRY_OR_RECONCILIATION"
 if state in {"CORRECT","CANCEL"}:
  return "CORRECTION_OR_CANCELLATION_ACCEPTED_ORIGINAL_PRESERVED" if e["original_lineage_current"] and e["period_state_current"] and e["provider_state_current"] else "CORRECTION_REJECTED_LINEAGE_PERIOD_OR_PROVIDER_STATE"
 return "FISCAL_DOCUMENT_ACCEPTED_SCHEMA_CALCULATION_AND_IDENTITY"
def baseline():return {"regime_current":True,"registration_current":True,"schema_current":True,"identifiers_current":True,"classification_current":True,"tax_calculation_current":True,"rounding_currency_current":True,"fiscal_identity_current":True,"digest_signature_current":True,"certificate_current":True,"submission_state":"DRAFT","idempotency_current":True,"unknown_reconciled":False,"contingency_scope_current":True,"contingency_expiry_current":True,"original_lineage_current":True,"period_state_current":True,"provider_state_current":True,"human_machine_parity":True,"archive_current":True,"control_totals_reconciled":True,"blocking_unknown":False}
