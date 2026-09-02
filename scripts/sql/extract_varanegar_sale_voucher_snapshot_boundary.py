"""Extract sale-voucher snapshot lifecycle and conversion boundaries read-only."""
from __future__ import annotations
import argparse, hashlib, json, re
from datetime import datetime
from pathlib import Path
from typing import Any
from extract_varanegar_org_domain import DATABASE,SERVER,_assert_safe_target,_connect,_json_default,_rows
from extract_varanegar_ngt_order_target_deletion_boundary import _executable_text

MODULES=(("SLE","usp_FillSaleVocher"),("dbo","usp_sdsnet_ConvertSaleToVocher"),
         ("SLE","usp_RollbackDisSaleSaleVocher"),("SLE","usp_sdsnet_CreateSaleByOrder"),
         ("dbo","usp_sdsnet_Sale_Cancel"),("SLE","trg_VN_Replication_tblSaleVocherHdr_DELETE"))
def _sha(x):return hashlib.sha256(x.encode()).hexdigest()
def _code(x):return " ".join(_executable_text(x).replace("[","").replace("]","").casefold().split())
def _count(x,p):return len(re.findall(p,x,re.I|re.S))

def _profiles(cur):
    out,codes=[],{}
    for schema,name in MODULES:
        rows=_rows(cur,"""SELECT s.name schema_name,o.name object_name,o.object_id,o.type_desc,o.create_date,o.modify_date,
          CASE WHEN t.object_id IS NULL THEN NULL ELSE t.is_disabled END is_disabled,m.definition
          FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
          LEFT JOIN sys.triggers t ON t.object_id=o.object_id WHERE s.name=%s AND o.name=%s""",(schema,name))
        if len(rows)!=1:raise AssertionError({"missing_or_duplicate_module":f"{schema}.{name}"})
        row=rows[0];oid=row.pop("object_id");definition=row.pop("definition") or "";code=_code(definition);q=f"{schema}.{name}";codes[q]=code
        deps=_rows(cur,"""SELECT DISTINCT COALESCE(referenced_schema_name,'') referenced_schema,COALESCE(referenced_entity_name,'') referenced_entity
          FROM sys.sql_expression_dependencies WHERE referencing_id=%s AND referenced_entity_name IS NOT NULL ORDER BY referenced_schema,referenced_entity""",(oid,))
        out.append({**row,"qualified_name":q,"definition_sha256":_sha(definition),"definition_character_count":len(definition),
                    "dependency_count":len(deps),"dependencies":[".".join(x for x in(d["referenced_schema"],d["referenced_entity"]) if x) for d in deps],
                    "begin_transaction_signal_count":_count(code,r"\bbegin\s+(?:tran|transaction)\b"),"save_transaction_signal_count":_count(code,r"\bsave\s+transaction\b"),
                    "commit_signal_count":_count(code,r"\bcommit\b"),"rollback_signal_count":_count(code,r"\brollback\b"),"try_catch_signal":"begin try" in code and "begin catch" in code,
                    "insert_signal_count":_count(code,r"\binsert\b"),"update_signal_count":_count(code,r"\bupdate\b"),"delete_signal_count":_count(code,r"\bdelete\b"),"definition_or_literal_values_persisted":False})
    return out,codes

def _state(cur):
    shapes=_rows(cur,"""WITH v AS(SELECT SaleRef,COUNT_BIG(*) snapshot_count,MIN(SaleVocherNo) snapshot_no,
      MIN(TotalAmount) snapshot_amount FROM SLE.tblSaleVocherHdr GROUP BY SaleRef)
      SELECT h.Status,h.CancelFlag,CASE WHEN h.SaleNo IS NULL THEN 0 ELSE 1 END has_sale_no,COUNT_BIG(*) sale_count,
      SUM(CASE WHEN h.SaleVocherNo IS NOT NULL THEN 1 ELSE 0 END) with_voucher_number_count,
      SUM(CASE WHEN v.SaleRef IS NOT NULL THEN 1 ELSE 0 END) with_snapshot_count,
      SUM(CASE WHEN v.snapshot_count>1 THEN 1 ELSE 0 END) multi_snapshot_count,
      SUM(CASE WHEN h.SaleVocherNo IS NOT NULL AND v.SaleRef IS NULL THEN 1 ELSE 0 END) number_without_snapshot_count,
      SUM(CASE WHEN h.SaleVocherNo IS NULL AND v.SaleRef IS NOT NULL THEN 1 ELSE 0 END) snapshot_without_number_count,
      SUM(CASE WHEN h.SaleVocherNo IS NOT NULL AND v.snapshot_no<>h.SaleVocherNo THEN 1 ELSE 0 END) voucher_number_mismatch_count,
      SUM(CASE WHEN v.SaleRef IS NOT NULL AND v.snapshot_amount<>h.TotalAmount THEN 1 ELSE 0 END) snapshot_amount_diff_count,
      SUM(CASE WHEN v.SaleRef IS NOT NULL AND v.snapshot_amount<>h.TotalAmount
        AND h.SaleDate>='1405/03/01' AND h.SaleDate<='1405/05/31' THEN 1 ELSE 0 END) recent_snapshot_amount_diff_count,
      SUM(CASE WHEN h.SaleDate>='1405/03/01' AND h.SaleDate<='1405/05/31' THEN 1 ELSE 0 END) recent_count
      FROM SLE.tblSaleHdr h LEFT JOIN v ON v.SaleRef=h.ID
      GROUP BY h.Status,h.CancelFlag,CASE WHEN h.SaleNo IS NULL THEN 0 ELSE 1 END ORDER BY h.Status,h.CancelFlag""")
    integrity=_rows(cur,"""WITH v AS(SELECT SaleRef,COUNT_BIG(*) c FROM SLE.tblSaleVocherHdr GROUP BY SaleRef)
      SELECT (SELECT COUNT_BIG(*) FROM SLE.tblSaleVocherHdr) snapshot_header_count,
      (SELECT COUNT_BIG(*) FROM SLE.tblSaleVocherItm) snapshot_item_count,
      (SELECT COUNT_BIG(*) FROM SLE.tblSaleVocherHdr x LEFT JOIN SLE.tblSaleHdr h ON h.ID=x.SaleRef WHERE h.ID IS NULL) orphan_snapshot_count,
      (SELECT COUNT_BIG(*) FROM v WHERE c>1) duplicate_sale_snapshot_group_count,
      (SELECT COUNT_BIG(*) FROM SLE.tblSaleVocherItm i LEFT JOIN SLE.tblSaleVocherHdr h ON h.ID=i.HdrRef WHERE h.ID IS NULL) orphan_snapshot_item_count""")[0]
    return {"sale_state_shapes":shapes,"snapshot_integrity":integrity}

