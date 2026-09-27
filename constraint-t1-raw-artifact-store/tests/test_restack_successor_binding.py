"""Reject drift in the reconciled README successor; never bypass blob checks."""
import copy
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('successor_guard', ROOT / 'tools/validate_constraint_first_slice_successor.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
MAP = ROOT / 'docs/constraint/validation/HYDRA_CONSTRAINT_BATCH017_T1_PRIVATE_RECORD_SUPERSESSION_MAP_V001_20260926.json'

class RestackSuccessorBindingTests(unittest.TestCase):
    def test_readme_preserves_original_and_intermediate_predecessors(self):
        rows = guard.load_supersessions(guard.CUSTODY_SUPERSESSION)
        row = rows['constraint-t1-raw-artifact-store/README.md']
        self.assertEqual('df498d35dc3acdfb2fbef95fac1e1505c80105c8', row['predecessor_git_blob_sha'])
        self.assertEqual('5958840f95811a147758913bce8e42419ed55750', row['intermediate_git_blob_sha'])
        self.assertEqual('2e762c7919b0e8c3a1c36f4e83c4d423d729e34a', row['successor_git_blob_sha'])

    def test_hostile_map_drift_is_rejected(self):
        original = guard.load_json
        changes = [
            lambda d: d['transitions'].pop(),
            lambda d: d['transitions'][0].update(path='t6-fail-closed-validator/src/hydra_t6_failclosed/pit_conservative_availability.py'),
            lambda d: d['transitions'][0].update(successor_git_blob_sha='0'*40),
            lambda d: d['transitions'][2].update(successor_git_blob_sha='0'*40),
            lambda d: d['transitions'][2].update(predecessor_git_blob_sha='0'*40),
            lambda d: d['transitions'].append(copy.deepcopy(d['transitions'][2])),
            lambda d: d.update(guardrails=[]),
            lambda d: d.update(scope='CANONICAL_ADMISSION'),
        ]
        for change in changes:
            with self.subTest(change=change):
                doc = original(MAP); change(doc)
                with patch.object(guard, 'load_json', side_effect=lambda p: doc if p == MAP else original(p)):
                    with self.assertRaises(guard.ValidationFailure):
                        guard.load_supersessions(guard.CUSTODY_SUPERSESSION)
