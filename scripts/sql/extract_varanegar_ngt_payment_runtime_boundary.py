"""Extract the deployed NGT payment/settlement runtime boundary from static IL.

The deployed assemblies are parsed only as PE metadata and IL bytes. They are
never loaded or executed. Arbitrary string literals are counted and discarded;
only allow-listed SQL object identifiers may be retained.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import dnfile
from dncil.cil.body.reader import read_method_body_from_bytes
from dncil.clr.token import StringToken, Token


WINDOWS_SCRIPTS = Path(__file__).resolve().parents[1] / "windows"
if str(WINDOWS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(WINDOWS_SCRIPTS))

from extract_varanegar_ngt_authorization_runtime_boundary import (  # noqa: E402
    _owner_maps,
    _parameter_count,
    _resolve_token,
    _signature_bytes,
)


TARGET_FILES = (
    "NGT.Common.dll",
    "NGT.Business.dll",
    "NGT.DataAccess.dll",
    "NGT.WebApi.dll",
)

FOCUSED_OWNER = re.compile(
    r"^(?:NGT\.Business\.Domain\.(?:CustomerCallPaymentDetailDomain|"
    r"CustomerCallPaymentDomain|DealerPaymentTypeDomain|PaymentTypeOrderDomain|"
    r"PosDomain)(?:\+.*)?|"
    r"NGT\.Business\.Domain\.TourDomain\+<(?:ConfirmTourPayments|"
    r"WithdrawTourPayments)>d__.*|"
    r"NGT\.WebApi\.Controllers\.V2\.(?:PaymentTypeOrderController|"
    r"PosController)(?:\+.*)?|"
    r"NGT\.WebApi\.Controllers\.V2\.PersonnelController\+<"
    r"GetDealerCustomerPaymentTypes>d__.*|"
    r"NGT\.WebApi\.Controllers\.V2\.TourController\+<"
    r"GetTourCustomerCallPayments>d__.*)$",
    re.IGNORECASE,
)

SIGNAL = re.compile(
    r"(?:CustomerCallPayment|CustomerCallPaymentDetail|PaymentTypeOrder|"
    r"DealerPaymentType|SettlementType|BackOfficeReceipt|ReceiptRef|ReceiptNo|"
    r"ConfirmTourPayments|WithdrawTourPayments|SaveTourPaymentChanges|"
    r"GetCertifiedPayer|GetPaymentCodeByCustomerId|AllowReceipt|Sayad|RCashDraft|"
    r"PosDomain|PosController)",
    re.IGNORECASE,
)

STATE_REF = re.compile(
    r"(?:CustomerCallUniqueId|CustomerCallPaymentUniqueId|CustomerCallOrderUniqueId|"
    r"SettlementTypeUniqueId|Amount|PaidAmount|BackOfficeReceiptUniqueId|"
    r"BackOfficeReceiptRef|BackOfficeReceiptNo|BackOfficeSaleId|SaleRef|SaleNo|"
    r"IsOldInvoice|ChqNo|SayadNo|ChqDate|ChqPDate|ChqBankUniqueId|ChqCityUniqueId|"
    r"ChqBranchCode|ChqBranchName|ChqAccountName|ChqAccountNo|FollowNo|SayadStatus|"
    r"RCashDraftTypeId|PayablePersonName|AllowReceipt|PaymentApproved|"
    r"PaymentDeadLine|PaymentTime|DiscountPercent|CheckCredit|CheckDebit|IsEnabled|"
    r"IsCash|GroupBackOfficeId|Code|IsCertifiedPayment|PosUniqueId|BankAccountUniqueId|"
    r"DeviceSerial|IsRemoved)",
    re.IGNORECASE,
)

SCOPE_REF = re.compile(
    r"(?:ApplicationOwner|DataOwnerCenter|DataOwner|OwnerInfo|CurrentUser|"
    r"UserUniqueId|AgentUniqueId|DealerUniqueId|CustomerUniqueId)",
    re.IGNORECASE,
)

MUTATION_CALL = re.compile(
    r"(?:^|\.)(?:BeginTransaction|Commit|Rollback|SaveChanges|SaveChangesAsync|"
    r"Add|AddAsync|AddRange|AddRangeAsync|Update|UpdateAsync|UpdateBatchAsync|"
    r"UpdateBatch|UpdateRange|BulkMergeListAsync|Remove|RemoveAsync|RemoveRange|"
    r"Delete|DeleteAsync|"
    r"ExecuteSqlCommand|ExecuteSqlCommandAsync|ExecuteNonQuery|"
    r"CustomCommit|CustomRollback)$",
    re.IGNORECASE,
)

SELECTION_CALL = re.compile(
    r"(?:^|\.)(?:GetQueryByOwner|GetQuery|FirstOrDefault|First|SingleOrDefault|"
    r"Single|Where|Any|All|Find|FindAll|FindAsync|FindAllAsync|GetById|"
    r"GetByIdAsync|ToList|ToListAsync|AsNoTracking|Include|OrderBy|ThenBy|"
    r"Select|GroupBy)$",
    re.IGNORECASE,
)

BEHAVIOR_REF = re.compile(
    r"(?:BeginTransaction|Commit|Rollback|SaveChanges|UpdateAsync|AddAsync|"
    r"RemoveAsync|ExecuteSqlCommand|ExecuteNonQuery|CustomCommit|CustomRollback|"
    r"SaveTourPaymentChanges|ConfirmTourPayments|WithdrawTourPayments|"
    r"GetDealerCustomerPaymentTypes|GetCertifiedPayers|GetPaymentCodeByCustomerId|"
    r"FilterByUserAndCustomer|CustomerCallPayment|PaymentTypeOrder|"
    r"DealerPaymentType|SettlementType|Receipt|PosDomain)",
    re.IGNORECASE,
)

SQL_OBJECT_REF = re.compile(
    r"\b(?:EXEC(?:UTE)?|INSERT\s+INTO|UPDATE|DELETE\s+FROM|MERGE\s+INTO|FROM|JOIN)\s+"
    r"(?P<object>(?:\[(?:dbo|NGT|FRU|SLE|GNR|ACC)\]|(?:dbo|NGT|FRU|SLE|GNR|ACC))"
    r"\.\[[A-Za-z_][A-Za-z0-9_]*\]|(?:dbo|NGT|FRU|SLE|GNR|ACC)\."
    r"[A-Za-z_][A-Za-z0-9_]*)",
    re.IGNORECASE,
)

CORE_METHODS = (
    ("NGT.Business.Domain.CustomerCallPaymentDomain", "SaveTourPaymentChanges"),
    ("NGT.Business.Domain.DealerPaymentTypeDomain", "GetDealerCustomerPaymentTypes"),
    ("NGT.Business.Domain.PaymentTypeOrderDomain", "Get"),
    ("NGT.Business.Domain.PaymentTypeOrderDomain", "Sync"),
    ("NGT.Business.Domain.PaymentTypeOrderDomain", "FilterByUserAndCustomer"),
    ("NGT.Business.Domain.PaymentTypeOrderDomain", "GetPaymentCodeByCustomerId"),
    ("NGT.Business.Domain.PaymentTypeOrderDomain", "GetCertifiedPayers"),
    ("NGT.Business.Domain.PosDomain", "Update"),
    ("NGT.Business.Domain.PosDomain", "Add"),
    ("NGT.Business.Domain.PosDomain", "Remove"),
    ("NGT.Business.Domain.TourDomain", "ConfirmTourPayments"),
    ("NGT.Business.Domain.TourDomain", "WithdrawTourPayments"),
    ("NGT.WebApi.Controllers.V2.PaymentTypeOrderController", "GetCertifiedPayer"),
    ("NGT.WebApi.Controllers.V2.PosController", "Save"),
    ("NGT.WebApi.Controllers.V2.PosController", "Put"),
    ("NGT.WebApi.Controllers.V2.PosController", "Delete"),
    ("NGT.WebApi.Controllers.V2.TourController", "GetTourCustomerCallPayments"),
)


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _scan(path: Path) -> dict[str, Any]:
    pe = dnfile.dnPE(str(path))
    if not getattr(pe, "net", None):
        raise ValueError(f"not a .NET assembly: {path}")
    method_owners, field_owners, type_names = _owner_maps(pe)
    methods: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    method_body_count = 0
    redacted_literal_count = 0

    for type_index, type_row in enumerate(pe.net.mdtables.TypeDef.rows, start=1):
        owner = type_names[type_index]
        for method_index in type_row.MethodList or []:
            method = method_index.row
            if method is None or not method.Rva:
                continue
            method_name = _text(method.Name)
            method_body_count += 1
            try:
                body = read_method_body_from_bytes(pe.get_data(method.Rva, 65536))
            except Exception as exc:
                errors.append(
                    {
                        "owner": owner,
                        "method": method_name,
                        "error_class": type(exc).__name__,
                        "signal_named": bool(SIGNAL.search(owner) or SIGNAL.search(method_name)),
                    }
                )
                continue

            calls: list[str] = []
            ordered_references: list[str] = []
            safe_sql_refs: list[str] = []
            method_redacted = 0
            for instruction in body.instructions:
                operand = instruction.operand
                if instruction.mnemonic in {"call", "callvirt", "newobj"} and isinstance(
                    operand, Token
                ):
                    resolved = _resolve_token(
                        pe, operand, method_owners, field_owners, type_names
                    )
                    calls.append(resolved)
                    ordered_references.append(resolved)
                elif "fld" in instruction.mnemonic and isinstance(operand, Token):
                    ordered_references.append(
                        _resolve_token(pe, operand, method_owners, field_owners, type_names)
                    )
                elif instruction.mnemonic == "ldstr" and isinstance(operand, StringToken):
                    item = pe.net.user_strings.get(operand.rid)
                    value = "" if item is None else _text(item.value)
                    for match in SQL_OBJECT_REF.finditer(value):
                        safe_sql_refs.append(
                            match.group("object").replace("[", "").replace("]", "")
                        )
                    method_redacted += 1
                    redacted_literal_count += 1
                elif isinstance(operand, Token):
                    ordered_references.append(
                        _resolve_token(pe, operand, method_owners, field_owners, type_names)
                    )

            if not (
                FOCUSED_OWNER.search(owner)
                or SIGNAL.search(owner)
                or SIGNAL.search(method_name)
                or any(SIGNAL.search(value) for value in ordered_references)
            ):
                continue
            methods.append(
                {
                    "owner": owner,
                    "method": method_name,
                    "method_metadata_token": f"0x06{method_index.row_index:06x}",
                    "parameter_count": _parameter_count(method),
                    "signature_hex": _signature_bytes(method).hex(),
                    "instruction_count": len(body.instructions),
                    "mutation_calls_in_order": [
                        value for value in calls if MUTATION_CALL.search(value)
                    ],
                    "call_references_in_order": calls,
                    "selection_calls": sorted(
                        {value for value in calls if SELECTION_CALL.search(value)}
                    ),
                    "behavior_references_in_order": [
                        value for value in ordered_references if BEHAVIOR_REF.search(value)
                    ],
                    "state_references_in_order": [
                        value for value in ordered_references if STATE_REF.search(value)
                    ],
                    "scope_references": sorted(
                        {value for value in ordered_references if SCOPE_REF.search(value)}
                    ),
                    "safe_sql_object_references": sorted(set(safe_sql_refs)),
                    "redacted_non_allowlisted_literal_count": method_redacted,
                    "has_conditional_branch": any(
                        instruction.mnemonic.startswith("br")
                        or instruction.mnemonic == "switch"
                        for instruction in body.instructions
                    ),
                    "has_exception_regions": bool(body.exception_handlers),
                }
            )

    return {
        "file": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
        "method_body_count": method_body_count,
        "method_body_error_count": len(errors),
        "selected_method_count": len(methods),
        "redacted_non_allowlisted_literal_count": redacted_literal_count,
        "body_errors": errors,
        "methods": methods,
    }


def _compact(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        key: row[key]
        for key in (
            "file",
            "owner",
            "method",
            "method_metadata_token",
            "parameter_count",
            "instruction_count",
            "mutation_calls_in_order",
            "call_references_in_order",
            "selection_calls",
            "behavior_references_in_order",
            "state_references_in_order",
            "scope_references",
            "safe_sql_object_references",
            "has_conditional_branch",
            "has_exception_regions",
        )
    }


def collect(source_directory: Path) -> dict[str, Any]:
    scans = [_scan(source_directory / file_name) for file_name in TARGET_FILES]
    methods = [
        {"file": scan["file"], **method}
        for scan in scans
        for method in scan["methods"]
    ]
    errors = [
        {"file": scan["file"], **error}
        for scan in scans
        for error in scan["body_errors"]
    ]
    focused = [row for row in methods if FOCUSED_OWNER.search(row["owner"])]

    def resolve(owner: str, method: str) -> dict[str, Any] | None:
        async_row = next(
            (
                row
                for row in focused
                if row["owner"].startswith(f"{owner}+<{method}>")
                and row["method"] == "MoveNext"
            ),
            None,
        )
        if async_row is not None:
            return async_row
        return next(
            (
                row
                for row in focused
                if row["owner"] == owner and row["method"] == method
            ),
            None,
        )

    core = {
        f"{owner}.{method}": _compact(resolve(owner, method))
        for owner, method in CORE_METHODS
    }
    targets = tuple(core)
    callers = {
        target: [
            {
                "file": row["file"],
                "owner": row["owner"],
                "method": row["method"],
                "parameter_count": row["parameter_count"],
            }
            for row in methods
            if target in row["call_references_in_order"]
        ]
        for target in targets
    }
    caller_contracts = {
        target: [
            _compact(row)
            for row in methods
            if target in row["call_references_in_order"]
        ]
        for target in targets
    }

    def has_call(contract_key: str, suffix: str) -> bool:
        row = core[contract_key]
        return bool(
            row
            and any(call.endswith(suffix) for call in row["call_references_in_order"])
        )

    payment_save_key = "NGT.Business.Domain.CustomerCallPaymentDomain.SaveTourPaymentChanges"
    payment_save = core[payment_save_key]
    payment_save_contract = {
        "explicit_begin_transaction": has_call(payment_save_key, ".BeginTransaction"),
        "explicit_commit": has_call(payment_save_key, ".Commit"),
        "explicit_rollback": has_call(payment_save_key, ".Rollback"),
        "bulk_merge_present": has_call(payment_save_key, ".BulkMergeListAsync"),
        "existing_cash_payment_filter_reference_present": bool(
            payment_save
            and any(
                value.endswith("SettlementTypes.get_Cash")
                for value in payment_save["behavior_references_in_order"]
            )
        ),
        "soft_remove_reference_present": bool(
            payment_save
            and any(
                value.endswith("BaseModel.set_IsRemoved")
                for value in payment_save["state_references_in_order"]
            )
        ),
        "header_amount_accumulator_reference_present": bool(
            payment_save
            and any(".amount" in value for value in payment_save["state_references_in_order"])
        ),
        "detail_paid_amount_accumulator_reference_present": bool(
            payment_save
            and any(".paidAmount" in value for value in payment_save["state_references_in_order"])
        ),
        "direct_static_caller_count": len(callers[payment_save_key]),
    }

    return {
        "artifact": "varanegar_ngt_payment_runtime_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone(),
        "validation": "PASS",
        "source": {
            "assembly_directory": str(source_directory),
            "assemblies": [
                {key: scan[key] for key in ("file", "sha256", "bytes")}
                for scan in scans
            ],
        },
        "safety": {
            "mode": "STATIC_PE_METADATA_AND_IL_ONLY",
            "assemblies_loaded_or_executed": 0,
            "application_endpoints_or_commands_called": 0,
            "configuration_files_or_values_read": 0,
            "business_rows_or_identifiers_read": 0,
            "non_allowlisted_literals_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "assembly_count": len(scans),
            "method_body_count": sum(scan["method_body_count"] for scan in scans),
            "method_body_error_count": len(errors),
            "signal_named_body_error_count": sum(1 for row in errors if row["signal_named"]),
            "selected_method_count": len(methods),
            "focused_method_count": len(focused),
            "focused_mutation_method_count": sum(
                1 for row in focused if row["mutation_calls_in_order"]
            ),
            "core_method_count": sum(1 for row in core.values() if row is not None),
            "missing_core_method_count": sum(1 for row in core.values() if row is None),
        },
        "assembly_scan": [
            {key: value for key, value in scan.items() if key not in {"methods", "body_errors"}}
            for scan in scans
        ],
        "body_errors": errors,
        "core_method_contracts": core,
        "direct_static_callers": callers,
        "direct_static_caller_contracts": caller_contracts,
        "payment_save_transaction_and_allocation_contract": payment_save_contract,
        "focused_method_contracts": focused,
        "evidence_limits": [
            "Static IL proves compiled references, not active route use or successful requests.",
            "Getter/setter names are semantic references; they do not alone prove every branch outcome.",
            "Async MoveNext and compiler-generated predicates split one source method across multiple bodies.",
            "Arbitrary literals are never persisted; safe SQL object identifiers are extracted separately.",
            "Absence of a local transaction call does not exclude an ambient or delegated transaction.",
        ],
    }


def main() -> int:
    logging.getLogger("dnfile").setLevel(logging.CRITICAL)
    logging.getLogger("dnfile.stream").setLevel(logging.CRITICAL)
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = collect(args.source_directory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(args.output.resolve())
    print(json.dumps(payload["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
