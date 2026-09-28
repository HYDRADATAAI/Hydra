from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


BRANCH = "constraint/t1-private-capture-execution-packet-20260926"
EXPECTED_REMOTE_FRAGMENT = "HYDRADATAAI/Hydra"
RUNNER_RELATIVE_PATH = Path(
    "tools/private/HYDRA_CONSTRAINT_T1_AUTOMATED_BROWSER_FIRST_SLICE_CAPTURE_V001_20260926.py"
)
REQUIREMENTS_RELATIVE_PATH = Path(
    "tools/private/HYDRA_CONSTRAINT_T1_AUTOMATED_BROWSER_CAPTURE_REQUIREMENTS_V001_20260926.txt"
)
DEFAULT_PRIVATE_ROOT = Path(r"D:\HYDRA\_PRIVATE\constraint")


class BootstrapError(RuntimeError):
    pass


def _run(command: list[str], *, cwd: Path | None = None) -> None:
    completed = subprocess.run(command, cwd=str(cwd) if cwd else None, check=False)
    if completed.returncode != 0:
        raise BootstrapError(
            f"command failed with exit code {completed.returncode}: {' '.join(command)}"
        )


def _output(command: list[str], *, cwd: Path | None = None) -> str:
    completed = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise BootstrapError(
            f"command failed with exit code {completed.returncode}: {' '.join(command)}"
        )
    return completed.stdout.strip()


def _tracked_status(repo: Path) -> str:
    return _output(
        ["git", "status", "--porcelain=v1", "--untracked-files=no"],
        cwd=repo,
    )


def _assert_tracked_clean(repo: Path, *, when: str) -> None:
    status = _tracked_status(repo)
    if status:
        raise BootstrapError(
            f"HYDRA tracked working tree is not clean {when}; "
            "commit or revert tracked changes before capture bootstrap"
        )


def _repo_root() -> Path:
    repo = Path(__file__).resolve().parents[2]
    if not (repo / ".git").exists():
        raise BootstrapError(f"bootstrap is not inside a Git working tree: {repo}")

    top_level = Path(
        _output(["git", "rev-parse", "--show-toplevel"], cwd=repo)
    ).resolve()
    if os.path.normcase(str(top_level)) != os.path.normcase(str(repo.resolve())):
        raise BootstrapError(
            f"unexpected Git top-level path: expected {repo}, observed {top_level}"
        )

    remote = _output(["git", "remote", "get-url", "origin"], cwd=repo)
    if re.search(r"(?i)(^|[:/])HYDRADATAAI/Hydra(?:\.git)?$", remote) is None:
        raise BootstrapError(f"unexpected origin remote for HYDRA repo: {remote}")

    upper = str(repo).upper()
    if "AUDIT_RESULTS" in upper or "REMOTE_RUNTIME_SNAPSHOT" in upper:
        raise BootstrapError("refusing to run from an audit/snapshot clone")
    return repo


def _update_repo(repo: Path) -> None:
    _assert_tracked_clean(repo, when="before branch update")
    _run(["git", "config", "core.longpaths", "true"], cwd=repo)

    remote_ref = f"refs/remotes/origin/{BRANCH}"
    fetch_refspec = f"+refs/heads/{BRANCH}:{remote_ref}"
    _run(["git", "fetch", "--prune", "origin", fetch_refspec], cwd=repo)

    local_exists = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{BRANCH}"],
        cwd=str(repo),
        check=False,
    ).returncode == 0

    if local_exists:
        _run(["git", "switch", BRANCH], cwd=repo)
    else:
        _run(["git", "switch", "--track", f"origin/{BRANCH}"], cwd=repo)

    _run(["git", "merge", "--ff-only", f"origin/{BRANCH}"], cwd=repo)

    current = _output(["git", "branch", "--show-current"], cwd=repo)
    if current != BRANCH:
        raise BootstrapError(
            f"capture branch checkout failed: expected {BRANCH}, observed {current}"
        )

    _assert_tracked_clean(repo, when="after branch update")