def _audit(cur):
    ops=_rows(cur,"""SELECT OperationType,COUNT_BIG(*) event_count,COUNT(DISTINCT OperationId) id_count,
      SUM(CASE WHEN TransDate>='20260601' AND TransDate<'20260901' THEN 1 ELSE 0 END) recent_event_count,
      MIN(TransDate) first_event_date,MAX(TransDate) last_event_date FROM GNR.tblLog WITH(INDEX(IX_NC_tbllog_OperationTable_OperationId_Id))
      WHERE OperationTable='SLE.tblSaleVocherHdr' GROUP BY OperationType ORDER BY OperationType""")
    cov=_rows(cur,"""WITH l AS(SELECT OperationId,SUM(CASE WHEN OperationType='DELETE' THEN 1 ELSE 0 END) del,MAX(TransDate) last_log
      FROM GNR.tblLog WITH(INDEX(IX_NC_tbllog_OperationTable_OperationId_Id)) WHERE OperationTable='SLE.tblSaleVocherHdr' GROUP BY OperationId)
      SELECT COUNT_BIG(*) logged_snapshot_count,SUM(CASE WHEN v.ID IS NOT NULL THEN 1 ELSE 0 END) current_count,
      SUM(CASE WHEN v.ID IS NULL THEN 1 ELSE 0 END) absent_count,SUM(CASE WHEN v.ID IS NULL AND del>0 THEN 1 ELSE 0 END) absent_with_delete_count,
      SUM(CASE WHEN v.ID IS NULL AND del=0 THEN 1 ELSE 0 END) absent_without_delete_count,
      SUM(CASE WHEN v.ID IS NULL AND last_log>='20260601' AND last_log<'20260901' THEN 1 ELSE 0 END) recent_absent_count
      FROM l LEFT JOIN SLE.tblSaleVocherHdr v ON v.ID=l.OperationId""")[0]
    return {"operation_counts":ops,"logged_id_coverage":cov}

def _deletes(cur):
    rows=_rows(cur,"""SELECT s.name schema_name,o.name object_name,o.type_desc,m.definition FROM sys.sql_modules m
      JOIN sys.objects o ON o.object_id=m.object_id JOIN sys.schemas s ON s.schema_id=o.schema_id WHERE m.definition LIKE '%tblSaleVocherHdr%'""");out=[]
    for row in rows:
        definition=row.pop("definition") or "";code=_code(definition)
        if not re.search(r"\bdelete\s+(?:from\s+)?(?:sle\.)?tblsalevocherhdr\b",code):continue
        out.append({**row,"qualified_name":f"{row['schema_name']}.{row['object_name']}","definition_sha256":_sha(definition),
                    "begin_transaction_signal_count":_count(code,r"\bbegin\s+(?:tran|transaction)\b"),"save_transaction_signal_count":_count(code,r"\bsave\s+transaction\b"),
                    "commit_signal_count":_count(code,r"\bcommit\b"),"rollback_signal_count":_count(code,r"\brollback\b"),"definition_or_literal_values_persisted":False})
    return sorted(out,key=lambda x:x["qualified_name"].casefold())

