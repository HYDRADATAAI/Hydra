#!/usr/bin/env python3
"""Hosted-only regression checks for the pipeline artifact verifier and CI contract.

The target checkout is read-only. Verifier cases use fresh synthetic directories;
validator probes use independent temporary copies. No artifact is downloaded.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

WORKFLOW = Path('.github/workflows/market-data-pipeline.yml')
VALIDATOR = Path('tools/validate_public_repository.py')
VERIFY_NAME = 'Verify published pipeline artifact round-trip'
DOWNLOAD_NAME = 'Download published pipeline outputs'
ARTIFACT_ENV = 'PUBLISHED_PIPELINE_ARTIFACT_DIR'
DESTINATION = '${{ runner.temp }}/hydra-market-data-pipeline-published'
FIXTURE = {
    'demo/alpha.txt': b'synthetic verifier fixture alpha\n',
    'demo/nested/bravo.bin': b'synthetic\x00verifier\xfffixture\n',
    'operations/charlie.txt': b'synthetic verifier fixture charlie\n',
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def git(repo: Path, *args: str) -> str:
    return subprocess.run(['git', '-C', str(repo), *args], text=True,
                          capture_output=True, check=True).stdout.strip()


def step_span(workflow: str, name: str) -> tuple[int, int]:
    """Independent narrow extractor; does not import the validator's parser."""
    starts = list(re.finditer(r'(?m)^      - ', workflow))
    matches = []
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(workflow)
        block = workflow[match.start():end]
        if block.splitlines()[0] == '      - name: ' + name:
            matches.append((match.start(), end))
    require(len(matches) == 1, f'expected one exact named step: {name}')
    return matches[0]


def step_text(workflow: str, name: str) -> str:
    start, end = step_span(workflow, name)
    return workflow[start:end]


def exact_scalar(block: str, key: str) -> str:
    values = re.findall(r'(?m)^          ' + re.escape(key) + r': ([^\r\n]+)$', block)
    require(len(values) == 1, f'expected one nested scalar: {key}')
    return values[0]


def extract_run(workflow: str) -> tuple[str, str]:
    block = step_text(workflow, VERIFY_NAME)
    require(block.count('        run: |\n') == 1, 'verifier must have one literal run block')
    body = block.split('        run: |\n', 1)[1]
    lines = []
    for line in body.splitlines():
        if not line.strip():
            lines.append('')
        else:
            require(line.startswith('          '), 'unexpected YAML run-block indentation')
            lines.append(line[10:])
    # YAML literal | clipping retains exactly one terminal LF. Python indentation
    # is otherwise untouched; an original EOF heredoc is not given a delimiter.
    run = '\n'.join(lines).rstrip('\n') + '\n'
    run_lines = run.splitlines()
    require(run_lines[0] == "python -I -B - <<'PY'", 'isolated Python invocation changed')
    python_lines = run_lines[1:]
    if python_lines and python_lines[-1] == 'PY':
        python_lines = python_lines[:-1]
    require('PY' not in python_lines, 'unexpected commands after heredoc delimiter')
    script = '\n'.join(python_lines).rstrip('\n') + '\n'
    ast.parse(script)  # Parse only; execution remains the unchanged shell run block.
    return run, script


def replace_once(text: str, old: str, new: str) -> str:
    require(text.count(old) == 1, f'mutation anchor not unique: {old!r}')
    result = text.replace(old, new, 1)
    require(result != text, 'mutation did not change the workflow')
    return result


def mutate_step(workflow: str, name: str, old: str, new: str) -> str:
    start, end = step_span(workflow, name)
    return workflow[:start] + replace_once(workflow[start:end], old, new) + workflow[end:]


def validator_mutations(workflow: str) -> dict[str, str]:
    set_check = '          require(not missing and not extra, f"file set changed; missing={missing}, extra={extra}")'
    hash_check = '              require(actual == expected, f"SHA-256 mismatch for {name}")'
    return {
        'remove_file_set_rejection': mutate_step(workflow, VERIFY_NAME, set_check,
                                                '          pass  # synthetic mutation: omitted rejection'),
        'disable_require_helper': mutate_step(workflow, VERIFY_NAME,
                                              '              if not condition:', '              if False:'),
        'early_success_exit': mutate_step(workflow, VERIFY_NAME, '          import hashlib',
                                          '          raise SystemExit(0)\n          import hashlib'),
        'redirect_verifier_env_to_source': mutate_step(workflow, VERIFY_NAME,
            '          ' + ARTIFACT_ENV + ': ' + DESTINATION,
            '          ' + ARTIFACT_ENV + ': market-data-pipeline-sample/build'),
        'hide_digest_rejection_by_indentation': mutate_step(workflow, VERIFY_NAME, hash_check,
            '              if False:\n    ' + hash_check),
        'redirect_download_destination_control': mutate_step(workflow, DOWNLOAD_NAME,
            '          path: ' + DESTINATION,
            '          path: ${{ runner.temp }}/wrong-pipeline-destination'),
    }


