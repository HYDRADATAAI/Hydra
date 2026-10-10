"""Validate the Thread G receipt report and the files it promises."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from typing import Any

_HASH = re.compile(r"[0-9a-f]{64}", re.ASCII)
_BASE_OUTPUTS = (
    "baseline.json",
    "baseline.log",
    "RESULT.json",
    "SOURCE_HASHES.json",
)
_REPAIR_OUTPUTS = (
    "repaired_types.json",
    "repaired_types.log",
    "existing_admission.json",
    "existing_admission.log",
    "existing_bridge.json",
    "existing_bridge.log",
)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"RESULT.json contains duplicate field: {key}")
        result[key] = value
    return result


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


def validate_receipt_outputs(root: Path) -> None:
    """Raise ValueError unless the root contains every report-required receipt."""
    report_path = root / "RESULT.json"
    report = json.loads(
        report_path.read_text(encoding="utf-8"),
        object_pairs_hook=_unique_object,
    )
    required = _BASE_OUTPUTS + tuple(conditional_receipt_outputs(report))
    missing = [name for name in required if not (root / name).is_file()]
    if missing:
        raise ValueError("Expected receipt output missing: " + ", ".join(missing))


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: thread_g_receipt_validation.py RECEIPT_ROOT", file=sys.stderr)
        return 2
    try:
        validate_receipt_outputs(Path(args[0]))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