def collect():
    c=_connect()
    try:
        cur=c.cursor();safe=_assert_safe_target(cur);profiles,codes=_profiles(cur);state=_state(cur);audit=_audit(cur);deletes=_deletes(cur)
    finally:c.close()
    fill=codes["SLE.usp_FillSaleVocher"];convert=codes["dbo.usp_sdsnet_ConvertSaleToVocher"];rollback=codes["SLE.usp_RollbackDisSaleSaleVocher"];create=codes["SLE.usp_sdsnet_CreateSaleByOrder"];cancel=codes["dbo.usp_sdsnet_Sale_Cancel"];repl=codes["SLE.trg_VN_Replication_tblSaleVocherHdr_DELETE"]
    allsh=state["sale_state_shapes"];ops={x["OperationType"]:x for x in audit["operation_counts"]}
    total=lambda key:sum(x[key] for x in allsh)
    cancelled_snapshot=sum(x["with_snapshot_count"] for x in allsh if x["CancelFlag"]==1)
    return {"artifact":"varanegar_sale_voucher_snapshot_boundary","schema_version":1,"generated_at":datetime.now().astimezone(),"validation":"PASS","scope":{"server":SERVER,"database":DATABASE},
      "safety":{"mode":"READ_ONLY_CLONE_CATALOG_FINGERPRINTS_AND_ANONYMOUS_SNAPSHOT_AGGREGATES","database_updateability":safe["updateability"],"can_select":safe["can_select"],"can_view_definition":safe["can_view_definition"],"can_update":safe["can_update"],"denies_data_writes":safe["denies_data_writes"],"stored_procedure_trigger_form_or_application_command_executions":0,"sale_order_snapshot_customer_user_host_or_raw_values_persisted":0,"sql_definitions_error_texts_or_business_identifiers_persisted":0,"source_or_target_state_changed":0},
      "summary":{"selected_sql_module_count":len(profiles),"sale_with_voucher_number_count":total("with_voucher_number_count"),"sale_with_snapshot_count":total("with_snapshot_count"),"cancelled_sale_with_snapshot_count":cancelled_snapshot,"voucher_number_or_snapshot_mismatch_count":total("number_without_snapshot_count")+total("snapshot_without_number_count")+total("voucher_number_mismatch_count"),"snapshot_amount_diff_count":total("snapshot_amount_diff_count"),"recent_snapshot_amount_diff_count":total("recent_snapshot_amount_diff_count"),"snapshot_header_count":state["snapshot_integrity"]["snapshot_header_count"],"snapshot_item_count":state["snapshot_integrity"]["snapshot_item_count"],"direct_snapshot_delete_candidate_count":len(deletes),"retained_snapshot_delete_count":ops.get("DELETE",{"event_count":0})["event_count"],"logged_snapshot_absent_count":audit["logged_id_coverage"]["absent_count"]},
      "sql_module_profiles":profiles,"static_snapshot_contract":{"fill_inserts_snapshot_header_and_items":all(x in fill for x in("tblsalevocherhdr","tblsalevocheritm")) and _count(fill,r"\binsert\b")>0,"fill_has_no_local_transaction":not bool(re.search(r"\bbegin\s+(?:tran|transaction)\b|\bsave\s+transaction\b",fill)),"convert_has_local_transaction_try_catch_commit_and_rollback":bool(re.search(r"\bbegin\s+(?:tran|transaction)\b",convert)) and all(x in convert for x in("begin try","begin catch","commit","rollback")),"convert_references_snapshot_and_sale_header":all(x in convert for x in("tblsalevocherhdr","tblsalehdr")),"create_order_to_sale_references_fill_snapshot":("fillsalevocher" in create),"sale_cancel_does_not_delete_snapshot_header":not bool(re.search(r"\bdelete\s+(?:from\s+)?(?:sle\.)?tblsalevocherhdr\b",cancel)),"rollback_distribution_sale_voucher_mutates_snapshot_graph":all(x in rollback for x in("tblsalevocherhdr","tblsalevocheritm")) and (_count(rollback,r"\bdelete\b")+_count(rollback,r"\bupdate\b")>0),"replication_snapshot_delete_trigger_is_bypassable":"ufn_isreplicationmode" in repl and "return" in repl},
      "current_sale_voucher_state":state,"generic_snapshot_log_lifecycle":audit,"direct_snapshot_delete_candidates":deletes,
      "evidence_limits":["Snapshot equality supports current reconciliation but does not prove immutability of every historical field.","Retained snapshots on cancelled sales are history, not proof that the sale remains active.","Direct-delete candidates prove capability, not attribution.","No procedure, trigger, form or command was executed and no raw sale, order, customer, user, host, error text or identifier was persisted."]}

def main():
 p=argparse.ArgumentParser();p.add_argument("--output",required=True,type=Path);a=p.parse_args();x=collect();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(x,ensure_ascii=False,indent=2,default=_json_default)+"\n",encoding="utf-8");print(a.output.resolve());print(json.dumps(x["summary"],ensure_ascii=False));print(json.dumps(x["static_snapshot_contract"],ensure_ascii=False));return 0
if __name__=="__main__":raise SystemExit(main())
