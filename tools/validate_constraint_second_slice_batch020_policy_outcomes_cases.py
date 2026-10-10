#!/usr/bin/env python3
"""Validate Thread 6 Successor Batch020 semiconductor policy/substitution/outcome case depth."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("HYDRA_REPO_ROOT", Path(__file__).resolve().parents[1])).resolve()
BASE = ROOT / "docs" / "constraint" / "second_slice" / "semiconductor_advanced_packaging_critical_materials_v1"
ARCH = ROOT / "docs" / "constraint" / "architecture"
VAL = ROOT / "docs" / "constraint" / "validation"
SLICE = "SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1"
CAPTURE = "2026-09-26T21:28:33Z"

FILES = {
    "sources": BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH020_SEMICONDUCTOR_POLICY_SUBSTITUTION_OUTCOME_SOURCE_REGISTRY_EXTENSION_V001_20260926.json",
    "evidence": BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH020_SEMICONDUCTOR_POLICY_SUBSTITUTION_OUTCOME_EVIDENCE_SUPPLEMENT_V001_20260926.json",
    "policy": BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH020_SEMICONDUCTOR_EXPORT_POLICY_TIMELINE_OVERLAY_V001_20260926.json",
    "ramp": BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH020_TSMC_ARIZONA_RAMP_HISTORY_OUTCOME_OVERLAY_V001_20260926.json",
    "substitution": BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH020_SEMICONDUCTOR_SUBSTITUTION_EVALUATION_V001_20260926.json",
    "beneficiary": BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH020_SEMICONDUCTOR_FALSE_BENEFICIARY_EVALUATION_V001_20260926.json",
    "cases": BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH020_SEMICONDUCTOR_REQUIRED_CASE_OVERLAY_V001_20260926.json",
    "status": BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH020_SEMICONDUCTOR_POLICY_SUBSTITUTION_OUTCOME_STATUS_V001_20260926.json",
    "master": ARCH / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH020_MASTER_STATUS_V001_20260926.json",
    "manifest": VAL / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH020_ARTIFACT_MANIFEST_V001_20260926.json",
    "b19_cases": BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH019_SEMICONDUCTOR_REQUIRED_CASE_PROGRESS_V001_20260926.json",
    "b19_master": ARCH / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH019_MASTER_STATUS_V001_20260926.json",
    "b18_candidates": BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_T5_CANDIDATE_PROPOSALS_V001_20260926.json",
    "b18_evidence": BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_EVIDENCE_SEED_V001_20260926.json",
    "b19_evidence": BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH019_SEMICONDUCTOR_FACILITY_MATERIAL_EQUIPMENT_EVIDENCE_SUPPLEMENT_V001_20260926.json",
}

class ValidationFailure(Exception):
    pass

def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)

def load(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"required artifact missing: {path.relative_to(ROOT)}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value

def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()

def unique(rows: list[dict[str, Any]], field: str, label: str) -> set[str]:
    vals = [r.get(field) for r in rows]
    require(all(isinstance(v, str) and v for v in vals), f"{label}: invalid {field}")
    require(len(vals) == len(set(vals)), f"{label}: duplicate {field}")
    return set(vals)

def load_documents() -> dict[str, dict[str, Any]]:
    return {key: load(path) for key, path in FILES.items()}

def validate_documents(d: dict[str, dict[str, Any]]) -> dict[str, Any]:
    for key in ("sources","evidence","policy","ramp","substitution","beneficiary","cases","status"):
        require(d[key].get("slice_id") == SLICE, f"{key}: slice drift")

    # Predecessor immutability/current baseline.
    require(d["b19_master"].get("record_id") == "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH019_MASTER_STATUS_V001",
            "Batch019 master drift")
    require(d["b19_cases"].get("covered_case_count_after") == 2, "Batch019 coverage baseline drift")
    require(d["b19_cases"].get("remaining_gap_case_ids") == list(range(3,15)), "Batch019 gap baseline drift")

    # Sources are current-review only.
    src = d["sources"]
    rows = src.get("sources", [])
    require(len(rows) == 6, "source count drift")
    require(src.get("capture_completed_at") == CAPTURE, "capture timestamp drift")
    require(src.get("source_content_persisted") is False, "raw persistence falsely claimed")
    source_ids = unique(rows, "source_id", "sources")
    for row in rows:
        require(row.get("acquired_at") == CAPTURE and row.get("available_at") == CAPTURE,
                f"{row.get('source_id')}: current-review availability drift")
        require(row.get("ordinary_raw_lineage_eligible") is False,
                f"{row.get('source_id')}: ordinary raw lineage falsely enabled")
        require(row.get("availability_basis") == "HYDRA_FIRST_DEFENSIBLE_GITHUB_REVIEW_ARTIFACT_COMMIT",
                f"{row.get('source_id')}: availability basis drift")

    # Evidence and predecessor references.
    ev = d["evidence"]
    ev_rows = ev.get("evidence", [])
    require(len(ev_rows) == 6, "evidence count drift")
    new_eids = unique(ev_rows, "evidence_id", "evidence")
    b18_eids = {r.get("evidence_id") for r in d["b18_evidence"].get("evidence", [])}
    b19_eids = {r.get("evidence_id") for r in d["b19_evidence"].get("evidence", [])}
    all_eids = new_eids | b18_eids | b19_eids
    for row in ev_rows:
        require(row.get("source_id") in source_ids, f"{row.get('evidence_id')}: unresolved source")
        require(row.get("available_at") == CAPTURE, f"{row.get('evidence_id')}: available_at drift")
        require(isinstance(row.get("semantic_limit"), str) and row["semantic_limit"],
                f"{row.get('evidence_id')}: semantic firewall missing")
    require(ev.get("historical_replay_eligible") is False, "new evidence falsely replay eligible")

    # Policy clocks stay separate and fail closed.
    policy = d["policy"]
    events = policy.get("events", [])
    require(len(events) == 1, "policy event count drift")
    pe = events[0]
    require(pe.get("effective_at") == "2024-12-02", "policy effective date drift")
    require(pe.get("hbm_compliance_at") == "2024-12-31", "HBM compliance date drift")
    require(pe.get("known_at") == CAPTURE and pe.get("observed_at") == CAPTURE, "policy known/observed time drift")
    require(pe.get("effective_at") != pe.get("known_at"), "historical effective date collapsed into Hydra known_at")
    require(pe.get("ordinary_replay_eligible") is False, "policy falsely ordinary-replay eligible")
    require("PUBLIC_INSPECTION_AT_NE_HYDRA_KNOWN_AT" in pe.get("semantic_firewalls", []),
            "policy publication/known firewall missing")
    require("EFFECTIVE_AT_NE_HBM_COMPLIANCE_AT" in pe.get("semantic_firewalls", []),
            "policy effective/compliance firewall missing")
    require(set(pe.get("evidence_ids", [])) <= all_eids, "policy evidence unresolved")

    # Arizona preserves original, delayed, actual states.
    ramp = d["ramp"]
    timeline = ramp.get("timeline", [])
    require(len(timeline) == 3, "Arizona ramp timeline count drift")
    by = {r["state_id"]: r for r in timeline}
    original = by["ARIZONA-RAMP-2020-ORIGINAL"]
    delayed = by["ARIZONA-RAMP-2023-DELAY"]
    actual = by["ARIZONA-RAMP-2024-ACTUAL"]
    require(original.get("target_production_period") == "2024", "original Arizona 2024 target rewritten")
    require(original.get("process_plan") == "5NM", "original Arizona process plan rewritten")
    require(original.get("announced_capacity") == {"value":20000,"unit":"WAFERS_PER_MONTH"},
            "original Arizona announced capacity drift")
    require(delayed.get("target_production_period") == "2025", "Arizona delayed target drift")
    require(delayed.get("process_plan") == "N4", "Arizona revised N4 plan drift")
    require(delayed.get("delay_cause") == "INSUFFICIENT_SPECIALIZED_SKILLED_WORKERS_FOR_EQUIPMENT_INSTALLATION",
            "Arizona delay cause drift")
    require(actual.get("effective_period") == "2024-Q4" and actual.get("process_actual") == "N4",
            "Arizona actual state drift")
    require(actual.get("realized_capacity_value") is None, "original announced capacity smuggled into realized capacity")
    outcome = ramp.get("outcome", {})
    require(outcome.get("original_announced_capacity_carried_forward_to_actual") is False,
            "announced capacity carried into actual")
    require(outcome.get("historical_replay_eligible") is False, "Arizona current-review timeline falsely replay eligible")

    # Parent constraint exists and remains shadow.
    candidates = {r.get("constraint_candidate_id"): r for r in d["b18_candidates"].get("candidates", [])}
    parent = candidates.get("T5C-SEMI-HBM-BOOKED-SUPPLY-2024-2025-001")
    require(parent is not None, "HBM parent constraint candidate missing")
    require(parent.get("ordinary_t6_eligible") is False, "HBM parent candidate ordinary-T6 promoted")

    # Potential substitution must remain unqualified.
    sub = d["substitution"]
    subs = sub.get("evaluations", [])
    require(len(subs) == 1 and sub.get("qualified_substitution_count") == 0, "substitution count/qualification drift")
    se = subs[0]
    require(se.get("parent_constraint_candidate_id") == parent["constraint_candidate_id"], "substitution parent drift")
    require(se.get("technical_capability_state") == "PARTIAL_PROVEN", "Samsung technical capability drift")
    require(se.get("specific_target_qualification_state") == "UNKNOWN_NOT_PROVEN", "Samsung qualification invented")
    require(se.get("unbooked_addressable_capacity_state") == "UNKNOWN_NOT_PROVEN", "Samsung spare capacity invented")
    require(se.get("switching_time_state") == "UNKNOWN_NOT_PROVEN", "Samsung switching time invented")
    require(se.get("commercial_capture_state") == "UNKNOWN_NOT_PROVEN", "Samsung capture invented")
    require(se.get("substitution_state") == "POTENTIAL_NOT_QUALIFIED", "Samsung substitution falsely qualified")
    require(se.get("ordinary_t6_eligible") is False, "Samsung substitution ordinary-T6 promoted")
    require(set(se.get("evidence_ids", [])) <= all_eids, "substitution evidence unresolved")

    # False beneficiary is explicitly rejected.
    ben = d["beneficiary"]
    rels = ben.get("relationships", [])
    require(len(rels) == 1, "beneficiary evaluation count drift")
    require(ben.get("qualified_relationship_count") == 0, "qualified beneficiary falsely added")
    require(ben.get("false_beneficiary_rejection_count") == 1, "false-beneficiary rejection count drift")
    br = rels[0]
    require(br.get("constraint_candidate_id") == parent["constraint_candidate_id"], "beneficiary parent drift")
    require(br.get("qualification_state") == "INELIGIBLE_TO_EVALUATE", "beneficiary qualification escaped fail closed")
    require(br.get("case_disposition") == "FALSE_BENEFICIARY_REJECTED", "false beneficiary disposition drift")
    require(br.get("eligibility_state") == "BLOCKED", "beneficiary eligibility escaped BLOCKED")
    lineage = br.get("evidence_lineage", {})
    require(lineage.get("capacity_or_availability") == [], "unproven Samsung capacity/availability invented")
    require(lineage.get("economic_or_strategic_capture") == [], "unproven Samsung capture invented")
    require(len(lineage.get("disconfirming_or_blocking", [])) >= 3, "false beneficiary blockers incomplete")

    # Required cases: exactly 7,9,13 added; 10/12 progress only.
    cases = d["cases"]
    require(cases.get("covered_case_count_before") == 2, "Batch020 case baseline drift")
    require(cases.get("covered_case_count_after") == 5, "Batch020 case coverage drift")
    updates = {r.get("case_id"):r for r in cases.get("updates", [])}
    require(set(updates) == {7,9,13}, "Batch020 covered-case set drift")
    require(all(r.get("successor_status") == "COVERED_REVIEWED_SHADOW_REAL_PRIMARY_BOUNDED"
                for r in updates.values()), "Batch020 case coverage scope drift")
    progress = {r.get("case_id"):r for r in cases.get("progress_only", [])}
    require(set(progress) == {10,12}, "Batch020 progress-only set drift")
    require(cases.get("remaining_gap_case_ids") == [3,4,5,6,8,10,11,12,14], "remaining case gaps drift")

    # Status/master remain blocked.
    status = d["status"]
    res = status.get("results", {})
    expected = {
        "PRIMARY_SOURCES_ADDED":6,
        "EVIDENCE_OBSERVATIONS_ADDED":6,
        "POLICY_TIMELINES_ADDED":1,
        "RAMP_HISTORY_OUTCOMES_ADDED":1,
        "SUBSTITUTION_EVALUATIONS_ADDED":1,
        "QUALIFIED_SUBSTITUTIONS_ADDED":0,
        "BENEFICIARY_EVALUATIONS_ADDED":1,
        "FALSE_BENEFICIARIES_REJECTED":1,
        "QUALIFIED_BENEFICIARIES_ADDED":0,
        "REQUIRED_CASES_COVERED":5,
        "REQUIRED_CASES_TOTAL":14,
        "CANONICAL_CONSTRAINTS_MINTED":0,
        "HISTORICAL_REPLAY":"BLOCKED_RAW_SOURCE_VERSIONS_NOT_MATERIALIZED",
        "FIRST_SEMICONDUCTOR_RUN":"BLOCKED",
    }
    for key,val in expected.items():
        require(res.get(key) == val, f"status metric drift: {key}")
    require(res.get("NEW_REQUIRED_CASES_COVERED") == [7,9,13], "status new-case set drift")
    require(res.get("PROGRESS_ONLY_CASES") == [10,12], "status progress-only set drift")
    require(status.get("next_repo_executable_lane") ==
            "SECOND-SLICE-VALID-BENEFICIARY-SUBSTITUTION-MIGRATION-AND-CROSS-SLICE-POWER-DEPTH",
            "Batch020 next lane drift")

    master = d["master"]
    rd = master.get("readiness", {})
    require(rd.get("SECOND_SLICE_EXPORT_POLICY_TIMING", {}).get("status") == "PASS_REVIEWED_SHADOW",
            "master policy timing drift")
    require(rd.get("SECOND_SLICE_FALSE_BENEFICIARY_GOVERNANCE", {}).get("status") == "PASS_REVIEWED_SHADOW",
            "master false-beneficiary governance drift")
    require(rd.get("SECOND_SLICE_SUBSTITUTION", {}).get("status") == "PARTIAL_NOT_QUALIFIED",
            "master substitution falsely ready")
    require(rd.get("SECOND_SLICE_REQUIRED_CASES", {}).get("covered") == 5, "master case coverage drift")
    require(rd.get("SECOND_SLICE_REPLAY_READY", {}).get("status") == "NO", "master replay falsely ready")
    require(rd.get("FULL_CONSTRAINT_RUN_READY", {}).get("status") == "NO", "master full run falsely ready")
    require(master.get("first_serious_constraint_run") == "BLOCKED", "master serious run falsely ready")

    # Manifest integrity.
    manifest = d["manifest"]
    require(manifest.get("result") == "PASS_POLICY_SUBSTITUTION_OUTCOME_REQUIRED_CASE_DEPTH_PARTIAL",
            "manifest result drift")
    exp = manifest.get("expected", {})
    require(exp.get("required_cases_covered") == "5/14", "manifest case count drift")
    require(exp.get("new_required_cases_covered") == [7,9,13], "manifest new-case set drift")
    require(exp.get("qualified_beneficiaries_added") == 0, "manifest beneficiary promotion")
    require(exp.get("qualified_substitutions_added") == 0, "manifest substitution promotion")
    require(exp.get("historical_replay") == "BLOCKED", "manifest replay promotion")
    require(exp.get("first_semiconductor_run") == "BLOCKED", "manifest run promotion")
    seen: set[str] = set()
    for art in manifest.get("artifacts", []):
        rel = art.get("path")
        sha = art.get("git_blob_sha")
        require(isinstance(rel,str) and rel and rel not in seen, "manifest duplicate/invalid path")
        seen.add(rel)
        p = ROOT / rel
        require(p.is_file(), f"manifest artifact missing: {rel}")
        require(git_blob_sha(p) == sha, f"manifest blob pin mismatch: {rel}")

    return {
        "sources":len(rows),
        "evidence":len(ev_rows),
        "covered":cases["covered_case_count_after"],
        "false_beneficiaries":ben["false_beneficiary_rejection_count"],
        "qualified_substitutions":sub["qualified_substitution_count"],
    }

def main() -> int:
    try:
        result = validate_documents(load_documents())
    except (ValidationFailure,json.JSONDecodeError,KeyError,TypeError,OSError) as exc:
        print("CONSTRAINT_SECOND_SLICE_BATCH020_VALIDATION=FAIL")
        print(f"ERROR={exc}")
        return 1
    print("CONSTRAINT_SECOND_SLICE_BATCH020_VALIDATION=PASS")
    print(f"PRIMARY_SOURCES_ADDED={result['sources']}")
    print(f"EVIDENCE_OBSERVATIONS_ADDED={result['evidence']}")
    print(f"FALSE_BENEFICIARIES_REJECTED={result['false_beneficiaries']}")
    print(f"QUALIFIED_SUBSTITUTIONS_ADDED={result['qualified_substitutions']}")
    print(f"REQUIRED_CASES_COVERED={result['covered']}/14")
    print("NEW_REQUIRED_CASES_COVERED=7,9,13")
    print("HISTORICAL_REPLAY=BLOCKED")
    print("FIRST_SEMICONDUCTOR_RUN=BLOCKED")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
