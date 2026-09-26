#!/usr/bin/env python3
"""Validate Thread 6 Successor Batch019 semiconductor facility/material/equipment deepening."""

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

FILES = {
    "sources": BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH019_SEMICONDUCTOR_FACILITY_MATERIAL_EQUIPMENT_SOURCE_REGISTRY_EXTENSION_V001_20260926.json",
    "evidence": BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH019_SEMICONDUCTOR_FACILITY_MATERIAL_EQUIPMENT_EVIDENCE_SUPPLEMENT_V001_20260926.json",
    "population": BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH019_SEMICONDUCTOR_FACILITY_MATERIAL_EQUIPMENT_QUALIFICATION_OVERLAY_V001_20260926.json",
    "graph": BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH019_SEMICONDUCTOR_FACILITY_MATERIAL_EQUIPMENT_GRAPH_OVERLAY_V001_20260926.json",
    "outcome": BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH019_SEMICONDUCTOR_HISTORICAL_OUTCOME_OVERLAY_V001_20260926.json",
    "cases": BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH019_SEMICONDUCTOR_REQUIRED_CASE_PROGRESS_V001_20260926.json",
    "status": BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH019_SEMICONDUCTOR_FACILITY_MATERIAL_EQUIPMENT_QUALIFICATION_STATUS_V001_20260926.json",
    "master": ARCH / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH019_MASTER_STATUS_V001_20260926.json",
    "manifest": VAL / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH019_ARTIFACT_MANIFEST_V001_20260926.json",
    "b18_sources": BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_SOURCE_REGISTRY_V001_20260926.json",
    "b18_evidence": BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_EVIDENCE_SEED_V001_20260926.json",
    "b18_graph": BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_GRAPH_SEED_V001_20260926.json",
    "b18_cases": BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_REQUIRED_CASE_OVERLAY_V001_20260926.json",
    "b18_master": ARCH / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_MASTER_STATUS_V001_20260926.json",
}

SLICE = "SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1"
CAPTURE = "2026-09-26T21:17:39Z"


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


def unique_ids(rows: list[dict[str, Any]], field: str, label: str) -> set[str]:
    vals = [row.get(field) for row in rows]
    require(all(isinstance(v, str) and v for v in vals), f"{label}: invalid {field}")
    require(len(vals) == len(set(vals)), f"{label}: duplicate {field}")
    return set(vals)


