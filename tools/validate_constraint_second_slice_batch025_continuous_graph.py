#!/usr/bin/env python3
"""Validate Batch025 continuous AI→semiconductor→power graph closure."""

from __future__ import annotations

import json
import os
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("HYDRA_REPO_ROOT", Path(__file__).resolve().parents[1])).resolve()
BASE = ROOT / "docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1"
ARCH = ROOT / "docs/constraint/architecture"
VALIDATION = ROOT / "docs/constraint/validation"

FILES = {
    "source": BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH025_SEMICONDUCTOR_CONTINUOUS_CROSS_SLICE_SOURCE_REGISTRY_V001_20260926.json",
    "evidence": BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH025_SEMICONDUCTOR_CONTINUOUS_CROSS_SLICE_EVIDENCE_V001_20260926.json",
    "graph": BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH025_CONTINUOUS_AI_SEMICONDUCTOR_POWER_GRAPH_OVERLAY_V001_20260926.json",
    "gate": BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH025_SEMICONDUCTOR_STRICT_ACCEPTANCE_GATE_V001_20260926.json",
    "blockers": BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH025_SEMICONDUCTOR_ACCEPTANCE_BLOCKER_REGISTER_V001_20260926.json",
    "status": BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH025_SEMICONDUCTOR_CONTINUOUS_CROSS_SLICE_GRAPH_STATUS_V001_20260926.json",
    "master": ARCH / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH025_MASTER_STATUS_V001_20260926.json",
    "b018graph": BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_GRAPH_SEED_V001_20260926.json",
    "b019graph": BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH019_SEMICONDUCTOR_FACILITY_MATERIAL_EQUIPMENT_GRAPH_OVERLAY_V001_20260926.json",
    "b021power": BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH021_SEMICONDUCTOR_TO_POWER_INFRASTRUCTURE_GRAPH_OVERLAY_V001_20260926.json",
    "b023cases": BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH023_SEMICONDUCTOR_REQUIRED_CASE_OVERLAY_V001_20260926.json",
    "b024gate": BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH024_SEMICONDUCTOR_STRICT_ACCEPTANCE_GATE_V001_20260926.json",
    "b024blockers": BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH024_SEMICONDUCTOR_ACCEPTANCE_BLOCKER_REGISTER_V001_20260926.json",
    "admission": VALIDATION / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH002_NATIVE_T5_T6_ADMISSION_STATUS_V001_20260925.json",
}

SLICE = "SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1"
REPO_BLOCKER = "SEMI-ACCEPT-024-XSLICE-001-CONTINUOUS-AI-SEMICONDUCTOR-POWER-CHAIN-NOT-PROVEN"
RAW_BLOCKER = "SEMICONDUCTOR-SLICE-006-RAW-SOURCE-VERSIONS-NOT-MATERIALIZED"
ADMISSION_BLOCKER = "CI-TEST-008-BLOCKER-001B-NATIVE-T5-T6-SIGNED-ADMISSION-RECEIPT-ABSENT"


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


def directed_path(edges: list[dict[str, Any]], start: str, target: str) -> list[str] | None:
    adj: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        src = edge.get("from")
        dst = edge.get("to")
        if isinstance(src, str) and isinstance(dst, str):
            adj[src].append(dst)
    queue = deque([(start, [start])])
    seen = {start}
    while queue:
        node, path = queue.popleft()
        if node == target:
            return path
        for nxt in adj.get(node, []):
            if nxt not in seen:
                seen.add(nxt)
                queue.append((nxt, path + [nxt]))
    return None


