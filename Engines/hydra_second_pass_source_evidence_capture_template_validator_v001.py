#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ENGINE_ID = 'hydra_second_pass_source_evidence_capture_template_validator_v001.py'
VERSION = 'v0_1'
TEMPLATE_REL = Path('data/canonical/second_pass_source_evidence_capture_template_v0_1')
OUT_REL = Path('data/canonical/second_pass_source_evidence_capture_template_validator_v0_1')
TEMPLATE_SUMMARY_NAME = 'HYDRA_second_pass_source_evidence_capture_template_summary_v0_1.csv'
TEMPLATE_ROWS_NAME = 'HYDRA_second_pass_source_evidence_capture_template_v0_1.csv'
ALLOWED_DECISIONS_NAME = 'HYDRA_second_pass_source_evidence_capture_template_allowed_decisions_v0_1.csv'
TEMPLATE_CHECKS_NAME = 'HYDRA_second_pass_source_evidence_capture_template_checks_v0_1.csv'
EXPECTED_TEMPLATE_STATUS = 'SECOND_PASS_SOURCE_EVIDENCE_CAPTURE_TEMPLATE_BUILT_NO_APPLICATION'
EXPECTED_TEMPLATE_NEXT = 'MANUALLY_FILL_SECOND_PASS_SOURCE_EVIDENCE_CAPTURE_TEMPLATE_THEN_RUN_VALIDATOR'
ALLOWED_DECISIONS = {'evidence_captured','needs_chart_recheck','needs_source_recheck','keep_parked_no_row_specific_evidence'}
GUARD_FALSE = ['review_decisions_applied','simulator_called','simulation_results_written','simulation_authorized','active_queue_written','queue_mutation','source_packet_modified','capture_template_modified','setup4_rank4_rebuilt','evidence_merge_applied','template_created_sim_candidate','template_created_queue_rows','evidence_applied']

def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def norm(v: Any) -> str:
    return '' if v is None else str(v).strip()

def as_int(v: Any, default: int = 0) -> int:
    try:
        s = norm(v)
        return default if not s else int(float(s))
    except Exception:
        return default

def falseish(v: Any) -> bool:
    return norm(v).lower() in {'','false','0','no','n'}

def read_rows(path: Path) -> List[Dict[str,str]]:
    if not path.exists(): return []
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        return [dict(r) for r in csv.DictReader(f)]

