#!/usr/bin/env python3
"""Validate the manifest-gated Athena row count for the public synthetic fixture."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


EXPECTED_ACCEPTED_ROWS = 3
COUNT_HEADER = "accepted_rows"
INTEGER_TEXT = re.compile(r"^(?:0|[1-9][0-9]*)$")


def verify_accepted_row_count(result: Any) -> int:
    if not isinstance(result, dict):
        raise ValueError("Athena result must be a JSON object")
    result_set = result.get("ResultSet")
    if not isinstance(result_set, dict):
        raise ValueError("Athena result is missing ResultSet")
    rows = result_set.get("Rows")
    if not isinstance(rows, list) or len(rows) != 2:
        raise ValueError("Athena result must contain one header and one value row")

    header = rows[0]
    value_row = rows[1]
    if not isinstance(header, dict) or not isinstance(value_row, dict):
        raise ValueError("Athena result rows must be JSON objects")
    header_data = header.get("Data")
    value_data = value_row.get("Data")
    if not isinstance(header_data, list) or not isinstance(value_data, list):
        raise ValueError("Athena result rows are missing Data")
    if not header_data or not value_data:
        raise ValueError("Athena result rows contain no columns")
    header_value = header_data[0].get("VarCharValue") if isinstance(header_data[0], dict) else None
    value = value_data[0].get("VarCharValue") if isinstance(value_data[0], dict) else None
    if header_value != COUNT_HEADER:
        raise ValueError(f"unexpected Athena result column: {header_value!r}")
    if not isinstance(value, str) or not INTEGER_TEXT.fullmatch(value):
        raise ValueError(f"Athena returned an invalid accepted-row count: {value!r}")

    observed = int(value)
    if observed != EXPECTED_ACCEPTED_ROWS:
        raise ValueError(
            f"expected {EXPECTED_ACCEPTED_ROWS} accepted rows from committed view, got {observed}"
        )
    return observed


def verify_result_file(path: Path) -> int:
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"unable to read Athena result JSON: {exc}") from exc
    return verify_accepted_row_count(result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-path", type=Path, required=True)
    parser.add_argument("--github-env", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        accepted_rows = verify_result_file(args.results_path)
        with args.github_env.open("a", encoding="utf-8", newline="\n") as env_file:
            env_file.write(f"ATHENA_ACCEPTED_ROWS={accepted_rows}\n")
    except (OSError, ValueError) as exc:
        print(f"ATHENA_ACCEPTED_ROWS_CHECK=FAIL: {exc}", file=sys.stderr)
        return 1

    print(f"ATHENA_ACCEPTED_ROWS_CHECK=PASS:{accepted_rows}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
