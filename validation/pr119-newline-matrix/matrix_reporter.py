"""Record pytest collection, individual tests, subtests and skip reasons."""
import json
import os
from pathlib import Path

reports = []
inventory = []
source_paths = {}

def pytest_collection_finish(session):
    inventory.extend(item.nodeid for item in session.items)
    source_paths.update({item.nodeid:Path(item.path).resolve().relative_to(Path.cwd().resolve()).as_posix() for item in session.items})
    Path(os.environ['MATRIX_INVENTORY']).write_text(json.dumps(inventory, indent=2), encoding='utf-8')

def pytest_runtest_logreport(report):
    reports.append({'nodeid': report.nodeid, 'phase': report.when,
                    'outcome': report.outcome, 'report_type': type(report).__name__,
                    'duration': report.duration,
                    'detail': str(report.longrepr) if report.longrepr else None})

def pytest_collectreport(report):
    if report.failed:
        reports.append({'nodeid':report.nodeid, 'phase':'collection',
                        'outcome':'failed', 'report_type':type(report).__name__,
                        'detail':str(report.longrepr)})

def pytest_sessionfinish(session, exitstatus):
    Path(os.environ['MATRIX_RESULTS']).write_text(json.dumps({
        'exitstatus':int(exitstatus), 'inventory':inventory, 'reports':reports, 'source_paths':source_paths,
    }, indent=2), encoding='utf-8')