def _private_python(repo: Path, private_root: Path, no_bootstrap: bool) -> Path:
    runtime = private_root / "browser-runtime"
    venv_root = runtime / "playwright-venv"
    python_exe = venv_root / "Scripts" / "python.exe"
    marker = venv_root / "Lib" / "site-packages" / "playwright" / "__init__.py"
    requirements = repo / REQUIREMENTS_RELATIVE_PATH

    runtime.mkdir(parents=True, exist_ok=True)

    if not python_exe.is_file():
        if no_bootstrap:
            raise BootstrapError(
                f"private Playwright Python is absent and --no-bootstrap was specified: {python_exe}"
            )
        _run([sys.executable, "-m", "venv", str(venv_root)])

    if not marker.is_file():
        if no_bootstrap:
            raise BootstrapError(
                "Playwright Python client is absent and --no-bootstrap was specified"
            )
        if not requirements.is_file():
            raise BootstrapError(f"requirements file missing: {requirements}")
        _run(
            [
                str(python_exe),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--requirement",
                str(requirements),
            ]
        )
        if not marker.is_file():
            raise BootstrapError(
                f"Playwright package installation completed but package marker is absent: {marker}"
            )
    return python_exe


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Windows Python-only bootstrap for HYDRA Constraint exact-nine private browser capture. "
            "Updates the canonical branch, prepares the private Playwright client environment, "
            "then launches the authoritative browser capture runner."
        )
    )
    parser.add_argument("--authorized-public-acquisition", action="store_true")
    parser.add_argument("--private-root", default=str(DEFAULT_PRIVATE_ROOT))
    parser.add_argument("--browser", choices=("auto", "chrome", "msedge"), default="auto")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--challenge-wait-seconds", type=int, default=180)
    parser.add_argument("--navigation-timeout-seconds", type=int, default=90)
    parser.add_argument("--browser-restart-retries", type=int, default=2)
    parser.add_argument("--resume-journal")
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--no-update", action="store_true")
    parser.add_argument("--no-bootstrap", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.authorized_public_acquisition:
        print(
            "HYDRA_CONSTRAINT_PYTHON_BROWSER_CAPTURE_BOOTSTRAP=FAIL",
            file=sys.stderr,
        )
        print(
            "ERROR=explicit --authorized-public-acquisition is required",
            file=sys.stderr,
        )
        return 1
    if args.resume_journal and args.fresh:
        print(
            "HYDRA_CONSTRAINT_PYTHON_BROWSER_CAPTURE_BOOTSTRAP=FAIL",
            file=sys.stderr,
        )
        print("ERROR=--resume-journal and --fresh are mutually exclusive", file=sys.stderr)
        return 1

    try:
        repo = _repo_root()
        if not args.no_update:
            _update_repo(repo)

        runner = repo / RUNNER_RELATIVE_PATH
        if not runner.is_file():
            raise BootstrapError(f"authoritative browser runner missing: {runner}")

        private_root = Path(args.private_root).expanduser().resolve()
        private_python = _private_python(
            repo,
            private_root,
            args.no_bootstrap,
        )

        command = [
            str(private_python),
            str(runner),
            "--authorized-public-acquisition",
            "--repo-root",
            str(repo),
            "--private-root",
            str(private_root),
            "--browser",
            args.browser,
            "--challenge-wait-seconds",
            str(args.challenge_wait_seconds),
            "--navigation-timeout-seconds",
            str(args.navigation_timeout_seconds),
            "--browser-restart-retries",
            str(args.browser_restart_retries),
        ]
        if args.headless:
            command.append("--headless")
        if args.fresh:
            command.append("--fresh")
        if args.resume_journal:
            command.extend(["--resume-journal", args.resume_journal])

        print(f"REPO={repo}")
        print(f"PRIVATE_ROOT={private_root}")
        print(f"PYTHON={private_python}")
        print(f"RUNNER={runner}")
        print("STARTING_HYDRA_CONSTRAINT_BROWSER_CAPTURE=YES")

        completed = subprocess.run(command, check=False)
        return completed.returncode
    except BootstrapError as exc:
        print(
            "HYDRA_CONSTRAINT_PYTHON_BROWSER_CAPTURE_BOOTSTRAP=FAIL",
            file=sys.stderr,
        )
        print(f"ERROR={exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