def write_rows(path: Path, rows: List[Dict[str,Any]], fields: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        for r in rows: w.writerow({k:r.get(k,'') for k in fields})

def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')

def check(checks: List[Dict[str,Any]], cid: str, name: str, exp: Any, act: Any, ok: bool) -> None:
    checks.append({'check_id':cid,'check_name':name,'expected':exp,'actual':act,'passed':bool(ok),'severity':'ERROR'})

def main() -> int:
    ap = argparse.ArgumentParser(description='HYDRA second-pass source evidence capture template validator v0.1')
    ap.add_argument('--hydra-root', required=True)
    ap.add_argument('--expected-rows', type=int, default=45)
    args = ap.parse_args()

    root = Path(args.hydra_root)
    tdir = root / TEMPLATE_REL
    odir = root / OUT_REL
    docs = root / 'docs'
    summary_path = tdir / TEMPLATE_SUMMARY_NAME
    template_path = tdir / TEMPLATE_ROWS_NAME
    allowed_path = tdir / ALLOWED_DECISIONS_NAME
    template_checks_path = tdir / TEMPLATE_CHECKS_NAME

    summary_rows = read_rows(summary_path)
    template_rows = read_rows(template_path)
    allowed_rows = read_rows(allowed_path)
    template_checks = read_rows(template_checks_path)
    summary = summary_rows[0] if summary_rows else {}
    checks: List[Dict[str,Any]] = []

    check(checks,'FILE_001','template_summary_exists',True,summary_path.exists(),summary_path.exists())
    check(checks,'FILE_002','capture_template_exists',True,template_path.exists(),template_path.exists())
    check(checks,'FILE_003','allowed_decisions_exists',True,allowed_path.exists(),allowed_path.exists())
    check(checks,'FILE_004','template_checks_exists',True,template_checks_path.exists(),template_checks_path.exists())

    toverall = norm(summary.get('overall_status'))
    tstatus = norm(summary.get('template_status'))
    tnext = norm(summary.get('next_allowed_step'))
    trows_summary = as_int(summary.get('template_rows'))
    failed_template_checks = [r for r in template_checks if norm(r.get('passed')).lower() not in {'true','1','yes','y'}]

    check(checks,'STATUS_001','template_overall_status','PASS',toverall,toverall=='PASS')
    check(checks,'STATUS_002','template_status',EXPECTED_TEMPLATE_STATUS,tstatus,tstatus==EXPECTED_TEMPLATE_STATUS)
    check(checks,'STATUS_003','template_next_allowed_step',EXPECTED_TEMPLATE_NEXT,tnext,tnext==EXPECTED_TEMPLATE_NEXT)
    check(checks,'COUNT_001','template_rows_summary',args.expected_rows,trows_summary,trows_summary==args.expected_rows)
    check(checks,'COUNT_002','template_rows_file_count',args.expected_rows,len(template_rows),len(template_rows)==args.expected_rows)
    check(checks,'CHECK_001','template_checks_failed_summary',0,as_int(summary.get('checks_failed')),as_int(summary.get('checks_failed'))==0)
    check(checks,'CHECK_002','template_checks_table_failed_rows',0,len(failed_template_checks),len(failed_template_checks)==0)
    allowed_file = {norm(r.get('manual_capture_decision')) for r in allowed_rows if norm(r.get('manual_capture_decision'))}
    check(checks,'DECISION_001','allowed_decisions_file_contains_required',sorted(ALLOWED_DECISIONS),sorted(allowed_file),ALLOWED_DECISIONS.issubset(allowed_file))

    ids = [norm(r.get('review_row_id')) for r in template_rows if norm(r.get('review_row_id'))]
    check(checks,'COUNT_003','unique_review_row_ids',args.expected_rows,len(set(ids)),len(set(ids))==args.expected_rows)

    decision_counts = Counter()
    row_validation: List[Dict[str,Any]] = []
    counters = Counter()
    for i, r in enumerate(template_rows, 1):
        rid = norm(r.get('review_row_id'))
        decision = norm(r.get('manual_capture_decision'))
        reason = norm(r.get('manual_capture_reason'))
        reviewer = norm(r.get('reviewer_initials'))
        summary_text = norm(r.get('row_specific_chart_evidence_summary'))
        src_note = norm(r.get('source_context_note'))
        applied = norm(r.get('manual_capture_applied'))
        src_path = norm(r.get('selected_source_path'))
        src_row = norm(r.get('source_file_local_row_number'))
        decision_counts[decision] += 1
        valid_decision = decision in ALLOWED_DECISIONS
        has_reason = bool(reason)
        has_reviewer = bool(reviewer)
        has_source = bool(src_path and src_row)
        need_summary = decision in {'evidence_captured','keep_parked_no_row_specific_evidence'}
        need_note = decision in {'keep_parked_no_row_specific_evidence','needs_chart_recheck','needs_source_recheck'}
        has_summary = (not need_summary) or bool(summary_text)
        has_note = (not need_note) or bool(src_note)
        applied_ok = falseish(applied)
        if not valid_decision: counters['blank_or_invalid_decision_count'] += 1
        if not has_reason: counters['blank_reason_count'] += 1
        if not has_reviewer: counters['blank_reviewer_count'] += 1
        if not has_summary: counters['blank_required_evidence_summary_count'] += 1
        if not has_note: counters['blank_required_source_context_note_count'] += 1
        if not applied_ok: counters['manual_capture_applied_status_violation_count'] += 1
        if decision == 'evidence_captured': counters['evidence_captured_count'] += 1
        if decision == 'keep_parked_no_row_specific_evidence': counters['keep_parked_no_row_specific_evidence_count'] += 1
        if decision == 'needs_chart_recheck': counters['needs_chart_recheck_count'] += 1
        if decision == 'needs_source_recheck': counters['needs_source_recheck_count'] += 1
        ok = bool(rid) and has_source and valid_decision and has_reason and has_reviewer and has_summary and has_note and applied_ok
        if not ok: counters['row_validation_failed'] += 1
        row_validation.append({'row_validation_sequence':i,'review_row_id':rid,'manual_capture_decision':decision,'row_validation_status':'PASS' if ok else 'FAIL','has_source_details':has_source,'valid_decision':valid_decision,'has_reason':has_reason,'has_reviewer':has_reviewer,'has_required_evidence_summary':has_summary,'has_required_source_context_note':has_note,'manual_capture_applied_false':applied_ok,'selected_source_path':src_path,'source_file_local_row_number':src_row})

    check(checks,'ROW_001','row_validation_failed',0,counters['row_validation_failed'],counters['row_validation_failed']==0)
    check(checks,'ROW_002','blank_or_invalid_decision_count',0,counters['blank_or_invalid_decision_count'],counters['blank_or_invalid_decision_count']==0)
    check(checks,'ROW_003','blank_reason_count',0,counters['blank_reason_count'],counters['blank_reason_count']==0)
    check(checks,'ROW_004','blank_reviewer_count',0,counters['blank_reviewer_count'],counters['blank_reviewer_count']==0)
    check(checks,'ROW_005','blank_required_evidence_summary_count',0,counters['blank_required_evidence_summary_count'],counters['blank_required_evidence_summary_count']==0)
    check(checks,'ROW_006','blank_required_source_context_note_count',0,counters['blank_required_source_context_note_count'],counters['blank_required_source_context_note_count']==0)
    check(checks,'ROW_007','manual_capture_applied_status_violation_count',0,counters['manual_capture_applied_status_violation_count'],counters['manual_capture_applied_status_violation_count']==0)

    for n, field in enumerate(GUARD_FALSE, 1):
        actual = summary.get(field,'')
        check(checks,f'GUARD_{n:03d}',field,False,actual,falseish(actual))

    failed = [c for c in checks if not c['passed']]
    overall = 'PASS' if not failed else 'FAIL'
    if overall == 'PASS':
        validator_status = 'SECOND_PASS_SOURCE_EVIDENCE_CAPTURE_TEMPLATE_VALIDATED_NO_APPLICATION'
        next_allowed = 'BUILD_SECOND_PASS_SOURCE_EVIDENCE_CAPTURE_APPLY_PLAN_NO_APPLICATION'
    else:
        validator_status = 'SECOND_PASS_SOURCE_EVIDENCE_CAPTURE_TEMPLATE_VALIDATION_BLOCKED'
        next_allowed = 'FIX_SECOND_PASS_SOURCE_EVIDENCE_CAPTURE_TEMPLATE_THEN_RERUN_VALIDATOR'

    summary_out = odir / 'HYDRA_second_pass_source_evidence_capture_template_validator_summary_v0_1.csv'
    validated_out = odir / 'HYDRA_second_pass_source_evidence_capture_validated_rows_v0_1.csv'
    rowval_out = odir / 'HYDRA_second_pass_source_evidence_capture_row_validation_v0_1.csv'
    counts_out = odir / 'HYDRA_second_pass_source_evidence_capture_decision_counts_v0_1.csv'
    checks_out = odir / 'HYDRA_second_pass_source_evidence_capture_template_validator_checks_v0_1.csv'
    artifacts_out = odir / 'HYDRA_second_pass_source_evidence_capture_template_validator_artifacts_v0_1.csv'
    json_out = odir / 'HYDRA_second_pass_source_evidence_capture_template_validator_v0_1.json'
    report_out = docs / 'HYDRA_SECOND_PASS_SOURCE_EVIDENCE_CAPTURE_TEMPLATE_VALIDATOR_V0_1.md'
    checkpoint_out = docs / 'HYDRA_CHECKPOINT_20260524_SECOND_PASS_SOURCE_EVIDENCE_CAPTURE_TEMPLATE_VALIDATOR_V0_1.txt'

    summary_row = {'engine_id':ENGINE_ID,'version':VERSION,'created_utc':now(),'overall_status':overall,'validator_status':validator_status,'source_template_status':tstatus,'template_rows':len(template_rows),'validated_rows':len(template_rows),'evidence_captured_count':counters['evidence_captured_count'],'keep_parked_no_row_specific_evidence_count':counters['keep_parked_no_row_specific_evidence_count'],'needs_chart_recheck_count':counters['needs_chart_recheck_count'],'needs_source_recheck_count':counters['needs_source_recheck_count'],'row_validation_failed':counters['row_validation_failed'],'blank_or_invalid_decision_count':counters['blank_or_invalid_decision_count'],'blank_reason_count':counters['blank_reason_count'],'blank_reviewer_count':counters['blank_reviewer_count'],'blank_required_evidence_summary_count':counters['blank_required_evidence_summary_count'],'blank_required_source_context_note_count':counters['blank_required_source_context_note_count'],'manual_capture_applied_status_violation_count':counters['manual_capture_applied_status_violation_count'],'checks_passed':len(checks)-len(failed),'checks_failed':len(failed),'review_decisions_applied':False,'simulator_called':False,'simulation_results_written':False,'simulation_authorized':False,'active_queue_written':False,'queue_mutation':False,'source_packet_modified':False,'capture_template_modified':False,'setup4_rank4_rebuilt':False,'evidence_merge_applied':False,'validator_created_sim_candidate':False,'validator_created_queue_rows':False,'evidence_applied':False,'next_allowed_step':next_allowed}

    write_rows(summary_out,[summary_row],list(summary_row.keys()))
    write_rows(validated_out,template_rows,list(template_rows[0].keys()) if template_rows else [])
    write_rows(rowval_out,row_validation,list(row_validation[0].keys()) if row_validation else [])
    write_rows(counts_out,[{'manual_capture_decision':k,'count':v} for k,v in sorted(decision_counts.items())],['manual_capture_decision','count'])
    write_rows(checks_out,checks,['check_id','check_name','expected','actual','passed','severity'])
    artifacts = [{'artifact_type':'summary','path':str(summary_out)},{'artifact_type':'validated_rows','path':str(validated_out)},{'artifact_type':'row_validation','path':str(rowval_out)},{'artifact_type':'decision_counts','path':str(counts_out)},{'artifact_type':'checks','path':str(checks_out)},{'artifact_type':'json','path':str(json_out)},{'artifact_type':'report','path':str(report_out)},{'artifact_type':'checkpoint','path':str(checkpoint_out)},{'artifact_type':'source_template','path':str(template_path)}]
    write_rows(artifacts_out,artifacts,['artifact_type','path'])
    write_text(json_out,json.dumps({'summary':summary_row,'failed_checks':failed,'artifacts':artifacts},indent=2))
    write_text(report_out, f"""# HYDRA Second-Pass Source Evidence Capture Template Validator v0.1\n\n- overall_status: `{overall}`\n- validator_status: `{validator_status}`\n- template_rows: `{len(template_rows)}`\n- keep_parked_no_row_specific_evidence_count: `{counters['keep_parked_no_row_specific_evidence_count']}`\n- row_validation_failed: `{counters['row_validation_failed']}`\n- checks_failed: `{len(failed)}`\n- simulator_called: `False`\n- active_queue_written: `False`\n- queue_mutation: `False`\n- next_allowed_step: `{next_allowed}`\n""")
    write_text(checkpoint_out, f"HYDRA SECOND-PASS SOURCE EVIDENCE CAPTURE TEMPLATE VALIDATOR v0.1\noverall_status: {overall}\nvalidator_status: {validator_status}\ntemplate_rows: {len(template_rows)}\nkeep_parked_no_row_specific_evidence_count: {counters['keep_parked_no_row_specific_evidence_count']}\nrow_validation_failed: {counters['row_validation_failed']}\nchecks_failed: {len(failed)}\nsimulator_called: False\nactive_queue_written: False\nqueue_mutation: False\nnext_allowed_step: {next_allowed}\n")

    print('HYDRA SECOND-PASS SOURCE EVIDENCE CAPTURE TEMPLATE VALIDATOR v0.1 COMPLETE')
    for k in ['engine_id','version','overall_status','validator_status','template_rows','validated_rows','evidence_captured_count','keep_parked_no_row_specific_evidence_count','needs_chart_recheck_count','needs_source_recheck_count','row_validation_failed','blank_or_invalid_decision_count','blank_reason_count','blank_reviewer_count','blank_required_evidence_summary_count','blank_required_source_context_note_count','manual_capture_applied_status_violation_count','checks_passed','checks_failed','review_decisions_applied','simulator_called','simulation_results_written','simulation_authorized','active_queue_written','queue_mutation','source_packet_modified','capture_template_modified','setup4_rank4_rebuilt','evidence_merge_applied','validator_created_sim_candidate','validator_created_queue_rows','evidence_applied','next_allowed_step']:
        print(f'{k}: {summary_row[k]}')
    print(f'summary: {summary_out}')
    print(f'validated_rows: {validated_out}')
    print(f'row_validation: {rowval_out}')
    print(f'report: {report_out}')
    print(f'checkpoint: {checkpoint_out}')
    return 0 if overall == 'PASS' else 1

if __name__ == '__main__':
    raise SystemExit(main())
