# HYDRA Review Gate Idle Lock After Failed-Lane Repair v0.1

- engine_id: `hydra_review_gate_idle_lock_after_failed_lane_repair_v001.py`
- version: `v0_1`
- overall_status: `PASS`
- idle_lock_status: `REVIEW_GATE_IDLE_LOCK_AFTER_FAILED_LANE_REPAIR_CONFIRMED`
- source_selector_status: `POST_FAILED_LANE_REPAIR_GLOBAL_NEXT_SELECTOR_REVIEW_GATE_IDLE_CONFIRMED`
- source_final_closeout_status: `GLOBAL_FAILED_LANE_REPAIR_FINAL_CLOSEOUT_COMPLETE_NO_ACTIVE_FAILED_LANES`
- selected_next_lane: `REVIEW_GATE_IDLE`
- selected_next_action: `WAIT_FOR_NEW_EVIDENCE_OR_NEW_QUEUE_INPUT_DO_NOT_SIMULATE`
- new_input_signal_count: `0`
- active_failed_lane_summary_rows: `0`
- missing_registry_match_rows: `0`
- cumulative_stale_registry_rows: `4`
- checks_failed: `0`
- simulator_called: `False`
- simulation_authorized: `False`
- active_queue_written: `False`
- queue_mutation: `False`
- source_packet_modified: `False`
- evidence_merge_applied: `False`
- code_modified: `False`
- next_allowed_step: `REVIEW_GATE_IDLE_LOCKED_WAIT_FOR_NEW_EVIDENCE_OR_QUEUE_INPUT_NO_SIMULATION`

## Idle Rule

Only new evidence input or new queue/input packet may reopen Review Gate. No simulation or queue mutation is authorized from this state.
