"""Pure-data gate binding every collected method to its execution reports.

This complements subprocess exit checks and the existing narrow skip inventory.
It imports no repository code and does not modify the supplied report object.
"""
def validate_execution_reports(result, *, expected_count, permitted_skip_methods=None):
    errors = []
    if not isinstance(result, dict):
        return ['execution result is not an object']
    if type(result.get('exitstatus')) is not int or result['exitstatus'] != 0:
        errors.append('pytest session exitstatus must be integer zero')
    inventory = result.get('inventory', [])
    if not isinstance(inventory, list) or not all(isinstance(n, str) and n for n in inventory):
        return errors + ['invalid execution inventory']
    nodes = set(inventory)
    if len(inventory) != expected_count or len(nodes) != len(inventory):
        errors.append('execution inventory count or uniqueness mismatch')
    source_map = result.get('source_map', {})
    if not isinstance(source_map, dict) or set(source_map) != nodes:
        errors.append('source mapping does not match collected inventory')
    reports = result.get('reports', [])
    if not isinstance(reports, list):
        return errors + ['execution reports are not a list']
    phases = {n: {} for n in nodes}
    permitted = set(permitted_skip_methods or ())
    for index, report in enumerate(reports):
        if not isinstance(report, dict):
            errors.append('invalid report at index ' + str(index)); continue
        node, kind = report.get('nodeid'), report.get('report_type')
        phase, outcome = report.get('phase'), report.get('outcome')
        if outcome not in ('passed', 'failed', 'skipped'):
            errors.append('unknown outcome at report ' + str(index))
        if outcome == 'failed':
            errors.append('failed execution report: ' + str(node))
        if kind not in ('TestReport', 'SubTestReport'):
            errors.append('unexpected report kind: ' + str(kind)); continue
        if not isinstance(node, str) or node not in nodes:
            errors.append('report outside collected inventory: ' + str(node)); continue
        if outcome == 'skipped' and not (node.split('::')[-1] in permitted and isinstance(report.get('detail'), str) and 'WinError 1314' in report['detail']):
            errors.append('skip outside existing WinError 1314 condition: ' + node)
        if kind == 'SubTestReport':
            if phase != 'call': errors.append('subtest outside call phase: ' + node)
            continue
        if phase not in ('setup', 'call', 'teardown'):
            errors.append('unexpected method phase: ' + str(phase)); continue
        phases[node].setdefault(phase, []).append(report)
    for node, observed in phases.items():
        for phase, rows in observed.items():
            if len(rows) != 1:
                errors.append('duplicate ' + phase + ' report: ' + node)
        setup, calls, teardown = (observed.get(p, []) for p in ('setup', 'call', 'teardown'))
        setup_skips = [r for r in setup if r.get('outcome') == 'skipped']
        if len(calls) + len(setup_skips) != 1:
            errors.append('expected exactly one call or setup-skip terminal report: ' + node)
        if len(setup) != 1 or len(teardown) != 1:
            errors.append('missing setup or teardown report: ' + node)
        if any(r.get('outcome') != 'passed' for r in teardown):
            errors.append('teardown did not pass: ' + node)
        if calls and any(r.get('outcome') != 'passed' for r in setup):
            errors.append('called method without successful setup: ' + node)
    return errors
