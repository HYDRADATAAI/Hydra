#!/usr/bin/env python3
"""Hosted-only, exact-source proof of one synthetic Brier test's sensitivity.

No production file in the checkout is edited. Every pytest invocation receives
a fresh temporary copy. The sole negative result is accepted only when JUnit
identifies the exact Brier assertion, with no collection error, skip, or xfail.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

SOURCE_HEAD = 'e3b4dd000034a769794e378beff4b483ace8bfe1'
SOURCE_TREE = '5d931f6eb42efda127c0f988d0caa272ca9fb3a8'
TEST = Path('constraint-replay/tests/test_replay_scoring_typed_inputs.py')
METRICS = Path('constraint-replay/src/hydra_constraint_replay/metrics.py')
HARNESS = Path('tools/test_replay_denominator_sensitivity.py')
WORKFLOW = Path('.github/workflows/validation-replay-denominator-sensitivity.yml')
TEST_NAME = 'test_none_target_does_not_change_existing_brier_denominator'
NODE = 'tests/test_replay_scoring_typed_inputs.py::' + TEST_NAME
PINS = {
    'original_test': ('4bbc996060f7c314251c673f09380303cbee9f21',
                      '5d231d169a28b1c8b2d85260561979f88205f3d4f048fdf4c5f7175e9369e230'),
    'strengthened_test': ('aefa250ee9d144eff0ec72b572d794ffb0abd01b',
                          'b298c0f18aa08d61409a2ac3687b95ad6b8f6c286e880688249dec292a5df569'),
    'production_metrics': ('0516d5ff149369bf185ef9deb71e19caf07d24e2',
                           '312845656a58be71184e1042003e6935c44c7fa078fc2a3c9a865116e598b4fd'),
    'mutant_metrics': ('c734d9659912f34d334219a47a8e388d247dfa34',
                       'ff3f96f14aaf4c3b7b4a3e1f020dad7c294f8bc17af51f2b11302da4ee5f15a3'),
}
STRENGTHENED_BLOCK = b'''def test_none_target_does_not_change_existing_brier_denominator():
    cases = [
        _synthetic_case(confidence=0.75, realized=True),
        _synthetic_case(confidence=0.25, realized=False, outcome_class="TRUE_NEGATIVE"),
        _synthetic_case(confidence=0.8, realized=None),
    ]
    metrics = evaluate_cases(cases)
    assert metrics["case_count"] == 3
    assert metrics["resolved_count"] == 3
    assert metrics["brier_score"] == 0.0625
    assert metrics["precision"] == 1.0
    assert metrics["false_positive_rate"] == 0.0
'''
ORIGINAL_BLOCK = b'''def test_none_target_does_not_change_existing_brier_denominator():
    cases = [
        _synthetic_case(confidence=1.0, realized=True),
        _synthetic_case(confidence=0.0, realized=False, outcome_class="TRUE_NEGATIVE"),
        _synthetic_case(confidence=0.8, realized=None),
    ]
    metrics = evaluate_cases(cases)
    assert metrics["case_count"] == 3
    assert metrics["resolved_count"] == 3
    assert metrics["brier_score"] == 0.0
    assert metrics["precision"] == 1.0
    assert metrics["false_positive_rate"] == 0.0
'''
ORIGINAL_DENOMINATOR = b'"brier_score":None if not brier else sum(brier)/len(brier),'
MUTANT_DENOMINATOR = b'"brier_score":None if not brier else sum(brier)/len(resolved),'

# The bootstrap only selects the copied src directory and records actual import
# origins after pytest. It neither imports HYDRA before pytest nor changes tests.
PYTEST_BOOTSTRAP = r'''
import hashlib
import json
from pathlib import Path
import sys
src, origin_report, expected_test = map(Path, sys.argv[1:4])
sys.path.insert(0, str(src))
import pytest
result = pytest.main(sys.argv[4:])
metrics = sys.modules.get('hydra_constraint_replay.metrics')
modules = [m for m in tuple(sys.modules.values())
           if getattr(m, '__file__', None)
           and Path(m.__file__).resolve() == expected_test.resolve()]
origin = {'metrics_file': None, 'metrics_sha256': None,
          'test_modules_found': len(modules), 'test_file': None,
          'test_sha256': None, 'test_evaluate_cases_file': None,
          'pytest_exit_code': int(result)}
if metrics is not None:
    path = Path(metrics.__file__).resolve()
    origin['metrics_file'] = str(path)
    origin['metrics_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
if len(modules) == 1:
    module = modules[0]
    path = Path(module.__file__).resolve()
    origin['test_file'] = str(path)
    origin['test_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    origin['test_evaluate_cases_file'] = str(
        Path(module.evaluate_cases.__globals__['__file__']).resolve())
origin_report.write_text(json.dumps(origin, sort_keys=True), encoding='utf-8')
raise SystemExit(result)
'''


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


class CaseEvidenceError(AssertionError):
    def __init__(self, message: str, evidence: dict):
        super().__init__(message)
        self.evidence = evidence


def digests(raw: bytes) -> dict[str, str]:
    return {
        'git_blob': hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest(),
        'sha256': hashlib.sha256(raw).hexdigest(),
    }


def verify_pin(raw: bytes, label: str) -> dict[str, str]:
    result = digests(raw)
    require((result['git_blob'], result['sha256']) == PINS[label], label + ' pin mismatch')
    ast.parse(raw)  # Syntax only; no dynamic imports or source execution here.
    return result


def git(repo: Path, *args: str) -> str:
    return subprocess.run(['git', '-C', str(repo), *args], check=True,
                          text=True, capture_output=True).stdout.strip()


def inventory(root: Path) -> dict[str, dict[str, int | str]]:
    result = {}
    for current, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(name for name in dirs if name != '.git')
        for name in dirs:
            require(not (Path(current) / name).is_symlink(), 'unexpected directory symlink')
        for name in sorted(files):
            path = Path(current) / name
            mode = path.lstat().st_mode
            require(stat.S_ISREG(mode), 'unexpected nonregular source file: ' + str(path))
            raw = path.read_bytes()
            result[path.relative_to(root).as_posix()] = {
                'sha256': hashlib.sha256(raw).hexdigest(),
                'bytes': len(raw), 'mode': stat.S_IMODE(mode),
            }
    return result


def source_identity(repo: Path) -> dict[str, str]:
    require(not git(repo, 'status', '--porcelain', '--untracked-files=all'), 'source is dirty')
    return {'head': git(repo, 'rev-parse', 'HEAD'),
            'tree': git(repo, 'rev-parse', 'HEAD^{tree}')}


def assert_junit(path: Path, returncode: int, expected_failure: bool) -> dict:
    root = ET.parse(path).getroot()
    suites = list(root.iter('testsuite'))
    require(len(suites) == 1, 'expected exactly one JUnit suite')
    suite = suites[0]
    counts = {key: int(suite.attrib[key]) for key in ('tests', 'failures', 'errors', 'skipped')}
    require(counts == {'tests': 1, 'failures': int(expected_failure), 'errors': 0, 'skipped': 0},
            'wrong JUnit counts: ' + repr(counts))
    cases = list(root.iter('testcase'))
    require(len(cases) == 1, 'wrong JUnit testcase count')
    case = cases[0]
    require(case.attrib.get('name') == TEST_NAME, 'wrong selected test name')
    require(case.attrib.get('file') == 'tests/test_replay_scoring_typed_inputs.py',
            'wrong selected test file')
    require(case.attrib.get('classname') == 'tests.test_replay_scoring_typed_inputs',
            'wrong selected test class')
    require(case.attrib.get('line') == '177', 'selected test definition moved')
    failures = list(case.findall('failure'))
    require(len(failures) == int(expected_failure), 'wrong failure element count')
    require(not list(root.iter('error')) and not list(root.iter('skipped')),
            'unexpected error or skip element')
    require(returncode == int(expected_failure), 'unexpected pytest process exit code')
    result = {'counts': counts, 'testcase': dict(case.attrib), 'returncode': returncode}
    if expected_failure:
        failure = failures[0]
        expected_message = 'assert 0.041666666666666664 == 0.0625'
        require(failure.attrib.get('message') == expected_message,
                'failure was not the hand-computed denominator mismatch')
        detail = failure.text or ''
        require('>       assert metrics["brier_score"] == 0.0625' in detail,
                'failure was not at the strengthened Brier assertion')
        require('tests/test_replay_scoring_typed_inputs.py:187: AssertionError' in detail,
                'failure had the wrong exception type or source line')
        result['failure_message'] = expected_message
        result['failure_detail'] = detail
    return result


def run_case(repo: Path, name: str, test_raw: bytes, metrics_raw: bytes,
             expected_failure: bool) -> dict:
    with tempfile.TemporaryDirectory(prefix='hydra-denominator-' + name + '-') as temporary:
        workspace = Path(temporary)
        copied = workspace / 'source'
        shutil.copytree(repo, copied, ignore=shutil.ignore_patterns('.git'), symlinks=True)
        (copied / TEST).write_bytes(test_raw)
        (copied / METRICS).write_bytes(metrics_raw)
        before = inventory(copied)
        junit = workspace / 'junit.xml'
        origins = workspace / 'import-origins.json'
        command = [sys.executable, '-I', '-B', '-c', PYTEST_BOOTSTRAP,
                   str(copied / 'constraint-replay/src'), str(origins), str(copied / TEST),
                   '-q', '--tb=long', '--color=no', '-p', 'no:cacheprovider',
                   '--noconftest', '-c', 'pyproject.toml', '-o', 'addopts=',
                   '-o', 'junit_family=legacy', '--junitxml=' + str(junit), NODE]
        env = {key: os.environ[key] for key in ('PATH', 'LANG', 'LC_ALL') if key in os.environ}
        env.update({'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'PYTHONDONTWRITEBYTECODE': '1'})
        proc = subprocess.run(command, cwd=copied / 'constraint-replay', env=env,
                              text=True, capture_output=True, timeout=90)
        try:
            require(inventory(copied) == before, name + ': temporary source or cache inventory changed')
            origin = json.loads(origins.read_text(encoding='utf-8'))
            require(origin == {
                'metrics_file': str(copied / METRICS),
                'metrics_sha256': hashlib.sha256(metrics_raw).hexdigest(),
                'test_modules_found': 1,
                'test_file': str(copied / TEST),
                'test_sha256': hashlib.sha256(test_raw).hexdigest(),
                'test_evaluate_cases_file': str(copied / METRICS),
                'pytest_exit_code': proc.returncode,
            }, name + ': pytest did not import the exact temporary test and metrics')
            parsed = assert_junit(junit, proc.returncode, expected_failure)
        except Exception as exc:
            evidence = {'returncode': proc.returncode, 'stdout': proc.stdout,
                        'stderr': proc.stderr,
                        'junit_xml': junit.read_text(encoding='utf-8') if junit.is_file() else None,
                        'import_origins': origins.read_text(encoding='utf-8') if origins.is_file() else None}
            raise CaseEvidenceError(type(exc).__name__ + ': ' + str(exc), evidence) from exc
        return {'name': name, 'status': 'PASS', 'expected_test_failure': expected_failure,
                'test': digests(test_raw), 'metrics': digests(metrics_raw),
                'source_preservation': 'PASS', 'copied_file_count': len(before),
                'command': command[:4] + ['<recorded bootstrap>'] + command[5:],
                'bootstrap_sha256': hashlib.sha256(PYTEST_BOOTSTRAP.encode()).hexdigest(),
                'import_origins': origin, 'junit': parsed,
                'stdout': proc.stdout, 'stderr': proc.stderr}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    require(os.environ.get('GITHUB_ACTIONS') == 'true' and platform.system() == 'Linux',
            'this harness may run only in GitHub Actions on Linux')
    repo = args.repository.resolve(strict=True)
    report_path = args.report.resolve()
    require(not report_path.is_relative_to(repo), 'report must be outside the source checkout')
    identity = source_identity(repo)
    require(git(repo, 'rev-parse', 'HEAD^') == SOURCE_HEAD, 'wrong sole source parent')
    require(git(repo, 'rev-list', '--parents', '-n', '1', 'HEAD').split() ==
            [identity['head'], SOURCE_HEAD], 'carrier must have exactly one frozen source parent')
    require(git(repo, 'rev-parse', 'HEAD^^{tree}') == SOURCE_TREE, 'wrong frozen source tree')
    changed = git(repo, 'diff', '--name-only', SOURCE_HEAD, 'HEAD').splitlines()
    require(sorted(changed) == sorted(map(str, (TEST, HARNESS, WORKFLOW))),
            'carrier must change exactly the strengthened test, harness, and workflow')
    source_before = inventory(repo)
    tracked = git(repo, 'ls-files', '-z').split('\0')
    require(set(source_before) == set(filter(None, tracked)), 'source contains untracked or ignored files')
    strengthened = (repo / TEST).read_bytes()
    production = (repo / METRICS).read_bytes()
    bindings = {'strengthened_test': verify_pin(strengthened, 'strengthened_test'),
                'production_metrics': verify_pin(production, 'production_metrics')}
    require(strengthened.count(STRENGTHENED_BLOCK) == 1, 'strengthened test anchor changed')
    original = strengthened.replace(STRENGTHENED_BLOCK, ORIGINAL_BLOCK, 1)
    bindings['original_test'] = verify_pin(original, 'original_test')
    require(production.count(ORIGINAL_DENOMINATOR) == 1 and MUTANT_DENOMINATOR not in production,
            'production denominator mutation anchor changed')
    mutant = production.replace(ORIGINAL_DENOMINATOR, MUTANT_DENOMINATOR, 1)
    bindings['mutant_metrics'] = verify_pin(mutant, 'mutant_metrics')
    numerator = (Fraction(3, 4) - 1) ** 2 + (Fraction(1, 4) - 0) ** 2
    require(numerator == Fraction(1, 8) and numerator / 2 == Fraction(1, 16)
            and numerator / 3 == Fraction(1, 24), 'hand-computed oracle changed')
    report = {'source_parent': SOURCE_HEAD, 'source_tree': SOURCE_TREE,
              'candidate': identity, 'candidate_files': len(source_before), 'bindings': bindings,
              'selected_node': NODE, 'oracle': {'numerator': str(numerator),
              'correct_denominator': 2, 'correct_result': '1/16 = 0.0625',
              'mutant_denominator': 3, 'mutant_result': '1/24 = 0.041666666666666664'},
              'cases': [], 'source_preservation': 'NOT_CHECKED'}
    matrix = (
        ('original_test_original_metrics', original, production, False),
        ('original_test_mutant_metrics', original, mutant, False),
        ('strengthened_test_original_metrics', strengthened, production, False),
        ('strengthened_test_mutant_metrics', strengthened, mutant, True),
    )
    try:
        for name, test_raw, metrics_raw, expected_failure in matrix:
            try:
                case = run_case(repo, name, test_raw, metrics_raw, expected_failure)
            except Exception as exc:
                case = {'name': name, 'status': 'FAIL', 'error': type(exc).__name__ + ': ' + str(exc)}
                if isinstance(exc, CaseEvidenceError):
                    case['subprocess_evidence'] = exc.evidence
            report['cases'].append(case)
            print('DENOMINATOR_CASE=' + json.dumps(case, sort_keys=True), flush=True)
    finally:
        preserved = source_identity(repo) == identity and inventory(repo) == source_before
        report['source_preservation'] = 'PASS' if preserved else 'FAIL'
        report['status'] = ('PASS' if preserved and len(report['cases']) == 4
                            and all(case['status'] == 'PASS' for case in report['cases']) else 'FAIL')
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        print('DENOMINATOR_SENSITIVITY_SOURCE_PRESERVATION=' + report['source_preservation'])
        print('DENOMINATOR_SENSITIVITY=' + report['status'])
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
