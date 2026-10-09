#!/usr/bin/env python3
"""Reject generated artifacts in tracked public sample paths."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent
PUBLIC_SAMPLE_ROOTS = {
    "aws-market-data-pipeline",
    "governed-intelligence-sample",
    "market-data-pipeline-sample",
    "sql-data-quality-sample",
    "t6-fail-closed-validator",
}
GENERATED_OUTPUT_DIRECTORIES = {
    "artifacts",
    "bin",
    "build",
    "dist",
    "log",
    "logs",
    "obj",
    "outputs",
    "results",
}
ROOT_DUPLICATE_NAME = re.compile(r" \\([0-9]+\\)\\.[^/]+$")


def tracked_path_violation(path: str) -> str | None:
    """Return a rejection reason for a tracked artifact path, if any."""
    parts = PurePosixPath(path).parts
    if not parts:
        return None

    if parts[0] == "archive":
        return None

    name = parts[-1]
    lowered_name = name.casefold()
    if lowered_name.endswith((".zip", ".zip.sha256")):
        return "transfer bundle"
    if name.upper().startswith("EXTRACT_") and lowered_name.endswith(".ps1"):
        return "transfer extractor"

    if (
        len(parts) >= 3
        and parts[0] in PUBLIC_SAMPLE_ROOTS
        and parts[1] in GENERATED_OUTPUT_DIRECTORIES
    ):
        return "generated output directory"

    if len(parts) == 1 and ROOT_DUPLICATE_NAME.search(name):
        return "root-level duplicate download"

    return None


def tracked_paths() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
    )
    return [os.fsdecode(path) for path in result.stdout.split(b"\\0") if path]


def main() -> int:
    failures = [
        (path, tracked_path_violation(path))
        for path in tracked_paths()
    ]
    failures = [(path, reason) for path, reason in failures if reason is not None]
    if failures:
        for path, reason in failures:
            print(f"PUBLIC_ROOT_HYGIENE=FAIL: {reason}: {path}", file=sys.stderr)
        return 1
    print("PUBLIC_ROOT_HYGIENE=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
