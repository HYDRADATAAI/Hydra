from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "constraint-t1-raw-artifact-store" / "src"
sys.path.insert(0, str(SRC))

from hydra_constraint_t1_raw.browser_response_capture import (  # noqa: E402
    BrowserResponseCaptureError,
    extract_exact_response,
)


SOURCES = (
    {
        "source_id": "SRC-LBNL-QUEUED-UP-2025",
        "argument": "lbnl_har",
        "exact_url": "https://emp.lbl.gov/publications/queued-2025-edition-characteristics",
        "expected_text": "Queued Up: 2025 Edition",
    },
    {
        "source_id": "SRC-FERC-ORDER-2023-FACT-SHEET",
        "argument": "ferc_har",
        "exact_url": "https://www.ferc.gov/news-events/news/fact-sheet-improvements-generator-interconnection-procedures-and-agreements",
        "expected_text": "Fact Sheet | Improvements to Generator Interconnection Procedures and Agreements",
    },
    {
        "source_id": "SRC-PJM-2025-YEAR-IN-REVIEW-2026-01-08",
        "argument": "pjm_har",
        "exact_url": "https://insidelines.pjm.com/2025-year-in-review-planning-prepares-for-burgeoning-electricity-demand/",
        "expected_text": "2025 Year in Review: Planning Prepares for Burgeoning Electricity Demand",
    },
)


def _outside_repo(path: Path, repo: Path, label: str) -> Path:
    resolved = path.expanduser().resolve()
    repo = repo.expanduser().resolve()
    if resolved == repo or resolved.is_relative_to(repo):
        raise BrowserResponseCaptureError(f"{label} must remain outside the public repository")
    return resolved


def _load_har(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise BrowserResponseCaptureError(f"unable to parse HAR JSON: {path}") from exc
    if not isinstance(value, dict):
        raise BrowserResponseCaptureError(f"HAR top-level object required: {path}")
    return value


def validate_three_hars(
    *,
    lbnl_har: str | Path,
    ferc_har: str | Path,
    pjm_har: str | Path,
    public_repo_root: str | Path,
) -> dict:
    repo = Path(public_repo_root).expanduser().resolve()
    supplied = {
        "lbnl_har": Path(lbnl_har),
        "ferc_har": Path(ferc_har),
        "pjm_har": Path(pjm_har),
    }

    results = []
    for source in SOURCES:
        har_path = _outside_repo(
            supplied[source["argument"]],
            repo,
            f'{source["source_id"]} HAR',
        )
        if not har_path.is_file():
            raise BrowserResponseCaptureError(
                f'{source["source_id"]}: sanitized HAR file not found'
            )

        body, metadata = extract_exact_response(
            har=_load_har(har_path),
            exact_url=source["exact_url"],
            expected_mime_prefix="text/html",
            expected_text=source["expected_text"],
        )

        results.append({
            "source_id": source["source_id"],
            "exact_url": source["exact_url"],
            "status": metadata["status"],
            "mime_type": metadata["mime_type"],
            "started_date_time": metadata["started_date_time"],
            "body_sha256": metadata["body_sha256"],
            "byte_length": len(body),
            "capture_method": metadata["capture_method"],
            "rendered_dom_used": metadata["rendered_dom_used"],
            "linked_file_substituted": metadata["linked_file_substituted"],
            "cloudflare_bypass_attempted": metadata["cloudflare_bypass_attempted"],
        })

    return {
        "schema_version": "hydra-constraint-three-source-sanitized-har-preflight/v1",
        "slice_id": "AI_DATA_CENTER_POWER_INFRASTRUCTURE_V1",
        "source_count": 3,
        "preflight_only": True,
        "capture_plan_created": False,
        "t1_objects_created": False,
        "t1_receipts_created": False,
        "t1_release_created": False,
        "raw_bodies_written_by_preflight": False,
        "ordinary_replay_promoted": False,
        "canonical_admission_promoted": False,
        "results": sorted(results, key=lambda row: row["source_id"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the three private sanitized HARs for exact registered "
            "LBNL/FERC/PJM document responses without creating T1 records."
        )
    )
    parser.add_argument("--lbnl-har", required=True)
    parser.add_argument("--ferc-har", required=True)
    parser.add_argument("--pjm-har", required=True)
    parser.add_argument("--public-repo-root", default=str(ROOT))
    parser.add_argument("--summary-output")
    args = parser.parse_args()

    try:
        summary = validate_three_hars(
            lbnl_har=args.lbnl_har,
            ferc_har=args.ferc_har,
            pjm_har=args.pjm_har,
            public_repo_root=args.public_repo_root,
        )

        if args.summary_output:
            output = _outside_repo(
                Path(args.summary_output),
                Path(args.public_repo_root),
                "summary output",
            )
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(
                json.dumps(summary, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
    except BrowserResponseCaptureError as exc:
        print("HYDRA_THREE_SOURCE_HAR_PREFLIGHT=FAIL")
        print(f"ERROR={exc}")
        return 1

    print("HYDRA_THREE_SOURCE_HAR_PREFLIGHT=PASS")
    print("SOURCE_COUNT=3")
    for row in summary["results"]:
        print(
            "SOURCE_OK="
            + row["source_id"]
            + " sha256="
            + row["body_sha256"]
            + " bytes="
            + str(row["byte_length"])
        )
    print("CAPTURE_PLAN_CREATED=NO")
    print("T1_OBJECTS_CREATED=NO")
    print("T1_RELEASE_CREATED=NO")
    print("ORDINARY_REPLAY_PROMOTED=NO")
    print("CANONICAL_ADMISSION_PROMOTED=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