def validate_documents(d: dict[str, dict[str, Any]]) -> dict[str, Any]:
    for key in ("sources", "evidence", "population", "graph", "outcome", "cases", "status"):
        require(d[key].get("slice_id") == SLICE, f"{key}: slice drift")

    # Predecessor stays frozen and establishes the current 2/14 baseline.
    require(d["b18_master"].get("record_id") == "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_MASTER_STATUS_V001",
            "Batch018 predecessor master drift")
    require(d["b18_cases"].get("covered_case_count_after") == 2, "Batch018 case baseline drift")
    require(d["b18_cases"].get("remaining_gap_case_ids") == list(range(3, 15)), "Batch018 gap baseline drift")

    # Source extension: current review only, no raw-lineage promotion.
    src = d["sources"]
    rows = src.get("sources", [])
    require(len(rows) == 10, "Batch019 source extension count drift")
    require(src.get("capture_completed_at") == CAPTURE, "Batch019 capture timestamp drift")
    require(src.get("source_content_persisted") is False, "Batch019 falsely claims raw source persistence")
    source_ids = unique_ids(rows, "source_id", "sources")
    predecessor_source_ids = {r.get("source_id") for r in d["b18_sources"].get("sources", [])}
    require(set(src.get("reused_source_ids", [])) <= predecessor_source_ids, "reused source IDs unresolved")
    for row in rows:
        require(row.get("acquired_at") == CAPTURE and row.get("available_at") == CAPTURE,
                f"{row.get('source_id')}: conservative current-review availability drift")
        require(row.get("ordinary_raw_lineage_eligible") is False,
                f"{row.get('source_id')}: ordinary raw lineage falsely enabled")
        require(row.get("availability_basis") == "HYDRA_FIRST_DEFENSIBLE_GITHUB_REVIEW_ARTIFACT_COMMIT",
                f"{row.get('source_id')}: availability basis drift")

    # New evidence is current-reviewed only and resolves to predecessor/new source authority.
    ev = d["evidence"]
    ev_rows = ev.get("evidence", [])
    require(len(ev_rows) == 14, "Batch019 evidence count drift")
    evidence_ids = unique_ids(ev_rows, "evidence_id", "evidence")
    predecessor_evidence_ids = {r.get("evidence_id") for r in d["b18_evidence"].get("evidence", [])}
    all_source_ids = source_ids | predecessor_source_ids
    for row in ev_rows:
        require(row.get("source_id") in all_source_ids, f"{row.get('evidence_id')}: unresolved source")
        require(row.get("available_at") == CAPTURE, f"{row.get('evidence_id')}: available_at drift")
        require(isinstance(row.get("semantic_limit"), str) and row["semantic_limit"],
                f"{row.get('evidence_id')}: semantic firewall missing")
    require(ev.get("historical_replay_eligible") is False, "new evidence falsely replay eligible")

    # Population counts and semantic state separation.
    pop = d["population"]
    require(pop.get("available_at") == CAPTURE, "population available_at drift")
    require(len(pop.get("companies_added", [])) == 3, "company add count drift")
    require(len(pop.get("facilities_added", [])) == 3, "facility add count drift")
    require(len(pop.get("equipment_added", [])) == 2, "equipment add count drift")
    require(len(pop.get("materials_added", [])) == 6, "material add count drift")
    require(len(pop.get("technologies_and_processes_added", [])) == 4, "technology/process add count drift")
    require(len(pop.get("qualification_observations", [])) == 2, "qualification observation count drift")
    require(len(pop.get("policy_events_added", [])) == 1, "policy event count drift")

    facilities = {r["facility_id"]: r for r in pop["facilities_added"]}
    ap6 = facilities["FAC-SEMI-TSMC-AP6-ZHUNAN"]
    require(ap6.get("available_capacity") is None, "AP6 design capacity promoted to available capacity")
    require(ap6.get("lifecycle_state") == "OPENED_PREPARED_FOR_MASS_PRODUCTION", "AP6 lifecycle drift")
    require(len(ap6.get("stated_design_capacity", [])) == 2, "AP6 design capacity observations missing")
    require("STATED_DESIGN_CAPACITY_NE_AVAILABLE_OR_UNBOOKED_CAPACITY" in ap6.get("semantic_limit", ""),
            "AP6 design-capacity firewall missing")

    amkor = facilities["FAC-SEMI-AMKOR-VIETNAM-BAC-NINH"]
    require(amkor.get("available_capacity") is None, "Amkor cleanroom plan promoted to available capacity")
    require("production_capacity" not in amkor, "Amkor cleanroom area fabricated into production capacity")
    require(amkor.get("lifecycle_state") == "OPENED_PHASED_RAMP", "Amkor lifecycle drift")

    arizona = facilities["FAC-SEMI-TSMC-ARIZONA-FIRST-FAB"]
    require(arizona.get("lifecycle_state") == "OPERATIONAL_HIGH_VOLUME_PRODUCTION", "Arizona HVM state drift")
    require(arizona.get("effective_from") == "2024-Q4", "Arizona actual timing drift")
    for fld in ("installed_capacity", "available_capacity", "effective_capacity"):
        require(arizona.get(fld) is None, f"Arizona fabricated {fld}")

    materials = {r["material_id"]: r for r in pop["materials_added"]}
    require(materials["MAT-SILICA-QUARTZITE"].get("material_grade") == "UNSPECIFIED_NATURAL_RESOURCE",
            "raw silica promoted to semiconductor grade")
    require(materials["MAT-SILICON-METAL"].get("material_grade") == "METALLURGICAL_OR_BROAD_SILICON_MATERIAL",
            "broad silicon metal promoted to semiconductor grade")
    require("HIGH_PURITY" in materials["MAT-HIGH-PURITY-POLYSILICON"].get("material_grade", ""),
            "high-purity polysilicon stage missing")
    require(materials["MAT-SILICON-WAFER"].get("material_grade") == "SEMICONDUCTOR_WAFER",
            "semiconductor wafer stage missing")

    qual = {r["observation_id"]: r for r in pop["qualification_observations"]}
    qn = qual["QUALOBS-NVIDIA-NEW-PRODUCT-2024-001"]
    require(qn.get("qualification_state") == "TIME_REQUIRED_UNQUANTIFIED", "NVIDIA qualification duration fabricated")
    require("qualification_duration_days" not in qn, "NVIDIA qualification duration fabricated numerically")
    qm = qual["QUALOBS-MICRON-HBM3E12H-2025-B019-REF"]
    require(qm.get("predecessor_observation_id") == "CAPOBS-MICRON-HBM3E12H-RAMP-001",
            "Micron qualification predecessor reuse lost")

    policy = pop["policy_events_added"][0]
    require(policy.get("effective_at") is None, "ASML policy exact effective_at fabricated")
    require(policy.get("known_at") == CAPTURE, "ASML policy known_at drift")

    # Graph overlay must resolve nodes/evidence and preserve the material-stage chain.
    graph = d["graph"]
    require(graph.get("edges_added_count") == 29 and len(graph.get("edges_added", [])) == 29,
            "graph edge count drift")
    new_nodes = set(graph.get("nodes_added", []))
    predecessor_nodes = {r.get("node_id") for r in d["b18_graph"].get("nodes", [])}
    allowed_nodes = new_nodes | predecessor_nodes
    all_evidence_ids = evidence_ids | predecessor_evidence_ids
    edge_ids = unique_ids(graph["edges_added"], "edge_id", "graph")
    del edge_ids
    edge_by = {r["edge_id"]: r for r in graph["edges_added"]}
    for edge in graph["edges_added"]:
        require(edge.get("from") in allowed_nodes and edge.get("to") in allowed_nodes,
                f"{edge.get('edge_id')}: unresolved endpoint")
        refs = edge.get("evidence_ids", [])
        require(refs, f"{edge.get('edge_id')}: evidence missing")
        require(set(refs) <= all_evidence_ids, f"{edge.get('edge_id')}: unresolved evidence")

    chain = [
        ("SEMI-B019-E017", "MAT-SILICA-QUARTZITE", "MAT-SILICON-METAL"),
        ("SEMI-B019-E018", "MAT-SILICON-METAL", "MAT-HIGH-PURITY-POLYSILICON"),
        ("SEMI-B019-E019", "MAT-HIGH-PURITY-POLYSILICON", "PROCESS-CZ-CRYSTAL-GROWTH"),
        ("SEMI-B019-E021", "PROCESS-CZ-CRYSTAL-GROWTH", "MAT-MONOCRYSTALLINE-SILICON-INGOT"),
        ("SEMI-B019-E022", "MAT-MONOCRYSTALLINE-SILICON-INGOT", "MAT-SILICON-WAFER"),
        ("SEMI-B019-E023", "MAT-SILICON-WAFER", "CLASS-SEMICONDUCTOR-DEVICE"),
    ]
    for eid, frm, to in chain:
        require(edge_by[eid].get("from") == frm and edge_by[eid].get("to") == to,
                f"material chain drift: {eid}")

    concentration = edge_by["SEMI-B019-E025"]
    require("NOT_SEMICONDUCTOR_GRADE_SHARE" in concentration.get("semantic_limit", ""),
            "broad silicon concentration promoted to semiconductor-grade concentration")
    require(concentration.get("scope") == "BROAD_SILICON_MATERIALS_2023", "silicon concentration scope drift")

    policy_edge = edge_by["SEMI-B019-E016"]
    require("NOT_COMPLETE_CUTOFF" in policy_edge.get("semantic_limit", ""),
            "partial ASML restriction promoted to complete cutoff")
    qual_edge = edge_by["SEMI-B019-E028"]
    require(qual_edge.get("semantic_limit") == "DURATION_UNQUANTIFIED", "qualification duration invented")

    # Outcome must preserve plan and successor fact without granting replay.
    outcome = d["outcome"]
    outs = outcome.get("outcomes", [])
    require(outcome.get("outcome_count") == 1 and len(outs) == 1, "outcome count drift")
    row = outs[0]
    require(row.get("predecessor_plan", {}).get("target_period") == "2025-H1", "Arizona predecessor plan rewritten")
    require(row.get("observed_outcome", {}).get("effective_period") == "2024-Q4", "Arizona observed outcome drift")
    require(row.get("historical_replay_eligible") is False, "current-review outcome falsely replay eligible")
    require(row.get("available_at") == CAPTURE, "outcome available_at drift")

    # Case coverage remains 2/14. Progress is not coverage.
    cases = d["cases"]
    require(cases.get("covered_case_count_before") == 2 and cases.get("covered_case_count_after") == 2,
            "required-case coverage falsely advanced")
    require(cases.get("remaining_gap_case_ids") == list(range(3, 15)), "remaining case gaps drift")
    progress_ids = {r.get("case_id") for r in cases.get("progress", [])}
    require(progress_ids == {4, 5, 6, 9, 13}, "case progress set drift")
    require(all("NOT_COVERED" in r.get("progress_state", "") or "CASE_STILL_GAP" in r.get("progress_state", "")
                for r in cases.get("progress", [])), "case progress promoted to coverage")

    # Status/master remain fail-closed.
    status = d["status"]
    res = status.get("results", {})
    expected = {
        "PRIMARY_SOURCES_ADDED": 10,
        "EVIDENCE_OBSERVATIONS_ADDED": 14,
        "FACILITIES_ADDED": 3,
        "EQUIPMENT_NODES_ADDED": 2,
        "MATERIAL_STAGE_NODES_ADDED": 6,
        "QUALIFICATION_OBSERVATIONS_ADDED": 2,
        "DEPENDENCY_EDGES_ADDED": 29,
        "OUTCOMES_CAPTURED_SHADOW": 1,
        "CANONICAL_CONSTRAINTS_MINTED": 0,
        "REQUIRED_CASES_COVERED": 2,
        "REQUIRED_CASES_TOTAL": 14,
        "HISTORICAL_REPLAY": "BLOCKED_RAW_SOURCE_VERSIONS_NOT_MATERIALIZED",
        "FIRST_SEMICONDUCTOR_RUN": "BLOCKED",
    }
    for key, val in expected.items():
        require(res.get(key) == val, f"status metric drift: {key}")
    require(status.get("next_repo_executable_lane") ==
            "SECOND-SLICE-POLICY-SUBSTITUTION-OUTCOME-AND-REQUIRED-CASE-DEPTH",
            "Batch019 next lane drift")

    master = d["master"]
    rd = master.get("readiness", {})
    require(rd.get("SECOND_SLICE_REPLAY_READY", {}).get("status") == "NO", "master replay falsely ready")
    require(rd.get("FULL_CONSTRAINT_RUN_READY", {}).get("status") == "NO", "master full run falsely ready")
    require(master.get("first_serious_constraint_run") == "BLOCKED", "master serious run falsely ready")
    require(rd.get("SECOND_SLICE_REQUIRED_CASES", {}).get("covered") == 2, "master case count drift")
    require(rd.get("SECOND_SLICE_OUTCOMES_READY", {}).get("status") == "PARTIAL_SHADOW",
            "master outcome readiness drift")

    # Manifest pins every durable Batch019 artifact.
    manifest = d["manifest"]
    require(manifest.get("result") == "PASS_FACILITY_MATERIAL_EQUIPMENT_QUALIFICATION_DEEPENING_PARTIAL",
            "manifest result drift")
    exp = manifest.get("expected", {})
    require(exp.get("required_cases_covered") == "2/14", "manifest case coverage drift")
    require(exp.get("historical_replay") == "BLOCKED", "manifest replay drift")
    require(exp.get("first_semiconductor_run") == "BLOCKED", "manifest run gate drift")
    seen: set[str] = set()
    for art in manifest.get("artifacts", []):
        rel = art.get("path")
        sha = art.get("git_blob_sha")
        require(isinstance(rel, str) and rel and rel not in seen, "manifest artifact path invalid/duplicate")
        seen.add(rel)
        p = ROOT / rel
        require(p.is_file(), f"manifest artifact missing: {rel}")
        require(git_blob_sha(p) == sha, f"manifest blob pin mismatch: {rel}")

    return {
        "sources_added": len(rows),
        "evidence_added": len(ev_rows),
        "facilities_added": len(pop["facilities_added"]),
        "materials_added": len(pop["materials_added"]),
        "equipment_added": len(pop["equipment_added"]),
        "edges_added": len(graph["edges_added"]),
        "outcomes": len(outs),
        "cases_covered": cases["covered_case_count_after"],
    }


