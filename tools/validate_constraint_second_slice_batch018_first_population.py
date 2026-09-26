from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SLICE = ROOT / "docs" / "constraint" / "second_slice" / "semiconductor_advanced_packaging_critical_materials_v1"

PATHS = {
    "sources": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_SEMICONDUCTOR_SOURCE_AUTHORITY_REGISTRY_V001_20260926.json",
    "evidence": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_SEMICONDUCTOR_EVIDENCE_SEED_V001_20260926.json",
    "population": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_SEMICONDUCTOR_FIRST_POPULATION_V001_20260926.json",
    "graph": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_SEMICONDUCTOR_DEPENDENCY_GRAPH_SEED_V001_20260926.json",
    "status": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_SEMICONDUCTOR_SOURCE_AUTHORITY_FIRST_POPULATION_STATUS_V001_20260926.json",
    "required_cases": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH017_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_REQUIRED_CASE_MATRIX_V001_20260926.json",
    "master": ROOT / "docs" / "constraint" / "architecture" / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_MASTER_STATUS_V001_20260926.json",
    "manifest": ROOT / "docs" / "constraint" / "validation" / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_ARTIFACT_MANIFEST_V001_20260926.json",
}

EXPECTED_SLICE = "SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1"
EXPECTED_SOURCE_COUNT = 10
EXPECTED_EVIDENCE_COUNT = 11
EXPECTED_EDGE_COUNT = 24
ALLOWED_EXTERNAL_NODE_IDS = {"N-AI-COMPUTE-DEMAND"}


class Batch018ValidationError(ValueError):
    pass


def _fail(message: str) -> None:
    raise Batch018ValidationError(message)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    header = b"blob " + str(len(data)).encode("ascii") + b"\\0"
    return hashlib.sha1(header + data).hexdigest()


def load_documents() -> dict[str, dict[str, Any]]:
    return {name: _load(path) for name, path in PATHS.items()}


def _ids(rows: list[dict[str, Any]], field: str) -> set[str]:
    values = [row.get(field) for row in rows]
    if any(not isinstance(value, str) or not value for value in values):
        _fail(f"{field}: missing or invalid identifier")
    if len(values) != len(set(values)):
        _fail(f"{field}: duplicate identifier")
    return set(values)