def isolated_environment(published: Path | None = None) -> dict[str, str]:
    env = {key: os.environ[key] for key in ('PATH', 'LANG', 'LC_ALL') if key in os.environ}
    if published is not None:
        env[ARTIFACT_ENV] = str(published)
    return env


def run_process(command: list[str], cwd: Path, env: dict[str, str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True,
                          timeout=timeout, check=False)


def fixture(root: Path) -> tuple[Path, Path]:
    source = root / 'market-data-pipeline-sample/build'
    published = root / 'runner-temp/hydra-market-data-pipeline-published'
    for name, content in FIXTURE.items():
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    published.parent.mkdir(parents=True)
    shutil.copytree(source, published)
    return source, published


def alter_fixture(name: str, root: Path, source: Path, published: Path) -> None:
    if name == 'matching_files':
        return
    if name == 'missing_expected_file':
        (published / 'demo/alpha.txt').unlink()
    elif name == 'changed_expected_bytes':
        (published / 'operations/charlie.txt').write_bytes(b'synthetic changed bytes\n')
    elif name == 'extra_file_within_expected_root':
        (published / 'demo/extra.txt').write_bytes(b'synthetic unexpected member\n')
    elif name == 'extra_file_at_download_root':
        (published / 'unexpected.txt').write_bytes(b'synthetic unexpected root member\n')
    elif name == 'extra_file_in_sibling_directory':
        (published / 'sibling').mkdir()
        (published / 'sibling/extra.txt').write_bytes(b'synthetic unexpected sibling member\n')
    elif name == 'symlink_at_download_root':
        (published / 'linked.txt').symlink_to(source / 'demo/alpha.txt')
    elif name == 'symlink_sibling_directory':
        (published / 'linked-directory').symlink_to(source / 'demo', target_is_directory=True)
    elif name == 'fifo_at_download_root':
        os.mkfifo(published / 'unexpected-pipe')
    elif name == 'expected_file_replaced_by_symlink':
        path = published / 'demo/alpha.txt'
        path.unlink()
        path.symlink_to(source / 'demo/alpha.txt')
    else:
        raise AssertionError(f'unknown fixture case: {name}')


def output_detail(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    return {'returncode': result.returncode, 'stdout': result.stdout[-6000:], 'stderr': result.stderr[-6000:]}


def source_inventory(root: Path) -> dict[str, object]:
    if root.is_symlink():
        return {'.': {'kind': 'symlink', 'target': os.readlink(root)}}
    require(root.is_dir(), 'synthetic source root is missing')
    result: dict[str, object] = {'.': {'kind': 'directory'}}
    for path in sorted(root.rglob('*')):
        name = path.relative_to(root).as_posix()
        if path.is_symlink():
            result[name] = {'kind': 'symlink', 'target': os.readlink(path)}
        elif path.is_dir():
            result[name] = {'kind': 'directory'}
        elif path.is_file():
            result[name] = {'kind': 'regular_file', 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        else:
            result[name] = {'kind': 'non_regular', 'mode': path.lstat().st_mode}
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--repository', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    require(os.environ.get('GITHUB_ACTIONS') == 'true', 'hosted-only harness; no local execution authorized')
    require(platform.system() == 'Linux', 'this regression proof targets the original hosted Linux boundary')
    repo = args.repository.resolve()
    head, tree = git(repo, 'rev-parse', 'HEAD'), git(repo, 'rev-parse', 'HEAD^{tree}')
    require(git(repo, 'status', '--porcelain') == '', 'target checkout must start clean')
    workflow_raw, validator_raw = (repo / WORKFLOW).read_bytes(), (repo / VALIDATOR).read_bytes()
    workflow = workflow_raw.decode('utf-8-sig')
    run, script = extract_run(workflow)
    require(exact_scalar(step_text(workflow, DOWNLOAD_NAME), 'path') == DESTINATION,
            'download destination differs from the tested contract')
    require(exact_scalar(step_text(workflow, VERIFY_NAME), ARTIFACT_ENV) == DESTINATION,
            'verifier environment is not bound to the download destination')
    mutations = validator_mutations(workflow)
    for text in mutations.values():
        extract_run(text)  # Invalid Python/extraction must not impersonate rejection.
    results = []

    def record(name: str, operation) -> None:
        try:
            detail = operation()
            entry = {'name': name, 'passed': True, **detail}
        except Exception as exc:
            entry = {'name': name, 'passed': False, 'error': str(exc)}
        results.append(entry)
        print(f"REGRESSION_CASE={name} RESULT={'PASS' if entry['passed'] else 'FAIL'}", flush=True)
        print(json.dumps(entry, sort_keys=True), flush=True)

    artifact_cases = (
        'matching_files', 'missing_expected_file', 'changed_expected_bytes',
        'extra_file_within_expected_root', 'extra_file_at_download_root',
        'extra_file_in_sibling_directory', 'symlink_at_download_root',
        'symlink_sibling_directory', 'fifo_at_download_root', 'expected_file_replaced_by_symlink',
    )
    for case in artifact_cases:
        def artifact_case(case=case):
            with tempfile.TemporaryDirectory(prefix='pipeline-artifact-case-') as directory:
                root = Path(directory)
                source, published = fixture(root)
                alter_fixture(case, root, source, published)
                original_sources = source_inventory(source)
                result = run_process(['bash', '-e', '-c', run], root, isolated_environment(published), 30)
                detail = output_detail(result)
                detail['source_fixture_unchanged'] = source_inventory(source) == original_sources
                require(detail['source_fixture_unchanged'], 'verifier modified synthetic source comparison files')
                combined = result.stdout + result.stderr
                passed = result.returncode == 0 and result.stdout.splitlines() == [f'PUBLISHED_PIPELINE_ARTIFACT=PASS:{len(FIXTURE)}']
                rejected = (result.returncode != 0 and 'PUBLISHED_PIPELINE_ARTIFACT=FAIL:' in combined
                            and 'PUBLISHED_PIPELINE_ARTIFACT=PASS:' not in combined)
                require(passed if case == 'matching_files' else rejected,
                        f"expected {'acceptance' if case == 'matching_files' else 'verifier rejection'}; {json.dumps(detail)}")
                return detail
        record('artifact/' + case, artifact_case)

    for name, mutated in [('unmodified_positive_control', workflow), *mutations.items()]:
        def validator_case(name=name, mutated=mutated):
            with tempfile.TemporaryDirectory(prefix='pipeline-validator-case-') as directory:
                checkout = Path(directory) / 'repository'
                shutil.copytree(repo, checkout, symlinks=True, ignore=shutil.ignore_patterns('.git'))
                if name != 'unmodified_positive_control':
                    (checkout / WORKFLOW).write_text(mutated, encoding='utf-8')
                require((checkout / VALIDATOR).read_bytes() == validator_raw, 'validator bytes changed in probe')
                result = run_process([sys.executable, '-I', '-B', str(checkout / VALIDATOR)],
                                     checkout, isolated_environment(), 60)
                detail = output_detail(result)
                combined = result.stdout + result.stderr
                passed = (result.returncode == 0 and 'PUBLIC_REPOSITORY_VALIDATION=PASS' in result.stdout
                          and 'MARKET_PIPELINE_CI_CONTRACT=PASS' in result.stdout)
                rejected = (result.returncode != 0 and 'PUBLIC_REPOSITORY_VALIDATION=FAIL' in result.stdout
                            and 'ERROR: market-pipeline CI' in result.stdout
                            and 'Traceback' not in combined)
                require(passed if name == 'unmodified_positive_control' else rejected,
                        f"expected {'validator acceptance' if name == 'unmodified_positive_control' else 'market-pipeline contract rejection'}; {json.dumps(detail)}")
                return detail
        record('validator/' + name, validator_case)

    clean = (git(repo, 'rev-parse', 'HEAD') == head and git(repo, 'rev-parse', 'HEAD^{tree}') == tree
             and git(repo, 'status', '--porcelain') == ''
             and (repo / WORKFLOW).read_bytes() == workflow_raw and (repo / VALIDATOR).read_bytes() == validator_raw)
    report = {'head': head, 'tree': tree, 'python': sys.version, 'platform': platform.platform(),
              'workflow_git_blob': git_blob(workflow_raw), 'validator_git_blob': git_blob(validator_raw),
              'harness_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'extracted_run_sha256': hashlib.sha256(run.encode()).hexdigest(),
              'extracted_python_sha256': hashlib.sha256(script.encode()).hexdigest(),
              'synthetic_file_count': len(FIXTURE), 'source_unchanged': clean,
              'total': len(results), 'passed': sum(case['passed'] for case in results),
              'failed': sum(not case['passed'] for case in results), 'cases': results}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('PIPELINE_REGRESSION_REPORT=' + json.dumps(report, sort_keys=True), flush=True)
    print(f"PIPELINE_REGRESSION_CASES={len(results)} PASS={report['passed']} FAIL={report['failed']}", flush=True)
    require(clean, 'source checkout changed during regression tests')
    return 0 if report['failed'] == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
