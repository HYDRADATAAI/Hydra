#!/usr/bin/env python3
# HYDRA_V019_DAILY_PLAN_PRODUCER_COPY_PATCH_VALIDATION_GATE_V001
#
# Creates a reviewable patched copy of the primary upstream producer and adds a
# validation gate that fails if canonical VWAP/ONH/ONL columns remain blank for
# ES/NQ symbol/date rows. No live producer mutation by default. No fabrication.

from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SCHEMA_VERSION = "HYDRA_V019_DAILY_PLAN_PRODUCER_COPY_PATCH_VALIDATION_GATE_V001"

TARGET_FIELDS = ["VWAP_Daily", "VWAP_Weekly", "VWAP_Monthly", "ONH", "ONL"]

FIELD_ALIASES = {
    "VWAP_Daily": ["VWAP_Daily", "daily_vwap", "DailyVWAP", "vwap_daily", "VWAPDaily", "vwap", "VWAP"],
    "VWAP_Weekly": ["VWAP_Weekly", "weekly_vwap", "WeeklyVWAP", "vwap_weekly", "VWAPWeekly"],
    "VWAP_Monthly": ["VWAP_Monthly", "monthly_vwap", "MonthlyVWAP", "vwap_monthly", "VWAPMonthly"],
    "ONH": ["ONH", "onh", "overnight_high", "OvernightHigh", "overnightHigh", "overnight_session_high"],
    "ONL": ["ONL", "onl", "overnight_low", "OvernightLow", "overnightLow", "overnight_session_low"],
}

