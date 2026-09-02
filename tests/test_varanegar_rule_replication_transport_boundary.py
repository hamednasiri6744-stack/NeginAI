import json
from pathlib import Path


ARTIFACT = Path(
    "artifacts/varanegar_analysis/domains/"
    "rule_replication_transport_boundary_20260828.json"
)


def _load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_transport_evidence_is_hash_pinned_and_non_executing() -> None:
    payload = _load()
    assert payload["artifact"] == "varanegar_rule_replication_transport_boundary"
    assert payload["schema_version"] == 1
    assert {
        row["file"]: row["sha256"] for row in payload["source"]["binaries"]
    } == {
        "VN.Replication.dll": "741f5e4d56b9d5ae22c954a6bce6c62d618d7d62aebc7b9abaf01bae4702047e",
        "VN.ReplicationService.exe": "335a5efb719dead2c39c46c46b61969f73813772783fbaedf8887456278cf213",
        "VaranegarMonitorReplication.exe": "02ac26f49058d13e9717047a3af40e0754e1ad40deb1da489f07c85358eee0c6",
        "FluentFTP.dll": "dabf2f9a7307dfc4d81b2d70fcb079b15bed07d228eae0ae401c07d6df82bf2a",
    }
    safety = payload["safety"]
    assert safety["assemblies_loaded_or_executed"] == 0
    assert safety["configuration_files_read"] == 0
    assert safety["archive_or_log_files_read"] == 0
    assert safety["operational_sql_modules_or_replication_scripts_executed"] == 0
    assert safety["raw_sql_or_string_literal_values_persisted"] == 0


def test_send_path_uses_database_binary_outbox_before_upload() -> None:
    payload = _load()
    assert payload["send_sequence"] == {
        "send_log_creates_file_before_outbox_insert": True,
        "send_log_inserts_outbox_before_watermark_update": True,
        "replicate_begins_transaction_before_send_log": True,
        "replicate_commits_before_binary_upload": True,
        "upload_reads_outbox_before_upload": True,
        "replicate_has_rollback_path": True,
    }
    assert payload["sql_boundary"]["structural_signals"][
        "replication_file_is_binary_outbox"
    ] is True
    assert payload["sql_boundary"]["structural_signals"][
        "replication_send_has_center_watermark"
    ] is True
    matrix = {
        row["requirement_or_risk"]: row
        for row in payload["verification_matrix"]
    }
    assert matrix["outbound replication has a durable pre-upload store"][
        "result"
    ] == "PASS"


def test_receive_executes_and_records_last_exec_inside_transaction() -> None:
    payload = _load()
    assert payload["receive_sequence"] == {
        "local_receive_executes_script_before_last_exec_receipt": True,
        "local_receive_records_receipt_before_commit": True,
        "local_receive_has_rollback_paths": True,
        "ftp_receive_executes_script_before_last_exec_receipt": True,
        "ftp_receive_records_receipt_before_commit": True,
        "ftp_receive_has_rollback_paths": True,
    }
    assert payload["sql_boundary"]["structural_signals"][
        "receive_receipt_has_range_and_last_exec"
    ] is True
    assert payload["summary"][
        "receive_script_and_receipt_transaction_proven"
    ] is True


def test_clone_does_not_retain_delivery_proof_for_recent_rule_changes() -> None:
    payload = _load()
    summary = payload["summary"]
    assert summary["retained_replication_file_rows"] == 0
    assert summary["retained_replication_send_rows"] == 0
    assert summary["retained_receive_receipt_rows"] == 0
    assert summary["retained_send_receipt_rows"] == 0
    assert summary["clone_downstream_success_proven"] is False
    assert payload["sql_boundary"]["structural_signals"][
        "receive_receipt_has_success_or_checksum"
    ] is False
    matrix = {
        row["requirement_or_risk"]: row
        for row in payload["verification_matrix"]
    }
    assert matrix[
        "clone retains transport receipts sufficient to prove successful downstream rule application"
    ]["result"] == "FAIL"