def load_documents() -> dict[str, dict[str, Any]]:
    return {key: load(path) for key, path in FILES.items()}


def main() -> int:
    try:
        result = validate_documents(load_documents())
    except (ValidationFailure, json.JSONDecodeError, KeyError, TypeError, OSError) as exc:
        print("CONSTRAINT_SECOND_SLICE_BATCH019_VALIDATION=FAIL")
        print(f"ERROR={exc}")
        return 1

    print("CONSTRAINT_SECOND_SLICE_BATCH019_VALIDATION=PASS")
    print(f"PRIMARY_SOURCES_ADDED={result['sources_added']}")
    print(f"EVIDENCE_OBSERVATIONS_ADDED={result['evidence_added']}")
    print(f"FACILITIES_ADDED={result['facilities_added']}")
    print(f"MATERIAL_STAGE_NODES_ADDED={result['materials_added']}")
    print(f"EQUIPMENT_NODES_ADDED={result['equipment_added']}")
    print(f"DEPENDENCY_EDGES_ADDED={result['edges_added']}")
    print(f"OUTCOMES_CAPTURED_SHADOW={result['outcomes']}")
    print(f"REQUIRED_CASES_COVERED={result['cases_covered']}/14")
    print("HISTORICAL_REPLAY=BLOCKED")
    print("FIRST_SEMICONDUCTOR_RUN=BLOCKED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
