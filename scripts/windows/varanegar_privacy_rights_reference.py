"""Pure synthetic privacy/rights evaluator; it reads no personal data."""
from __future__ import annotations
FIELDS={"inventory_current","subject_linkage_current","purpose_current","legal_basis_current","jurisdiction_policy_current","notice_current","consent_required","consent_current","consent_withdrawn","minimization_current","sensitive_guard_current","requested_action","identity_verified","representative_current","record_discovery_complete","third_party_redaction_current","legal_hold","conflicting_obligation","recipient_processor_scope_current","human_review_current","breach_evidence_current","retention_disposition_current","blocking_unknown"}
BOOL=FIELDS-{"requested_action"};ACTIONS={"PROCESS","ACCESS","CORRECT","PORTABLE","ERASE","RESTRICT","SHARE","AUTOMATED_DECISION","BREACH_RESPONSE","DISPOSE"}
def evaluate(e):
 if not isinstance(e,dict) or set(e)!=FIELDS:return "SCHEMA_INVALID"
 if any(type(e[x]) is not bool for x in BOOL) or e["requested_action"] not in ACTIONS:return "SCHEMA_INVALID"
 if not e["inventory_current"] or not e["subject_linkage_current"]:return "PRIVACY_ACTION_REJECTED_INVENTORY_OR_SUBJECT_LINKAGE"
 if not e["purpose_current"] or not e["legal_basis_current"] or not e["jurisdiction_policy_current"]:return "PROCESSING_REJECTED_PURPOSE_BASIS_SCOPE_OR_JURISDICTION"
 if not e["notice_current"]:return "PROCESSING_REJECTED_NOTICE"
 if e["consent_required"] and (not e["consent_current"] or e["consent_withdrawn"]):return "CONSENT_REJECTED_OR_WITHDRAWAL_PROPAGATION_REQUIRED"
 if not e["minimization_current"] or not e["sensitive_guard_current"]:return "PROCESSING_REJECTED_MINIMIZATION_OR_SENSITIVE_GUARD"
 action=e["requested_action"]
 if action in {"ACCESS","CORRECT","PORTABLE","ERASE","RESTRICT"}:
  if not e["identity_verified"] or not e["representative_current"]:return "RIGHTS_REQUEST_REJECTED_IDENTITY_SCOPE_OR_REPRESENTATIVE"
  if not e["record_discovery_complete"]:return "RIGHTS_REQUEST_REJECTED_INCOMPLETE_RECORD_DISCOVERY"
  if action in {"ACCESS","PORTABLE"} and not e["third_party_redaction_current"]:return "RIGHTS_RESPONSE_REJECTED_THIRD_PARTY_OR_PRIVILEGE_REVIEW"
  if action=="ERASE" and (e["legal_hold"] or e["conflicting_obligation"]):return "ERASURE_REJECTED_LEGAL_HOLD_OR_CONFLICTING_OBLIGATION"
  if action=="ERASE":return "ERASURE_ACCEPTED_VERIFIED_AND_PROPAGATABLE"
  if action=="RESTRICT":return "RESTRICTION_ACCEPTED_SCOPED_AND_EVIDENCED"
  return "RIGHTS_RESPONSE_ACCEPTED_VERIFIED_COMPLETE_AND_SAFE"
 if action=="SHARE":return "SHARING_ACCEPTED_RECIPIENT_PROCESSOR_AND_TRANSFER_SCOPED" if e["recipient_processor_scope_current"] else "SHARING_REJECTED_RECIPIENT_PROCESSOR_OR_TRANSFER_SCOPE"
 if action=="AUTOMATED_DECISION":return "AUTOMATED_DECISION_ACCEPTED_EXPLAINED_AND_REVIEWABLE" if e["human_review_current"] else "AUTOMATED_DECISION_HUMAN_REVIEW_REQUIRED"
 if action=="BREACH_RESPONSE":return "BREACH_RESPONSE_ACCEPTED_SCOPED_AND_EVIDENCED" if e["breach_evidence_current"] else "BREACH_RESPONSE_REQUIRED_SCOPED_AND_EVIDENCED"
 if action=="DISPOSE":return "DISPOSITION_ACCEPTED_VERIFIED_AND_PROPAGATED" if e["retention_disposition_current"] and not e["legal_hold"] else "DISPOSITION_REJECTED_RETENTION_HOLD_OR_VERIFICATION"
 if e["blocking_unknown"]:return "MANUAL_REVIEW_REQUIRED_BLOCKING_UNKNOWN"
 return "PROCESSING_ACCEPTED_PURPOSE_BASIS_SCOPE_AND_NECESSITY"
def baseline():return {"inventory_current":True,"subject_linkage_current":True,"purpose_current":True,"legal_basis_current":True,"jurisdiction_policy_current":True,"notice_current":True,"consent_required":False,"consent_current":True,"consent_withdrawn":False,"minimization_current":True,"sensitive_guard_current":True,"requested_action":"PROCESS","identity_verified":True,"representative_current":True,"record_discovery_complete":True,"third_party_redaction_current":True,"legal_hold":False,"conflicting_obligation":False,"recipient_processor_scope_current":True,"human_review_current":True,"breach_evidence_current":True,"retention_disposition_current":True,"blocking_unknown":False}