def test_only_allowlisted_call_names_are_persisted() -> None:
    payload = _load()
    contracts = payload["deployed_il"]["VN.Replication.dll"][
        "method_contracts"
    ]
    assert len(contracts) == 49
    assert all(
        contract["string_literal_values_persisted"] == 0
        for contract in contracts.values()
    )
    assert all(
        contract["signature_signals"]["signature_blob_persisted"] is False
        for contract in contracts.values()
    )
    assert all(
        row["called_signature_signals"]["signature_blob_persisted"] is False
        for contract in contracts.values()
        for row in contract["allowlisted_calls"]
    )
    assert all(
        row["call"].startswith(
            (
                "VN.Replication.",
                "System.IO.",
                "Ionic.Zip.ZipFile.",
                "FluentFTP.FtpClient.",
                "System.Timers.Timer.",
                "System.Threading.Thread.Sleep",
                "System.Threading.Mutex.",
                "System.Threading.Monitor.",
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
        )
        for contract in contracts.values()
        for row in contract["allowlisted_calls"]
    )


def test_ftp_and_package_authentication_are_not_overclaimed() -> None:
    payload = _load()
    boundary = payload["ftp_and_package_integrity"]
    assert boundary == {
        "fluentftp_version": "32.4.3.0",
        "fluentftp_none_encryption_enum_value": 0,
        "fluentftp_constructor_sets_encryption_mode_count": 0,
        "connect_uses_default_ftp_client_constructor": True,
        "connect_sets_credentials": True,
        "connect_sets_encryption_mode": False,
        "connect_sets_ssl_protocols": False,
        "connect_sets_certificate_validation": False,
        "zip_create_sets_password": True,
        "zip_extract_sets_password": True,
        "named_package_flow_hash_or_signature_call_count": 0,
        "local_file_share_transport_also_supported": True,
        "production_transport_mode_read_from_configuration": False,
    }
    assert payload["summary"][
        "ftp_branch_explicit_transport_encryption_proven"
    ] is False
    assert payload["summary"][
        "replication_package_content_authentication_proven"
    ] is False
    matrix = {
        row["requirement_or_risk"]: row
        for row in payload["verification_matrix"]
    }
    assert matrix[
        "FTP branch explicitly enables encrypted authenticated transport"
    ]["result"] == "FAIL"
    assert matrix[
        "replication package is content-authenticated before script execution"
    ]["result"] == "FAIL"


def test_receiver_uses_text_sql_without_a_proven_universal_typed_allowlist() -> None:
    payload = _load()
    assert payload["package_execution_boundary"] == {
        "executor_constructs_sql_command": True,
        "executor_sets_command_text": True,
        "executor_calls_execute_non_query": True,
        "executor_calls_named_record_validator": False,
        "outer_file_path_calls_executor_before_named_record_validator": True,
        "named_record_validator_instruction_count": 51,
        "typed_operation_allowlist_proven": False,
        "raw_package_sql_persisted": False,
    }


def test_receipt_guard_is_monotonic_but_not_replay_safe_or_gapless() -> None:
    payload = _load()
    assert payload["retry_and_concurrency"] == {
        "outbox_filename_unique_constraint_proven": False,
        "send_center_watermark_unique_constraint_proven": False,
        "receive_site_range_unique_constraint_proven": False,
        "receipt_rejects_watermark_regression": True,
        "receipt_rejects_equal_replay": False,
        "receipt_enforces_gapless_sequence": False,
        "receipt_trigger_is_multirow_safe": False,
        "receipt_insert_delete_history_present": True,
        "current_snapshot_can_demonstrate_duplicate_or_gap_behavior": False,
    }
    assert payload["sql_boundary"]["receipt_trigger_contract"] == {
        "rejects_start_greater_than_end": True,
        "rejects_end_watermark_regression": True,
        "rejects_last_exec_watermark_regression": True,
        "rejects_equal_end_or_last_exec_replay": False,
        "enforces_next_start_equals_previous_end_plus_one": False,
        "uses_scalar_assignment_from_inserted": True,
        "writes_insert_history": True,
        "writes_delete_history": True,
        "can_synthesize_local_log_successor": True,
        "uses_nolock_for_local_log_reads": True,
        "definition_persisted": False,
    }
    assert payload["summary"]["replication_receipt_idempotency_proven"] is False
    matrix = {
        row["requirement_or_risk"]: row for row in payload["verification_matrix"]
    }
    assert matrix[
        "replication receipt identity is unique replay-safe and gapless"
    ]["result"] == "FAIL"


def test_post_receive_maintenance_is_not_proven_atomic_with_file_receipt() -> None:
    payload = _load()
    assert payload["service_sequence"] == {
        "run_receives_before_post_receive_script_lookup": True,
        "run_post_receive_script_lookup_precedes_dynamic_execute": True,
        "run_owns_explicit_database_transaction": False,
        "exact_active_post_receive_script_from_configuration_proven": False,
    }
    assert payload["post_receive_maintenance_boundary"] == {
        "configured_script_lookup_and_execute_occurs_after_receive": True,
        "service_run_wraps_receive_and_post_hook_in_one_transaction": False,
        "exact_active_post_receive_script_mapping_proven": False,
        "declared_after_receive_wrapper_calls_log_sort_and_identity_hooks": True,
        "declared_after_receive_wrapper_owns_transaction": False,
        "declared_after_receive_wrapper_has_try_catch": False,
        "log_sort_hook_is_transactional": True,
        "identity_hook_uses_dynamic_execute": True,
        "identity_hook_owns_transaction": False,
        "identity_hook_has_try_catch": False,
        "clone_configured_identity_target_count": 0,
        "clone_has_active_identity_targets": False,
        "production_identity_configuration_parity_proven": False,
        "target_modules_have_execute_as_override_count": 0,
        "target_modules_have_explicit_object_permission_record_count": 0,
        "effective_service_principal_authority_proven": False,
    }
    assert payload["summary"][
        "post_receive_maintenance_atomic_with_package_receipt_proven"
    ] is False
    matrix = {
        row["requirement_or_risk"]: row for row in payload["verification_matrix"]
    }
    assert matrix[
        "post-receive maintenance is atomic with each received package and receipt"
    ]["result"] == "FAIL"


def test_dynamic_identity_hook_has_no_configured_clone_targets() -> None:
    payload = _load()
    assert payload["sql_boundary"]["identity_configuration_quality"] == {
        "configured_row_count": 0,
        "blank_table_token_count": 0,
        "blank_column_token_count": 0,
        "obvious_sql_token_count": 0,
        "unresolved_table_token_count": 0,
        "ambiguous_table_token_count": 0,
        "unresolved_column_token_count": 0,
        "exact_identity_match_count": 0,
        "non_identity_column_match_count": 0,
        "duplicate_table_column_shape_count": 0,
    }
    assert payload["sql_boundary"]["post_receive_contract"][
        "identity_hook_mentions_dbcc_checkident"
    ] is True
    assert payload["sql_boundary"]["post_receive_contract"][
        "identity_hook_uses_quotename"
    ] is False


def test_package_ordering_and_gap_checks_are_not_proven() -> None:
    payload = _load()
    assert payload["package_ordering_boundary"] == {
        "local_receiver_enumerates_directory_files": True,
        "local_receiver_explicit_sort_call_count": 0,
        "ftp_listing_uses_server_get_listing": True,
        "ftp_listing_and_receiver_explicit_sort_call_count": 0,
        "receipt_enforces_gapless_sequence": False,
        "deterministic_range_order_before_execution_proven": False,
        "current_snapshot_can_demonstrate_out_of_order_behavior": False,
    }
    assert payload["summary"][
        "received_package_ordering_and_gap_check_proven"
    ] is False
    matrix = {
        row["requirement_or_risk"]: row for row in payload["verification_matrix"]
    }
    assert matrix[
        "received packages are deterministically ordered and gap-checked before execution"
    ]["result"] == "FAIL"


def test_center_lookups_do_not_prove_preexecution_scope_validation() -> None:
    payload = _load()
    assert payload["package_center_scope_boundary"] == {
        "local_site_and_center_lookup_precede_unzip": True,
        "ftp_site_and_center_lookup_precede_unzip": True,
        "site_lookup_accepts_single_string_and_returns_int32": True,
        "center_lookup_accepts_single_string_and_returns_int32": True,
        "site_lookup_concatenates_before_execute_scalar": True,
        "center_lookup_concatenates_before_execute_scalar": True,
        "lookup_parameterization_proven": False,
        "filename_to_lookup_character_validation_proven": False,
        "local_named_record_validator_runs_before_executor": False,
        "ftp_named_record_validator_runs_before_executor": False,
        "cryptographic_center_binding_proven": False,
    }
    assert payload["summary"][
        "package_center_scope_preexecution_validation_proven"
    ] is False
    matrix = {
        row["requirement_or_risk"]: row for row in payload["verification_matrix"]
    }
    assert matrix[
        "package center scope and lookup tokens are authenticated and validated before execution"
    ]["result"] == "FAIL"


def test_executor_failure_rolls_back_before_receive_receipt() -> None:
    payload = _load()
    assert payload["executor_outcome_boundary"] == {
        "executor_returns_boolean": True,
        "executor_has_immediate_false_return": True,
        "executor_has_immediate_true_return": True,
        "executor_exception_tail_returns_false": True,
        "local_receiver_branches_on_executor_boolean": True,
        "ftp_receiver_branches_on_executor_boolean": True,
        "local_false_path_rolls_back_before_receipt": True,
        "ftp_false_path_rolls_back_before_receipt": True,
    }
    assert payload["summary"][
        "executor_failure_prevents_receive_receipt_proven"
    ] is True
    matrix = {
        row["requirement_or_risk"]: row for row in payload["verification_matrix"]
    }
    assert matrix[
        "executor false or exception result is rejected before receive receipt"
    ]["result"] == "PASS"


def test_connector_rethrows_execute_and_commit_but_swallows_rollback_failure() -> None:
    payload = _load()
    assert payload["transaction_error_boundary"] == {
        "connector_execute_has_exception_handler": True,
        "connector_execute_rethrows": True,
        "receipt_writer_delegates_to_connector_execute": True,
        "receipt_writer_has_no_local_exception_handler": True,
        "commit_failure_rethrows": True,
        "rollback_has_exception_handler": True,
        "rollback_failure_rethrows": False,
        "rollback_failure_observability_proven": False,
    }
    assert payload["summary"][
        "rollback_failure_observability_proven"
    ] is False
    matrix = {
        row["requirement_or_risk"]: row for row in payload["verification_matrix"]
    }
    assert matrix[
        "rollback failure is propagated or durably observable"
    ]["result"] == "FAIL"


def test_named_lock_does_not_prove_cross_process_sender_serialization() -> None:
    payload = _load()
    assert payload["sender_concurrency_boundary"] == {
        "service_start_calls_named_control_lock": True,
        "service_run_calls_named_control_lock": True,
        "named_lock_graph_mutex_call_count": 0,
        "named_lock_graph_monitor_call_count": 0,
        "named_lock_graph_database_call_count": 0,
        "named_lock_graph_file_exists_call_count": 1,
        "send_watermark_read_concatenates_query": True,
        "send_watermark_update_concatenates_query": True,
        "connector_begin_transaction_uses_single_string_name_overload": True,
        "explicit_transaction_isolation_override_proven": False,
        "send_center_unique_constraint_proven": False,
        "database_application_lock_proven": False,
        "per_center_sender_serialization_proven": False,
        "current_snapshot_can_demonstrate_sender_race": False,
    }
    assert payload["summary"]["per_center_sender_serialization_proven"] is False
    matrix = {
        row["requirement_or_risk"]: row for row in payload["verification_matrix"]
    }
    assert matrix[
        "one sender per center is serialized across processes and database sessions"
    ]["result"] == "FAIL"


def test_periodic_service_single_flight_is_not_overclaimed() -> None:
    payload = _load()
    assert payload["service_timer_reentrancy_boundary"] == {
        "timer_uses_parameterless_constructor": True,
        "timer_sets_interval": True,
        "timer_subscribes_elapsed_handler": True,
        "timer_enables_periodic_source": True,
        "init_timer_enabled_constant_values": [1],
        "timer_explicit_auto_reset_setter_call_count": 0,
        "timer_explicit_synchronizing_object_setter_call_count": 0,
        "stop_disables_timer": True,
        "run_timer_enabled_constant_values": [1],
        "run_explicitly_disables_timer": False,
        "run_thread_sleep_call_count": 1,
        "run_mutex_call_count": 0,
        "run_monitor_call_count": 0,
        "run_interlocked_or_semaphore_call_count": 0,
        "named_control_lock_is_execution_mutex_proven": False,
        "periodic_run_single_flight_proven": False,
        "overlapping_timer_run_observed_in_runtime": False,
    }
    assert payload["summary"]["periodic_service_single_flight_proven"] is False
    matrix = {
        row["requirement_or_risk"]: row for row in payload["verification_matrix"]
    }
    assert matrix[
        "periodic replication service execution is non-reentrant or single-flight"
    ]["result"] == "FAIL"


def test_package_execution_deadline_is_not_overclaimed() -> None:
    payload = _load()
    assert payload["package_execution_timeout_boundary"] == {
        "package_executor_command_timeout_constant_values": [0, 600, 30000],
        "connector_execute_command_timeout_constant_values": [600],
        "package_executor_has_zero_timeout_constant": True,
        "package_executor_maximum_positive_timeout_constant": 30000,
        "finite_positive_timeout_on_every_package_execution_path_proven": False,
        "cancellation_or_deadline_propagation_proven": False,
        "long_running_package_execution_observed_in_runtime": False,
    }
    assert payload["summary"]["bounded_package_execution_deadline_proven"] is False
    matrix = {
        row["requirement_or_risk"]: row for row in payload["verification_matrix"]
    }
    assert matrix[
        "package SQL execution has a finite positive timeout and cancellation deadline on every path"
    ]["result"] == "FAIL"


def test_rejected_package_disposition_is_not_overclaimed() -> None:
    payload = _load()
    assert payload["receive_rejection_disposition_boundary"] == {
        "local_three_parameter_wrapper_delegates_with_false_flag": True,
        "local_listing_discards_execute_local_file_result": True,
        "local_false_path_rollback_precedes_cleanup": True,
        "local_false_path_file_delete_call_count": 5,
        "local_false_path_marks_defective_center": True,
        "local_false_path_quarantine_move_call_count": 0,
        "ftp_false_path_rollback_precedes_local_cleanup": True,
        "ftp_false_path_local_file_delete_call_count": 3,
        "ftp_false_path_remote_delete_call_count": 0,
        "exact_deleted_file_roles_proven": False,
        "durable_quarantine_receipt_proven": False,
        "retry_safe_rejection_disposition_parity_proven": False,
        "rejected_package_observed_in_runtime": False,
    }
    assert payload["summary"][
        "rejected_package_quarantine_and_retry_safety_proven"
    ] is False
    matrix = {
        row["requirement_or_risk"]: row for row in payload["verification_matrix"]
    }
    assert matrix[
        "rejected replication packages have a durable quarantined and retry-safe disposition across transports"
    ]["result"] == "FAIL"


def test_receive_cleanup_precedes_commit_without_proven_automatic_recovery() -> None:
    payload = _load()
    assert payload["receive_file_database_atomicity_boundary"] == {
        "local_archive_copy_occurs_after_receipt_before_commit": True,
        "local_file_delete_occurs_after_receipt_before_commit": True,
        "ftp_local_file_delete_occurs_after_receipt_before_commit": True,
        "ftp_remote_file_delete_occurs_after_receipt_before_commit": True,
        "commit_failure_rethrows": True,
        "filesystem_and_database_share_atomic_commit": False,
        "automatic_retry_from_preserved_input_after_commit_failure_proven": False,
        "commit_failure_window_observed_in_runtime": False,
    }
    assert payload["summary"][
        "receive_cleanup_recoverable_after_commit_failure_proven"
    ] is False
    matrix = {
        row["requirement_or_risk"]: row for row in payload["verification_matrix"]
    }
    assert matrix[
        "received package cleanup is recoverable if database commit fails"
    ]["result"] == "FAIL"


def test_post_receive_reset_failure_result_is_discarded() -> None:
    payload = _load()
    assert payload["post_receive_reset_boundary"] == {
        "local_reset_runs_after_primary_commit": True,
        "local_caller_discards_reset_result": True,
        "reset_returns_boolean": True,
        "reset_has_true_success_path": True,
        "reset_has_false_failure_path": True,
        "reset_owns_transaction_and_commits_two_commands": True,
        "reset_has_rollback_path": True,
        "exact_reset_sql_effect_proven": False,
        "reset_failure_is_propagated_to_local_receiver": False,
        "reset_failure_observed_in_runtime": False,
    }
    assert payload["summary"][
        "post_receive_reset_failure_propagation_proven"
    ] is False
    matrix = {
        row["requirement_or_risk"]: row for row in payload["verification_matrix"]
    }
    assert matrix[
        "post-receive reset failure is propagated to the orchestration outcome"
    ]["result"] == "FAIL"


def test_transport_marks_completion_before_post_upload_database_ack() -> None:
    payload = _load()
    assert payload["outbound_acknowledgement_boundary"] == {
        "local_copy_precedes_local_completion_marker": True,
        "local_completion_marker_uses_atomic_move": True,
        "local_completion_returns_before_database_ack_helper": True,
        "ftp_upload_precedes_remote_size_read": True,
        "ftp_remote_size_read_precedes_validation_helper": True,
        "ftp_validation_precedes_completion_rename": True,
        "ftp_completion_returns_before_database_ack_helper": True,
        "post_upload_ack_helper_executes_database_command": True,
        "post_upload_ack_exact_database_effect_proven": False,
        "remote_content_hash_validation_proven": False,
    }
    assert payload["summary"][
        "transport_completion_precedes_database_ack_helper_proven"
    ] is True
    matrix = {
        row["requirement_or_risk"]: row for row in payload["verification_matrix"]
    }
    assert matrix[
        "transport completion marker precedes post-upload database acknowledgement helper"
    ]["result"] == "PASS"


def test_retained_replication_rows_are_not_treated_as_complete_history() -> None:
    payload = _load()
    assert payload["retention_and_cleanup_boundary"] == {
        "service_run_calls_receive_cleanup_before_receive": True,
        "replicate_calls_receive_cleanup_before_send": True,
        "deployed_clear_procedure_deletes_receive_receipts": True,
        "deployed_clear_procedure_deletes_main_log": False,
        "deployed_clear_procedure_uses_max_last_exec_watermark": True,
        "deployed_clear_procedure_owns_transaction": False,
        "deployed_clear_procedure_has_try_catch": False,
        "exact_helper_to_clear_procedure_binding_proven": False,
        "main_log_delete_candidate_count": 3,
        "retained_receive_receipts_are_complete_history_proven": False,
        "retained_main_log_is_complete_history_proven": False,
    }
    assert payload["summary"][
        "retained_replication_history_completeness_proven"
    ] is False
    assert all(
        row["exact_main_log_delete_or_truncate"] is True
        and row["definition_persisted"] is False
        for row in payload["sql_boundary"]["main_log_retention_candidates"]
    )
    matrix = {
        row["requirement_or_risk"]: row for row in payload["verification_matrix"]
    }
    assert matrix[
        "retained receive receipts and main log are complete immutable history"
    ]["result"] == "FAIL"
