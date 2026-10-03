"""Record source paths, collection, individual methods, subtests and skip reasons."""
import json
import os
from pathlib import Path

reports = []
inventory = []
source_map = {}


def pytest_collection_finish(session):
    root = Path(os.environ['MATRIX_SOURCE_ROOT']).resolve()
    for item in session.items:
        inventory.append(item.nodeid)
        source_map[item.nodeid] = {'path': item.path.resolve().relative_to(root).as_posix(),
                                  'line': item.location[1] + 1}
    Path(os.environ['MATRIX_INVENTORY']).write_text(json.dumps(inventory, indent=2), encoding='utf-8')


def pytest_runtest_logreport(report):
    reports.append({'nodeid': report.nodeid, 'phase': report.when,
                    'outcome': report.outcome, 'report_type': type(report).__name__,
                    'duration': report.duration,
                    'detail': str(report.longrepr) if report.longrepr else None})


def pytest_collectreport(report):
    if report.failed:
        reports.append({'nodeid': report.nodeid, 'phase': 'collection',
                        'outcome': 'failed', 'report_type': type(report).__name__,
                        'detail': str(report.longrepr)})


def pytest_sessionfinish(session, exitstatus):
    Path(os.environ['MATRIX_RESULTS']).write_text(json.dumps({
        'exitstatus': int(exitstatus), 'inventory': inventory, 'source_map': source_map,
        'reports': reports,
    }, indent=2), encoding='utf-8')
