"""Validate Thread G receipt hashes and report conditional output names."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from typing import Any

_HASH = re.compile(r"[0-9a-f]{64}", re.ASCII)
_REPAIR_OUTPUTS = (
    "repaired_types.json",
    "repaired_types.log",
    "existing_admission.json",
    "existing_admission.log",
    "existing_bridge.json",
    "existing_bridge.log",
)


def conditional_receipt_outputs(report: Any) -> list[str]:
    """Return repair receipts required when valid source hashes differ."""
    if not isinstance(report, dict):
        raise ValueError("RESULT.json must contain a JSON object")

    baseline = report.get("baseline_source_sha256")
    candidate = report.get("candidate_source_sha256")
    if not isinstance(baseline, str) or not isinstance(candidate, str):
        raise ValueError("RESULT.json must contain string source hashes")
    if _HASH.fullmatch(baseline) is None or _HASH.fullmatch(candidate) is None:
        raise ValueError("RESULT.json source hashes must be lowercase SHA-256 values")

    return list(_REPAIR_OUTPUTS) if baseline != candidate else []


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: thread_g_receipt_validation.py RESULT.json", file=sys.stderr)
        return 2
    try:
        report = json.loads(Path(args[0]).read_text(encoding="utf-8"))
        outputs = conditional_receipt_outputs(report)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(outputs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