def validate_documents(docs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    sources = docs["sources"]
    evidence = docs["evidence"]
    population = docs["population"]
    graph = docs["graph"]
    status = docs["status"]
    required_cases = docs["required_cases"]
    master = docs["master"]
    manifest = docs["manifest"]

    for name, doc in docs.items():
        if name != "required_cases" and doc.get("slice_id") not in (None, EXPECTED_SLICE):
            _fail(f"{name}: slice_id drift")
    if sources.get("slice_id") != EXPECTED_SLICE:
        _fail("sources: wrong slice")
    if evidence.get("slice_id") != EXPECTED_SLICE:
        _fail("evidence: wrong slice")
    if population.get("slice_id") != EXPECTED_SLICE:
        _fail("population: wrong slice")
    if graph.get("slice_id") != EXPECTED_SLICE:
        _fail("graph: wrong slice")
    if status.get("slice_id") != EXPECTED_SLICE:
        _fail("status: wrong slice")

    source_rows = sources.get("sources", [])
    if len(source_rows) != EXPECTED_SOURCE_COUNT:
        _fail(f"sources: expected {EXPECTED_SOURCE_COUNT}, found {len(source_rows)}")
    source_ids = _ids(source_rows, "source_id")
    urls = [row.get("url") for row in source_rows]
    if any(not isinstance(url, str) or not url.startswith("https://") for url in urls):
        _fail("sources: every source must have an https URL")
    if len(urls) != len(set(urls)):
        _fail("sources: duplicate URL")
    for row in source_rows:
        sid = row["source_id"]
        if row.get("primary_source") is not True:
            _fail(f"{sid}: non-primary source entered Batch018 authority seed")
        if row.get("t1_materialized") is not False:
            _fail(f"{sid}: T1 materialization was claimed")
        for field in ("raw_artifact_id", "source_version_id", "acquired_at", "available_at"):
            if row.get(field) is not None:
                _fail(f"{sid}: fabricated {field}")
        if row.get("strict_original_as_of_eligible") is not False:
            _fail(f"{sid}: strict replay eligibility escaped fail-closed state")

    if sources.get("ordinary_replay_eligible_source_count") != 0:
        _fail("sources: ordinary replay-eligible source count must remain zero")

    evidence_rows = evidence.get("observations", [])
    if len(evidence_rows) != EXPECTED_EVIDENCE_COUNT:
        _fail(f"evidence: expected {EXPECTED_EVIDENCE_COUNT}, found {len(evidence_rows)}")
    evidence_ids = _ids(evidence_rows, "evidence_id")
    for row in evidence_rows:
        eid = row["evidence_id"]
        if row.get("source_id") not in source_ids:
            _fail(f"{eid}: unknown source_id")
        if row.get("admissibility") != "REVIEWED_SEED_NOT_STRICT_REPLAY_READY":
            _fail(f"{eid}: evidence escaped reviewed-seed admissibility")
        if not row.get("semantic_firewall"):
            _fail(f"{eid}: missing semantic firewall")
    if evidence.get("ordinary_t2_evidence") is not False:
        _fail("evidence: ordinary T2 admission was claimed")
    if evidence.get("strict_original_as_of_ready") is not False:
        _fail("evidence: strict original-as-of readiness was claimed")

    if population.get("ordinary_t3_eligible") is not False:
        _fail("population: ordinary T3 eligibility was claimed")
    if population.get("canonical_constraints_minted") != 0:
        _fail("population: canonical constraint minted")
    if population.get("qualified_beneficiaries_minted") != 0:
        _fail("population: qualified beneficiary minted")

    sections = (
        "companies",
        "facilities",
        "products_and_technologies",
        "geographies",
        "policy_events",
        "material_records",
    )
    population_rows: list[dict[str, Any]] = []
    for section in sections:
        rows = population.get(section, [])
        if not isinstance(rows, list):
            _fail(f"population.{section}: must be a list")
        population_rows.extend(rows)

    populated_ids = _ids(population_rows, "entity_id")
    for row in population_rows:
        rid = row["entity_id"]
        for eid in row.get("evidence_ids", []):
            if eid not in evidence_ids:
                _fail(f"{rid}: unknown evidence {eid}")
        if row.get("source_version_ids", []) not in ([], None):
            _fail(f"{rid}: source-version lineage invented before T1 materialization")
        if row.get("available_at") is not None:
            _fail(f"{rid}: available_at invented before T1 materialization")
        if row.get("quarantine_state") != "SHADOW_NOT_T1_MATERIALIZED":
            _fail(f"{rid}: population escaped shadow quarantine")

    if len(population.get("companies", [])) != 6:
        _fail("population: company count drift")
    if len(population.get("facilities", [])) != 1:
        _fail("population: facility count drift")
    if len(population.get("products_and_technologies", [])) != 8:
        _fail("population: products/technology count drift")
    if len(population.get("geographies", [])) != 5:
        _fail("population: geography count drift")
    if len(population.get("policy_events", [])) != 3:
        _fail("population: policy event count drift")
    if population.get("material_records") != []:
        _fail("population: unsupported critical-material record admitted in Batch018")

    facilities = {row["entity_id"]: row for row in population.get("facilities", [])}
    az = facilities.get("S2-FAC-TSMC-ARIZONA-FIRST-FAB")
    if not az:
        _fail("population: TSMC Arizona first fab missing")
    if az.get("process_node") != "N4" or az.get("capacity_state") != "HIGH_VOLUME_PRODUCTION":
        _fail("TSMC Arizona: N4 high-volume-production state drift")
    if az.get("effective_from") != "2024-Q4":
        _fail("TSMC Arizona: Q4 2024 production timing drift")
    for field in ("installed_capacity", "operational_capacity", "available_capacity", "effective_capacity"):
        if az.get(field) is not None:
            _fail(f"TSMC Arizona: fabricated numeric {field}")

    graph_nodes = graph.get("nodes", [])
    if not isinstance(graph_nodes, list) or len(graph_nodes) != len(set(graph_nodes)):
        _fail("graph: node list invalid or duplicated")
    graph_node_ids = set(graph_nodes)
    if not graph_node_ids <= populated_ids | ALLOWED_EXTERNAL_NODE_IDS:
        unknown = sorted(graph_node_ids - populated_ids - ALLOWED_EXTERNAL_NODE_IDS)
        _fail(f"graph: unknown node ids {unknown}")

    edges = graph.get("edges", [])
    if len(edges) != EXPECTED_EDGE_COUNT:
        _fail(f"graph: expected {EXPECTED_EDGE_COUNT} edges, found {len(edges)}")
    edge_ids = _ids(edges, "edge_id")
    del edge_ids
    for edge in edges:
        edge_id = edge["edge_id"]
        if edge.get("from") not in graph_node_ids or edge.get("to") not in graph_node_ids:
            _fail(f"{edge_id}: edge endpoint absent from graph nodes")
        refs = edge.get("evidence_ids", [])
        if not refs:
            _fail(f"{edge_id}: supported edge has no evidence")
        for eid in refs:
            if eid not in evidence_ids:
                _fail(f"{edge_id}: unknown evidence {eid}")
        if edge.get("status") != "SUPPORTED_REVIEWED_SEED":
            _fail(f"{edge_id}: unsupported status promotion")

    samsung = next((edge for edge in edges if edge["edge_id"] == "S2-E006"), None)
    if not samsung:
        _fail("graph: Samsung development edge missing")
    if samsung.get("relation") != "DEVELOPED_PRODUCT":
        _fail("Samsung HBM3E: development was promoted to production")
    if samsung.get("qualification_state") != "NOT_PROVEN_VOLUME_OR_NVIDIA_QUALIFIED":
        _fail("Samsung HBM3E: qualification state was promoted without evidence")

    if graph.get("graph_status") != "REVIEWED_EVIDENCE_BACKED_SEED_PARTIAL_NOT_REPLAY_READY":
        _fail("graph: replay-readiness state drift")
    if graph.get("cross_slice_predecessor_node_ids") != ["N-AI-COMPUTE-DEMAND"]:
        _fail("graph: unexpected cross-slice predecessor")
    if graph.get("cross_slice_path_proven_in_shadow") != [
        "N-AI-COMPUTE-DEMAND",
        "S2-PROD-NVIDIA-H200",
        "S2-PROD-HBM3E",
        "S2-COMP-MICRON",
    ]:
        _fail("graph: bounded cross-slice shadow path drift")

    cases = required_cases.get("cases", [])
    if required_cases.get("required_case_count") != 14 or len(cases) != 14:
        _fail("required cases: Batch017 frozen 14-case matrix drift")
    if required_cases.get("covered_case_count") != 0:
        _fail("required cases: Batch018 falsely claimed case coverage")
    if any(case.get("status") != "GAP" for case in cases):
        _fail("required cases: a frozen case was promoted without execution")

    results = status.get("results", {})
    if status.get("result") != "PASS_REVIEWED_SOURCE_AUTHORITY_AND_FIRST_POPULATION_SHADOW_ONLY":
        _fail("status: Batch018 result drift")
    if results.get("T1_RAW_ARTIFACT_MATERIALIZATION") != "NO":
        _fail("status: T1 materialization escaped NO")
    if results.get("AVAILABLE_AT_CAPTURE") != "NO":
        _fail("status: available_at capture escaped NO")
    if results.get("HISTORICAL_REPLAY") != "BLOCKED_T1_LINEAGE_NOT_MATERIALIZED":
        _fail("status: historical replay escaped blocking gate")
    if results.get("FIRST_SEMICONDUCTOR_RUN") != "BLOCKED":
        _fail("status: first semiconductor run was authorized")
    if results.get("REQUIRED_CASES_COVERED") != 0:
        _fail("status: required-case coverage falsely promoted")
    if results.get("DEPENDENCY_EDGES") != EXPECTED_EDGE_COUNT:
        _fail("status: dependency-edge count mismatch")

    readiness = master.get("readiness", {})
    if master.get("first_serious_constraint_run") != "BLOCKED":
        _fail("master: first serious Constraint run escaped BLOCKED")
    if readiness.get("SECOND_SLICE_T1_CUSTODY", {}).get("status") != "NO":
        _fail("master: T1 custody escaped NO")
    if readiness.get("SECOND_SLICE_AVAILABLE_AT", {}).get("status") != "NO":
        _fail("master: available_at escaped NO")
    if readiness.get("SECOND_SLICE_REPLAY_READY", {}).get("status") != "NO":
        _fail("master: replay readiness escaped NO")
    if readiness.get("FULL_CONSTRAINT_RUN_READY", {}).get("status") != "NO":
        _fail("master: full Constraint run escaped NO")

    if manifest.get("result") != "PASS_REVIEWED_SOURCE_AUTHORITY_AND_FIRST_POPULATION_SHADOW_ONLY":
        _fail("manifest: result drift")
    expected_manifest = manifest.get("expected", {})
    if expected_manifest.get("source_count") != EXPECTED_SOURCE_COUNT:
        _fail("manifest: source count drift")
    if expected_manifest.get("evidence_observation_count") != EXPECTED_EVIDENCE_COUNT:
        _fail("manifest: evidence count drift")
    if expected_manifest.get("dependency_edge_count") != EXPECTED_EDGE_COUNT:
        _fail("manifest: edge count drift")
    if expected_manifest.get("ordinary_t3_eligible") is not False:
        _fail("manifest: ordinary T3 eligibility promoted")
    if expected_manifest.get("strict_original_as_of_ready") is not False:
        _fail("manifest: strict original-as-of readiness promoted")
    if expected_manifest.get("historical_replay") != "BLOCKED":
        _fail("manifest: historical replay promoted")
    if expected_manifest.get("required_cases_covered") != 0:
        _fail("manifest: required-case coverage promoted")
    if expected_manifest.get("first_semiconductor_run") != "BLOCKED":
        _fail("manifest: first semiconductor run promoted")

    manifest_paths = set()
    for artifact in manifest.get("artifacts", []):
        rel = artifact.get("path")
        expected_sha = artifact.get("git_blob_sha")
        if not isinstance(rel, str) or not isinstance(expected_sha, str):
            _fail("manifest: malformed artifact entry")
        if rel in manifest_paths:
            _fail(f"manifest: duplicate artifact path {rel}")
        manifest_paths.add(rel)
        artifact_path = ROOT / rel
        if not artifact_path.is_file():
            _fail(f"manifest: missing artifact {rel}")
        if _git_blob_sha(artifact_path) != expected_sha:
            _fail(f"manifest: blob pin mismatch for {rel}")

    return {
        "source_count": len(source_rows),
        "evidence_count": len(evidence_rows),
        "population_count": len(population_rows),
        "edge_count": len(edges),
        "required_cases_covered": required_cases.get("covered_case_count"),
        "status": "PASS_BATCH018_REVIEWED_SHADOW_FIRST_POPULATION",
    }


def main() -> int:
    try:
        result = validate_documents(load_documents())
    except (OSError, json.JSONDecodeError, KeyError, TypeError, Batch018ValidationError) as exc:
        print("CONSTRAINT_SECOND_SLICE_BATCH018=FAIL")
        print(f"ERROR={exc}")
        return 1

    print("CONSTRAINT_SECOND_SLICE_BATCH018=PASS")
    print(f"SOURCES={result['source_count']}")
    print(f"EVIDENCE_OBSERVATIONS={result['evidence_count']}")
    print(f"POPULATION_RECORDS={result['population_count']}")
    print(f"DEPENDENCY_EDGES={result['edge_count']}")
    print(f"REQUIRED_CASES_COVERED={result['required_cases_covered']}")
    print("ORDINARY_T3_ELIGIBLE=NO")
    print("HISTORICAL_REPLAY=BLOCKED")
    print("FIRST_SEMICONDUCTOR_RUN=BLOCKED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
