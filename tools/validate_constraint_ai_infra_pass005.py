#!/usr/bin/env python3
"""Reproduce current-owner shadow availability; never grants ordinary admission."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 't6-fail-closed-validator/src'))
from hydra_t6_failclosed.first_slice_shadow_replay import build_shadow_snapshot, canonical_sha256, future_leaks
import validate_constraint_lily_owner_seams as owner


def main():
    # Use the mainline owner's exact V002 inputs; do not import older authority.
    if owner.main() != 0:
        return 1
    inputs = dict(claim_registry=owner.load(owner.PATHS['claims']),
                  candidates=owner.load(owner.PATHS['candidates']),
                  beneficiaries=owner.load(owner.PATHS['beneficiaries']),
                  candidate_overlay=owner.load(owner.PATHS['temporal_identity_overlay']))
    for key, name in (
        ('relief_paths', 'HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH010_AI_DATA_CENTER_POWER_INFRASTRUCTURE_RELIEF_PATHS_V001_20260925.json'),
        ('outcomes', 'HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH011_AI_DATA_CENTER_POWER_INFRASTRUCTURE_OUTCOME_RECORDS_V001_20260925.json'),
    ):
        inputs[key] = owner.load(owner.SLICE / name)
    fields = ('eligible_claim_ids', 'constraint_candidate_ids', 'relief_path_ids', 'beneficiary_relationship_ids', 'outcome_ids')
    windows = []
    for stamp, counts in (
        ('2020-01-01T00:00:00Z', (0, 0, 0, 0, 0)),
        ('2026-09-26T01:56:59Z', (4, 0, 0, 0, 0)),
        ('2026-09-26T01:57:00Z', (10, 0, 0, 0, 1)),
        ('2026-09-26T12:47:00Z', (10, 3, 5, 4, 1)),
    ):
        snapshot = build_shadow_snapshot(as_of=stamp, **inputs)
        if tuple(len(snapshot[field]) for field in fields) != counts:
            raise ValueError('shadow window counts drifted')
        if future_leaks(snapshot, **inputs):
            raise ValueError('shadow lineage leak')
        if snapshot != build_shadow_snapshot(as_of=stamp, **inputs):
            raise ValueError('nondeterministic shadow replay')
        windows.append(dict(snapshot=snapshot, sha256=canonical_sha256(snapshot)))
    print(json.dumps(dict(scope='NORMALIZED_SHADOW_AVAILABILITY_ONLY', ordinary_replay_admitted=False,
                          owner_overlay='V002', windows=windows), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
