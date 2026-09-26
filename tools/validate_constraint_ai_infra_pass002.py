#!/usr/bin/env python3
"""Reproduce the Pass002 owner repair; never grants ordinary replay admission."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/constraint/first_slice/ai_data_center_power_infrastructure_v1'
sys.path.insert(0, str(ROOT / 't6-fail-closed-validator/src'))
from hydra_t6_failclosed.first_slice_shadow_replay import build_shadow_snapshot, canonical_sha256, future_leaks


def one(pattern):
    matches = list(BASE.glob(pattern))
    if len(matches) != 1:
        raise ValueError(f'exactly one artifact required: {pattern}')
    return json.loads(matches[0].read_text())


def main():
    inputs = dict(claim_registry=one('*BATCH010*CLAIM_REGISTRY*'),
                  candidates=one('*BATCH010*T5_CANDIDATE_PROPOSALS*'),
                  relief_paths=one('*BATCH010*RELIEF_PATHS*'),
                  beneficiaries=one('*BATCH010*BENEFICIARY_EVALUATIONS*'),
                  outcomes=one('*BATCH011*OUTCOME_RECORDS*'),
                  candidate_overlay=one('*LILY_OWNER_SEAM*T5_CANDIDATE_TEMPORAL_IDENTITY*'))
    windows = []
    expected_counts = [(0, 0, 0, 0, 0), (4, 0, 0, 0, 0), (10, 0, 0, 0, 1), (10, 3, 5, 4, 1)]
    fields = ('eligible_claim_ids', 'constraint_candidate_ids', 'relief_path_ids', 'beneficiary_relationship_ids', 'outcome_ids')
    for stamp, counts in zip(('2020-01-01T00:00:00Z', '2026-09-26T01:56:59Z',
                             '2026-09-26T01:57:00Z', '2026-09-26T12:47:00Z'), expected_counts):
        snapshot = build_shadow_snapshot(as_of=stamp, **inputs)
        if tuple(len(snapshot[field]) for field in fields) != counts:
            raise ValueError('successor window counts drifted')
        if future_leaks(snapshot, **inputs):
            raise ValueError('lineage leak detected')
        if snapshot != build_shadow_snapshot(as_of=stamp, **inputs):
            raise ValueError('nondeterministic replay')
        windows.append(dict(snapshot=snapshot, sha256=canonical_sha256(snapshot), lineage_leaks=[]))
    audit = one('*LILY_AI_INFRA_PASS002_COVERAGE_AUDIT*')
    for pin in audit['input_pins']:
        path = ROOT / pin['path']
        if hashlib.sha256(path.read_bytes()).hexdigest() != pin['sha256']:
            raise ValueError(f'audited input changed: {pin["path"]}')
    commands = [
        ['-m', 'unittest', 'discover', '-s', 't6-fail-closed-validator/tests'],
        ['tools/validate_constraint_first_slice_successor.py'],
        ['tools/validate_constraint_lily_owner_seams.py'],
        ['tools/test_constraint_first_slice_adversarial.py'],
    ]
    checks = []
    env = dict(os.environ, PYTHONPATH=str(ROOT / 't6-fail-closed-validator/src'))
    for args in commands:
        result = subprocess.run([sys.executable, *args], cwd=ROOT, env=env,
                                text=True, capture_output=True, check=False)
        checks.append(dict(command='python ' + ' '.join(args), exit_code=result.returncode,
                           stdout=result.stdout.strip(), stderr=result.stderr.strip()))
        if result.returncode:
            print(json.dumps(checks, indent=2))
            return 1
    print(json.dumps(dict(record_id='HYDRA_CONSTRAINT_LILY_AI_INFRA_PASS002_VERIFICATION_V001_20260926',
                         scope='NORMALIZED_SHADOW_KNOWLEDGE_AVAILABILITY_NOT_EFFECTIVE_STATE',
                         status='VERTICAL_INTEGRATION_THIN', ordinary_replay_admitted=False,
                         predecessor_receipts_superseded_for_current_lineage_assertions=True,
                         windows=windows, checks=checks), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
