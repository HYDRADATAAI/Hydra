#!/usr/bin/env python3
"""Hostile mutation matrix for Batch025 continuous cross-slice graph closure."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "tools/validate_constraint_second_slice_batch025_continuous_graph.py"
BASE = "docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1"
SRC = f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH025_SEMICONDUCTOR_CONTINUOUS_CROSS_SLICE_SOURCE_REGISTRY_V001_20260926.json"
GRAPH = f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH025_CONTINUOUS_AI_SEMICONDUCTOR_POWER_GRAPH_OVERLAY_V001_20260926.json"
GATE = f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH025_SEMICONDUCTOR_STRICT_ACCEPTANCE_GATE_V001_20260926.json"
BLOCK = f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH025_SEMICONDUCTOR_ACCEPTANCE_BLOCKER_REGISTER_V001_20260926.json"
STATUS = f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH025_SEMICONDUCTOR_CONTINUOUS_CROSS_SLICE_GRAPH_STATUS_V001_20260926.json"
MASTER = "docs/constraint/architecture/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH025_MASTER_STATUS_V001_20260926.json"


def sandbox() -> Path:
    root = Path(tempfile.mkdtemp(prefix="hydra-semi-b025-hostile-"))
    shutil.copytree(ROOT / "docs/constraint", root / "docs/constraint", dirs_exist_ok=True)
    return root


def mutate(root: Path, rel: str, fn) -> None:
    path = root / rel
    data = json.loads(path.read_text(encoding="utf-8"))
    fn(data)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def run(root: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["HYDRA_REPO_ROOT"] = str(root)
    return subprocess.run([sys.executable, str(VALIDATOR)], cwd=ROOT, env=env, text=True, capture_output=True, check=False)


def expect(name, fn, fragment) -> None:
    root = sandbox()
    try:
        baseline = run(root)
        if baseline.returncode:
            raise AssertionError(f"{name}: baseline failed\n{baseline.stdout}\n{baseline.stderr}")
        fn(root)
        result = run(root)
        if result.returncode == 0:
            raise AssertionError(f"{name}: hostile mutation passed")
        output = result.stdout + result.stderr
        if fragment not in output:
            raise AssertionError(f"{name}: expected {fragment!r}\n{output}")
        print(f"PASS :: {name} :: {fragment}")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main() -> int:
    cases = [
        ("source_backdated", lambda r: mutate(r, SRC, lambda d: d["sources"][0].__setitem__("available_at", "2025-04-14T00:00:00Z")), "conservative available_at drifted"),
        ("source_raw_lineage_faked", lambda r: mutate(r, SRC, lambda d: d["sources"][0].__setitem__("ordinary_raw_lineage_eligible", True)), "source unexpectedly ordinary raw-lineage eligible"),
        ("stitch_edge_removed", lambda r: mutate(r, GRAPH, lambda d: d["edges_added"].pop(1)), "Batch025 graph edge count drifted"),
        ("wrong_facility", lambda r: mutate(r, GRAPH, lambda d: d["edges_added"][1].__setitem__("to", "FAC-SEMI-TSMC-AP6-ZHUNAN")), "continuous AI-semiconductor-power directed path is missing"),
        ("packaging_arizona_faked", lambda r: mutate(r, GRAPH, lambda d: d.__setitem__("advanced_packaging_in_arizona_asserted", True)), "Arizona advanced packaging was invented"),
        ("power_shortage_faked", lambda r: mutate(r, GRAPH, lambda d: d.__setitem__("active_power_shortage_asserted", True)), "active power shortage was invented"),
        ("cross_slice_gate_regressed", lambda r: mutate(r, GATE, lambda d: d["dimension_updates"]["CROSS_SLICE_GRAPH"].__setitem__("status", "BLOCKED")), "Batch025 cross-slice graph did not pass"),
        ("repo_blocker_reappears", lambda r: mutate(r, BLOCK, lambda d: d.__setitem__("repo_executable_blockers", ["SEMI-ACCEPT-024-XSLICE-001-CONTINUOUS-AI-SEMICONDUCTOR-POWER-CHAIN-NOT-PROVEN"])), "repo blocker register not empty"),
        ("external_blockers_deleted", lambda r: mutate(r, BLOCK, lambda d: d.__setitem__("external_or_private_blockers", [])), "external blocker register count drifted"),
        ("replay_faked_ready", lambda r: mutate(r, STATUS, lambda d: d["results"].__setitem__("HISTORICAL_REPLAY", "PASS")), "status falsely replay-ready"),
        ("master_implementation_admitted", lambda r: mutate(r, MASTER, lambda d: d["readiness"]["SECOND_SLICE_IMPLEMENTATION_ADMITTED"].__setitem__("status", "YES")), "master implementation falsely admitted"),
        ("master_full_ready", lambda r: mutate(r, MASTER, lambda d: d["readiness"]["FULL_CONSTRAINT_RUN_READY"].__setitem__("status", "YES")), "master falsely full-run ready"),
    ]
    for case in cases:
        expect(*case)

    print("CONSTRAINT_SECOND_SLICE_BATCH025_HOSTILE_MATRIX=PASS")
    print(f"HOSTILE_CASES={len(cases)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
