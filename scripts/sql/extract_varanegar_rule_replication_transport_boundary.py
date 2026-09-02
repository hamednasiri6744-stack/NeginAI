"""Extract Varanegar's deployed rule-replication transport boundary.

Safety properties:
- connects only to the local read-only NeginPakhsh_WebDev clone;
- hash-pins and parses the separate Replication deployment without loading it;
- does not read configuration, archive, log, credential, or business-data files;
- never executes a SQL module, generated replication script, or assembly;
- persists only catalog structure, aggregates, hashes, and allowlisted call names.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any

import dnfile
from dncil.cil.body.reader import read_method_body_from_bytes
from dncil.clr.token import StringToken, Token

from extract_varanegar_org_domain import (
    _assert_safe_target,
    _connect,
    _json_default,
    _rows,
)
from extract_varanegar_voucher_creation_atomicity_policy import (
    _full_type_name,
    _owner_maps,
    _resolve_token,
    _text,
)


EXPECTED_FILES = {
    "VN.Replication.dll": "741f5e4d56b9d5ae22c954a6bce6c62d618d7d62aebc7b9abaf01bae4702047e",
    "VN.ReplicationService.exe": "335a5efb719dead2c39c46c46b61969f73813772783fbaedf8887456278cf213",
    "VaranegarMonitorReplication.exe": "02ac26f49058d13e9717047a3af40e0754e1ad40deb1da489f07c85358eee0c6",
    "FluentFTP.dll": "dabf2f9a7307dfc4d81b2d70fcb079b15bed07d228eae0ae401c07d6df82bf2a",
}

TARGET_METHODS = {
    "VN.Replication.DataLayer.DBConnector": {
        "Execute",
        "ExecuteScalar",
        "BeginTransaction",
        "CommitTransaction",
        "RollBackTransaction",
    },
    "VN.Replication.Helpers.LockHelper": {
        "ControlLock",
        "GetNEWSysTestPass",
        "CheckLockSt",
        "CheckLock",
        "setlockServerName",
        "n1lHseS3qp",
    },
    "ReplicationService.ReplicationService": {"OnStart", "OnStop"},
    "ReplicationService.Program": {"Main"},
    "VaranegarMonitorReplication.Program": {"Main"},
    "VN.Replication.ReplicationServiceLibrary": {
        "Start",
        "InitTimer",
        "Run",
        "Stop",
    },
    "VN.Replication.Helpers.ReplicationHelper": {
        "SendLog",
        "CreateReplicationFile",
        "ReadAndUploadBinaryFile",
        "Replicate",
        "Receive",
        "SendFileFromTransfer",
        "ReceiveLocalReplicationFiles",
        "JustReceiveThisFile",
        "rIJHaMbB5v",
        "ReplicationByFtp",
    },
    "VN.Replication.Helpers.DatabaseHelper": {
        "Execute",
        "ISValidRecordToInsert",
        "InsertToReplicationFileTable",
        "ExecuteLocalFile",
        "InsertLastExecutedlogIdUpdateLog",
        "TryToClearReplicationReceive",
        "ResetReplicationSendTable",
        "GetSiteIdByDCCode",
        "GetCenterIdByCenterCode",
        "GetLastSendId",
        "UpdateLastSendId",
    },
    "VN.Replication.Helpers.FTPHelper": {
        "ConnectToFtpServer",
        "TrustFTPAddress",
        "SendFiles",
        "ReceiveReplicationFiles",
        "ExecuteBatchScript",
        "UploadFile",
        "UploadCompleteFtp",
        "fiUHjVtq7n",
        "ftpGetTextDirListing",
    },
    "VN.Replication.Helpers.FileHelper": {
        "ZipFile",
        "SaveTolocal",
        "UploadCompleteByFile",
    },
    "VN.Replication.Helpers.Utilities": {"UnZip"},
}

ALLOWED_CALL_PREFIXES = (
    "VN.Replication.",
    "System.IO.File.",
    "System.IO.Directory.",
    "System.IO.FileStream.",
    "Ionic.Zip.ZipFile.",
    "FluentFTP.FtpClient.",
    "System.Timers.Timer.",
    "System.Threading.Thread.Sleep",
    "System.Threading.Mutex.",
    "System.Threading.Monitor.",
    "System.Threading.Interlocked.",
    "System.Threading.Semaphore.",
    "System.Threading.SemaphoreSlim.",
    "System.Threading.ReaderWriterLockSlim.",
    "System.Diagnostics.Process.",
    "System.Security.Cryptography.",
    "System.Data.SqlClient.SqlCommand.",
    "System.Data.SqlClient.SqlConnection.",
    "System.Data.Common.DbCommand.",
    "System.Data.Common.DbConnection.",
    "System.Text.RegularExpressions.Regex.",
    "System.Array.",
    "System.Linq.Enumerable.",
    "System.Collections.Generic.List",
    "System.String.",
)


def _integer_constant(instruction: Any) -> int | None:
    fixed = {
        "ldc.i4.m1": -1,
        "ldc.i4.0": 0,
        "ldc.i4.1": 1,
        "ldc.i4.2": 2,
        "ldc.i4.3": 3,
        "ldc.i4.4": 4,
        "ldc.i4.5": 5,
        "ldc.i4.6": 6,
        "ldc.i4.7": 7,
        "ldc.i4.8": 8,
    }
    if instruction.mnemonic in fixed:
        return fixed[instruction.mnemonic]
    if instruction.mnemonic in {"ldc.i4", "ldc.i4.s"} and isinstance(
        instruction.operand, int
    ):
        return instruction.operand
    return None


def _fluentftp_default_contract(path: Path) -> dict[str, Any]:
    pe = dnfile.dnPE(str(path))
    assembly = pe.net.mdtables.Assembly.rows[0]
    field_rids: dict[str, int] = {}
    client_type = None
    for type_row in pe.net.mdtables.TypeDef.rows:
        name = _full_type_name(type_row)
        if name == "FluentFTP.FtpEncryptionMode":
            field_rids = {
                _text(field.row.Name): field.row_index
                for field in type_row.FieldList or []
            }
        elif name == "FluentFTP.FtpClient":
            client_type = type_row
    constants: dict[int, int] = {}
    for row in pe.net.mdtables.Constant.rows:
        parent = getattr(row, "Parent", None)
        parent_rid = getattr(parent, "row_index", None)
        value = getattr(row.Value, "value", b"")
        if parent_rid is not None and value:
            constants[parent_rid] = int.from_bytes(value, "little", signed=True)
    if client_type is None:
        raise RuntimeError("FluentFTP.FtpClient metadata missing")
    method_owners, field_owners = _owner_maps(pe)
    constructors = []
    for method_index in client_type.MethodList or []:
        method = method_index.row
        if _text(method.Name) != ".ctor" or not method.Rva:
            continue
        body = read_method_body_from_bytes(pe.get_data(method.Rva, 65536))
        field_writes = []
        for instruction in body.instructions:
            if instruction.mnemonic == "stfld" and isinstance(
                instruction.operand, Token
            ):
                field_writes.append(
                    _resolve_token(pe, instruction.operand, method_owners, field_owners)
                )
        constructors.append(
            {
                "rva": int(method.Rva),
                "instruction_count": len(body.instructions),
                "sets_encryption_mode": any(
                    row.endswith(".m_encryptionmode") for row in field_writes
                ),
                "sets_validate_any_certificate": any(
                    row.endswith(".m_ValidateAnyCertificate") for row in field_writes
                ),
                "sets_ssl_protocols": any(
                    row.endswith(".m_SslProtocols") for row in field_writes
                ),
            }
        )
    return {
        "assembly_version": ".".join(
            str(value)
            for value in (
                assembly.MajorVersion,
                assembly.MinorVersion,
                assembly.BuildNumber,
                assembly.RevisionNumber,
            )
        ),
        "encryption_mode_enum": {
            name: constants.get(rid) for name, rid in field_rids.items() if name != "value__"
        },
        "constructor_count": len(constructors),
        "constructor_sets_encryption_mode_count": sum(
            row["sets_encryption_mode"] for row in constructors
        ),
        "constructor_sets_validate_any_certificate_count": sum(
            row["sets_validate_any_certificate"] for row in constructors
        ),
        "constructor_sets_ssl_protocols_count": sum(
            row["sets_ssl_protocols"] for row in constructors
        ),
        "raw_library_strings_persisted": 0,
    }


def _method_contracts(path: Path) -> dict[str, Any]:
    pe = dnfile.dnPE(str(path))
    if pe.net is None:
        raise RuntimeError(f"Expected managed assembly: {path.name}")
    method_owners, field_owners = _owner_maps(pe)
    candidates: dict[tuple[str, str], list[dict[str, Any]]] = {}
    parse_errors = 0
    for type_row in pe.net.mdtables.TypeDef.rows:
        type_name = _full_type_name(type_row)
        if type_name not in TARGET_METHODS:
            continue
        for method_index in type_row.MethodList or []:
            method = method_index.row
            method_name = _text(method.Name)
            if method_name not in TARGET_METHODS[type_name] or not method.Rva:
                continue
            try:
                body = read_method_body_from_bytes(pe.get_data(method.Rva, 131072))
            except Exception:
                parse_errors += 1
                continue
            instructions = list(body.instructions)
            calls: list[dict[str, Any]] = []
            literal_values: list[str] = []
            command_timeout_constants: list[int] = []
            timer_enabled_constants: list[int] = []
            signature = bytes(method.Signature.value)
            for index, instruction in enumerate(instructions):
                if isinstance(instruction.operand, StringToken):
                    literal_values.append(
                        _text(pe.net.user_strings.get(instruction.operand.rid).value)
                    )
                if instruction.mnemonic not in {"call", "callvirt", "newobj"}:
                    continue
                if not isinstance(instruction.operand, Token):
                    continue
                resolved = _resolve_token(
                    pe, instruction.operand, method_owners, field_owners
                )
                if resolved.startswith(ALLOWED_CALL_PREFIXES):
                    if resolved.endswith("DbCommand.set_CommandTimeout") and index > 0:
                        timeout_value = _integer_constant(instructions[index - 1])
                        if timeout_value is not None:
                            command_timeout_constants.append(timeout_value)
                    if resolved.endswith("Timer.set_Enabled") and index > 0:
                        enabled_value = _integer_constant(instructions[index - 1])
                        if enabled_value is not None:
                            timer_enabled_constants.append(enabled_value)
                    table = pe.net.mdtables.tables.get(instruction.operand.table)
                    called_signature = b""
                    if (
                        table is not None
                        and 0 < instruction.operand.rid <= len(table.rows)
                    ):
                        called_row = table.rows[instruction.operand.rid - 1]
                        signature_value = getattr(
                            getattr(called_row, "Signature", None), "value", b""
                        )
                        called_signature = bytes(signature_value or b"")
                    calls.append(
                        {
                            "instruction_index": index,
                            "call": resolved,
                            "next_mnemonic": instructions[index + 1].mnemonic
                            if index + 1 < len(instructions)
                            else None,
                            "called_signature_signals": {
                                "single_string_parameter": len(called_signature) >= 3
                                and called_signature[1] == 1
                                and called_signature[-1] == 0x0E,
                                "signature_blob_persisted": False,
                            },
                        }
                    )
            mnemonics = [instruction.mnemonic for instruction in instructions]
            return_indexes = [
                index for index, mnemonic in enumerate(mnemonics) if mnemonic == "ret"
            ]
            candidates.setdefault((type_name, method_name), []).append(
                {
                    "type": type_name,
                    "method": method_name,
                    "rva": int(method.Rva),
                    "instruction_count": len(body.instructions),
                    "branch_instruction_count": sum(
                        item.startswith("br")
                        or item in {"leave", "leave.s", "switch"}
                        for item in mnemonics
                    ),
                    "exception_handler_count": len(
                        getattr(body, "exception_handlers", []) or []
                    ),
                    "allowlisted_calls": calls,
                    "literal_signals": {
                        "mentions_replication_file": any(
                            "replicationfile" in value.casefold()
                            for value in literal_values
                        ),
                        "contains_delete_verb": any(
                            re.search(r"\bdelete\b", value, re.IGNORECASE)
                            for value in literal_values
                        ),
                        "contains_update_verb": any(
                            re.search(r"\bupdate\b", value, re.IGNORECASE)
                            for value in literal_values
                        ),
                    },
                    "signature_signals": {
                        "returns_boolean": len(signature) >= 3
                        and signature[2] == 0x02,
                        "single_string_parameter_returning_int32": len(signature) >= 4
                        and signature[1] == 1
                        and signature[2] == 0x08
                        and signature[3] == 0x0E,
                        "signature_blob_persisted": False,
                    },
                    "return_signals": {
                        "immediate_false_return_count": sum(
                            index > 0 and mnemonics[index - 1] == "ldc.i4.0"
                            for index in return_indexes
                        ),
                        "immediate_true_return_count": sum(
                            index > 0 and mnemonics[index - 1] == "ldc.i4.1"
                            for index in return_indexes
                        ),
                        "tail_local_is_assigned_false_before_return": len(mnemonics) >= 5
                        and mnemonics[-5:] == [
                            "ldc.i4.0",
                            "stloc.s",
                            "leave",
                            "ldloc.s",
                            "ret",
                        ],
                        "local_true_assignment_before_leave_count": sum(
                            mnemonics[index : index + 3]
                            == ["ldc.i4.1", "stloc.1", "leave"]
                            for index in range(max(0, len(mnemonics) - 2))
                        ),
                        "local_false_assignment_before_leave_count": sum(
                            mnemonics[index : index + 3]
                            == ["ldc.i4.0", "stloc.1", "leave"]
                            for index in range(max(0, len(mnemonics) - 2))
                        ),
                    },
                    "throw_instruction_count": sum(
                        mnemonic in {"throw", "rethrow"} for mnemonic in mnemonics
                    ),
                    "command_timeout_constant_values": sorted(
                        set(command_timeout_constants)
                    ),
                    "timer_enabled_constant_values": sorted(
                        set(timer_enabled_constants)
                    ),
                    "delegates_to_same_method_with_trailing_false": any(
                        row["instruction_index"] > 0
                        and row["call"] == f"{type_name}.{method_name}"
                        and mnemonics[row["instruction_index"] - 1] == "ldc.i4.0"
                        for row in calls
                    ),
                    "string_literal_values_persisted": 0,
                }
            )

    selected: dict[str, Any] = {}
    for (type_name, method_name), overloads in sorted(candidates.items()):
        # Tiny overloads only delegate to the substantial implementation. Keeping the
        # largest body makes the ordering contract deterministic without signatures.
        contract = max(overloads, key=lambda row: row["instruction_count"])
        contract["overload_candidate_count"] = len(overloads)
        contract["overload_with_trailing_false_delegate_count"] = sum(
            row["delegates_to_same_method_with_trailing_false"]
            for row in overloads
        )
        selected[f"{type_name}.{method_name}"] = contract
    return {
        "method_contracts": selected,
        "method_body_parse_error_count": parse_errors,
    }


def _positions(contract: dict[str, Any], suffix: str) -> list[int]:
    return [
        row["instruction_index"]
        for row in contract["allowlisted_calls"]
        if row["call"].endswith(suffix)
    ]


def _first(contract: dict[str, Any], suffix: str) -> int | None:
    positions = _positions(contract, suffix)
    return positions[0] if positions else None


def _first_after(
    contract: dict[str, Any], suffix: str, after: int | None
) -> int | None:
    if after is None:
        return None
    return next(
        (position for position in _positions(contract, suffix) if position > after),
        None,
    )


def _first_call_next_mnemonic(
    contract: dict[str, Any], suffix: str
) -> str | None:
    return next(
        (
            row["next_mnemonic"]
            for row in contract["allowlisted_calls"]
            if row["call"].endswith(suffix)
        ),
        None,
    )


def _first_call_signature_signal(
    contract: dict[str, Any], suffix: str, signal: str
) -> bool:
    return next(
        (
            bool(row["called_signature_signals"][signal])
            for row in contract["allowlisted_calls"]
            if row["call"].endswith(suffix)
        ),
        False,
    )


def _ordered(*positions: int | None) -> bool:
    return all(value is not None for value in positions) and list(positions) == sorted(
        positions
    )


def _deletes_table(definition: str, schema: str, table: str) -> bool:
    folded = " ".join(definition.casefold().split())
    target = (
        rf"\[?{re.escape(schema.casefold())}\]?\s*\.\s*"
        rf"\[?{re.escape(table.casefold())}\]?(?![\w])"
    )
    return any(
        re.search(pattern, folded) is not None
        for pattern in (
            rf"\bdelete\s+from\s+{target}",
            rf"\bdelete\s+{target}",
            rf"\bdelete\s+\[?\w+\]?\s+from\s+{target}",
            rf"\btruncate\s+table\s+{target}",
        )
    )


def _sql_contract(cursor: Any) -> dict[str, Any]:
    module_names = (
        "ReplicationData",
        "ReplicationReceive",
        "InsteadInsertTriggerReplicationReceive",
        "usp_GetLogRcv",
        "usp_Replication_GeneratePack",
        "trg_tblLogRcv_CheckValidation",
        "usp_ReplicationAfterReciveAll",
        "USP_VSA_SortTblLog",
        "uspSetIdentityColValue",
        "usp_Replication_ClearReplicationReceive",
    )
    placeholders = ",".join("%s" for _ in module_names)
    modules = _rows(
        cursor,
        f"""
        SELECT s.name schema_name,o.name object_name,o.type_desc,
               m.execute_as_principal_id,o.principal_id object_principal_id,
               m.definition
        FROM sys.sql_modules m JOIN sys.objects o ON o.object_id=m.object_id
        JOIN sys.schemas s ON s.schema_id=o.schema_id
        WHERE o.name IN ({placeholders}) ORDER BY s.name,o.name
        """,
        module_names,
    )
    module_contracts = []
    receipt_trigger_contract: dict[str, Any] = {}
    post_receive_contract: dict[str, Any] = {}
    log_retention_contract: dict[str, Any] = {}
    clear_receive_contract: dict[str, Any] = {}
    for row in modules:
        definition = row.pop("definition") or ""
        folded = " ".join(definition.casefold().split())
        module_contracts.append(
            row
            | {
                "reads_generated_script": "script" in folded
                and "tbllog" in folded,
                "writes_receive_receipt": "insert into gnr.tbllogrcv" in folded,
                "records_last_exec_log": "lastexeclog" in folded,
                "owns_explicit_transaction": "begin tran" in folded,
                "has_try_catch": "begin try" in folded and "begin catch" in folded,
                "has_rollback": "rollback" in folded,
                "has_insert": bool(re.search(r"\binsert\b", folded)),
                "has_update": bool(re.search(r"\bupdate\b", folded)),
                "has_delete": bool(re.search(r"\bdelete\b", folded)),
                "has_merge": bool(re.search(r"\bmerge\b", folded)),
                "has_dynamic_execute": "sp_executesql" in folded
                or "exec(" in folded
                or "execute(" in folded,
                "uses_nolock": "nolock" in folded,
                "definition_sha256": hashlib.sha256(
                    definition.encode("utf-8")
                ).hexdigest(),
                "definition_persisted": False,
            }
        )
        if row["object_name"] == "trg_tblLogRcv_CheckValidation":
            compact = "".join(definition.casefold().split())
            receipt_trigger_contract = {
                "rejects_start_greater_than_end": "if@startlog>@endlog" in compact,
                "rejects_end_watermark_regression": "if@endlog<@previousendlog" in compact,
                "rejects_last_exec_watermark_regression": "if@lastexeclog<@previouslastexeclog" in compact,
                "rejects_equal_end_or_last_exec_replay": "@endlog<=@previousendlog" in compact
                or "@lastexeclog<=@previouslastexeclog" in compact,
                "enforces_next_start_equals_previous_end_plus_one": "@startlog=@previousendlog+1" in compact
                or "@startlog<>@previousendlog+1" in compact,
                "uses_scalar_assignment_from_inserted": "frominserted" in compact
                and "select@id=id" in compact,
                "writes_insert_history": "insertintognr.tbllogrcvlog" in compact,
                "writes_delete_history": "insertintognr.tbllogrcvlogdelete" in compact,
                "can_synthesize_local_log_successor": "insertintognr.tbllog(id,script" in compact,
                "uses_nolock_for_local_log_reads": "fromgnr.tbllogwith(nolock)" in compact,
                "definition_persisted": False,
            }
        if row["object_name"] == "usp_ReplicationAfterReciveAll":
            post_receive_contract |= {
                "has_insert": bool(re.search(r"\binsert\b", folded)),
                "has_update": bool(re.search(r"\bupdate\b", folded)),
                "has_delete": bool(re.search(r"\bdelete\b", folded)),
                "has_merge": bool(re.search(r"\bmerge\b", folded)),
                "has_dynamic_execute": "sp_executesql" in folded
                or "exec(" in folded
                or "execute(" in folded,
                "owns_explicit_transaction": "begin tran" in folded,
                "has_try_catch": "begin try" in folded and "begin catch" in folded,
                "has_rollback": "rollback" in folded,
                "uses_nolock": "nolock" in folded,
                "definition_persisted": False,
            }
        if row["object_name"] == "uspSetIdentityColValue":
            post_receive_contract |= {
                "identity_hook_has_insert": bool(
                    re.search(r"\binsert\b", folded)
                ),
                "identity_hook_has_dynamic_execute": "sp_executesql" in folded
                or "exec(" in folded
                or "execute(" in folded,
                "identity_hook_mentions_identity_insert": "identity_insert"
                in folded,
                "identity_hook_mentions_dbcc_checkident": "checkident" in folded,
                "identity_hook_uses_quotename": "quotename" in folded,
                "identity_hook_owns_explicit_transaction": "begin tran" in folded,
                "identity_hook_has_try_catch": "begin try" in folded
                and "begin catch" in folded,
            }
        if row["object_name"] == "USP_VSA_SortTblLog":
            post_receive_contract |= {
                "log_sort_hook_has_update": bool(
                    re.search(r"\bupdate\b", folded)
                ),
                "log_sort_hook_has_delete": bool(
                    re.search(r"\bdelete\b", folded)
                ),
                "log_sort_hook_owns_explicit_transaction": "begin tran" in folded,
                "log_sort_hook_has_try_catch": "begin try" in folded
                and "begin catch" in folded,
                "log_sort_hook_has_rollback": "rollback" in folded,
                "log_sort_hook_uses_nolock": "nolock" in folded,
            }
            compact = "".join(definition.casefold().split())
            log_retention_contract = {
                "deletes_from_main_log": _deletes_table(
                    definition, "gnr", "tblLog"
                ),
                "deletes_from_receive_receipt": _deletes_table(
                    definition, "gnr", "tblLogRcv"
                ),
                "uses_receive_last_exec_watermark": "lastexeclog" in compact,
                "uses_minimum_aggregate": "min(" in compact,
                "uses_maximum_aggregate": "max(" in compact,
                "mentions_replication_error": "replicationerror" in compact,
                "mentions_dbcc_checkident": "checkident" in compact,
                "mentions_identity_insert": "identity_insert" in compact,
                "uses_nolock": "nolock" in compact,
                "owns_explicit_transaction": "begintran" in compact
                or "begintransaction" in compact,
                "has_try_catch": "begintry" in compact and "begincatch" in compact,
                "has_rollback": "rollback" in compact,
                "definition_persisted": False,
            }
        if row["object_name"] == "usp_Replication_ClearReplicationReceive":
            compact = "".join(definition.casefold().split())
            clear_receive_contract = {
                "deletes_from_main_log": _deletes_table(
                    definition, "gnr", "tblLog"
                ),
                "deletes_from_receive_receipt": _deletes_table(
                    definition, "gnr", "tblLogRcv"
                ),
                "uses_receive_last_exec_watermark": "lastexeclog" in compact,
                "uses_minimum_aggregate": "min(" in compact,
                "uses_maximum_aggregate": "max(" in compact,
                "uses_date_cutoff": "dateadd(" in compact
                or "datediff(" in compact
                or "getdate(" in compact,
                "owns_explicit_transaction": "begin tran" in folded,
                "has_try_catch": "begin try" in folded
                and "begin catch" in folded,
                "has_rollback": "rollback" in folded,
                "definition_persisted": False,
            }

    dependencies = _rows(
        cursor,
        f"""
        SELECT rs.name referencing_schema,ro.name referencing_object,
               d.referenced_class_desc,
               COALESCE(OBJECT_SCHEMA_NAME(d.referenced_id),d.referenced_schema_name)
                   referenced_schema_name,
               COALESCE(OBJECT_NAME(d.referenced_id),d.referenced_entity_name)
                   referenced_entity_name,
               d.is_ambiguous
        FROM sys.sql_expression_dependencies d
        JOIN sys.objects ro ON ro.object_id=d.referencing_id
        JOIN sys.schemas rs ON rs.schema_id=ro.schema_id
        WHERE ro.name IN ({placeholders})
        ORDER BY rs.name,ro.name,d.referenced_schema_name,d.referenced_entity_name
        """,
        module_names,
    )
    object_permissions = _rows(
        cursor,
        f"""
        SELECT s.name schema_name,o.name object_name,pr.type_desc grantee_type_desc,
               dp.permission_name,dp.state_desc,COUNT_BIG(*) grant_record_count
        FROM sys.database_permissions dp
        JOIN sys.objects o ON o.object_id=dp.major_id AND dp.class=1
        JOIN sys.schemas s ON s.schema_id=o.schema_id
        JOIN sys.database_principals pr ON pr.principal_id=dp.grantee_principal_id
        WHERE o.name IN ({placeholders})
        GROUP BY s.name,o.name,pr.type_desc,dp.permission_name,dp.state_desc
        ORDER BY s.name,o.name,pr.type_desc,dp.permission_name,dp.state_desc
        """,
        module_names,
    )
    schema_database_permissions = _rows(
        cursor,
        """
        SELECT dp.class_desc,
               CASE WHEN dp.class=3 THEN s.name ELSE NULL END schema_name,
               pr.type_desc grantee_type_desc,dp.permission_name,dp.state_desc,
               COUNT_BIG(*) grant_record_count
        FROM sys.database_permissions dp
        JOIN sys.database_principals pr ON pr.principal_id=dp.grantee_principal_id
        LEFT JOIN sys.schemas s ON dp.class=3 AND s.schema_id=dp.major_id
        WHERE dp.class=0 OR (dp.class=3 AND s.name IN ('dbo','GNR'))
        GROUP BY dp.class_desc,CASE WHEN dp.class=3 THEN s.name ELSE NULL END,
                 pr.type_desc,dp.permission_name,dp.state_desc
        ORDER BY dp.class_desc,schema_name,pr.type_desc,dp.permission_name,dp.state_desc
        """,
    )
    dml_dependencies = _rows(
        cursor,
        """
        SELECT 'dbo' referencing_schema,'USP_VSA_SortTblLog' referencing_object,
               referenced_schema_name,referenced_entity_name,is_selected,is_updated,
               is_select_all,is_all_columns_found
        FROM sys.dm_sql_referenced_entities('dbo.USP_VSA_SortTblLog','OBJECT')
        UNION ALL
        SELECT 'GNR','uspSetIdentityColValue',referenced_schema_name,
               referenced_entity_name,is_selected,is_updated,is_select_all,
               is_all_columns_found
        FROM sys.dm_sql_referenced_entities('GNR.uspSetIdentityColValue','OBJECT')
        ORDER BY referencing_schema,referencing_object,referenced_schema_name,
                 referenced_entity_name
        """,
    )
    log_delete_modules = _rows(
        cursor,
        """
        SELECT s.name schema_name,o.name object_name,o.type_desc,m.definition
        FROM sys.sql_modules m
        JOIN sys.objects o ON o.object_id=m.object_id
        JOIN sys.schemas s ON s.schema_id=o.schema_id
        WHERE m.definition LIKE '%tblLog%'
          AND (m.definition LIKE '%delete%' OR m.definition LIKE '%truncate%')
        ORDER BY s.name,o.name
        """,
    )
    log_retention_candidates = []
    for row in log_delete_modules:
        definition = row.pop("definition") or ""
        folded = " ".join(definition.casefold().split())
        compact = "".join(definition.casefold().split())
        exact_main_delete = _deletes_table(definition, "gnr", "tblLog")
        if exact_main_delete:
            log_retention_candidates.append(
                row
                | {
                    "exact_main_log_delete_or_truncate": True,
                    "owns_explicit_transaction": "begin tran" in folded,
                    "has_try_catch": "begin try" in folded
                    and "begin catch" in folded,
                    "has_rollback": "rollback" in folded,
                    "definition_sha256": hashlib.sha256(
                        definition.encode("utf-8")
                    ).hexdigest(),
                    "definition_persisted": False,
                }
            )

    table_names = (
        "ReplicationFile",
        "ReplicationSend",
        "ReplicationError",
        "ReplicationException",
        "tblLogRcv",
        "tblLogSnd",
        "ColValueTable",
        "tblServerConfig",
    )
    table_placeholders = ",".join("%s" for _ in table_names)
    columns = _rows(
        cursor,
        f"""
        SELECT s.name schema_name,t.name table_name,c.column_id,c.name column_name,
               ty.name data_type,c.is_nullable,c.is_identity
        FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id
        JOIN sys.columns c ON c.object_id=t.object_id
        JOIN sys.types ty ON ty.user_type_id=c.user_type_id
        WHERE t.name IN ({table_placeholders})
        ORDER BY s.name,t.name,c.column_id
        """,
        table_names,
    )
    indexes = _rows(
        cursor,
        f"""
        SELECT s.name schema_name,t.name table_name,i.name index_name,
               i.is_unique,i.is_primary_key,i.is_disabled,i.has_filter,
               ic.key_ordinal,ic.is_included_column,c.name column_name
        FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id
        JOIN sys.indexes i ON i.object_id=t.object_id
        JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id
        JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
        WHERE t.name IN ({table_placeholders})
        ORDER BY s.name,t.name,i.index_id,ic.key_ordinal,ic.index_column_id
        """,
        table_names,
    )
    counts = _rows(
        cursor,
        """
        SELECT 'dbo.ReplicationFile' object_name,COUNT_BIG(*) retained_rows FROM dbo.ReplicationFile
        UNION ALL SELECT 'dbo.ReplicationSend',COUNT_BIG(*) FROM dbo.ReplicationSend
        UNION ALL SELECT 'dbo.ReplicationError',COUNT_BIG(*) FROM dbo.ReplicationError
        UNION ALL SELECT 'dbo.ReplicationException',COUNT_BIG(*) FROM dbo.ReplicationException
        UNION ALL SELECT 'GNR.tblLogRcv',COUNT_BIG(*) FROM GNR.tblLogRcv
        UNION ALL SELECT 'GNR.tblLogSnd',COUNT_BIG(*) FROM GNR.tblLogSnd
        ORDER BY object_name
        """,
    )
    identity_configuration_quality = _rows(
        cursor,
        """
        WITH ConfigRows AS (
            SELECT NAME table_token,ColName column_token
            FROM dbo.ColvalueTable
        ), Resolved AS (
            SELECT c.table_token,c.column_token,
                   x.table_match_count,x.column_match_count,x.identity_match_count
            FROM ConfigRows c
            OUTER APPLY (
                SELECT COUNT(DISTINCT t.object_id) table_match_count,
                       COUNT(DISTINCT CASE WHEN col.column_id IS NOT NULL
                                           THEN t.object_id END) column_match_count,
                       COUNT(DISTINCT CASE WHEN col.is_identity=1
                                           THEN t.object_id END) identity_match_count
                FROM sys.tables t
                LEFT JOIN sys.columns col ON col.object_id=t.object_id
                     AND col.name=c.column_token
                WHERE t.name=c.table_token
            ) x
        ), DuplicateShapes AS (
            SELECT table_token,column_token,COUNT_BIG(*) row_count
            FROM ConfigRows GROUP BY table_token,column_token
        )
        SELECT COUNT_BIG(*) configured_row_count,
               COALESCE(SUM(CASE WHEN table_token IS NULL OR LTRIM(RTRIM(table_token))=''
                         THEN 1 ELSE 0 END),0) blank_table_token_count,
               COALESCE(SUM(CASE WHEN column_token IS NULL OR LTRIM(RTRIM(column_token))=''
                         THEN 1 ELSE 0 END),0) blank_column_token_count,
               COALESCE(SUM(CASE WHEN table_token LIKE '%;%' OR table_token LIKE '%--%'
                              OR table_token LIKE '%/*%' OR table_token LIKE '%''%'
                              OR column_token LIKE '%;%' OR column_token LIKE '%--%'
                              OR column_token LIKE '%/*%' OR column_token LIKE '%''%'
                         THEN 1 ELSE 0 END),0) obvious_sql_token_count,
               COALESCE(SUM(CASE WHEN table_match_count=0 THEN 1 ELSE 0 END),0)
                   unresolved_table_token_count,
               COALESCE(SUM(CASE WHEN table_match_count>1 THEN 1 ELSE 0 END),0)
                   ambiguous_table_token_count,
               COALESCE(SUM(CASE WHEN table_match_count>0 AND column_match_count=0
                         THEN 1 ELSE 0 END),0) unresolved_column_token_count,
               COALESCE(SUM(CASE WHEN identity_match_count=1 THEN 1 ELSE 0 END),0)
                   exact_identity_match_count,
               COALESCE(SUM(CASE WHEN column_match_count>0 AND identity_match_count=0
                         THEN 1 ELSE 0 END),0) non_identity_column_match_count,
               (SELECT COUNT_BIG(*) FROM DuplicateShapes WHERE row_count>1)
                   duplicate_table_column_shape_count
        FROM Resolved
        """,
    )[0]
    column_sets: dict[str, set[str]] = {}
    for row in columns:
        key = f"{row['schema_name']}.{row['table_name']}"
        column_sets.setdefault(key, set()).add(row["column_name"].casefold())
    unique_index_columns: dict[tuple[str, str], list[str]] = {}
    for row in indexes:
        if row["is_unique"] and not row["is_disabled"] and not row["is_included_column"]:
            key = (f"{row['schema_name']}.{row['table_name']}", row["index_name"])
            unique_index_columns.setdefault(key, []).append(row["column_name"].casefold())
    unique_shapes = {
        table: [columns for (name, _), columns in unique_index_columns.items() if name == table]
        for table in column_sets
    }
    return {
        "module_contracts": module_contracts,
        "table_columns": columns,
        "table_indexes": indexes,
        "retained_row_counts": counts,
        "identity_configuration_quality": identity_configuration_quality,
        "receipt_trigger_contract": receipt_trigger_contract,
        "post_receive_contract": post_receive_contract,
        "log_retention_contract": log_retention_contract,
        "clear_receive_contract": clear_receive_contract,
        "module_dependencies": dependencies,
        "object_permission_aggregates": object_permissions,
        "schema_database_permission_aggregates": schema_database_permissions,
        "post_receive_dml_dependencies": dml_dependencies,
        "main_log_retention_candidates": log_retention_candidates,
        "structural_signals": {
            "replication_file_is_binary_outbox": {
                "filename",
                "filecontent",
                "insertdate",
            }.issubset(column_sets.get("dbo.ReplicationFile", set())),
            "replication_send_has_center_watermark": {
                "centerid",
                "sendid",
            }.issubset(column_sets.get("dbo.ReplicationSend", set())),
            "receive_receipt_has_range_and_last_exec": {
                "startlog",
                "endlog",
                "lastexeclog",
                "siteref",
            }.issubset(column_sets.get("GNR.tblLogRcv", set())),
            "receive_receipt_has_success_or_checksum": any(
                token in column_sets.get("GNR.tblLogRcv", set())
                for token in ("success", "status", "checksum", "hash")
            ),
            "replication_file_has_unique_filename": ["filename"]
            in unique_shapes.get("dbo.ReplicationFile", []),
            "replication_send_has_unique_center": ["centerid"]
            in unique_shapes.get("dbo.ReplicationSend", []),
            "receive_receipt_has_unique_site_range": any(
                set(shape) >= {"siteref", "startlog", "endlog"}
                for shape in unique_shapes.get("GNR.tblLogRcv", [])
            ),
        },
    }


def collect(replication_directory: Path) -> dict[str, Any]:
    binaries = []
    parsed: dict[str, Any] = {}
    for file_name, expected_hash in EXPECTED_FILES.items():
        path = replication_directory / file_name
        data = path.read_bytes()
        actual_hash = hashlib.sha256(data).hexdigest()
        if actual_hash != expected_hash:
            raise RuntimeError(f"Hash drift for {file_name}")
        binaries.append(
            {
                "file": file_name,
                "size_bytes": len(data),
                "sha256": actual_hash,
            }
        )
        parsed[file_name] = _method_contracts(path)

    core = parsed["VN.Replication.dll"]["method_contracts"]
    replicate = core["VN.Replication.Helpers.ReplicationHelper.Replicate"]
    send_log = core["VN.Replication.Helpers.ReplicationHelper.SendLog"]
    upload = core[
        "VN.Replication.Helpers.ReplicationHelper.ReadAndUploadBinaryFile"
    ]
    post_upload_database_ack = core[
        "VN.Replication.Helpers.ReplicationHelper.rIJHaMbB5v"
    ]
    ftp_upload = core["VN.Replication.Helpers.FTPHelper.UploadFile"]
    ftp_complete = core["VN.Replication.Helpers.FTPHelper.UploadCompleteFtp"]
    local_save = core["VN.Replication.Helpers.FileHelper.SaveTolocal"]
    local_complete = core[
        "VN.Replication.Helpers.FileHelper.UploadCompleteByFile"
    ]
    local_receive = core[
        "VN.Replication.Helpers.DatabaseHelper.ExecuteLocalFile"
    ]
    local_listing = core[
        "VN.Replication.Helpers.ReplicationHelper.ReceiveLocalReplicationFiles"
    ]
    ftp_receive = core[
        "VN.Replication.Helpers.FTPHelper.ReceiveReplicationFiles"
    ]
    ftp_listing = core[
        "VN.Replication.Helpers.FTPHelper.ftpGetTextDirListing"
    ]
    ftp_connect = core[
        "VN.Replication.Helpers.FTPHelper.ConnectToFtpServer"
    ]
    zip_create = core["VN.Replication.Helpers.FileHelper.ZipFile"]
    zip_extract = core["VN.Replication.Helpers.Utilities.UnZip"]
    package_execute = core["VN.Replication.Helpers.DatabaseHelper.Execute"]
    connector_execute = core["VN.Replication.DataLayer.DBConnector.Execute"]
    connector_commit = core[
        "VN.Replication.DataLayer.DBConnector.CommitTransaction"
    ]
    connector_rollback = core[
        "VN.Replication.DataLayer.DBConnector.RollBackTransaction"
    ]
    receipt_writer = core[
        "VN.Replication.Helpers.DatabaseHelper.InsertLastExecutedlogIdUpdateLog"
    ]
    reset_send = core[
        "VN.Replication.Helpers.DatabaseHelper.ResetReplicationSendTable"
    ]
    record_validator = core[
        "VN.Replication.Helpers.DatabaseHelper.ISValidRecordToInsert"
    ]
    get_site = core[
        "VN.Replication.Helpers.DatabaseHelper.GetSiteIdByDCCode"
    ]
    get_center = core[
        "VN.Replication.Helpers.DatabaseHelper.GetCenterIdByCenterCode"
    ]
    get_last_send = core[
        "VN.Replication.Helpers.DatabaseHelper.GetLastSendId"
    ]
    update_last_send = core[
        "VN.Replication.Helpers.DatabaseHelper.UpdateLastSendId"
    ]
    control_lock = core["VN.Replication.Helpers.LockHelper.ControlLock"]
    check_lock_state = core["VN.Replication.Helpers.LockHelper.CheckLockSt"]
    check_lock = core["VN.Replication.Helpers.LockHelper.CheckLock"]
    set_lock_server = core[
        "VN.Replication.Helpers.LockHelper.setlockServerName"
    ]
    fluentftp = _fluentftp_default_contract(
        replication_directory / "FluentFTP.dll"
    )
    with _connect() as connection:
        cursor = connection.cursor()
        safety = _assert_safe_target(cursor)
        sql = _sql_contract(cursor)

    service_run = core["VN.Replication.ReplicationServiceLibrary.Run"]
    service_init_timer = core[
        "VN.Replication.ReplicationServiceLibrary.InitTimer"
    ]
    service_stop = core["VN.Replication.ReplicationServiceLibrary.Stop"]
    run_receive = _first(service_run, "ReplicationHelper.Receive")
    run_post_receive_script_lookup = _first_after(
        service_run, "DatabaseHelper.GetLogIsActiveScript", run_receive
    )
    run_post_receive_dynamic_execute = _first_after(
        service_run, "DBConnector.Execute", run_post_receive_script_lookup
    )
    service_sequence = {
        "run_receives_before_post_receive_script_lookup": _ordered(
            run_receive, run_post_receive_script_lookup
        ),
        "run_post_receive_script_lookup_precedes_dynamic_execute": _ordered(
            run_post_receive_script_lookup, run_post_receive_dynamic_execute
        ),
        "run_owns_explicit_database_transaction": bool(
            _positions(service_run, "DBConnector.BeginTransaction")
        ),
        "exact_active_post_receive_script_from_configuration_proven": False,
    }
    retention_and_cleanup_boundary = {
        "service_run_calls_receive_cleanup_before_receive": _ordered(
            _first(service_run, "DatabaseHelper.TryToClearReplicationReceive"),
            run_receive,
        ),
        "replicate_calls_receive_cleanup_before_send": _ordered(
            _first(replicate, "DatabaseHelper.TryToClearReplicationReceive"),
            _first(replicate, "ReplicationHelper.SendLog"),
        ),
        "deployed_clear_procedure_deletes_receive_receipts": sql[
            "clear_receive_contract"
        ]["deletes_from_receive_receipt"],
        "deployed_clear_procedure_deletes_main_log": sql[
            "clear_receive_contract"
        ]["deletes_from_main_log"],
        "deployed_clear_procedure_uses_max_last_exec_watermark": sql[
            "clear_receive_contract"
        ]["uses_receive_last_exec_watermark"]
        and sql["clear_receive_contract"]["uses_maximum_aggregate"],
        "deployed_clear_procedure_owns_transaction": sql[
            "clear_receive_contract"
        ]["owns_explicit_transaction"],
        "deployed_clear_procedure_has_try_catch": sql[
            "clear_receive_contract"
        ]["has_try_catch"],
        "exact_helper_to_clear_procedure_binding_proven": False,
        "main_log_delete_candidate_count": len(
            sql["main_log_retention_candidates"]
        ),
        "retained_receive_receipts_are_complete_history_proven": False,
        "retained_main_log_is_complete_history_proven": False,
    }

    send_sequence = {
        "send_log_creates_file_before_outbox_insert": _ordered(
            _first(send_log, "CreateReplicationFile"),
            _first(send_log, "InsertToReplicationFileTable"),
        ),
        "send_log_inserts_outbox_before_watermark_update": _ordered(
            _first(send_log, "InsertToReplicationFileTable"),
            _first(send_log, "UpdateLastSendId"),
        ),
        "replicate_begins_transaction_before_send_log": _ordered(
            _first(replicate, "BeginTransaction"),
            _first(replicate, "SendLog"),
        ),
        "replicate_commits_before_binary_upload": _ordered(
            _first(replicate, "CommitTransaction"),
            _first(replicate, "ReadAndUploadBinaryFile"),
        ),
        "upload_reads_outbox_before_upload": _ordered(
            _first(upload, "ReadDataTable"),
            _first(upload, "UploadFile"),
        ),
        "replicate_has_rollback_path": bool(
            _positions(replicate, "RollBackTransaction")
        ),
    }
    post_upload_ack_positions = _positions(upload, "ReplicationHelper.rIJHaMbB5v")
    outbound_acknowledgement_boundary = {
        "local_copy_precedes_local_completion_marker": _ordered(
            _first(local_save, "File.Copy"),
            _first(local_save, "UploadCompleteByFile"),
        ),
        "local_completion_marker_uses_atomic_move": bool(
            _positions(local_complete, "File.Move")
        ),
        "local_completion_returns_before_database_ack_helper": bool(
            post_upload_ack_positions
        )
        and _ordered(
            _first(upload, "FileHelper.SaveTolocal"),
            post_upload_ack_positions[0],
        ),
        "ftp_upload_precedes_remote_size_read": _ordered(
            _first(ftp_upload, "FtpClient.UploadFile"),
            _first(ftp_upload, "FtpClient.GetFileSize"),
        ),
        "ftp_remote_size_read_precedes_validation_helper": _ordered(
            _first(ftp_upload, "FtpClient.GetFileSize"),
            _first(ftp_upload, "FTPHelper.fiUHjVtq7n"),
        ),
        "ftp_validation_precedes_completion_rename": _ordered(
            _first(ftp_upload, "FTPHelper.fiUHjVtq7n"),
            _first(ftp_upload, "FTPHelper.UploadCompleteFtp"),
        )
        and bool(_positions(ftp_complete, "FtpClient.Rename")),
        "ftp_completion_returns_before_database_ack_helper": len(
            post_upload_ack_positions
        )
        >= 2
        and _ordered(
            max(_positions(upload, "FTPHelper.UploadFile")),
            post_upload_ack_positions[-1],
        ),
        "post_upload_ack_helper_executes_database_command": bool(
            _positions(post_upload_database_ack, "DBConnector.Execute")
        ),
        "post_upload_ack_exact_database_effect_proven": False,
        "remote_content_hash_validation_proven": False,
    }
    receive_sequence = {
        "local_receive_executes_script_before_last_exec_receipt": _ordered(
            _first(local_receive, "DatabaseHelper.Execute"),
            _first(local_receive, "InsertLastExecutedlogIdUpdateLog"),
        ),
        "local_receive_records_receipt_before_commit": _ordered(
            _first(local_receive, "InsertLastExecutedlogIdUpdateLog"),
            _first(local_receive, "CommitTransaction"),
        ),
        "local_receive_has_rollback_paths": bool(
            _positions(local_receive, "RollBackTransaction")
        ),
        "ftp_receive_executes_script_before_last_exec_receipt": _ordered(
            _first(ftp_receive, "DatabaseHelper.Execute"),
            _first(ftp_receive, "InsertLastExecutedlogIdUpdateLog"),
        ),
        "ftp_receive_records_receipt_before_commit": _ordered(
            _first(ftp_receive, "InsertLastExecutedlogIdUpdateLog"),
            _first(ftp_receive, "CommitTransaction"),
        ),
        "ftp_receive_has_rollback_paths": bool(
            _positions(ftp_receive, "RollBackTransaction")
        ),
    }
    ftp_and_package_integrity = {
        "fluentftp_version": fluentftp["assembly_version"],
        "fluentftp_none_encryption_enum_value": fluentftp[
            "encryption_mode_enum"
        ].get("None"),
        "fluentftp_constructor_sets_encryption_mode_count": fluentftp[
            "constructor_sets_encryption_mode_count"
        ],
        "connect_uses_default_ftp_client_constructor": bool(
            _positions(ftp_connect, "FtpClient..ctor")
        ),
        "connect_sets_credentials": bool(
            _positions(ftp_connect, "FtpClient.set_Credentials")
        ),
        "connect_sets_encryption_mode": bool(
            _positions(ftp_connect, "FtpClient.set_EncryptionMode")
        ),
        "connect_sets_ssl_protocols": bool(
            _positions(ftp_connect, "FtpClient.set_SslProtocols")
        ),
        "connect_sets_certificate_validation": any(
            "Certificate" in row["call"] or "ValidateCertificate" in row["call"]
            for row in ftp_connect["allowlisted_calls"]
        ),
        "zip_create_sets_password": bool(
            _positions(zip_create, "ZipFile.set_Password")
        ),
        "zip_extract_sets_password": bool(
            _positions(zip_extract, "ZipFile.set_Password")
        ),
        "named_package_flow_hash_or_signature_call_count": sum(
            "Cryptography" in row["call"]
            or any(
                marker in row["call"]
                for marker in ("ComputeHash", "HMAC", "Signature", "SignData", "VerifyData")
            )
            for contract in core.values()
            for row in contract["allowlisted_calls"]
        ),
        "local_file_share_transport_also_supported": bool(
            _positions(
                core["VN.Replication.Helpers.ReplicationHelper.SendFileFromTransfer"],
                "SendFileFromTransferByFile",
            )
        ),
        "production_transport_mode_read_from_configuration": False,
    }
    package_execution_boundary = {
        "executor_constructs_sql_command": bool(
            _positions(package_execute, "SqlCommand..ctor")
        ),
        "executor_sets_command_text": bool(
            _positions(package_execute, "DbCommand.set_CommandText")
        ),
        "executor_calls_execute_non_query": bool(
            _positions(package_execute, "DbCommand.ExecuteNonQuery")
        ),
        "executor_calls_named_record_validator": bool(
            _positions(package_execute, "ISValidRecordToInsert")
        ),
        "outer_file_path_calls_executor_before_named_record_validator": _ordered(
            _first(local_receive, "DatabaseHelper.Execute"),
            _first(local_receive, "ISValidRecordToInsert"),
        ),
        "named_record_validator_instruction_count": record_validator[
            "instruction_count"
        ],
        "typed_operation_allowlist_proven": False,
        "raw_package_sql_persisted": False,
    }
    executor_outcome_boundary = {
        "executor_returns_boolean": package_execute["signature_signals"][
            "returns_boolean"
        ],
        "executor_has_immediate_false_return": package_execute["return_signals"][
            "immediate_false_return_count"
        ]
        > 0,
        "executor_has_immediate_true_return": package_execute["return_signals"][
            "immediate_true_return_count"
        ]
        > 0,
        "executor_exception_tail_returns_false": package_execute["return_signals"][
            "tail_local_is_assigned_false_before_return"
        ],
        "local_receiver_branches_on_executor_boolean": _first_call_next_mnemonic(
            local_receive, "DatabaseHelper.Execute"
        )
        == "brtrue",
        "ftp_receiver_branches_on_executor_boolean": _first_call_next_mnemonic(
            ftp_receive, "DatabaseHelper.Execute"
        )
        == "brtrue",
        "local_false_path_rolls_back_before_receipt": _ordered(
            _first(local_receive, "DatabaseHelper.Execute"),
            _first_after(
                local_receive,
                "DBConnector.RollBackTransaction",
                _first(local_receive, "DatabaseHelper.Execute"),
            ),
            _first(local_receive, "InsertLastExecutedlogIdUpdateLog"),
        ),
        "ftp_false_path_rolls_back_before_receipt": _ordered(
            _first(ftp_receive, "DatabaseHelper.Execute"),
            _first_after(
                ftp_receive,
                "DBConnector.RollBackTransaction",
                _first(ftp_receive, "DatabaseHelper.Execute"),
            ),
            _first(ftp_receive, "InsertLastExecutedlogIdUpdateLog"),
        ),
    }
    local_execute_call = _first(local_receive, "DatabaseHelper.Execute")
    local_false_rollback = _first_after(
        local_receive, "DBConnector.RollBackTransaction", local_execute_call
    )
    local_success_log_marker = _first_after(
        local_receive, "DatabaseHelper.GetLogIsActiveScript", local_execute_call
    )
    ftp_execute_call = _first(ftp_receive, "DatabaseHelper.Execute")
    ftp_false_rollback = _first_after(
        ftp_receive, "DBConnector.RollBackTransaction", ftp_execute_call
    )
    ftp_success_log_marker = _first_after(
        ftp_receive, "DatabaseHelper.GetLogIsActiveScript", ftp_execute_call
    )
    receive_rejection_disposition_boundary = {
        "local_three_parameter_wrapper_delegates_with_false_flag": local_receive[
            "overload_with_trailing_false_delegate_count"
        ]
        == 1,
        "local_listing_discards_execute_local_file_result": _first_call_next_mnemonic(
            local_listing, "DatabaseHelper.ExecuteLocalFile"
        )
        == "pop",
        "local_false_path_rollback_precedes_cleanup": _ordered(
            local_false_rollback,
            _first_after(local_receive, "File.Delete", local_false_rollback),
        ),
        "local_false_path_file_delete_call_count": sum(
            local_false_rollback is not None
            and local_false_rollback < position < local_success_log_marker
            for position in _positions(local_receive, "File.Delete")
        ),
        "local_false_path_marks_defective_center": _ordered(
            local_false_rollback,
            _first_after(local_receive, "ReplicationHelper.addDefectiveCenter", local_false_rollback),
            local_success_log_marker,
        ),
        "local_false_path_quarantine_move_call_count": sum(
            local_false_rollback is not None
            and local_false_rollback < position < local_success_log_marker
            for position in _positions(local_receive, "File.Move")
        ),
        "ftp_false_path_rollback_precedes_local_cleanup": _ordered(
            ftp_false_rollback,
            _first_after(ftp_receive, "File.Delete", ftp_false_rollback),
        ),
        "ftp_false_path_local_file_delete_call_count": sum(
            ftp_false_rollback is not None
            and ftp_false_rollback < position < ftp_success_log_marker
            for position in _positions(ftp_receive, "File.Delete")
        ),
        "ftp_false_path_remote_delete_call_count": sum(
            ftp_false_rollback is not None
            and ftp_false_rollback < position < ftp_success_log_marker
            for position in _positions(ftp_receive, "FtpClient.DeleteFile")
        ),
        "exact_deleted_file_roles_proven": False,
        "durable_quarantine_receipt_proven": False,
        "retry_safe_rejection_disposition_parity_proven": False,
        "rejected_package_observed_in_runtime": False,
    }
    transaction_error_boundary = {
        "connector_execute_has_exception_handler": connector_execute[
            "exception_handler_count"
        ]
        > 0,
        "connector_execute_rethrows": connector_execute[
            "throw_instruction_count"
        ]
        > 0,
        "receipt_writer_delegates_to_connector_execute": bool(
            _positions(receipt_writer, "DBConnector.Execute")
        ),
        "receipt_writer_has_no_local_exception_handler": receipt_writer[
            "exception_handler_count"
        ]
        == 0,
        "commit_failure_rethrows": connector_commit["exception_handler_count"]
        > 0
        and connector_commit["throw_instruction_count"] > 0,
        "rollback_has_exception_handler": connector_rollback[
            "exception_handler_count"
        ]
        > 0,
        "rollback_failure_rethrows": connector_rollback[
            "throw_instruction_count"
        ]
        > 0,
        "rollback_failure_observability_proven": False,
    }
    package_execution_timeout_boundary = {
        "package_executor_command_timeout_constant_values": package_execute[
            "command_timeout_constant_values"
        ],
        "connector_execute_command_timeout_constant_values": connector_execute[
            "command_timeout_constant_values"
        ],
        "package_executor_has_zero_timeout_constant": 0
        in package_execute["command_timeout_constant_values"],
        "package_executor_maximum_positive_timeout_constant": max(
            (
                value
                for value in package_execute["command_timeout_constant_values"]
                if value > 0
            ),
            default=None,
        ),
        "finite_positive_timeout_on_every_package_execution_path_proven": False,
        "cancellation_or_deadline_propagation_proven": False,
        "long_running_package_execution_observed_in_runtime": False,
    }
    local_receipt_position = _first(
        local_receive, "InsertLastExecutedlogIdUpdateLog"
    )
    ftp_receipt_position = _first(
        ftp_receive, "InsertLastExecutedlogIdUpdateLog"
    )
    local_commit_position = _first(local_receive, "DBConnector.CommitTransaction")
    ftp_commit_position = _first(ftp_receive, "DBConnector.CommitTransaction")
    receive_file_database_atomicity_boundary = {
        "local_archive_copy_occurs_after_receipt_before_commit": _ordered(
            local_receipt_position,
            _first_after(local_receive, "File.Copy", local_receipt_position),
            local_commit_position,
        ),
        "local_file_delete_occurs_after_receipt_before_commit": _ordered(
            local_receipt_position,
            _first_after(local_receive, "File.Delete", local_receipt_position),
            local_commit_position,
        ),
        "ftp_local_file_delete_occurs_after_receipt_before_commit": _ordered(
            ftp_receipt_position,
            _first_after(ftp_receive, "File.Delete", ftp_receipt_position),
            ftp_commit_position,
        ),
        "ftp_remote_file_delete_occurs_after_receipt_before_commit": _ordered(
            ftp_receipt_position,
            _first_after(ftp_receive, "FtpClient.DeleteFile", ftp_receipt_position),
            ftp_commit_position,
        ),
        "commit_failure_rethrows": transaction_error_boundary[
            "commit_failure_rethrows"
        ],
        "filesystem_and_database_share_atomic_commit": False,
        "automatic_retry_from_preserved_input_after_commit_failure_proven": False,
        "commit_failure_window_observed_in_runtime": False,
    }
    post_receive_reset_boundary = {
        "local_reset_runs_after_primary_commit": _ordered(
            local_commit_position,
            _first(local_receive, "DatabaseHelper.ResetReplicationSendTable"),
        ),
        "local_caller_discards_reset_result": _first_call_next_mnemonic(
            local_receive, "DatabaseHelper.ResetReplicationSendTable"
        )
        == "pop",
        "reset_returns_boolean": reset_send["signature_signals"][
            "returns_boolean"
        ],
        "reset_has_true_success_path": reset_send["return_signals"][
            "local_true_assignment_before_leave_count"
        ]
        > 0,
        "reset_has_false_failure_path": reset_send["return_signals"][
            "local_false_assignment_before_leave_count"
        ]
        > 0,
        "reset_owns_transaction_and_commits_two_commands": _ordered(
            _first(reset_send, "DBConnector.BeginTransaction"),
            *_positions(reset_send, "DBConnector.Execute")[:2],
            _first(reset_send, "DBConnector.CommitTransaction"),
        ),
        "reset_has_rollback_path": bool(
            _positions(reset_send, "DBConnector.RollBackTransaction")
        ),
        "exact_reset_sql_effect_proven": False,
        "reset_failure_is_propagated_to_local_receiver": False,
        "reset_failure_observed_in_runtime": False,
    }
    package_center_scope_boundary = {
        "local_site_and_center_lookup_precede_unzip": _ordered(
            _first(local_receive, "DatabaseHelper.GetSiteIdByDCCode"),
            _first(local_receive, "DatabaseHelper.GetCenterIdByCenterCode"),
            _first(local_receive, "Utilities.UnZip"),
        ),
        "ftp_site_and_center_lookup_precede_unzip": _ordered(
            _first(ftp_receive, "DatabaseHelper.GetSiteIdByDCCode"),
            _first(ftp_receive, "DatabaseHelper.GetCenterIdByCenterCode"),
            _first(ftp_receive, "Utilities.UnZip"),
        ),
        "site_lookup_accepts_single_string_and_returns_int32": get_site[
            "signature_signals"
        ]["single_string_parameter_returning_int32"],
        "center_lookup_accepts_single_string_and_returns_int32": get_center[
            "signature_signals"
        ]["single_string_parameter_returning_int32"],
        "site_lookup_concatenates_before_execute_scalar": _ordered(
            _first(get_site, "String.Concat"),
            _first(get_site, "DBConnector.ExecuteScalar"),
        ),
        "center_lookup_concatenates_before_execute_scalar": _ordered(
            _first(get_center, "String.Concat"),
            _first(get_center, "DBConnector.ExecuteScalar"),
        ),
        "lookup_parameterization_proven": False,
        "filename_to_lookup_character_validation_proven": False,
        "local_named_record_validator_runs_before_executor": _ordered(
            _first(local_receive, "ISValidRecordToInsert"),
            _first(local_receive, "DatabaseHelper.Execute"),
        ),
        "ftp_named_record_validator_runs_before_executor": _ordered(
            _first(ftp_receive, "ISValidRecordToInsert"),
            _first(ftp_receive, "DatabaseHelper.Execute"),
        ),
        "cryptographic_center_binding_proven": False,
    }
    retained = {
        row["object_name"]: row["retained_rows"]
        for row in sql["retained_row_counts"]
    }
    receipt_trigger = sql["receipt_trigger_contract"]
    retry_and_concurrency = {
        "outbox_filename_unique_constraint_proven": sql["structural_signals"][
            "replication_file_has_unique_filename"
        ],
        "send_center_watermark_unique_constraint_proven": sql[
            "structural_signals"
        ]["replication_send_has_unique_center"],
        "receive_site_range_unique_constraint_proven": sql[
            "structural_signals"
        ]["receive_receipt_has_unique_site_range"],
        "receipt_rejects_watermark_regression": receipt_trigger[
            "rejects_end_watermark_regression"
        ]
        and receipt_trigger["rejects_last_exec_watermark_regression"],
        "receipt_rejects_equal_replay": receipt_trigger[
            "rejects_equal_end_or_last_exec_replay"
        ],
        "receipt_enforces_gapless_sequence": receipt_trigger[
            "enforces_next_start_equals_previous_end_plus_one"
        ],
        "receipt_trigger_is_multirow_safe": not receipt_trigger[
            "uses_scalar_assignment_from_inserted"
        ],
        "receipt_insert_delete_history_present": receipt_trigger[
            "writes_insert_history"
        ]
        and receipt_trigger["writes_delete_history"],
        "current_snapshot_can_demonstrate_duplicate_or_gap_behavior": retained.get(
            "GNR.tblLogRcv", 0
        )
        > 0,
    }
    sorting_suffixes = (
        "Array.Sort",
        "Enumerable.OrderBy",
        "Enumerable.OrderByDescending",
        "Enumerable.ThenBy",
        "Enumerable.ThenByDescending",
        "List.Sort",
    )
    package_ordering_boundary = {
        "local_receiver_enumerates_directory_files": bool(
            _positions(local_listing, "Directory.GetFiles")
        ),
        "local_receiver_explicit_sort_call_count": sum(
            bool(_positions(local_listing, suffix)) for suffix in sorting_suffixes
        ),
        "ftp_listing_uses_server_get_listing": bool(
            _positions(ftp_listing, "FtpClient.GetListing")
        ),
        "ftp_listing_and_receiver_explicit_sort_call_count": sum(
            bool(_positions(contract, suffix))
            for contract in (ftp_listing, ftp_receive)
            for suffix in sorting_suffixes
        ),
        "receipt_enforces_gapless_sequence": retry_and_concurrency[
            "receipt_enforces_gapless_sequence"
        ],
        "deterministic_range_order_before_execution_proven": False,
        "current_snapshot_can_demonstrate_out_of_order_behavior": retained.get(
            "GNR.tblLogRcv", 0
        )
        > 0,
    }
    lock_contracts = (control_lock, check_lock_state, check_lock, set_lock_server)
    sender_concurrency_boundary = {
        "service_start_calls_named_control_lock": bool(
            _positions(
                core["VN.Replication.ReplicationServiceLibrary.Start"],
                "LockHelper.ControlLock",
            )
        ),
        "service_run_calls_named_control_lock": bool(
            _positions(service_run, "LockHelper.ControlLock")
        ),
        "named_lock_graph_mutex_call_count": sum(
            bool(_positions(contract, "Mutex..ctor"))
            or bool(_positions(contract, "Mutex.WaitOne"))
            for contract in lock_contracts
        ),
        "named_lock_graph_monitor_call_count": sum(
            bool(_positions(contract, "Monitor.Enter"))
            or bool(_positions(contract, "Monitor.TryEnter"))
            for contract in lock_contracts
        ),
        "named_lock_graph_database_call_count": sum(
            row["call"].startswith("VN.Replication.DataLayer.DBConnector.")
            for contract in lock_contracts
            for row in contract["allowlisted_calls"]
        ),
        "named_lock_graph_file_exists_call_count": sum(
            bool(_positions(contract, "File.Exists")) for contract in lock_contracts
        ),
        "send_watermark_read_concatenates_query": _ordered(
            _first(get_last_send, "String.Concat"),
            _first(get_last_send, "DbCommand.set_CommandText"),
            _first(get_last_send, "SqlCommand.ExecuteReader"),
        ),
        "send_watermark_update_concatenates_query": _ordered(
            _first(update_last_send, "String.Concat"),
            _first(update_last_send, "DBConnector.Execute"),
        ),
        "connector_begin_transaction_uses_single_string_name_overload": _first_call_signature_signal(
            core["VN.Replication.DataLayer.DBConnector.BeginTransaction"],
            "SqlConnection.BeginTransaction",
            "single_string_parameter",
        ),
        "explicit_transaction_isolation_override_proven": False,
        "send_center_unique_constraint_proven": retry_and_concurrency[
            "send_center_watermark_unique_constraint_proven"
        ],
        "database_application_lock_proven": False,
        "per_center_sender_serialization_proven": False,
        "current_snapshot_can_demonstrate_sender_race": retained.get(
            "dbo.ReplicationSend", 0
        )
        > 0,
    }
    service_timer_reentrancy_boundary = {
        "timer_uses_parameterless_constructor": bool(
            _positions(service_init_timer, "Timer..ctor")
        ),
        "timer_sets_interval": bool(
            _positions(service_init_timer, "Timer.set_Interval")
        ),
        "timer_subscribes_elapsed_handler": bool(
            _positions(service_init_timer, "Timer.add_Elapsed")
        ),
        "timer_enables_periodic_source": bool(
            _positions(service_init_timer, "Timer.set_Enabled")
        ),
        "init_timer_enabled_constant_values": service_init_timer[
            "timer_enabled_constant_values"
        ],
        "timer_explicit_auto_reset_setter_call_count": len(
            _positions(service_init_timer, "Timer.set_AutoReset")
        ),
        "timer_explicit_synchronizing_object_setter_call_count": len(
            _positions(service_init_timer, "Timer.set_SynchronizingObject")
        ),
        "stop_disables_timer": bool(
            _positions(service_stop, "Timer.set_Enabled")
        )
        and service_stop["timer_enabled_constant_values"] == [0],
        "run_timer_enabled_constant_values": service_run[
            "timer_enabled_constant_values"
        ],
        "run_explicitly_disables_timer": 0
        in service_run["timer_enabled_constant_values"],
        "run_thread_sleep_call_count": len(
            _positions(service_run, "Thread.Sleep")
        ),
        "run_mutex_call_count": sum(
            len(_positions(service_run, suffix))
            for suffix in ("Mutex..ctor", "Mutex.WaitOne")
        ),
        "run_monitor_call_count": sum(
            len(_positions(service_run, suffix))
            for suffix in ("Monitor.Enter", "Monitor.TryEnter")
        ),
        "run_interlocked_or_semaphore_call_count": sum(
            row["call"].startswith(
                (
                    "System.Threading.Interlocked.",
                    "System.Threading.Semaphore.",
                    "System.Threading.SemaphoreSlim.",
                    "System.Threading.ReaderWriterLockSlim.",
                )
            )
            for row in service_run["allowlisted_calls"]
        ),
        "named_control_lock_is_execution_mutex_proven": False,
        "periodic_run_single_flight_proven": False,
        "overlapping_timer_run_observed_in_runtime": False,
    }
    post_receive_dependencies = {
        (
            row["referenced_schema_name"],
            row["referenced_entity_name"],
        )
        for row in sql["module_dependencies"]
        if row["referencing_object"] == "usp_ReplicationAfterReciveAll"
    }
    post_receive_maintenance_boundary = {
        "configured_script_lookup_and_execute_occurs_after_receive": service_sequence[
            "run_receives_before_post_receive_script_lookup"
        ]
        and service_sequence[
            "run_post_receive_script_lookup_precedes_dynamic_execute"
        ],
        "service_run_wraps_receive_and_post_hook_in_one_transaction": service_sequence[
            "run_owns_explicit_database_transaction"
        ],
        "exact_active_post_receive_script_mapping_proven": service_sequence[
            "exact_active_post_receive_script_from_configuration_proven"
        ],
        "declared_after_receive_wrapper_calls_log_sort_and_identity_hooks": {
            (None, "USP_VSA_SortTblLog"),
            ("GNR", "uspSetIdentityColValue"),
        }.issubset(post_receive_dependencies),
        "declared_after_receive_wrapper_owns_transaction": sql[
            "post_receive_contract"
        ]["owns_explicit_transaction"],
        "declared_after_receive_wrapper_has_try_catch": sql[
            "post_receive_contract"
        ]["has_try_catch"],
        "log_sort_hook_is_transactional": sql["post_receive_contract"][
            "log_sort_hook_owns_explicit_transaction"
        ]
        and sql["post_receive_contract"]["log_sort_hook_has_try_catch"]
        and sql["post_receive_contract"]["log_sort_hook_has_rollback"],
        "identity_hook_uses_dynamic_execute": sql["post_receive_contract"][
            "identity_hook_has_dynamic_execute"
        ],
        "identity_hook_owns_transaction": sql["post_receive_contract"][
            "identity_hook_owns_explicit_transaction"
        ],
        "identity_hook_has_try_catch": sql["post_receive_contract"][
            "identity_hook_has_try_catch"
        ],
        "clone_configured_identity_target_count": sql["identity_configuration_quality"][
            "configured_row_count"
        ],
        "clone_has_active_identity_targets": sql["identity_configuration_quality"][
            "configured_row_count"
        ]
        > 0,
        "production_identity_configuration_parity_proven": False,
        "target_modules_have_execute_as_override_count": sum(
            row["execute_as_principal_id"] is not None
            for row in sql["module_contracts"]
        ),
        "target_modules_have_explicit_object_permission_record_count": sum(
            row["grant_record_count"]
            for row in sql["object_permission_aggregates"]
        ),
        "effective_service_principal_authority_proven": False,
    }
    verification = [
        {
            "requirement_or_risk": "outbound replication has a durable pre-upload store",
            "result": "PASS"
            if sql["structural_signals"]["replication_file_is_binary_outbox"]
            and send_sequence["send_log_inserts_outbox_before_watermark_update"]
            and send_sequence["upload_reads_outbox_before_upload"]
            else "FAIL",
            "evidence_grade": "hash-pinned IL call ordering plus read-only clone schema",
        },
        {
            "requirement_or_risk": "received script execution and LastExecLog receipt share a transaction boundary",
            "result": "PASS"
            if receive_sequence[
                "local_receive_executes_script_before_last_exec_receipt"
            ]
            and receive_sequence["local_receive_records_receipt_before_commit"]
            and receive_sequence["local_receive_has_rollback_paths"]
            and receive_sequence[
                "ftp_receive_executes_script_before_last_exec_receipt"
            ]
            and receive_sequence["ftp_receive_records_receipt_before_commit"]
            and receive_sequence["ftp_receive_has_rollback_paths"]
            else "FAIL",
            "evidence_grade": "hash-pinned IL call ordering",
        },
        {
            "requirement_or_risk": "clone retains transport receipts sufficient to prove successful downstream rule application",
            "result": "PASS"
            if retained.get("GNR.tblLogRcv", 0) > 0
            and sql["structural_signals"][
                "receive_receipt_has_success_or_checksum"
            ]
            else "FAIL",
            "evidence_grade": "read-only clone aggregates and schema",
        },
        {
            "requirement_or_risk": "FTP branch explicitly enables encrypted authenticated transport",
            "result": "PASS"
            if ftp_and_package_integrity["connect_sets_encryption_mode"]
            and ftp_and_package_integrity[
                "connect_sets_certificate_validation"
            ]
            else "FAIL",
            "evidence_grade": "hash-pinned VN.Replication and FluentFTP IL",
        },
        {
            "requirement_or_risk": "replication package is content-authenticated before script execution",
            "result": "PASS"
            if ftp_and_package_integrity[
                "named_package_flow_hash_or_signature_call_count"
            ]
            > 0
            else "FAIL",
            "evidence_grade": "hash-pinned named send/receive IL call graph",
        },
        {
            "requirement_or_risk": "replication receipt identity is unique replay-safe and gapless",
            "result": "PASS"
            if retry_and_concurrency[
                "receive_site_range_unique_constraint_proven"
            ]
            and retry_and_concurrency["receipt_rejects_equal_replay"]
            and retry_and_concurrency["receipt_enforces_gapless_sequence"]
            and retry_and_concurrency["receipt_trigger_is_multirow_safe"]
            else "FAIL",
            "evidence_grade": "read-only index catalog and static receipt-trigger SQL",
        },
        {
            "requirement_or_risk": "post-receive maintenance is atomic with each received package and receipt",
            "result": "PASS"
            if post_receive_maintenance_boundary[
                "service_run_wraps_receive_and_post_hook_in_one_transaction"
            ]
            and post_receive_maintenance_boundary[
                "exact_active_post_receive_script_mapping_proven"
            ]
            and post_receive_maintenance_boundary[
                "declared_after_receive_wrapper_owns_transaction"
            ]
            and post_receive_maintenance_boundary[
                "identity_hook_owns_transaction"
            ]
            else "FAIL",
            "evidence_grade": "hash-pinned service ordering plus static SQL module graph",
        },
        {
            "requirement_or_risk": "transport completion marker precedes post-upload database acknowledgement helper",
            "result": "PASS"
            if outbound_acknowledgement_boundary[
                "local_copy_precedes_local_completion_marker"
            ]
            and outbound_acknowledgement_boundary[
                "local_completion_marker_uses_atomic_move"
            ]
            and outbound_acknowledgement_boundary[
                "local_completion_returns_before_database_ack_helper"
            ]
            and outbound_acknowledgement_boundary[
                "ftp_upload_precedes_remote_size_read"
            ]
            and outbound_acknowledgement_boundary[
                "ftp_remote_size_read_precedes_validation_helper"
            ]
            and outbound_acknowledgement_boundary[
                "ftp_validation_precedes_completion_rename"
            ]
            and outbound_acknowledgement_boundary[
                "ftp_completion_returns_before_database_ack_helper"
            ]
            else "FAIL",
            "evidence_grade": "hash-pinned local-file and FTP IL call ordering",
        },
        {
            "requirement_or_risk": "retained receive receipts and main log are complete immutable history",
            "result": "PASS"
            if retention_and_cleanup_boundary[
                "retained_receive_receipts_are_complete_history_proven"
            ]
            and retention_and_cleanup_boundary[
                "retained_main_log_is_complete_history_proven"
            ]
            else "FAIL",
            "evidence_grade": "hash-pinned cleanup call ordering plus static SQL delete surface",
        },
        {
            "requirement_or_risk": "received packages are deterministically ordered and gap-checked before execution",
            "result": "PASS"
            if package_ordering_boundary[
                "deterministic_range_order_before_execution_proven"
            ]
            and package_ordering_boundary["receipt_enforces_gapless_sequence"]
            else "FAIL",
            "evidence_grade": "hash-pinned local/FTP listing call graph plus static receipt trigger",
        },
        {
            "requirement_or_risk": "package center scope and lookup tokens are authenticated and validated before execution",
            "result": "PASS"
            if package_center_scope_boundary[
                "lookup_parameterization_proven"
            ]
            and package_center_scope_boundary[
                "filename_to_lookup_character_validation_proven"
            ]
            and package_center_scope_boundary[
                "local_named_record_validator_runs_before_executor"
            ]
            and package_center_scope_boundary[
                "ftp_named_record_validator_runs_before_executor"
            ]
            and package_center_scope_boundary[
                "cryptographic_center_binding_proven"
            ]
            else "FAIL",
            "evidence_grade": "hash-pinned receiver, lookup and validator IL ordering",
        },
        {
            "requirement_or_risk": "executor false or exception result is rejected before receive receipt",
            "result": "PASS"
            if all(executor_outcome_boundary.values())
            else "FAIL",
            "evidence_grade": "hash-pinned executor return and receiver branch IL",
        },
        {
            "requirement_or_risk": "rollback failure is propagated or durably observable",
            "result": "PASS"
            if transaction_error_boundary["rollback_failure_rethrows"]
            and transaction_error_boundary[
                "rollback_failure_observability_proven"
            ]
            else "FAIL",
            "evidence_grade": "hash-pinned connector exception-handler IL",
        },
        {
            "requirement_or_risk": "one sender per center is serialized across processes and database sessions",
            "result": "PASS"
            if sender_concurrency_boundary[
                "send_center_unique_constraint_proven"
            ]
            and sender_concurrency_boundary["database_application_lock_proven"]
            and sender_concurrency_boundary[
                "per_center_sender_serialization_proven"
            ]
            else "FAIL",
            "evidence_grade": "hash-pinned named lock/watermark IL plus read-only index catalog",
        },
        {
            "requirement_or_risk": "received package cleanup is recoverable if database commit fails",
            "result": "PASS"
            if receive_file_database_atomicity_boundary[
                "filesystem_and_database_share_atomic_commit"
            ]
            or receive_file_database_atomicity_boundary[
                "automatic_retry_from_preserved_input_after_commit_failure_proven"
            ]
            else "FAIL",
            "evidence_grade": "hash-pinned receipt, filesystem, FTP and commit IL ordering",
        },
        {
            "requirement_or_risk": "post-receive reset failure is propagated to the orchestration outcome",
            "result": "PASS"
            if post_receive_reset_boundary[
                "reset_failure_is_propagated_to_local_receiver"
            ]
            else "FAIL",
            "evidence_grade": "hash-pinned reset return and local caller IL ordering",
        },
        {
            "requirement_or_risk": "periodic replication service execution is non-reentrant or single-flight",
            "result": "PASS"
            if service_timer_reentrancy_boundary[
                "periodic_run_single_flight_proven"
            ]
            else "FAIL",
            "evidence_grade": "hash-pinned timer initialization and Run synchronization call graph",
        },
        {
            "requirement_or_risk": "package SQL execution has a finite positive timeout and cancellation deadline on every path",
            "result": "PASS"
            if package_execution_timeout_boundary[
                "finite_positive_timeout_on_every_package_execution_path_proven"
            ]
            and package_execution_timeout_boundary[
                "cancellation_or_deadline_propagation_proven"
            ]
            else "FAIL",
            "evidence_grade": "hash-pinned package executor and connector timeout call graph",
        },
        {
            "requirement_or_risk": "rejected replication packages have a durable quarantined and retry-safe disposition across transports",
            "result": "PASS"
            if receive_rejection_disposition_boundary[
                "durable_quarantine_receipt_proven"
            ]
            and receive_rejection_disposition_boundary[
                "retry_safe_rejection_disposition_parity_proven"
            ]
            else "FAIL",
            "evidence_grade": "hash-pinned local/FTP false-branch rollback and cleanup call ordering",
        },
    ]
    return {
        "artifact": "varanegar_rule_replication_transport_boundary",
        "schema_version": 1,
        "generated_at": __import__("datetime").datetime.now().astimezone().isoformat(),
        "source": {
            "replication_directory": str(replication_directory),
            "binaries": binaries,
            "database": safety,
        },
        "safety": {
            "mode": "READ_ONLY_STATIC_IL_AND_CLONE_CATALOG",
            "assemblies_loaded_or_executed": 0,
            "configuration_files_read": 0,
            "archive_or_log_files_read": 0,
            "operational_sql_modules_or_replication_scripts_executed": 0,
            "raw_sql_or_string_literal_values_persisted": 0,
        },
        "deployed_il": parsed,
        "send_sequence": send_sequence,
        "outbound_acknowledgement_boundary": outbound_acknowledgement_boundary,
        "receive_sequence": receive_sequence,
        "service_sequence": service_sequence,
        "retention_and_cleanup_boundary": retention_and_cleanup_boundary,
        "ftp_and_package_integrity": ftp_and_package_integrity,
        "package_execution_boundary": package_execution_boundary,
        "executor_outcome_boundary": executor_outcome_boundary,
        "receive_rejection_disposition_boundary": receive_rejection_disposition_boundary,
        "transaction_error_boundary": transaction_error_boundary,
        "package_execution_timeout_boundary": package_execution_timeout_boundary,
        "receive_file_database_atomicity_boundary": receive_file_database_atomicity_boundary,
        "post_receive_reset_boundary": post_receive_reset_boundary,
        "package_center_scope_boundary": package_center_scope_boundary,
        "retry_and_concurrency": retry_and_concurrency,
        "package_ordering_boundary": package_ordering_boundary,
        "sender_concurrency_boundary": sender_concurrency_boundary,
        "service_timer_reentrancy_boundary": service_timer_reentrancy_boundary,
        "post_receive_maintenance_boundary": post_receive_maintenance_boundary,
        "fluentftp_default_contract": fluentftp,
        "sql_boundary": sql,
        "verification_matrix": verification,
        "summary": {
            "hash_pinned_binary_count": len(binaries),
            "target_method_contract_count": len(core),
            "outbound_binary_outbox_proven": verification[0]["result"] == "PASS",
            "receive_script_and_receipt_transaction_proven": verification[1]["result"]
            == "PASS",
            "retained_replication_file_rows": retained.get("dbo.ReplicationFile", 0),
            "retained_replication_send_rows": retained.get("dbo.ReplicationSend", 0),
            "retained_receive_receipt_rows": retained.get("GNR.tblLogRcv", 0),
            "retained_send_receipt_rows": retained.get("GNR.tblLogSnd", 0),
            "clone_downstream_success_proven": verification[2]["result"] == "PASS",
            "ftp_branch_explicit_transport_encryption_proven": verification[3][
                "result"
            ]
            == "PASS",
            "replication_package_content_authentication_proven": verification[4][
                "result"
            ]
            == "PASS",
            "replication_receipt_idempotency_proven": verification[5]["result"]
            == "PASS",
            "post_receive_maintenance_atomic_with_package_receipt_proven": verification[
                6
            ]["result"]
            == "PASS",
            "transport_completion_precedes_database_ack_helper_proven": verification[
                7
            ]["result"]
            == "PASS",
            "retained_replication_history_completeness_proven": verification[8][
                "result"
            ]
            == "PASS",
            "received_package_ordering_and_gap_check_proven": verification[9][
                "result"
            ]
            == "PASS",
            "package_center_scope_preexecution_validation_proven": verification[
                10
            ]["result"]
            == "PASS",
            "executor_failure_prevents_receive_receipt_proven": verification[11][
                "result"
            ]
            == "PASS",
            "rollback_failure_observability_proven": verification[12]["result"]
            == "PASS",
            "per_center_sender_serialization_proven": verification[13]["result"]
            == "PASS",
            "receive_cleanup_recoverable_after_commit_failure_proven": verification[
                14
            ]["result"]
            == "PASS",
            "post_receive_reset_failure_propagation_proven": verification[15][
                "result"
            ]
            == "PASS",
            "periodic_service_single_flight_proven": verification[16]["result"]
            == "PASS",
            "bounded_package_execution_deadline_proven": verification[17]["result"]
            == "PASS",
            "rejected_package_quarantine_and_retry_safety_proven": verification[18][
                "result"
            ]
            == "PASS",
        },
        "interpretation": (
            "The separate service owns file/FTP transport. It persists generated packages in "
            "a database binary outbox before upload and applies received scripts plus LastExecLog "
            "receipt within an IL-visible transaction. The clone retains no send/receive/outbox "
            "rows, and its receipt schema has no success/checksum field, so historical delivery "
            "of the four recent rule changes is not proven by this snapshot."
        ),
        "limits": [
            "Call ordering is static IL evidence; no service, assembly, file, or script was executed.",
            "Obfuscated literal values and configuration files were not read or persisted.",
            "Empty clone transport tables may be a clone/sanitization artifact and do not prove production inactivity.",
            "A LastExecLog range records progress but is not immutable rule-version or approval provenance.",
            "The FTP branch lacks an explicit encryption/certificate-validation setup in the deployed call path; local-file transport is also supported and production mode was not read.",
            "Password-protected ZIP is not treated as proof of sender authenticity or content version.",
            "Receipt monotonicity guards do not prove uniqueness, gaplessness, or multi-row trigger safety.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replication-directory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    logging.getLogger("dnfile").setLevel(logging.ERROR)
    logging.getLogger("dnfile.stream").setLevel(logging.ERROR)
    payload = collect(args.replication_directory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )
    print(args.output.resolve())
    print(json.dumps(payload["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
