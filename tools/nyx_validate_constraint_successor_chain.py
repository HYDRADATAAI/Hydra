#!/usr/bin/env python3
"""Read-only cross-batch integration guard for the Constraint first slice.

NYX owns validation here, not domain population. This guard verifies successor
continuity, bounded semantics, manifest integrity, and fail-closed readiness.
It does not fetch source data, create claims, mint authority, activate runtime
behavior, or promote canonical state.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("HYDRA_REPO_ROOT", Path(__file__).resolve().parents[1])).resolve()
SLICE = ROOT / "docs/constraint/first_slice/ai_data_center_power_infrastructure_v1"
VALIDATION = ROOT / "docs/constraint/validation"
ARCH = ROOT / "docs/constraint/architecture"
IMPL = ROOT / "docs/constraint/implementation"

SLICE_ID = "AI_DATA_CENTER_POWER_INFRASTRUCTURE_V1"
ADMISSION_BLOCKER = "CI-TEST-008-BLOCKER-001B-NATIVE-T5-T6-SIGNED-ADMISSION-RECEIPT-ABSENT"
RAW_MATERIALIZATION_BLOCKER = "PIT-002B-FIRST-SLICE-NINE-SOURCE-RAW-CAPTURE-MATERIALIZATION"
HISTORICAL_FIBER_BLOCKER = "SOURCE-GAP-FIBER-CONNECTIVITY-CAPACITY"
BATCH009_NEXT = "FIRST-SLICE-CONSTRAINT-AND-BENEFICIARY-CLAIM-POPULATION"
BATCH010_NEXT = "FIRST-SLICE-OUTCOME-LABEL-AND-REPLAY-FIXTURE-DESIGN"
FIBER_STATUS = "POPULATED_BOUNDED_SITE_AND_PROVIDER_PROFILE"

MANIFEST_RE = re.compile(
    r"BATCH(?P<batch>\d{3})_ARTIFACT_MANIFEST_V(?P<revision>\d{3})_"
)
MASTER_RE = re.compile(r"BATCH(?P<batch>\d{3})_MASTER_STATUS")

FILES = {
    "source_registry": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH003_AI_DATA_CENTER_POWER_INFRASTRUCTURE_SOURCE_REGISTRY_V001_20260925.json",
    "pit_capture": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH004_AI_DATA_CENTER_POWER_INFRASTRUCTURE_PIT_ACQUISITION_CAPTURE_V001_20260925.json",
    "temporal_audit": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH005_AI_DATA_CENTER_POWER_INFRASTRUCTURE_SOURCE_TEMPORAL_AUDIT_V001_20260925.json",
    "batch006_gap": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH006_AI_DATA_CENTER_POWER_INFRASTRUCTURE_SOURCE_GAP_STATUS_V001_20260925.json",
    "availability": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH007_AI_DATA_CENTER_POWER_INFRASTRUCTURE_CONSERVATIVE_AVAILABILITY_OVERLAY_V001_20260925.json",
    "batch002_admission": VALIDATION / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH002_NATIVE_T5_T6_ADMISSION_STATUS_V001_20260925.json",
    "batch008_raw_status": VALIDATION / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH008_T1_RAW_ARTIFACT_PERSISTENCE_STATUS_V001_20260925.json",
    "batch008_master": ARCH / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH008_MASTER_STATUS_V001_20260925.json",
    "batch008_raw_contract": IMPL / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH008_T1_RAW_ARTIFACT_PERSISTENCE_CONTRACT_V001_20260925.json",
    "batch009_gap": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH009_AI_DATA_CENTER_POWER_INFRASTRUCTURE_SOURCE_GAP_STATUS_V001_20260925.json",
    "batch009_master": ARCH / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH009_MASTER_STATUS_V001_20260925.json",
    "batch009_fiber_sources": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH009_AI_DATA_CENTER_POWER_INFRASTRUCTURE_SOURCE_REGISTRY_EXTENSION_V001_20260925.json",
    "batch009_fiber_evidence": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH009_AI_DATA_CENTER_POWER_INFRASTRUCTURE_FIBER_EVIDENCE_SUPPLEMENT_V001_20260925.json",
    "batch009_fiber_field": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH009_AI_DATA_CENTER_POWER_INFRASTRUCTURE_FIBER_FIELD_OVERLAY_V001_20260925.json",
    "batch009_fiber_graph": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH009_AI_DATA_CENTER_POWER_INFRASTRUCTURE_FIBER_GRAPH_OVERLAY_V001_20260925.json",
    "batch010_status": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH010_AI_DATA_CENTER_POWER_INFRASTRUCTURE_CLAIM_CANDIDATE_BENEFICIARY_STATUS_V001_20260925.json",
    "batch010_master": ARCH / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH010_MASTER_STATUS_V001_20260925.json",
    "batch010_claims": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH010_AI_DATA_CENTER_POWER_INFRASTRUCTURE_CLAIM_REGISTRY_V001_20260925.json",
    "batch010_candidates": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH010_AI_DATA_CENTER_POWER_INFRASTRUCTURE_T5_CANDIDATE_PROPOSALS_V001_20260925.json",
    "batch010_relief": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH010_AI_DATA_CENTER_POWER_INFRASTRUCTURE_RELIEF_PATHS_V001_20260925.json",
    "batch010_beneficiaries": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH010_AI_DATA_CENTER_POWER_INFRASTRUCTURE_BENEFICIARY_EVALUATIONS_V001_20260925.json",
    "batch010_beneficiary_sources": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH010_AI_DATA_CENTER_POWER_INFRASTRUCTURE_BENEFICIARY_SOURCE_REGISTRY_EXTENSION_V001_20260925.json",
    "batch011_taxonomy": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH011_AI_DATA_CENTER_POWER_INFRASTRUCTURE_OUTCOME_TAXONOMY_V001_20260925.json",
    "batch011_outcomes": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH011_AI_DATA_CENTER_POWER_INFRASTRUCTURE_OUTCOME_RECORDS_V001_20260925.json",
    "batch011_replay": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH011_AI_DATA_CENTER_POWER_INFRASTRUCTURE_SHADOW_REPLAY_PACKET_V001_20260925.json",
    "batch011_determinism": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH011_AI_DATA_CENTER_POWER_INFRASTRUCTURE_DETERMINISM_RECEIPT_V001_20260925.json",
    "batch011_required_cases": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH011_AI_DATA_CENTER_POWER_INFRASTRUCTURE_REQUIRED_CASES_OUTCOME_REPLAY_OVERLAY_V001_20260925.json",
    "batch011_master": ARCH / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH011_MASTER_STATUS_V001_20260925.json",
    "batch012_cases": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH012_AI_DATA_CENTER_POWER_INFRASTRUCTURE_HISTORICAL_CASE_REGISTRY_V001_20260925.json",
    "batch012_evidence": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH012_AI_DATA_CENTER_POWER_INFRASTRUCTURE_HISTORICAL_CASE_EVIDENCE_SUPPLEMENT_V001_20260925.json",
    "batch012_outcomes": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH012_AI_DATA_CENTER_POWER_INFRASTRUCTURE_OUTCOME_RECORDS_SUPPLEMENT_V001_20260925.json",
    "batch012_overlay": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH012_AI_DATA_CENTER_POWER_INFRASTRUCTURE_REQUIRED_CASES_HISTORICAL_CLOSURE_OVERLAY_V001_20260925.json",
    "batch012_master": ARCH / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH012_MASTER_STATUS_V001_20260925.json",
    "batch016_custody_contract": IMPL / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH016_T1_T2_PERSISTED_CHAIN_OF_CUSTODY_CONTRACT_V001_20260925.json",
    "batch016_custody_status": VALIDATION / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH016_T1_T2_CHAIN_OF_CUSTODY_STATUS_V001_20260925.json",
    "batch016_master": ARCH / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH016_MASTER_STATUS_V001_20260925.json",
}


class ValidationFailure(Exception):
    pass


def fail(message: str) -> None:
    raise ValidationFailure(message)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def load_json(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"required artifact missing: {path.relative_to(ROOT)}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"invalid JSON {path.relative_to(ROOT)}: {exc}")
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def source_ids(records: list[dict[str, Any]]) -> set[str]:
    ids = [record.get("source_id") for record in records]
    require(all(isinstance(item, str) and item for item in ids), "source_id missing or invalid")
    require(len(ids) == len(set(ids)), "duplicate source_id in one artifact")
    return set(ids)


def unique_ids(records: list[dict[str, Any]], field: str, label: str) -> set[str]:
    ids = [record.get(field) for record in records]
    require(all(isinstance(item, str) and item for item in ids), f"{label} identity missing")
    require(len(ids) == len(set(ids)), f"duplicate {label} identity")
    return set(ids)


def git_blob_sha(path: Path) -> str:
    result = subprocess.run(
        ["git", "hash-object", str(path.relative_to(ROOT))],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    require(
        result.returncode == 0,
        f"git hash-object failed for {path.relative_to(ROOT)}: {result.stderr.strip()}",
    )
    return result.stdout.strip()


def manifest_identity(path: Path) -> tuple[int, int]:
    match = MANIFEST_RE.search(path.name)
    require(match is not None, f"manifest batch/revision missing: {path.name}")
    return int(match.group("batch")), int(match.group("revision"))


def master_batch(path: Path) -> int:
    match = MASTER_RE.search(path.name)
    require(match is not None, f"master batch missing: {path.name}")
    return int(match.group("batch"))


def discover_current_manifests() -> list[Path]:
    """Return the highest-revision manifest for each contiguous successor batch."""

    grouped: dict[int, list[tuple[int, Path]]] = {}
    for path in VALIDATION.glob(
        "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH*_ARTIFACT_MANIFEST_V*_20260925.json"
    ):
        batch, revision = manifest_identity(path)
        if batch >= 3:
            grouped.setdefault(batch, []).append((revision, path))

    require(grouped, "no successor manifests discovered")
    highest_batch = max(grouped)
    expected_batches = set(range(3, highest_batch + 1))
    require(
        set(grouped) == expected_batches,
        f"successor manifest sequence has gaps: found={sorted(grouped)}",
    )

    selected: list[Path] = []
    for batch in sorted(grouped):
        revision, path = max(grouped[batch], key=lambda item: item[0])
        if revision > 1:
            doc = load_json(path)
            supersedes = doc.get("supersedes")
            require(
                isinstance(supersedes, dict)
                and supersedes.get("predecessor_preserved") is True,
                f"Batch{batch:03d} revised manifest lacks preserved supersession boundary",
            )
        selected.append(path)
    return selected


def discover_latest_master() -> tuple[int, Path, dict[str, Any]]:
    paths = list(
        ARCH.glob(
            "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH*_MASTER_STATUS_V001_20260925.json"
        )
    )
    require(paths, "no successor master status discovered")
    path = max(paths, key=master_batch)
    batch = master_batch(path)
    return batch, path, load_json(path)


def validate_manifest(manifest_path: Path) -> tuple[int, int]:
    """Validate immutable domain pins while allowing shared operational code to evolve."""

    manifest = load_json(manifest_path)
    artifacts = manifest.get("artifacts")
    require(
        isinstance(artifacts, list) and artifacts,
        f"manifest artifacts missing: {manifest_path.name}",
    )
    count = 0
    shared_pin_divergence = 0
    for entry in artifacts:
        require(isinstance(entry, dict), f"invalid manifest entry: {manifest_path.name}")
        relative = entry.get("path")
        expected = entry.get("git_blob_sha")
        require(isinstance(relative, str) and relative, f"manifest path missing: {manifest_path.name}")
        require(
            isinstance(expected, str) and re.fullmatch(r"[0-9a-f]{40}", expected) is not None,
            f"manifest git_blob_sha invalid: {relative}",
        )
        artifact = ROOT / relative
        require(artifact.is_file(), f"manifest member missing: {relative}")
        actual = git_blob_sha(artifact)
        if relative.startswith("docs/constraint/"):
            require(
                actual == expected,
                f"immutable domain artifact blob mismatch: {relative}: expected={expected} actual={actual}",
            )
        elif actual != expected:
            # Tests and shared operational code legitimately evolve after a
            # historical batch seals. The manifest still pins the version that
            # batch used, but current HEAD is not required to retain those bytes.
            shared_pin_divergence += 1
        count += 1
    return count, shared_pin_divergence


def main() -> int:
    docs = {name: load_json(path) for name, path in FILES.items()}

    registry = docs["source_registry"]
    capture = docs["pit_capture"]
    temporal = docs["temporal_audit"]
    batch006_gap = docs["batch006_gap"]
    availability = docs["availability"]
    admission = docs["batch002_admission"]
    raw_status = docs["batch008_raw_status"]
    batch008_master = docs["batch008_master"]
    raw_contract = docs["batch008_raw_contract"]

    batch009_gap = docs["batch009_gap"]
    batch009_master = docs["batch009_master"]
    fiber_sources = docs["batch009_fiber_sources"]
    fiber_evidence = docs["batch009_fiber_evidence"]
    fiber_field = docs["batch009_fiber_field"]
    fiber_graph = docs["batch009_fiber_graph"]

    batch010_status = docs["batch010_status"]
    batch010_master = docs["batch010_master"]
    claims = docs["batch010_claims"]
    candidates = docs["batch010_candidates"]
    relief = docs["batch010_relief"]
    beneficiaries = docs["batch010_beneficiaries"]
    beneficiary_sources = docs["batch010_beneficiary_sources"]

    outcome_taxonomy = docs["batch011_taxonomy"]
    outcome_records = docs["batch011_outcomes"]
    shadow_replay = docs["batch011_replay"]
    determinism = docs["batch011_determinism"]
    required_cases = docs["batch011_required_cases"]
    batch011_master = docs["batch011_master"]

    cases12 = docs["batch012_cases"]
    evidence12 = docs["batch012_evidence"]
    outcomes12 = docs["batch012_outcomes"]
    overlay12 = docs["batch012_overlay"]
    batch012_master = docs["batch012_master"]

    custody16 = docs["batch016_custody_contract"]
    custody_status16 = docs["batch016_custody_status"]
    batch016_master = docs["batch016_master"]

    # Stable first-slice identity across domain artifacts.
    for name, doc in (
        ("source_registry", registry),
        ("pit_capture", capture),
        ("temporal_audit", temporal),
        ("batch006_gap", batch006_gap),
        ("availability", availability),
        ("batch009_gap", batch009_gap),
        ("batch009_fiber_sources", fiber_sources),
        ("batch009_fiber_evidence", fiber_evidence),
        ("batch009_fiber_field", fiber_field),
        ("batch009_fiber_graph", fiber_graph),
        ("batch010_status", batch010_status),
        ("batch010_claims", claims),
        ("batch010_candidates", candidates),
        ("batch010_relief", relief),
        ("batch010_beneficiaries", beneficiaries),
        ("batch010_beneficiary_sources", beneficiary_sources),
        ("batch011_taxonomy", outcome_taxonomy),
        ("batch011_outcomes", outcome_records),
        ("batch011_replay", shadow_replay),
        ("batch011_determinism", determinism),
        ("batch011_required_cases", required_cases),
        ("batch012_cases", cases12),
        ("batch012_evidence", evidence12),
        ("batch012_outcomes", outcomes12),
        ("batch012_overlay", overlay12),
    ):
        require(doc.get("slice_id") == SLICE_ID, f"{name} slice_id drifted")

    # Original nine-source point-in-time continuity.
    registry_records = registry.get("sources")
    capture_records = capture.get("records")
    temporal_records = temporal.get("records")
    availability_records = availability.get("records")
    for label, records in (
        ("registry", registry_records),
        ("capture", capture_records),
        ("temporal", temporal_records),
        ("availability", availability_records),
    ):
        require(isinstance(records, list), f"{label} records missing")

    registry_ids = source_ids(registry_records)
    capture_ids = source_ids(capture_records)
    temporal_ids = source_ids(temporal_records)
    availability_ids = source_ids(availability_records)
    require(len(registry_ids) == 9, f"expected nine original first-slice sources, found {len(registry_ids)}")
    require(capture_ids == registry_ids, "capture source set differs from registry")
    require(temporal_ids == registry_ids, "temporal source set differs from registry")
    require(availability_ids == registry_ids, "availability source set differs from registry")

    registry_by_id = {item["source_id"]: item for item in registry_records}
    capture_by_id = {item["source_id"]: item for item in capture_records}
    temporal_by_id = {item["source_id"]: item for item in temporal_records}
    availability_by_id = {item["source_id"]: item for item in availability_records}

    completed_at = capture.get("capture_completed_at")
    require(isinstance(completed_at, str) and completed_at.endswith("Z"), "capture_completed_at missing/invalid")
    require(
        capture.get("source_content_persisted") is False,
        "Batch004 must not retroactively claim raw source persistence",
    )

    for sid in sorted(registry_ids):
        require(capture_by_id[sid].get("url") == registry_by_id[sid].get("url"), f"URL drift for {sid}")
        require(
            capture_by_id[sid].get("acquisition_result") == "RESOLVED_PUBLIC_SOURCE",
            f"capture result not resolved for {sid}",
        )
        require(capture_by_id[sid].get("acquired_at") == completed_at, f"acquired_at drift for {sid}")
        require(capture_by_id[sid].get("available_at") is None, f"Batch004 backdated available_at for {sid}")
        require(temporal_by_id[sid].get("available_at") is None, f"Batch005 promoted available_at for {sid}")

        row = availability_by_id[sid]
        require(row.get("inherited_acquired_at") == completed_at, f"Batch007 inherited acquisition drift for {sid}")
        require(row.get("conservative_available_at") == completed_at, f"Batch007 conservative availability drift for {sid}")
        require(
            row.get("temporal_original_as_of_eligible_from") == completed_at,
            f"Batch007 eligibility timestamp drift for {sid}",
        )
        require(
            row.get("historical_backdating_authorized") is False,
            f"historical backdating unexpectedly authorized for {sid}",
        )
        require(row.get("source_content_persisted") is False, f"Batch007 raw persistence unexpectedly claimed for {sid}")
        require(row.get("ordinary_replay_lineage_eligible") is False, f"ordinary replay unexpectedly enabled for {sid}")

    require(temporal.get("available_at_proven_count") == 0, "Batch005 available_at_proven_count must remain zero")
    require(temporal.get("strict_original_as_of_ready") is False, "Batch005 strict replay unexpectedly ready")
    overrides = temporal.get("successor_overrides")
    require(isinstance(overrides, list) and len(overrides) == 1, "expected exactly one temporal successor override")
    require(overrides[0].get("source_id") == "SRC-NERC-LTRA-2025", "unexpected temporal override source")
    require(overrides[0].get("successor_value") == "2026-01", "NERC publication correction drifted")
    require(overrides[0].get("assessment_year") == "2025", "NERC assessment year drifted")

    # Preserve historical Batch006 truth: fiber was open at that point.
    hist_gap = batch006_gap.get("results")
    require(isinstance(hist_gap, dict), "Batch006 results missing")
    require(hist_gap.get("SWITCHGEAR_LEAD_TIME_FIELD") == "POPULATED_APPROXIMATE_REGIONAL", "switchgear status drifted")
    require(hist_gap.get("LAND_PERMITTING_STATUS_FIELD") == "POPULATED_BOUNDED_FEDERAL_SCOPE", "land status drifted")
    require(hist_gap.get("FIBER_CONNECTIVITY_CAPACITY_FIELD") == "SOURCE_GAP", "Batch006 historical fiber gap was rewritten")
    require(hist_gap.get("SOURCE_GAP_FIELDS_REMAINING") == 1, "Batch006 source-gap count drifted")
    require(hist_gap.get("FIRST_SERIOUS_CONSTRAINT_RUN") == "BLOCKED", "Batch006 falsely claims serious-run readiness")

    # Batch009 legitimately closes that gap at bounded scope.
    gap9 = batch009_gap.get("results")
    require(isinstance(gap9, dict), "Batch009 source-gap results missing")
    require(gap9.get("FIBER_CONNECTIVITY_CAPACITY_FIELD") == FIBER_STATUS, "Batch009 fiber closure drifted")
    require(gap9.get("ORIGINAL_FROZEN_SOURCE_GAP_FIELDS_REMAINING") == 0, "Batch009 original source-gap count is not zero")
    require(gap9.get("DOMAIN_DATA_POPULATED") == "PARTIAL", "Batch009 falsely claims complete domain population")
    require(gap9.get("BENEFICIARY_LAYER_POPULATED") == "NO", "Batch009 falsely claims beneficiary population")
    require(gap9.get("FIRST_SLICE_REAL_RAW_ARTIFACTS_MATERIALIZED") == "NO", "Batch009 falsely claims raw materialization")
    require(gap9.get("IMPLEMENTATION_ADMISSION_READY") == "NO", "Batch009 falsely claims implementation admission")
    require(gap9.get("FIRST_SERIOUS_CONSTRAINT_RUN") == "BLOCKED", "Batch009 falsely claims serious-run readiness")
    require(batch009_gap.get("closed_blocker") == HISTORICAL_FIBER_BLOCKER, "Batch009 closed blocker drifted")
    require(
        set(batch009_gap.get("remaining_blockers", []))
        == {RAW_MATERIALIZATION_BLOCKER, ADMISSION_BLOCKER},
        "Batch009 current remaining blockers drifted",
    )
    require(batch009_gap.get("next_repo_executable_lane") == BATCH009_NEXT, "Batch009 next executable lane drifted")
    require(batch009_gap.get("predecessor_artifacts_rewritten") is False, "Batch009 rewrote predecessor state")

    source_extension = fiber_sources.get("sources")
    require(isinstance(source_extension, list) and len(source_extension) == 2, "Batch009 fiber source extension must contain two sources")
    extension_ids = source_ids(source_extension)
    require(
        extension_ids
        == {
            "SRC-DOE-PADUCAH-AI-ENERGY-PARTNERSHIP-2026-07-29",
            "SRC-LUMEN-RAPIDROUTES-2025-09-09",
        },
        "Batch009 fiber source identities drifted",
    )
    require(fiber_sources.get("source_content_persisted") is False, "Batch009 fiber source content falsely persisted")
    for source in source_extension:
        require(source.get("available_at") == source.get("acquired_at"), f"conservative availability drift for {source.get('source_id')}")
        require(source.get("historical_backdating_authorized") is False, f"fiber source backdating unexpectedly authorized for {source.get('source_id')}")
        require(source.get("ordinary_raw_lineage_eligible") is False, f"fiber source ordinary raw lineage unexpectedly ready for {source.get('source_id')}")

    updates = fiber_field.get("field_updates")
    require(isinstance(updates, list) and len(updates) == 1, "Batch009 fiber field overlay must contain one update")
    fiber_update = updates[0]
    require(fiber_update.get("field_name") == "fiber_connectivity_capacity", "fiber field name drifted")
    require(fiber_update.get("predecessor_status") == "SOURCE_GAP", "fiber predecessor status drifted")
    require(fiber_update.get("successor_status") == FIBER_STATUS, "fiber successor status drifted")
    require(fiber_field.get("source_gap_count_before") == 1, "fiber source-gap before count drifted")
    require(fiber_field.get("source_gap_count_after") == 0, "fiber source-gap after count drifted")

    value = fiber_update.get("value")
    require(isinstance(value, dict), "fiber structured value missing")
    site = value.get("site_access_example")
    provider = value.get("provider_capacity_example")
    require(isinstance(site, dict) and isinstance(provider, dict), "fiber bounded examples missing")
    require(site.get("site") == "DOE Paducah Site, Kentucky", "fiber site example drifted")
    require(site.get("fiber_connectivity") == "EXISTING", "fiber site connectivity claim drifted")
    require(site.get("exact_site_capacity") == "UNSPECIFIED", "fiber exact site capacity unexpectedly quantified")
    require(provider.get("provider") == "Lumen Technologies", "fiber provider example drifted")
    require(provider.get("advertised_connection_speeds_gbps") == [100, 400], "fiber provider speed profile drifted")
    uncertainty = fiber_update.get("uncertainty")
    require(
        isinstance(uncertainty, str)
        and "NOT_UNIVERSAL" in uncertainty
        and "DOES_NOT_ASSERT_EXACT_CAPACITY_AT_PADUCAH" in uncertainty,
        "fiber uncertainty boundary drifted",
    )

    observations = fiber_evidence.get("observations")
    require(isinstance(observations, list) and len(observations) == 2, "fiber evidence supplement must contain two observations")
    evidence_ids = {item.get("evidence_id") for item in observations}
    require(set(fiber_update.get("evidence_ids", [])) == evidence_ids, "fiber field/evidence IDs drifted")
    edges = fiber_graph.get("edge_updates")
    require(isinstance(edges, list) and len(edges) == 1, "fiber graph overlay must contain one edge update")
    require(edges[0].get("successor_status") == "SUPPORTED_BOUNDED_SITE_PROVIDER_SCOPE", "fiber graph scope drifted")
    require(
        "EXACT UNIVERSAL SITE CAPACITY IS NOT ASSERTED" in str(edges[0].get("semantic_limit", "")),
        "fiber graph universal-capacity guard missing",
    )

    # Batch010 shadow causal-chain population remains shadow and blocked.
    counts = batch010_status.get("counts")
    results10 = batch010_status.get("results")
    require(isinstance(counts, dict) and isinstance(results10, dict), "Batch010 status incomplete")
    require(
        counts
        == {
            "typed_claims": 10,
            "t5_candidate_proposals": 3,
            "relief_paths": 5,
            "beneficiary_relationship_evaluations": 4,
            "qualified_beneficiary_relationships": 0,
        },
        "Batch010 population counts drifted",
    )
    require(results10.get("CLAIM_LAYER_POPULATED") == "YES_SHADOW", "Batch010 claim layer status drifted")
    require(results10.get("T5_CONSTRAINT_CANDIDATE_LAYER_POPULATED") == "YES_SHADOW", "Batch010 candidate layer status drifted")
    require(results10.get("RELIEF_INVALIDATOR_LAYER_POPULATED") == "YES_SHADOW", "Batch010 relief layer status drifted")
    require(results10.get("T6_BENEFICIARY_RELATIONSHIP_LAYER_POPULATED") == "YES_BLOCKED_EVALUATIONS", "Batch010 beneficiary layer status drifted")
    require(results10.get("WATER_DEPENDENCY_PROMOTED_TO_CONSTRAINT") == "NO", "water dependency was promoted to constraint")
    require(results10.get("FIBER_DEPENDENCY_PROMOTED_TO_CONSTRAINT") == "NO", "fiber dependency was promoted to constraint")
    require(results10.get("CANONICAL_CONSTRAINTS_MINTED") == "NO", "Batch010 falsely minted canonical constraints")
    require(results10.get("QUALIFIED_BENEFICIARIES_MINTED") == "NO", "Batch010 falsely minted qualified beneficiaries")
    require(results10.get("FIRST_SERIOUS_CONSTRAINT_RUN") == "BLOCKED", "Batch010 falsely claims serious-run readiness")
    require(
        set(batch010_status.get("remaining_blockers", []))
        == {RAW_MATERIALIZATION_BLOCKER, ADMISSION_BLOCKER},
        "Batch010 current remaining blockers drifted",
    )
    require(batch010_status.get("next_repo_executable_lane") == BATCH010_NEXT, "Batch010 next executable lane drifted")
    require(batch010_status.get("predecessor_artifacts_rewritten") is False, "Batch010 rewrote predecessor state")

    claim_rows = claims.get("claims")
    require(isinstance(claim_rows, list) and len(claim_rows) == 10, "Batch010 claim registry count drifted")
    claim_ids = unique_ids(claim_rows, "claim_id", "claim")
    require(claim_ids == {f"CLM-AIDC-{n:03d}" for n in range(1, 11)}, "Batch010 claim IDs drifted")
    require(claims.get("claim_mode") == "REVIEWED_SHADOW_CLAIMS_NOT_ORDINARY_T3", "Batch010 claim mode drifted")

    candidate_rows = candidates.get("candidates")
    require(isinstance(candidate_rows, list) and len(candidate_rows) == 3, "Batch010 candidate count drifted")
    candidate_ids = unique_ids(candidate_rows, "constraint_candidate_id", "candidate")
    require(candidates.get("canonicalization_performed") is False, "Batch010 candidate canonicalization unexpectedly performed")
    require(
        set(candidates.get("explicitly_not_formed_as_constraints", []))
        == {"water_cooling_dependency", "fiber_connectivity_dependency"},
        "Batch010 dependency non-promotion boundary drifted",
    )
    for row in candidate_rows:
        cid = row.get("constraint_candidate_id")
        require(row.get("canonical_constraint_id") is None, f"candidate {cid} unexpectedly canonicalized")
        require(row.get("ordinary_t6_eligible") is False, f"candidate {cid} unexpectedly ordinary-T6 eligible")
        require(
            set(row.get("ineligibility_reasons", []))
            == {RAW_MATERIALIZATION_BLOCKER, ADMISSION_BLOCKER},
            f"candidate {cid} blocker set drifted",
        )
        require(set(row.get("claim_ids", [])).issubset(claim_ids), f"candidate {cid} references unknown claim")

    relief_rows = relief.get("relief_paths")
    require(isinstance(relief_rows, list) and len(relief_rows) == 5, "Batch010 relief-path count drifted")
    unique_ids(relief_rows, "relief_path_id", "relief path")
    for row in relief_rows:
        rid = row.get("relief_path_id")
        require(row.get("constraint_candidate_id") in candidate_ids, f"relief path {rid} references unknown candidate")
        require(row.get("invalidates_constraint") is False, f"relief path {rid} automatically invalidates constraint")
        require(set(row.get("support_claim_ids", [])).issubset(claim_ids), f"relief path {rid} references unknown claim")

    beneficiary_source_rows = beneficiary_sources.get("sources")
    require(isinstance(beneficiary_source_rows, list) and len(beneficiary_source_rows) == 6, "Batch010 beneficiary source count drifted")
    unique_ids(beneficiary_source_rows, "source_id", "beneficiary source")
    require(beneficiary_sources.get("source_content_persisted") is False, "Batch010 beneficiary source content falsely persisted")
    for source in beneficiary_source_rows:
        sid = source.get("source_id")
        require(source.get("available_at") == source.get("acquired_at"), f"beneficiary source availability drift for {sid}")
        require(source.get("historical_backdating_authorized") is False, f"beneficiary source backdating unexpectedly authorized for {sid}")
        require(source.get("ordinary_raw_lineage_eligible") is False, f"beneficiary source ordinary lineage unexpectedly ready for {sid}")

    relationship_rows = beneficiaries.get("relationships")
    require(isinstance(relationship_rows, list) and len(relationship_rows) == 4, "Batch010 beneficiary evaluation count drifted")
    unique_ids(relationship_rows, "beneficiary_relationship_id", "beneficiary relationship")
    require(beneficiaries.get("qualified_relationship_count") == 0, "Batch010 qualified relationship count is not zero")
    for row in relationship_rows:
        rid = row.get("beneficiary_relationship_id")
        require(row.get("constraint_candidate_id") in candidate_ids, f"{rid} references unknown candidate")
        require(row.get("constraint_id") is None, f"{rid} unexpectedly references canonical constraint")
        require(row.get("qualification_state") == "INELIGIBLE_TO_EVALUATE", f"{rid} unexpectedly qualified")
        require(row.get("eligibility_state") == "BLOCKED", f"{rid} unexpectedly eligible")
        require(row.get("beneficiary_confidence") is None, f"{rid} unexpectedly assigned beneficiary confidence")

    # Batch011 adds a thin real outcome and deterministic shadow replay only.
    labels = set(outcome_taxonomy.get("labels", []))
    taxonomy_rules = set(outcome_taxonomy.get("rules", []))
    require("CAPACITY_ADDED" in labels, "Batch011 outcome taxonomy lost CAPACITY_ADDED")
    require(
        "OUTCOME_EFFECTIVE_TIME_MUST_NOT_BE_REPLACED_BY_HYDRA_AVAILABLE_AT" in taxonomy_rules,
        "Batch011 outcome taxonomy lost effective-time boundary",
    )
    require(
        "CAPACITY_ADDED_DOES_NOT_IMPLY_CONSTRAINT_RESOLVED" in taxonomy_rules,
        "Batch011 outcome taxonomy lost capacity-versus-resolution boundary",
    )
    require(
        "FIRST_CUSTOMER_SHIPMENT_DOES_NOT_BY_ITSELF_PROVE_BENEFICIARY_CAPTURE" in taxonomy_rules,
        "Batch011 outcome taxonomy lost beneficiary-capture boundary",
    )

    outcome_rows = outcome_records.get("records")
    require(isinstance(outcome_rows, list) and len(outcome_rows) == 1, "Batch011 real outcome count drifted")
    outcome = outcome_rows[0]
    require(outcome.get("outcome_label") == "CAPACITY_ADDED", "Batch011 outcome label drifted")
    require(
        outcome.get("related_constraint_candidate_id") == "T5C-AIDC-US-TRANSFORMER-SUPPLY-001",
        "Batch011 outcome candidate binding drifted",
    )
    effective = outcome.get("real_world_effective_time")
    require(isinstance(effective, dict), "Batch011 real-world effective-time object missing")
    require(effective.get("value") is None, "Batch011 invented exact real-world effective time")
    require(effective.get("no_later_than") == "2025-10-08", "Batch011 bounded effective date drifted")
    require(outcome.get("hydra_available_at") == "2026-09-26T01:57:00Z", "Batch011 HYDRA availability drifted")
    require(outcome.get("ordinary_replay_eligible") is False, "Batch011 ordinary replay unexpectedly eligible")
    require(
        RAW_MATERIALIZATION_BLOCKER in set(outcome.get("ordinary_replay_blockers", [])),
        "Batch011 outcome lost raw-materialization blocker",
    )
    outcome_counts = outcome_records.get("counts")
    require(
        outcome_counts
        == {
            "outcomes_captured": 1,
            "constraint_resolutions": 0,
            "beneficiary_capture_confirmed": 0,
        },
        "Batch011 outcome counts drifted",
    )

    require(shadow_replay.get("replay_mode") == "SHADOW_NORMALIZED_FIXTURE", "Batch011 replay mode drifted")
    require(shadow_replay.get("ordinary_replay_eligible") is False, "Batch011 ordinary replay unexpectedly enabled")
    require(
        shadow_replay.get("source_version_hash_status") == "BLOCKED_RAW_SOURCE_BODY_NOT_MATERIALIZED",
        "Batch011 source-version hash gate drifted",
    )
    frozen_inputs = shadow_replay.get("frozen_input_manifest")
    require(isinstance(frozen_inputs, list) and frozen_inputs, "Batch011 frozen replay input manifest missing")
    for entry in frozen_inputs:
        relative = entry.get("path")
        expected = entry.get("git_blob_sha")
        require(isinstance(relative, str) and isinstance(expected, str), "Batch011 frozen input entry invalid")
        path = ROOT / relative
        require(path.is_file(), f"Batch011 frozen replay input missing: {relative}")
        require(git_blob_sha(path) == expected, f"Batch011 frozen replay input drifted: {relative}")

    windows = shadow_replay.get("windows")
    require(isinstance(windows, list) and len(windows) == 2, "Batch011 replay-window count drifted")
    by_window = {row.get("window_id"): row for row in windows}
    pre = by_window.get("PRE_BATCH010_SUPPLIER_AVAILABILITY")
    post = by_window.get("AT_BATCH010_SUPPLIER_AVAILABILITY")
    require(isinstance(pre, dict) and isinstance(post, dict), "Batch011 replay windows missing")
    require(pre.get("diff") == [] and pre.get("future_leak_test") == "PASS", "Batch011 pre-window no-lookahead failed")
    require(post.get("diff") == [] and post.get("future_leak_test") == "PASS", "Batch011 post-window replay mismatch")
    pre_state = pre.get("expected_graph_state")
    post_state = post.get("expected_graph_state")
    require(isinstance(pre_state, dict) and isinstance(post_state, dict), "Batch011 expected graph states missing")
    require(
        pre_state.get("eligible_claim_ids") == [f"CLM-AIDC-{n:03d}" for n in range(1, 5)],
        "Batch011 pre-window claim boundary drifted",
    )
    require(pre_state.get("beneficiary_relationship_ids") == [], "Batch011 pre-window leaked beneficiary relationships")
    require(pre_state.get("outcome_ids") == [], "Batch011 pre-window leaked outcomes")
    require(len(post_state.get("eligible_claim_ids", [])) == 10, "Batch011 post-window claim count drifted")
    require(len(post_state.get("beneficiary_relationship_ids", [])) == 4, "Batch011 post-window beneficiary count drifted")
    require(
        post_state.get("outcome_ids") == ["OUT-AIDC-EATON-NACOGDOCHES-CAPACITY-ADDED-001"],
        "Batch011 post-window outcome set drifted",
    )

    require(determinism.get("repeat_execution_match") is True, "Batch011 determinism repeat execution drifted")
    require(determinism.get("future_leak_test") == "PASS", "Batch011 determinism future-leak test drifted")
    require(determinism.get("ordinary_replay_determinism_claimed") is False, "Batch011 falsely claims ordinary replay determinism")
    require(
        determinism.get("ordinary_replay_blocker") == RAW_MATERIALIZATION_BLOCKER,
        "Batch011 determinism blocker drifted",
    )

    updates11 = required_cases.get("updates")
    require(isinstance(updates11, list) and len(updates11) == 2, "Batch011 required-case update count drifted")
    case_updates = {row.get("case_id"): row for row in updates11}
    require(
        case_updates.get(7, {}).get("successor_status") == "COVERED_BOUNDED_CAPACITY_RELIEF_OUTCOME",
        "Batch011 case 7 outcome coverage drifted",
    )
    require(
        case_updates.get(8, {}).get("successor_status") == "COVERED_SHADOW_NORMALIZED_FIXTURE_ONLY",
        "Batch011 case 8 replay coverage drifted",
    )
    require(
        set(required_cases.get("remaining_real_case_gaps", []))
        == {
            "CASE_1_PROJECT_SPECIFIC_TRUE_CAPACITY_CONSTRAINT",
            "CASE_2_MATCHED_FALSE_CONSTRAINT_PRIMARY_COUNTEREVIDENCE",
            "CASE_4_REAL_CONTRADICTION",
            "CASE_6_FULLY_QUALIFIED_AND_CAPTURED_BENEFICIARY",
            "CASE_10_REAL_CANCELLED_PROJECT",
        },
        "Batch011 remaining real-case gaps drifted",
    )

    r11 = batch011_master.get("readiness")
    require(isinstance(r11, dict), "Batch011 master readiness missing")
    require(r11["OUTCOME_LABEL_LAYER_POPULATED"].get("status") == "YES_SLICE_SCOPED", "Batch011 master outcome-label status drifted")
    require(r11["REAL_OUTCOME_RECORDS"].get("status") == "THIN", "Batch011 master falsely thickens real outcomes")
    require(r11["REAL_OUTCOME_RECORDS"].get("count") == 1, "Batch011 master real-outcome count drifted")
    require(r11["SHADOW_REPLAY_FIXTURE_READY"].get("status") == "YES", "Batch011 master shadow replay not ready")
    require(r11["SHADOW_NO_LOOKAHEAD"].get("status") == "PASS", "Batch011 master no-lookahead failed")
    require(r11["SHADOW_DETERMINISM"].get("status") == "PASS", "Batch011 master determinism failed")
    require(r11["POINT_IN_TIME_REPLAY_READY"].get("status") == "NO_ORDINARY", "Batch011 master falsely enables ordinary replay")
    require(r11["OUTCOME_EVALUATION_READY"].get("status") == "THIN_NOT_ACCEPTANCE_READY", "Batch011 master outcome readiness overstated")
    require(r11["FULL_CONSTRAINT_RUN_READY"].get("status") == "NO", "Batch011 master falsely claims full-run readiness")
    require(batch011_master.get("first_serious_constraint_run") == "BLOCKED", "Batch011 master falsely claims serious-run readiness")
    require(
        {
            RAW_MATERIALIZATION_BLOCKER,
            ADMISSION_BLOCKER,
            "HISTORICAL-CASE-004-CONTRADICTION-REAL-CASE-ABSENT",
            "HISTORICAL-CASE-010-CANCELLED-PROJECT-ABSENT",
            "REQUIRED-CASE-001-PROJECT-SPECIFIC-TRUE-CONSTRAINT-ABSENT",
            "REQUIRED-CASE-002-MATCHED-FALSE-CONSTRAINT-ABSENT",
            "REQUIRED-CASE-006-FULLY-QUALIFIED-CAPTURED-BENEFICIARY-ABSENT",
        }.issubset(set(batch011_master.get("remaining_blockers", []))),
        "Batch011 master blocker set lost required gates",
    )

    # Batch012 closes contradiction/cancelled-project examples without
    # overpromoting the remaining true/false/beneficiary acceptance cases.
    case_rows12 = cases12.get("records")
    require(isinstance(case_rows12, list) and len(case_rows12) == 3, "Batch012 historical case count drifted")
    case_ids12 = unique_ids(case_rows12, "historical_case_id", "Batch012 historical case")
    by_required12 = {row.get("required_case_id"): row for row in case_rows12}
    require(set(by_required12) == {1, 4, 10}, "Batch012 historical required-case set drifted")

    case1 = by_required12[1]
    require(
        case1.get("status") == "PARTIAL_STRENGTHENED_REAL_LOCALIZED_CONSTRAINT",
        "Batch012 case1 falsely promoted beyond localized partial constraint",
    )
    require(
        case1.get("unresolved_requirement")
        == "NO_NAMED_PROJECT_WITH_PLANNED_ENERGIZATION_FAILURE_CAUSALLY_TIED_TO_THIS_CONSTRAINT",
        "Batch012 case1 named-project energization gap drifted",
    )
    require(case1.get("overpromotion_prohibited") is True, "Batch012 case1 overpromotion guard removed")

    case4 = by_required12[4]
    require(case4.get("status") == "COVERED_REVIEWED_SHADOW", "Batch012 contradiction status drifted")
    require(
        case4.get("contradiction_state") == "PRESERVE_BOTH_SCOPE_STATES_NO_FABRICATED_CONSENSUS",
        "Batch012 contradiction no-consensus boundary drifted",
    )
    require(
        case4.get("semantic_resolution")
        == "DEVELOPMENT_PLAN_CAPACITY_IS_NOT_APPROVED_INTERCONNECTION_SERVICE_CAPACITY",
        "Batch012 contradiction scope separation drifted",
    )
    require(case4.get("ordinary_replay_eligible") is False, "Batch012 contradiction became ordinary-replay eligible")

    case10 = by_required12[10]
    require(case10.get("status") == "COVERED_REVIEWED_SHADOW", "Batch012 cancelled-project status drifted")
    require(case10.get("prior_state_preserved") is True, "Batch012 cancelled-project prior state was erased")
    require(case10.get("historical_rewrite") is False, "Batch012 cancelled-project history was rewritten")
    require(
        case10.get("semantic_limit")
        == "DO_NOT_GENERALIZE_WITHDRAWAL_TO_AWS_REGIONAL_OR_NATIONAL_DEMAND",
        "Batch012 cancelled-project scope was generalized",
    )
    require(case10.get("ordinary_replay_eligible") is False, "Batch012 cancelled-project case became ordinary-replay eligible")

    observations12 = evidence12.get("observations")
    require(isinstance(observations12, list) and len(observations12) == 5, "Batch012 historical evidence count drifted")
    evidence_ids12 = unique_ids(observations12, "evidence_id", "Batch012 historical evidence")
    for row in case_rows12:
        require(
            set(row.get("evidence_ids", [])).issubset(evidence_ids12),
            f"Batch012 case {row.get('historical_case_id')} references unknown evidence",
        )

    outcome_rows12 = outcomes12.get("records")
    require(isinstance(outcome_rows12, list) and len(outcome_rows12) == 1, "Batch012 outcome supplement count drifted")
    cancelled = outcome_rows12[0]
    require(cancelled.get("outcome_label") == "PROJECT_CANCELLED", "Batch012 cancelled outcome label drifted")
    require(
        cancelled.get("project") == "Calvert Technology Center Conceptual Site Development Plan",
        "Batch012 cancelled-project identity drifted",
    )
    require(cancelled.get("real_world_effective_time") == "2026-08-04", "Batch012 cancellation effective date drifted")
    require(cancelled.get("hydra_available_at") is None, "Batch012 invented exact HYDRA available_at")
    require(cancelled.get("observed_at") is None, "Batch012 invented exact observed_at")
    require(cancelled.get("ordinary_replay_eligible") is False, "Batch012 cancelled outcome became ordinary-replay eligible")
    require(outcomes12.get("current_slice_outcome_count_after") == 2, "Batch012 total real-outcome count drifted")
    require(outcomes12.get("constraint_resolutions_total") == 0, "Batch012 falsely claims constraint resolution")
    require(outcomes12.get("beneficiary_capture_confirmed_total") == 0, "Batch012 falsely claims beneficiary capture")

    overlay_updates12 = overlay12.get("updates")
    require(isinstance(overlay_updates12, list) and len(overlay_updates12) == 3, "Batch012 required-case overlay count drifted")
    overlay_by_case12 = {row.get("case_id"): row for row in overlay_updates12}
    require(
        overlay_by_case12.get(1, {}).get("successor_status")
        == "PARTIAL_STRENGTHENED_REAL_LOCALIZED_CONSTRAINT",
        "Batch012 case1 overlay falsely closed true-project case",
    )
    require(
        overlay_by_case12.get(4, {}).get("successor_status") == "COVERED_REVIEWED_SHADOW",
        "Batch012 contradiction overlay drifted",
    )
    require(
        overlay_by_case12.get(10, {}).get("successor_status") == "COVERED_REVIEWED_SHADOW",
        "Batch012 cancelled-project overlay drifted",
    )
    current_case_state12 = overlay12.get("current_case_state")
    require(isinstance(current_case_state12, dict), "Batch012 current case state missing")
    require(set(current_case_state12.get("partial", [])) == {1, 6}, "Batch012 partial-case set drifted")
    require(set(current_case_state12.get("gap", [])) == {2}, "Batch012 gap-case set drifted")

    r12 = batch012_master.get("readiness")
    require(isinstance(r12, dict), "Batch012 master readiness missing")
    require(r12["REAL_OUTCOME_RECORDS"].get("status") == "THIN", "Batch012 master falsely thickens real outcomes")
    require(r12["REAL_OUTCOME_RECORDS"].get("count") == 2, "Batch012 master real-outcome count drifted")
    require(r12["REAL_CONTRADICTION_CASE"].get("status") == "YES_REVIEWED_SHADOW", "Batch012 master contradiction status drifted")
    require(r12["REAL_CANCELLED_PROJECT_CASE"].get("status") == "YES_REVIEWED_SHADOW", "Batch012 master cancelled-project status drifted")
    require(
        r12["TRUE_PROJECT_SPECIFIC_CAPACITY_CASE"].get("status")
        == "PARTIAL_LOCALIZED_SYSTEM_CONSTRAINT_ONLY",
        "Batch012 master falsely closes named project capacity case",
    )
    require(r12["FALSE_CONSTRAINT_CASE"].get("status") == "NO_MATCHED_CASE", "Batch012 master falsely closes matched false-constraint case")
    require(r12["VALID_BENEFICIARY_CASE"].get("status") == "PARTIAL_NOT_QUALIFIED", "Batch012 master falsely qualifies beneficiary case")
    require(r12["POINT_IN_TIME_REPLAY_READY"].get("status") == "NO_ORDINARY", "Batch012 master falsely enables ordinary replay")
    require(r12["OUTCOME_EVALUATION_READY"].get("status") == "THIN_NOT_ACCEPTANCE_READY", "Batch012 master outcome readiness overstated")
    require(r12["FULL_CONSTRAINT_RUN_READY"].get("status") == "NO", "Batch012 master falsely claims full-run readiness")
    require(batch012_master.get("first_serious_constraint_run") == "BLOCKED", "Batch012 master falsely claims serious-run readiness")
    require(
        set(batch012_master.get("remaining_blockers", []))
        == {
            RAW_MATERIALIZATION_BLOCKER,
            ADMISSION_BLOCKER,
            "REQUIRED-CASE-001-NAMED-PROJECT-ENERGIZATION-FAILURE-NOT-PROVEN",
            "REQUIRED-CASE-002-MATCHED-FALSE-CONSTRAINT-PRIMARY-COUNTEREVIDENCE-ABSENT",
            "REQUIRED-CASE-006-FULLY-QUALIFIED-BENEFICIARY-NOT-PROVEN",
        },
        "Batch012 master remaining blocker set drifted",
    )
    require(
        batch012_master.get("next_repo_executable_lane")
        == "FIRST-SLICE-REMAINING-CASE-001-002-006-EVIDENCE-CLOSURE",
        "Batch012 next executable lane drifted",
    )

    # Authority and raw-materialization blockers remain open.
    decomposition = admission.get("decomposition")
    require(isinstance(decomposition, dict), "Batch002 admission decomposition missing")
    blocker = decomposition.get(ADMISSION_BLOCKER)
    require(
        isinstance(blocker, dict) and blocker.get("state") == "OPEN_BLOCKING",
        "signed admission blocker no longer OPEN_BLOCKING",
    )
    require(admission.get("implementation_admitted") == "NO", "native implementation unexpectedly admitted")
    require(admission.get("runtime_activation_authorized") == "NO", "runtime activation unexpectedly authorized")
    require(admission.get("canonical_promotion_authorized") == "NO", "canonical promotion unexpectedly authorized")
    require(admission.get("live_source_authorized") == "NO", "live source unexpectedly authorized")

    raw_results = raw_status.get("results")
    require(isinstance(raw_results, dict), "Batch008 raw results missing")
    require(raw_results.get("PRIVATE_RAW_STORE_IMPLEMENTED") == "YES", "private raw store not marked implemented")
    require(raw_results.get("NINE_REAL_SOURCE_ARTIFACTS_MATERIALIZED") == "NO", "real raw sources falsely marked materialized")
    require(raw_results.get("NETWORK_ACQUISITION_AUTHORIZED") == "NO", "network acquisition unexpectedly authorized")
    require(raw_results.get("PUBLIC_RAW_SOURCE_CONTENT_PUBLISHED") == "NO", "raw third-party source content unexpectedly public")
    require(
        set(raw_status.get("remaining_blockers", []))
        == {RAW_MATERIALIZATION_BLOCKER, HISTORICAL_FIBER_BLOCKER, ADMISSION_BLOCKER},
        "Batch008 historical remaining blockers drifted",
    )

    batch008_readiness = batch008_master.get("readiness")
    require(isinstance(batch008_readiness, dict), "Batch008 master readiness missing")
    require(
        batch008_readiness["FIBER_CONNECTIVITY_CAPACITY_READY"].get("status") == "NO",
        "Batch008 historical master fiber state was rewritten",
    )

    boundary = raw_contract.get("public_repository_boundary")
    contract = raw_contract.get("artifact_contract")
    require(isinstance(boundary, dict) and isinstance(contract, dict), "raw-store contract incomplete")
    require(boundary.get("raw_source_bytes_allowed_in_public_repo") is False, "raw bytes unexpectedly allowed in public repo")
    require(boundary.get("private_raw_root_required") is True, "private raw root requirement removed")
    require(boundary.get("network_acquisition_performed_by_store") is False, "raw store unexpectedly performs network acquisition")
    require(
        set(contract.get("ordinary_t2_eligibility_requires", []))
        == {
            "VALID_RAW_ARTIFACT_BYTES",
            "MATCHING_ARTIFACT_SHA256",
            "SOURCE_ID",
            "SOURCE_VERSION_ID",
            "ACQUIRED_AT",
            "AVAILABLE_AT",
            "ELIGIBLE_PROCESSING_DISPOSITION",
            "DECLARED_RELEASE_MEMBERSHIP",
        },
        "ordinary T2 eligibility contract drifted",
    )

    # Batch009 and Batch010 master transitions.
    r9 = batch009_master.get("readiness")
    require(isinstance(r9, dict), "Batch009 master readiness missing")
    require(r9["ORIGINAL_FIRST_SLICE_SOURCE_GAPS_CLOSED"].get("status") == "YES", "Batch009 master did not close original source gaps")
    require(batch009_master.get("next_repo_executable_lane") == BATCH009_NEXT, "Batch009 master next lane drifted")

    r10 = batch010_master.get("readiness")
    require(isinstance(r10, dict), "Batch010 master readiness missing")
    require(r10["CLAIM_LAYER_POPULATED"].get("status") == "YES_SHADOW", "Batch010 master claim status drifted")
    require(r10["T5_CANDIDATE_LAYER_POPULATED"].get("status") == "YES_SHADOW", "Batch010 master candidate status drifted")
    require(r10["RELIEF_INVALIDATOR_LAYER_POPULATED"].get("status") == "YES_SHADOW", "Batch010 master relief status drifted")
    require(r10["BENEFICIARY_LAYER_POPULATED"].get("status") == "YES_BLOCKED_EVALUATIONS", "Batch010 master beneficiary status drifted")
    require(r10["QUALIFIED_BENEFICIARY_RELATIONSHIPS"].get("status") == "NO", "Batch010 master falsely qualifies beneficiaries")
    require(r10["FIRST_SLICE_RAW_ARTIFACTS_MATERIALIZED"].get("status") == "NO", "Batch010 master falsely marks raw artifacts materialized")
    require(r10["FIRST_SLICE_RAW_ARTIFACTS_MATERIALIZED"].get("blocker") == RAW_MATERIALIZATION_BLOCKER, "Batch010 master raw blocker drifted")
    require(r10["IMPLEMENTATION_ADMITTED"].get("status") == "NO", "Batch010 master falsely admits implementation")
    require(r10["IMPLEMENTATION_ADMITTED"].get("blocker") == ADMISSION_BLOCKER, "Batch010 master admission blocker drifted")
    require(r10["FULL_CONSTRAINT_RUN_READY"].get("status") == "NO", "Batch010 master falsely claims full-run readiness")
    require(batch010_master.get("first_serious_constraint_run") == "BLOCKED", "Batch010 master falsely claims serious-run readiness")
    require(batch010_master.get("next_repo_executable_lane") == BATCH010_NEXT, "Batch010 master next lane drifted")

    # Batch016 persists receipt/release authority and preserves Batch015 confidence semantics.
    custody_required16 = set(custody16.get("ordinary_t2_eligibility_requires", []))
    require(
        custody_required16
        == {
            "VALID_RAW_ARTIFACT_BYTES",
            "MATCHING_ARTIFACT_SHA256",
            "SOURCE_ID",
            "SOURCE_VERSION_ID",
            "ACQUIRED_AT",
            "AVAILABLE_AT",
            "ELIGIBLE_PROCESSING_DISPOSITION",
            "EXACT_PERSISTED_SOURCE_VERSION_RECEIPT",
            "EXACT_PERSISTED_RELEASE_MANIFEST",
            "EXACT_RELEASE_MEMBERSHIP",
        },
        f"Batch016 persisted custody requirement set drifted: {sorted(custody_required16)}",
    )
    custody_semantics16 = custody16.get("authority_semantics")
    require(isinstance(custody_semantics16, dict), "Batch016 custody semantics missing")
    require(
        custody_semantics16.get("caller_supplied_in_memory_receipt_authoritative") is False,
        "Batch016 in-memory receipt authority unexpectedly enabled",
    )
    require(
        custody_semantics16.get("caller_supplied_in_memory_release_manifest_authoritative") is False,
        "Batch016 in-memory release authority unexpectedly enabled",
    )
    require(
        custody_semantics16.get("self_consistent_recomputed_digest_sufficient") is False,
        "Batch016 recomputed digest unexpectedly sufficient for authority",
    )
    require(
        custody_semantics16.get("persisted_record_identity_required") is True,
        "Batch016 persisted identity requirement removed",
    )

    custody_results16 = custody_status16.get("results")
    require(isinstance(custody_results16, dict), "Batch016 custody status missing")
    require(custody_results16.get("PERSISTED_RECEIPT_IDENTITY_REQUIRED") == "YES", "Batch016 persisted receipt identity not required")
    require(custody_results16.get("PERSISTED_RELEASE_IDENTITY_REQUIRED") == "YES", "Batch016 persisted release identity not required")
    require(custody_results16.get("FORGED_IN_MEMORY_RELEASE_AUTHORITY") == "NO", "Batch016 forged release became authority")
    require(custody_results16.get("FORGED_RECEIPT_DISPOSITION_UPGRADE") == "BLOCKED", "Batch016 forged disposition upgrade not blocked")
    require(custody_results16.get("TYPED_CONFIDENCE_TRANSPORT_READY") == "YES", "Batch016 lost Batch015 typed confidence")
    require(custody_results16.get("CONFIDENCE_READY") == "YES_WITH_EXPLICIT_UNKNOWNS", "Batch016 confidence state regressed")
    require(custody_results16.get("EVALUATION_PROTOCOL_READY") == "YES_SHADOW_BOUNDED", "Batch016 evaluation protocol regressed")
    require(custody_results16.get("FIRST_SLICE_REAL_RAW_ARTIFACTS_MATERIALIZED") == "NO", "Batch016 falsely materializes raw source bodies")
    require(custody_results16.get("IMPLEMENTATION_ADMITTED") == "NO", "Batch016 falsely admits implementation")
    require(custody_results16.get("FULL_CONSTRAINT_RUN_READY") == "NO", "Batch016 falsely claims full-run readiness")
    require(custody_results16.get("FIRST_SERIOUS_CONSTRAINT_RUN") == "BLOCKED", "Batch016 falsely claims serious-run readiness")

    r16 = batch016_master.get("readiness")
    require(isinstance(r16, dict), "Batch016 master readiness missing")
    require(r16["TYPED_CONFIDENCE_TRANSPORT_READY"].get("status") == "YES", "Batch016 master lost typed confidence")
    require(r16["CONFIDENCE_READY"].get("status") == "YES_WITH_EXPLICIT_UNKNOWNS", "Batch016 master confidence state regressed")
    require(r16["EVALUATION_PROTOCOL_READY"].get("status") == "YES_SHADOW_BOUNDED", "Batch016 master evaluation protocol regressed")
    require(r16["T1_T2_PERSISTED_CHAIN_OF_CUSTODY_READY"].get("status") == "YES", "Batch016 master lost custody readiness")
    require(r16["FIRST_SLICE_RAW_ARTIFACTS_MATERIALIZED"].get("status") == "NO", "Batch016 master falsely materializes raw artifacts")
    require(r16["IMPLEMENTATION_ADMITTED"].get("status") == "NO", "Batch016 master falsely admits implementation")
    require(r16["FULL_CONSTRAINT_RUN_READY"].get("status") == "NO", "Batch016 master falsely claims full-run readiness")
    require(batch016_master.get("first_serious_constraint_run") == "BLOCKED", "Batch016 master falsely claims serious-run readiness")
    require(
        batch016_master.get("next_repo_executable_lane") == "FIRST-SLICE-REAL-OUTCOME-COVERAGE-EXPANSION",
        "Batch016 next repo-executable lane drifted",
    )

    # Manifest discovery is dynamic so a new Lily successor batch cannot silently
    # bypass the guard or break it merely because the list was hard-coded.
    manifests = discover_current_manifests()
    manifest_members = 0
    shared_pin_divergences = 0
    for path in manifests:
        members, divergences = validate_manifest(path)
        manifest_members += members
        shared_pin_divergences += divergences

    latest_batch, latest_master_path, latest_master = discover_latest_master()
    latest_manifest_batch, latest_manifest_revision = manifest_identity(manifests[-1])
    require(latest_manifest_batch == latest_batch, "latest successor manifest/master batch mismatch")

    latest_readiness = latest_master.get("readiness")
    require(isinstance(latest_readiness, dict), "latest master readiness missing")
    if "FULL_CONSTRAINT_RUN_READY" in latest_readiness:
        require(
            latest_readiness["FULL_CONSTRAINT_RUN_READY"].get("status") == "NO",
            "latest master falsely claims full-run readiness",
        )
    require(
        latest_master.get("first_serious_constraint_run") == "BLOCKED",
        "latest master falsely claims serious-run readiness",
    )

    print("CONSTRAINT_FIRST_SLICE_INTEGRATION_VALIDATION=PASS")
    print(f"SLICE_ID={SLICE_ID}")
    print(f"ORIGINAL_REGISTERED_SOURCE_COUNT={len(registry_ids)}")
    print(f"FIBER_EXTENSION_SOURCE_COUNT={len(extension_ids)}")
    print(f"BATCH010_CLAIMS={len(claim_ids)}")
    print(f"BATCH010_CANDIDATES={len(candidate_ids)}")
    print(f"BATCH010_BENEFICIARY_EVALUATIONS={len(relationship_rows)}")
    print(f"BATCH011_REAL_OUTCOMES={len(outcome_rows)}")
    print(f"BATCH011_SHADOW_REPLAY_WINDOWS={len(windows)}")
    print(f"BATCH012_HISTORICAL_CASES={len(case_ids12)}")
    print(f"BATCH012_REAL_OUTCOMES_TOTAL={outcomes12.get('current_slice_outcome_count_after')}")
    print(f"CAPTURE_COMPLETED_AT={completed_at}")
    print(f"MANIFESTS_VALIDATED={len(manifests)}")
    print(f"MANIFEST_MEMBERS_VALIDATED={manifest_members}")
    print(f"HISTORICAL_SHARED_PIN_DIVERGENCES={shared_pin_divergences}")
    print(f"LATEST_SUCCESSOR_BATCH={latest_batch:03d}")
    print(f"LATEST_MANIFEST_REVISION=V{latest_manifest_revision:03d}")
    print(f"LATEST_MASTER={latest_master_path.name}")
    print("IMPLEMENTATION_ADMITTED=NO")
    print("REAL_NINE_SOURCE_MATERIALIZATION=NO")
    print("QUALIFIED_BENEFICIARIES=0")
    print("T1_T2_PERSISTED_CHAIN_OF_CUSTODY_READY=YES")
    print("FIRST_SERIOUS_CONSTRAINT_RUN=BLOCKED")
    print(f"LATEST_NEXT_REPO_EXECUTABLE_LANE={latest_master.get('next_repo_executable_lane')}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print("CONSTRAINT_FIRST_SLICE_INTEGRATION_VALIDATION=FAIL")
        print(f"ERROR={exc}")
        raise SystemExit(1)
