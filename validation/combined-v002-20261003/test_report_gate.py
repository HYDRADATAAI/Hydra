"""Pure JSON accounting regressions: no HYDRA imports, no network or source checkout."""
import copy
import unittest

from report_gate import validate_execution_reports

ALLOWED = {'test_symlinked_object_tree_into_public_repo_is_rejected'}
NODE_A = 'tests/test_fixture.py::TestFixture::test_a'
NODE_B = 'tests/test_fixture.py::TestFixture::test_b'
SKIP_NODE = 'tests/test_store.py::TestStore::test_symlinked_object_tree_into_public_repo_is_rejected'

def row(node, phase, outcome='passed', detail=None, report_type='TestReport'):
    return {'nodeid': node, 'phase': phase, 'outcome': outcome,
            'detail': detail, 'report_type': report_type}

def fixture():
    nodes = [NODE_A, NODE_B]
    return {'exitstatus': 0, 'inventory': nodes,
            'source_map': {n: {'path': 'tests/test_fixture.py', 'line': 1} for n in nodes},
            'reports': [row(n, phase) for n in nodes for phase in ('setup', 'call', 'teardown')]}

def legacy_collection_predicate(result, expected_count):
    return (set(result['source_map']) == set(result['inventory'])
            and len(result['source_map']) == expected_count)

class ExecutionReportGateTests(unittest.TestCase):
    def assert_rejected(self, result):
        self.assertTrue(validate_execution_reports(result, expected_count=2, permitted_skip_methods=ALLOWED))

    def assert_accepted(self, result):
        self.assertEqual(validate_execution_reports(result, expected_count=2, permitted_skip_methods=ALLOWED), [])

    def test_historical_predicate_accepts_missing_execution_reports(self):
        result = fixture(); result['reports'] = []
        self.assertTrue(legacy_collection_predicate(result, 2))

    def test_complete_run_is_accepted(self):
        self.assert_accepted(fixture())

    def test_missing_all_execution_reports_is_rejected(self):
        result = fixture(); result['reports'] = []
        self.assert_rejected(result)

    def test_missing_one_terminal_report_is_rejected(self):
        result = fixture(); result['reports'] = [r for r in result['reports'] if not (r['nodeid'] == NODE_A and r['phase'] == 'call')]
        self.assert_rejected(result)

    def test_duplicate_terminal_report_is_rejected(self):
        result = fixture(); result['reports'].append(row(NODE_A, 'call'))
        self.assert_rejected(result)

    def test_extra_method_report_is_rejected(self):
        result = fixture(); result['reports'].append(row('tests/unknown.py::test_extra', 'call'))
        self.assert_rejected(result)

    def test_nonzero_session_exitstatus_is_rejected(self):
        result = fixture(); result['exitstatus'] = 1
        self.assert_rejected(result)

    def test_missing_session_exitstatus_is_rejected(self):
        result = fixture(); del result['exitstatus']
        self.assert_rejected(result)

    def test_boolean_session_exitstatus_is_rejected(self):
        result = fixture(); result['exitstatus'] = False
        self.assert_rejected(result)

    def test_failed_teardown_is_rejected(self):
        result = fixture(); result['reports'][-1]['outcome'] = 'failed'
        self.assert_rejected(result)

    def test_missing_teardown_is_rejected(self):
        result = fixture(); result['reports'].pop()
        self.assert_rejected(result)

    def skipped_fixture(self, phase):
        result = fixture(); result['inventory'][0] = SKIP_NODE
        result['source_map'][SKIP_NODE] = result['source_map'].pop(NODE_A)
        result['reports'] = [r for r in result['reports'] if r['nodeid'] != NODE_A]
        if phase == 'call': result['reports'].append(row(SKIP_NODE, 'setup'))
        result['reports'] += [row(SKIP_NODE, phase, 'skipped', '[WinError 1314] A required privilege is not held by the client'), row(SKIP_NODE, 'teardown')]
        return result

    def test_named_1314_setup_skip_is_accepted(self):
        self.assert_accepted(self.skipped_fixture('setup'))

    def test_named_1314_call_skip_is_accepted(self):
        self.assert_accepted(self.skipped_fixture('call'))

    def test_skip_without_1314_reason_is_rejected(self):
        result = self.skipped_fixture('call')
        for r in result['reports']:
            if r['outcome'] == 'skipped': r['detail'] = 'unrelated failure'
        self.assert_rejected(result)

    def test_unapproved_skip_method_is_rejected(self):
        result = fixture(); result['reports'][1].update(outcome='skipped', detail='WinError 1314')
        self.assert_rejected(result)

    def test_failed_subtest_is_rejected(self):
        result = fixture(); result['reports'].append(row(NODE_A, 'call', 'failed', 'hostile case', 'SubTestReport'))
        self.assert_rejected(result)

    def test_successful_subtests_do_not_duplicate_method_terminal(self):
        result = fixture(); result['reports'] += [row(NODE_A, 'call', report_type='SubTestReport') for _ in range(3)]
        self.assert_accepted(result)

    def test_duplicate_inventory_is_rejected(self):
        result = fixture(); result['inventory'].append(NODE_A)
        self.assert_rejected(result)

    def test_missing_source_mapping_is_rejected(self):
        result = fixture(); result['source_map'].pop(NODE_A)
        self.assert_rejected(result)

    def test_duplicate_setup_is_rejected(self):
        result = fixture(); result['reports'].append(row(NODE_A, 'setup'))
        self.assert_rejected(result)

    def test_unknown_report_kind_is_rejected(self):
        result = fixture(); result['reports'].append(row(NODE_A, 'call', report_type='UnknownReport'))
        self.assert_rejected(result)

    def test_invalid_outcome_is_rejected(self):
        result = fixture(); result['reports'][1]['outcome'] = 'unknown'
        self.assert_rejected(result)

    def test_input_is_not_mutated(self):
        result = fixture(); before = copy.deepcopy(result)
        self.assert_accepted(result); self.assertEqual(result, before)

if __name__ == '__main__':
    unittest.main(verbosity=2)