SOURCE_LINE_CONTEXT = 4


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv_dicts(path: Path) -> List[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: List[dict], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def resolve_primary_candidate(v018_dir: Path, explicit: Optional[str]) -> Tuple[Optional[Path], List[str]]:
    notes = []
    if explicit:
        p = Path(explicit)
        notes.append(f"producer_path explicitly supplied: {p}")
        return p, notes

    summary_path = v018_dir / "run_summary_v018.json"
    if summary_path.exists():
        try:
            data = json.loads(read_text(summary_path))
            cand = data.get("primary_candidate_path") or data.get("primary_producer_path")
            if cand:
                p = Path(cand)
                notes.append(f"primary candidate from run_summary_v018.json: {p}")
                return p, notes
        except Exception as exc:
            notes.append(f"could not parse run_summary_v018.json: {exc}")

    patch_recs = read_csv_dicts(v018_dir / "PATCH_RECOMMENDATIONS.csv")
    for row in patch_recs:
        target = (row.get("target_path") or "").strip()
        if target.lower().endswith(".py") and ("v008" in target.lower() or "v005" in target.lower()):
            p = Path(target)
            notes.append(f"primary candidate from PATCH_RECOMMENDATIONS.csv: {p}")
            return p, notes

    report = v018_dir / "V018_PRIMARY_PRODUCER_REVIEW_REPORT.md"
    if report.exists():
        text = read_text(report)
        m = re.search(r"candidate_path:\s*`([^`]+\.py)`", text)
        if m:
            p = Path(m.group(1))
            notes.append(f"primary candidate from report markdown: {p}")
            return p, notes

    return None, notes


def get_field_line_numbers(v018_dir: Path) -> Dict[str, List[int]]:
    result: Dict[str, List[int]] = {field: [] for field in TARGET_FIELDS}
    rows = read_csv_dicts(v018_dir / "FIELD_POPULATION_CODE_MAP.csv")
    if rows:
        for row in rows:
            field = (row.get("field_name") or "").strip()
            if field not in result:
                continue
            raw = (row.get("assignment_or_mapping_lines") or row.get("source_lines") or "").strip()
            nums = []
            for token in re.split(r"[;,|\s]+", raw):
                token = token.strip()
                if token.isdigit():
                    nums.append(int(token))
            result[field] = sorted(set(nums))
        return result

    report = v018_dir / "V018_PRIMARY_PRODUCER_REVIEW_REPORT.md"
    if report.exists():
        text = read_text(report)
        for field in TARGET_FIELDS:
            m = re.search(rf"- `{re.escape(field)}`:.*?mapping_lines=`([^`]+)`", text)
            if m:
                nums = []
                for token in re.split(r"[;,|\s]+", m.group(1)):
                    if token.strip().isdigit():
                        nums.append(int(token.strip()))
                result[field] = sorted(set(nums))
    return result


def extract_source_slices(source_lines: List[str], line_map: Dict[str, List[int]]) -> List[dict]:
    rows: List[dict] = []
    for field, nums in line_map.items():
        for n in nums:
            start = max(1, n - SOURCE_LINE_CONTEXT)
            end = min(len(source_lines), n + SOURCE_LINE_CONTEXT)
            for lineno in range(start, end + 1):
                text = source_lines[lineno - 1].rstrip("\n")
                rows.append({
                    "field_name": field,
                    "focus_line": n,
                    "line_no": lineno,
                    "is_focus_line": str(lineno == n).lower(),
                    "line_text": text,
                    "contains_target_field": str(field in text or any(alias in text for alias in FIELD_ALIASES.get(field, []))).lower(),
                    "contains_assignment_or_mapping": str(("=" in text or ":" in text or "get(" in text or "[" in text)).lower(),
                })
    seen = set()
    out = []
    for r in rows:
        key = (r["field_name"], r["focus_line"], r["line_no"], r["line_text"])
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def make_validation_snippet() -> str:
    return r'''
# --- HYDRA V019 PRODUCER VALIDATION GATE START ---
# This gate does not fabricate values. It fails loudly when canonical VWAP/ONH/ONL
# columns exist but ES/NQ target symbol/date rows are blank or non-numeric.
def hydra_v019__is_numeric_value(value):
    if value is None:
        return False
    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "none", "null", "na", "n/a"}:
        return False
    try:
        float(text.replace(",", ""))
        return True
    except Exception:
        return False


def hydra_v019__row_get_any(row, aliases):
    if row is None:
        return ""
    if hasattr(row, "get"):
        for key in aliases:
            if key in row:
                return row.get(key)
            for existing_key in row.keys():
                if str(existing_key).lower() == str(key).lower():
                    return row.get(existing_key)
    return ""


def hydra_v019_validate_vwap_onh_onl_population(
    context_rows,
    required_fields=None,
    target_symbols=None,
    target_dates=None,
    source_label="unknown_producer",
):
    required_fields = required_fields or ["VWAP_Daily", "VWAP_Weekly", "VWAP_Monthly", "ONH", "ONL"]
    field_aliases = {
        "VWAP_Daily": ["VWAP_Daily", "daily_vwap", "DailyVWAP", "vwap_daily", "VWAPDaily"],
        "VWAP_Weekly": ["VWAP_Weekly", "weekly_vwap", "WeeklyVWAP", "vwap_weekly", "VWAPWeekly"],
        "VWAP_Monthly": ["VWAP_Monthly", "monthly_vwap", "MonthlyVWAP", "vwap_monthly", "VWAPMonthly"],
        "ONH": ["ONH", "onh", "overnight_high", "OvernightHigh", "overnight_session_high"],
        "ONL": ["ONL", "onl", "overnight_low", "OvernightLow", "overnight_session_low"],
    }
    symbol_aliases = ["symbol", "Symbol", "root_symbol", "ticker", "instrument"]
    date_aliases = ["session_date", "trade_date", "date", "Date", "session", "SessionDate"]

    rows = list(context_rows or [])
    observed_symbols = []
    observed_dates = []
    for row in rows:
        sym = str(hydra_v019__row_get_any(row, symbol_aliases)).strip().upper()
        dt = str(hydra_v019__row_get_any(row, date_aliases)).strip()
        if sym and sym not in observed_symbols:
            observed_symbols.append(sym)
        if dt and dt not in observed_dates:
            observed_dates.append(dt)

    symbols = [str(s).strip().upper() for s in (target_symbols or observed_symbols) if str(s).strip()]
    dates = [str(d).strip() for d in (target_dates or observed_dates) if str(d).strip()]
    symbols = [s for s in symbols if s in {"ES", "NQ"}] or symbols

    failures = []
    for field in required_fields:
        aliases = field_aliases.get(field, [field])
        for sym in symbols:
            for dt in dates:
                matched = []
                usable = []
                for row in rows:
                    row_sym = str(hydra_v019__row_get_any(row, symbol_aliases)).strip().upper()
                    row_dt = str(hydra_v019__row_get_any(row, date_aliases)).strip()
                    if row_sym == sym and row_dt == dt:
                        matched.append(row)
                        val = hydra_v019__row_get_any(row, aliases)
                        if hydra_v019__is_numeric_value(val):
                            usable.append(val)
                if matched and not usable:
                    failures.append(f"{field} {sym} {dt}: matched_rows={len(matched)} usable_numeric_values=0")

    if failures:
        preview = "; ".join(failures[:12])
        more = "" if len(failures) <= 12 else f"; ... {len(failures) - 12} more"
        raise RuntimeError(
            "HYDRA_V019_PRODUCER_VALIDATION_GATE_FAIL: "
            f"blank/non-numeric VWAP/ONH/ONL fields detected before output write in {source_label}: "
            f"{preview}{more}"
        )
    return True
# --- HYDRA V019 PRODUCER VALIDATION GATE END ---
'''.strip("\n") + "\n"


def find_import_insertion_index(lines: List[str]) -> int:
    last_import = -1
    for i, line in enumerate(lines[:160]):
        stripped = line.strip()
        if i == 0 and stripped.startswith("#!"):
            last_import = i
            continue
        if "coding" in stripped and stripped.startswith("#"):
            last_import = i
            continue
        if stripped.startswith("import ") or stripped.startswith("from "):
            last_import = i
            continue
        if stripped == "" or stripped.startswith("#"):
            if last_import >= 0:
                continue
        if last_import >= 0:
            break
    return max(0, last_import + 1)


def find_validation_insertion_point(lines: List[str]) -> Tuple[Optional[int], Optional[str], str]:
    candidate_vars = [
        "upgraded_context_rows",
        "upgraded_rows",
        "context_rows",
        "safe_context_rows",
        "rows",
    ]
    write_patterns = [
        "UPGRADED_CONTEXT_ROWS",
        "upgraded_context_rows",
        "upgraded_rows",
        "write_csv",
        "DictWriter",
        ".writerows",
        ".to_csv",
    ]
    for i, line in enumerate(lines):
        low = line.lower()
        if any(p.lower() in low for p in write_patterns):
            window = "\n".join(lines[max(0, i - 80):i + 8])
            for var in candidate_vars:
                if re.search(rf"\b{re.escape(var)}\b", window):
                    return i, var, f"insert before likely write site at line {i + 1}; row variable `{var}` observed nearby"
    for i, line in enumerate(lines):
        if "__name__" in line and "__main__" in line:
            window = "\n".join(lines[max(0, i - 160):i])
            for var in candidate_vars:
                if re.search(rf"\b{re.escape(var)}\b", window):
                    return i, var, f"insert before __main__ block at line {i + 1}; row variable `{var}` observed nearby"
    return None, None, "no safe write-site insertion point with visible context row variable"


def indent_of(line: str) -> str:
    m = re.match(r"^\s*", line)
    return m.group(0) if m else ""


def build_patched_source(original: str, source_label: str) -> Tuple[str, List[dict], List[dict]]:
    lines = original.splitlines(keepends=True)
    snippet = make_validation_snippet().splitlines(keepends=True)

    audit: List[dict] = []
    blockers: List[dict] = []

    if "hydra_v019_validate_vwap_onh_onl_population" in original:
        blockers.append({
            "blocker_code": "V019_GATE_ALREADY_PRESENT",
            "blocker_reason": "Producer source already contains hydra_v019_validate_vwap_onh_onl_population; refusing duplicate patch.",
        })
        return original, audit, blockers

    import_idx = find_import_insertion_index(lines)
    lines_with_helper = lines[:import_idx] + ["\n"] + snippet + ["\n"] + lines[import_idx:]
    audit.append({
        "event": "HELPER_INSERTED",
        "line_index_0_based": import_idx,
        "detail": "Inserted V019 validation helper after import/header block.",
        "row_variable": "",
    })

    insert_idx, row_var, reason = find_validation_insertion_point(lines_with_helper)
    if insert_idx is None or not row_var:
        blockers.append({
            "blocker_code": "NO_SAFE_VALIDATION_CALL_INSERTION_POINT",
            "blocker_reason": reason,
        })
        return "".join(lines_with_helper), audit, blockers

    indent = indent_of(lines_with_helper[insert_idx])
    call = (
        f"{indent}hydra_v019_validate_vwap_onh_onl_population(\n"
        f"{indent}    {row_var},\n"
        f"{indent}    required_fields={TARGET_FIELDS!r},\n"
        f"{indent}    source_label={source_label!r},\n"
        f"{indent})\n"
    )
    patched_lines = lines_with_helper[:insert_idx] + [call] + lines_with_helper[insert_idx:]
    audit.append({
        "event": "VALIDATION_CALL_INSERTED",
        "line_index_0_based": insert_idx,
        "detail": reason,
        "row_variable": row_var,
    })
    return "".join(patched_lines), audit, blockers


def compile_check(source_text: str, filename: str) -> Tuple[bool, str]:
    try:
        compile(source_text, filename, "exec")
        return True, ""
    except SyntaxError as exc:
        return False, f"SyntaxError line {exc.lineno}: {exc.msg}"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def smoke_fixture(out_dir: Path) -> Path:
    src = out_dir / "_smoke_primary_producer.py"
    src.write_text('''#!/usr/bin/env python3
import csv
from pathlib import Path

FIELDS = ["symbol", "session_date", "Open", "daily_vwap", "weekly_vwap", "monthly_vwap", "ONH", "ONL"]

def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

def main():
    upgraded_context_rows = [
        {"symbol": "ES", "session_date": "2025-03-26", "Open": "5831", "daily_vwap": "", "weekly_vwap": "", "monthly_vwap": "", "ONH": "", "ONL": ""},
        {"symbol": "NQ", "session_date": "2025-03-26", "Open": "20083.25", "daily_vwap": "", "weekly_vwap": "", "monthly_vwap": "", "ONH": "", "ONL": ""},
    ]
    write_csv("out.csv", upgraded_context_rows)

if __name__ == "__main__":
    main()
''', encoding="utf-8")
    v018 = out_dir / "_smoke_v018"
    v018.mkdir(parents=True, exist_ok=True)
    write_json(v018 / "run_summary_v018.json", {
        "primary_candidate_path": str(src),
        "schema_version": "SMOKE",
    })
    rows = []
    for field in TARGET_FIELDS:
        rows.append({
            "field_name": field,
            "code_map_status": "TARGET_FIELD_REFERENCED_WITH_ASSIGNMENT_OR_ROW_MAPPING",
            "source_lines": "6;13;14;17",
            "assignment_or_mapping_lines": "6;17",
            "interpretation": "smoke",
        })
    write_csv(v018 / "FIELD_POPULATION_CODE_MAP.csv", rows, ["field_name", "code_map_status", "source_lines", "assignment_or_mapping_lines", "interpretation"])
    write_csv(v018 / "PATCH_RECOMMENDATIONS.csv", [
        {"action_rank": "1", "action_type": "REVIEW_PRIMARY_PRODUCER_FIELD_ASSIGNMENTS", "target_path": str(src), "reason": "smoke"},
    ], ["action_rank", "action_type", "target_path", "reason"])
    return v018


def run(v018_dir: Path, out_dir: Path, producer_path: Optional[str] = None, smoke_test: bool = False) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    hard_errors: List[str] = []
    warnings: List[str] = []
    patch_audit: List[dict] = []
    patch_blockers: List[dict] = []

    if smoke_test:
        v018_dir = smoke_fixture(out_dir)

    primary_path, resolve_notes = resolve_primary_candidate(v018_dir, producer_path)
    source_exists = bool(primary_path and primary_path.exists())
    source_text = ""
    source_sha = ""
    source_lines: List[str] = []

    if not primary_path:
        hard_errors.append("Could not resolve primary producer path from V018 outputs.")
    elif not source_exists:
        hard_errors.append(f"Primary producer source does not exist: {primary_path}")
    else:
        source_text = read_text(primary_path)
        source_sha = sha256_path(primary_path)
        source_lines = source_text.splitlines(keepends=True)

    line_map = get_field_line_numbers(v018_dir) if v018_dir.exists() else {f: [] for f in TARGET_FIELDS}
    slices = extract_source_slices(source_lines, line_map) if source_lines else []

    snippet_path = out_dir / "V019_VALIDATION_GATE_SNIPPET.py"
    snippet_path.write_text(make_validation_snippet(), encoding="utf-8")

    patched_path = out_dir / "V019_PATCHED_PRIMARY_PRODUCER_COPY.py"
    diff_path = out_dir / "V019_UNIFIED_DIFF.patch"
    install_path = out_dir / "V019_INSTALL_PATCH_COMMANDS_REVIEW_ONLY.ps1"

    patched_written = False
    compile_ok = False
    compile_error = ""

    if source_text and primary_path:
        patched_text, audit, blockers = build_patched_source(source_text, str(primary_path))
        patch_audit.extend(audit)
        patch_blockers.extend(blockers)

        patched_path.write_text(patched_text, encoding="utf-8")
        patched_written = True

        compile_ok, compile_error = compile_check(patched_text, str(patched_path))
        if not compile_ok:
            patch_blockers.append({
                "blocker_code": "PATCHED_COPY_COMPILE_FAILED",
                "blocker_reason": compile_error,
            })

        diff_text = "\n".join(difflib.unified_diff(
            source_text.splitlines(),
            patched_text.splitlines(),
            fromfile=str(primary_path),
            tofile=str(patched_path),
            lineterm="",
        )) + "\n"
        diff_path.write_text(diff_text, encoding="utf-8")

        install_text = (
            "# V019 review-only install commands.\n"
            "# Do not run unless Cody explicitly accepts the patched copy after review.\n"
            f"$Original = \"{primary_path}\"\n"
            f"$Patched = \"{patched_path}\"\n"
            "$Backup = \"$Original.v019_backup_$(Get-Date -Format yyyyMMdd_HHmmss)\"\n"
            "Copy-Item $Original $Backup -Force\n"
            "Copy-Item $Patched $Original -Force\n"
            "Write-Host \"Installed V019 patched producer after backup: $Backup\"\n"
        )
        install_path.write_text(install_text, encoding="utf-8")
    else:
        patched_path.write_text("", encoding="utf-8")
        diff_path.write_text("", encoding="utf-8")
        install_path.write_text("# No install commands written because patch was blocked before source load.\n", encoding="utf-8")

    source_audit_rows = []
    if primary_path:
        source_audit_rows.append({
            "producer_path": str(primary_path),
            "source_exists": str(source_exists).lower(),
            "source_sha256_before": source_sha,
            "source_lines_loaded": str(len(source_lines)),
            "resolve_notes": " | ".join(resolve_notes),
            "mutation_performed": "false",
        })

    write_csv(out_dir / "V019_SOURCE_SLICE_FOR_PATCH_REVIEW.csv", slices, [
        "field_name", "focus_line", "line_no", "is_focus_line", "line_text", "contains_target_field", "contains_assignment_or_mapping"
    ])
    write_csv(out_dir / "V019_PATCH_AUDIT.csv", patch_audit, [
        "event", "line_index_0_based", "detail", "row_variable"
    ])
    write_csv(out_dir / "V019_PATCH_BLOCKERS.csv", patch_blockers, [
        "blocker_code", "blocker_reason"
    ])
    write_csv(out_dir / "V019_PRIMARY_PRODUCER_SOURCE_AUDIT.csv", source_audit_rows, [
        "producer_path", "source_exists", "source_sha256_before", "source_lines_loaded", "resolve_notes", "mutation_performed"
    ])

    run_status = "PASS_PATCHED_PRODUCER_COPY_WRITTEN"
    if hard_errors:
        run_status = "FAIL_HARD_ERRORS"
    elif patch_blockers:
        run_status = "BLOCKED_PATCH_REVIEW_REQUIRED"
    elif not compile_ok:
        run_status = "BLOCKED_PATCHED_COPY_COMPILE_FAILED"
    elif not patched_written:
        run_status = "BLOCKED_NO_PATCH_WRITTEN"

    report_lines = [
        "# V019 Producer Copy Patch + Validation Gate Report",
        "",
        f"- schema_version: `{SCHEMA_VERSION}`",
        f"- run_status: `{run_status}`",
        f"- created_at_utc: `{utc_now()}`",
        "- manual_input_requirement: `NOT_REQUIRED`",
        "- no_fake_enrichment_policy: `ENFORCED`",
        "- mutation_policy: `PATCHED_COPY_ONLY_NO_ORIGINAL_MUTATION`",
        "- patch_policy: `ADD_VALIDATION_GATE_FAILS_ON_BLANK_CANONICAL_VWAP_ONH_ONL_TARGET_ROWS`",
        "",
        "## Input",
        f"- v018_dir: `{v018_dir}`",
        f"- primary_producer_path: `{primary_path or ''}`",
        f"- source_exists: `{str(source_exists).lower()}`",
        f"- source_sha256_before: `{source_sha}`",
        "",
        "## Outputs",
        f"- patched_producer_copy: `{patched_path}`",
        f"- unified_diff: `{diff_path}`",
        f"- validation_gate_snippet: `{snippet_path}`",
        f"- source_slice_review: `{out_dir / 'V019_SOURCE_SLICE_FOR_PATCH_REVIEW.csv'}`",
        f"- patch_audit: `{out_dir / 'V019_PATCH_AUDIT.csv'}`",
        f"- patch_blockers: `{out_dir / 'V019_PATCH_BLOCKERS.csv'}`",
        f"- install_commands_review_only: `{install_path}`",
        "",
        "## Counts",
        f"- source_lines_loaded: `{len(source_lines)}`",
        f"- source_slice_rows: `{len(slices)}`",
        f"- patch_audit_rows: `{len(patch_audit)}`",
        f"- patch_blocker_rows: `{len(patch_blockers)}`",
        f"- hard_errors: `{len(hard_errors)}`",
        f"- warnings: `{len(warnings)}`",
        f"- patched_copy_compile_ok: `{str(compile_ok).lower()}`",
        "",
        "## Patch audit",
    ]
    if patch_audit:
        for row in patch_audit:
            report_lines.append(f"- `{row.get('event')}`: {row.get('detail')}")
    else:
        report_lines.append("- NONE")
    report_lines += ["", "## Blockers"]
    if patch_blockers:
        for row in patch_blockers:
            report_lines.append(f"- `{row.get('blocker_code')}`: {row.get('blocker_reason')}")
    else:
        report_lines.append("- NONE")
    report_lines += ["", "## Compile check"]
    if compile_ok:
        report_lines.append("- Patched producer copy compiles.")
    else:
        report_lines.append(f"- Compile failed or not attempted: `{compile_error or 'not attempted'}`")
    report_lines += [
        "",
        "## Contract outcome",
        "V019 wrote a reviewable patched producer copy and validation-gate diff without mutating the live producer. If accepted, install commands are provided as review-only PowerShell. This does not fabricate VWAP/ONH/ONL; it prevents blank canonical fields from silently passing.",
    ]
    (out_dir / "V019_PRODUCER_PATCH_QA_REPORT.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    summary = {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": utc_now(),
        "run_status": run_status,
        "manual_input_requirement": "NOT_REQUIRED",
        "no_fake_enrichment_policy": "ENFORCED",
        "mutation_policy": "PATCHED_COPY_ONLY_NO_ORIGINAL_MUTATION",
        "primary_producer_path": str(primary_path or ""),
        "source_exists": source_exists,
        "source_sha256_before": source_sha,
        "counts": {
            "source_lines_loaded": len(source_lines),
            "source_slice_rows": len(slices),
            "patch_audit_rows": len(patch_audit),
            "patch_blocker_rows": len(patch_blockers),
            "hard_errors": len(hard_errors),
            "warnings": len(warnings),
            "patched_written": int(patched_written),
            "patched_copy_compile_ok": int(compile_ok),
        },
        "hard_errors": hard_errors,
        "warnings": warnings,
        "outputs": {
            "patched_producer_copy": str(patched_path),
            "unified_diff": str(diff_path),
            "validation_gate_snippet": str(snippet_path),
            "source_slice_review": str(out_dir / "V019_SOURCE_SLICE_FOR_PATCH_REVIEW.csv"),
            "patch_audit": str(out_dir / "V019_PATCH_AUDIT.csv"),
            "patch_blockers": str(out_dir / "V019_PATCH_BLOCKERS.csv"),
            "qa_report": str(out_dir / "V019_PRODUCER_PATCH_QA_REPORT.md"),
            "install_commands_review_only": str(install_path),
            "run_summary": str(out_dir / "run_summary_v019.json"),
        },
    }
    write_json(out_dir / "run_summary_v019.json", summary)
    return summary


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="HYDRA V019 producer copy patch + validation gate")
    ap.add_argument("--v018-dir", default="", help="V018 output directory")
    ap.add_argument("--producer-path", default="", help="Optional explicit primary producer path")
    ap.add_argument("--out-dir", required=True, help="Output directory")
    ap.add_argument("--smoke-test", action="store_true", help="Run against built-in smoke fixture")
    args = ap.parse_args(argv)

    v018_dir = Path(args.v018_dir) if args.v018_dir else Path(".")
    out_dir = Path(args.out_dir)

    summary = run(
        v018_dir=v018_dir,
        out_dir=out_dir,
        producer_path=args.producer_path or None,
        smoke_test=args.smoke_test,
    )
    print(json.dumps({
        "run_status": summary["run_status"],
        "out_dir": str(out_dir),
        "primary_producer_path": summary.get("primary_producer_path"),
        "counts": summary.get("counts"),
        "outputs": summary.get("outputs"),
    }, indent=2))
    return 0 if not summary.get("hard_errors") else 2


if __name__ == "__main__":
    raise SystemExit(main())