def main() -> int:
    d = {name: load(path) for name, path in FILES.items()}

    for name in ("source", "evidence", "graph", "gate", "blockers", "status"):
        require(d[name].get("slice_id") == SLICE, f"{name} slice_id drifted")

    src = d["source"]
    new_sources = src.get("sources", [])
    require(len(new_sources) == 1, "Batch025 new-source count drifted")
    require(src.get("source_content_persisted") is False, "Batch025 falsely claims raw persistence")
    nsrc = new_sources[0]
    require(nsrc.get("source_id") == "SRC-SEMI-B025-NVIDIA-US-BLACKWELL-PRODUCTION-2025-04-14", "NVIDIA source identity drifted")
    require(nsrc.get("acquired_at") == nsrc.get("available_at"), "Batch025 conservative available_at drifted")
    require(nsrc.get("ordinary_raw_lineage_eligible") is False, "Batch025 source unexpectedly ordinary raw-lineage eligible")

    evidence = d["evidence"].get("evidence", [])
    require(len(evidence) == 3, "Batch025 evidence count drifted")
    eids = {row.get("evidence_id") for row in evidence}
    require(len(eids) == 3, "Batch025 evidence IDs duplicate")
    require(all(row.get("source_id") in {nsrc["source_id"], "SRC-SEMI-TSMC-ANNUAL-REPORT-2024"} for row in evidence), "Batch025 evidence source lineage drifted")

    graph = d["graph"]
    require(graph.get("continuous_ai_semiconductor_power_chain_proven") is True, "continuous chain not marked proven")
    require(graph.get("active_power_shortage_asserted") is False, "active power shortage was invented")
    require(graph.get("advanced_packaging_in_arizona_asserted") is False, "Arizona advanced packaging was invented")
    require(len(graph.get("nodes_added", [])) == 1, "Batch025 graph node count drifted")
    require(graph["nodes_added"][0].get("node_id") == "PRODUCT-NVIDIA-BLACKWELL-AI-CHIP", "Blackwell product node identity drifted")
    require(len(graph.get("edges_added", [])) == 2, "Batch025 graph edge count drifted")
    require(all(set(edge.get("evidence_ids", [])) <= eids for edge in graph["edges_added"]), "Batch025 graph edge evidence unresolved")

    # Build the actual current directed graph from predecessor layers + Batch025.
    edges: list[dict[str, Any]] = []
    edges.extend(d["b018graph"].get("edges", []))
    edges.extend(d["b019graph"].get("edges_added", []))
    edges.extend(d["b021power"].get("edges_added", []))
    edges.extend(graph.get("edges_added", []))

    path = directed_path(edges, "N-AI-COMPUTE-DEMAND", "N-ELECTRICITY-DEMAND")
    require(path is not None, "continuous AI-semiconductor-power directed path is missing")
    expected = [
        "N-AI-COMPUTE-DEMAND",
        "N-SEMI-AI-ACCELERATOR-DEMAND",
        "PRODUCT-NVIDIA-BLACKWELL-AI-CHIP",
        "FAC-SEMI-TSMC-ARIZONA-FIRST-FAB",
        "N-ELECTRICITY-DEMAND",
    ]
    require(path == expected, f"continuous path drifted: {path}")
    require(graph.get("required_continuous_path") == expected, "declared continuous path drifted")
    require(directed_path(edges, "FAC-SEMI-TSMC-ARIZONA-FIRST-FAB", "N-TRANSMISSION") is not None, "TSMC Arizona transmission extension missing")

    # Batch024 must remain immutable history showing the pre-closure block.
    b024 = d["b024gate"]
    require(b024.get("dimensions", {}).get("CROSS_SLICE_GRAPH", {}).get("status") == "BLOCKED", "Batch024 cross-slice history was rewritten")
    require(REPO_BLOCKER in set(b024.get("dimensions", {}).get("CROSS_SLICE_GRAPH", {}).get("blockers", [])), "Batch024 repo blocker history drifted")
    require(len(d["b024blockers"].get("repo_executable_blockers", [])) == 1, "Batch024 blocker register was rewritten")

    gate = d["gate"]
    upd = gate.get("dimension_updates", {}).get("CROSS_SLICE_GRAPH", {})
    require(upd.get("predecessor_status") == "BLOCKED", "Batch025 cross-slice predecessor status drifted")
    require(upd.get("status") == "PASS", "Batch025 cross-slice graph did not pass")
    require(upd.get("closed_blocker") == REPO_BLOCKER, "Batch025 closed wrong repo blocker")
    require(set(gate.get("unchanged_blocked_dimensions", [])) == {
        "PROVENANCE", "ORIGINAL_AS_OF", "NO_LOOKAHEAD", "DETERMINISTIC_REPLAY", "LINEAGE", "IMPLEMENTATION_ADMITTED"
    }, "Batch025 external blocked dimensions drifted")
    require(gate.get("overall_status") == "BLOCKED", "Batch025 overall gate falsely unblocked")
    require(gate.get("repo_executable_acceptance_blockers") == 0, "Batch025 still reports repo acceptance blockers")
    require(gate.get("external_or_private_acceptance_blockers") == 6, "Batch025 external blocker count drifted")
    require(gate.get("full_constraint_run_allowed") is False, "Batch025 full run unexpectedly allowed")
    require(gate.get("first_semiconductor_run") == "BLOCKED", "Batch025 semiconductor run unexpectedly allowed")

    cases = d["b023cases"]
    require(cases.get("covered_case_count_after") == 13, "Batch023 case coverage drifted")
    require(cases.get("remaining_gap_case_ids") == [12], "Case12 external gap drifted")

    blockers = d["blockers"]
    require(blockers.get("repo_executable_blockers") == [], "Batch025 repo blocker register not empty")
    closed = {row.get("blocker_id") for row in blockers.get("closed_repo_executable_blockers", [])}
    require(closed == {REPO_BLOCKER}, "Batch025 closed repo-blocker set drifted")
    ext = set(blockers.get("external_or_private_blockers", []))
    require(len(ext) == 6, "Batch025 external blocker register count drifted")
    require(RAW_BLOCKER in ext, "Batch025 raw-lineage blocker missing")
    require(ADMISSION_BLOCKER in ext, "Batch025 native admission blocker missing")
    require(blockers.get("next_repo_executable_lane") == "NONE_SECOND_SLICE_ACCEPTANCE_REQUIRES_PRIVATE_RAW_MATERIALIZATION_AND_NATIVE_ADMISSION", "Batch025 blocker next lane drifted")

    adm = d["admission"]
    require(adm.get("implementation_admitted") == "NO", "native implementation unexpectedly admitted")
    require(adm.get("signed_admission_receipt") == "ABSENT", "native signed admission receipt unexpectedly present")

    status = d["status"].get("results", {})
    require(status.get("CONTINUOUS_AI_SEMICONDUCTOR_POWER_CHAIN") == "PASS", "Batch025 status lost continuous graph pass")
    require(status.get("REPO_EXECUTABLE_ACCEPTANCE_BLOCKERS") == 0, "Batch025 status repo blocker count drifted")
    require(status.get("EXTERNAL_OR_PRIVATE_ACCEPTANCE_BLOCKERS") == 6, "Batch025 status external blocker count drifted")
    require(status.get("REMAINING_REQUIRED_CASES") == [12], "Batch025 status remaining case drifted")
    require(status.get("HISTORICAL_REPLAY") == "BLOCKED_RAW_SOURCE_VERSIONS_NOT_MATERIALIZED", "Batch025 status falsely replay-ready")
    require(status.get("FIRST_SEMICONDUCTOR_RUN") == "BLOCKED", "Batch025 status falsely run-ready")

    master = d["master"]
    rd = master.get("readiness", {})
    require(rd.get("SECOND_SLICE_CROSS_SLICE_GRAPH_ACCEPTANCE", {}).get("status") == "PASS_CONTINUOUS_CHAIN", "master continuous graph status drifted")
    require(rd.get("SECOND_SLICE_PROVENANCE_READY", {}).get("status") == "NO", "master provenance falsely ready")
    require(rd.get("SECOND_SLICE_NO_LOOKAHEAD_READY", {}).get("status") == "NO_ORDINARY", "master no-lookahead falsely ready")
    require(rd.get("SECOND_SLICE_DETERMINISTIC_REPLAY_READY", {}).get("status") == "NO", "master replay falsely ready")
    require(rd.get("SECOND_SLICE_IMPLEMENTATION_ADMITTED", {}).get("status") == "NO", "master implementation falsely admitted")
    require(rd.get("FULL_CONSTRAINT_RUN_READY", {}).get("status") == "NO", "master falsely full-run ready")
    require(master.get("repo_executable_acceptance_blockers") == [], "master still reports repo acceptance blockers")
    require(len(master.get("external_or_private_acceptance_blockers", [])) == 6, "master external blocker count drifted")
    require(master.get("first_serious_constraint_run") == "BLOCKED", "master falsely serious-run ready")
    require(master.get("next_repo_executable_lane") == "NONE_SECOND_SLICE_ACCEPTANCE_REQUIRES_PRIVATE_RAW_MATERIALIZATION_AND_NATIVE_ADMISSION", "master next lane drifted")

    print("CONSTRAINT_SECOND_SLICE_BATCH025_CONTINUOUS_GRAPH_VALIDATION=PASS")
    print("CONTINUOUS_AI_SEMICONDUCTOR_POWER_CHAIN=PASS")
    print("CONTINUOUS_PATH=" + "->".join(expected))
    print("REPO_EXECUTABLE_ACCEPTANCE_BLOCKERS=0")
    print("EXTERNAL_OR_PRIVATE_ACCEPTANCE_BLOCKERS=6")
    print("REQUIRED_CASES_COVERED=13/14")
    print("REMAINING_REQUIRED_CASE=12")
    print("HISTORICAL_REPLAY=BLOCKED")
    print("FIRST_SEMICONDUCTOR_RUN=BLOCKED")
    print("NEXT_REPO_EXECUTABLE_LANE=NONE_SECOND_SLICE_ACCEPTANCE_REQUIRES_PRIVATE_RAW_MATERIALIZATION_AND_NATIVE_ADMISSION")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValidationFailure, json.JSONDecodeError) as exc:
        print("CONSTRAINT_SECOND_SLICE_BATCH025_VALIDATION=FAIL")
        print(f"ERROR={exc}")
        raise SystemExit(1)
