#!/usr/bin/env python3
"""Read-only cross-batch integration guard for the Constraint first slice.

The guard validates immutable successor evidence, bounded semantics, and current
fail-closed readiness. It does not fetch source data, create domain claims,
mint authority, activate runtime behavior, or promote canonical state.
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

MANIFEST_RE = re.compile(r"BATCH(?P<batch>\d{3})_ARTIFACT_MANIFEST")
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


def batch_from_name(path: Path, pattern: re.Pattern[str]) -> int:
    match = pattern.search(path.name)
    require(match is not None, f"batch number missing from {path.name}")
    return int(match.group("batch"))


def discover_manifests() -> list[Path]:
    found: dict[int, Path] = {}
    for path in VALIDATION.glob("HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH*_ARTIFACT_MANIFEST_V001_20260925.json"):
        batch = batch_from_name(path, MANIFEST_RE)
        if batch >= 3:
            require(batch not in found, f"duplicate manifest for Batch{batch:03d}")
            found[batch] = path
    require(found, "no successor manifests discovered")
    highest = max(found)
    expected = set(range(3, highest + 1))
    require(set(found) == expected, f"successor manifest sequence has gaps: found={sorted(found)}")
    return [found[n] for n in sorted(found)]


def discover_latest_master() -> tuple[int, Path, dict[str, Any]]:
    found: dict[int, Path] = {}
    for path in ARCH.glob("HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH*_MASTER_STATUS_V001_20260925.json"):
        batch = batch_from_name(path, MASTER_RE)
        found[batch] = path
    require(found, "no successor master status discovered")
    batch = max(found)
    path = found[batch]
    return batch, path, load_json(path)


def validate_manifest(manifest_path: Path) -> tuple[int, int]:
    """Validate versioned domain pins; tolerate historical shared-tool evolution.

    Batch manifests may pin shared validators/tests that legitimately evolve in
    later batches. Versioned docs/constraint artifacts, however, are immutable
    successor evidence and must still match their recorded git blob.
    """

    manifest = load_json(manifest_path)
    artifacts = manifest.get("artifacts")
    require(
        isinstance(artifacts, list) and artifacts,
        f"manifest artifacts missing: {manifest_path.name}",
    )
    count = 0
    shared_divergence = 0
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
            # Shared code/tests can evolve; the historical manifest still pins
            # the exact version used by that batch.
            shared_divergence += 1
        count += 1
    return count, shared_divergence


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
    ):
        require(doc.get("slice_id") == SLICE_ID, f"{name} slice_id drifted")

    # Original nine-source PIT continuity.
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

    # Preserve historical Batch006 state: fiber was genuinely open there.
    hist_gap = batch006_gap.get("results")
    require(isinstance(hist_gap, dict), "Batch006 results missing")
    require(hist_gap.get("SWITCHGEAR_LEAD_TIME_FIELD") == "POPULATED_APPROXIMATE_REGIONAL", "switchgear status drifted")
    require(hist_gap.get("LAND_PERMITTING_STATUS_FIELD") == "POPULATED_BOUNDED_FEDERAL_SCOPE", "land status drifted")
    require(hist_gap.get("FIBER_CONNECTIVITY_CAPACITY_FIELD") == "SOURCE_GAP", "Batch006 historical fiber gap was rewritten")
    require(hist_gap.get("SOURCE_GAP_FIELDS_REMAINING") == 1, "Batch006 source-gap count drifted")
    require(hist_gap.get("FIRST_SERIOUS_CONSTRAINT_RUN") == "BLOCKED", "Batch006 falsely claims serious-run readiness")

    # Batch009 closes that historical gap only at bounded scope.
    gap9 = batch009_gap.get("results")
    require(isinstance(gap9, dict), "Batch009 source-gap results missing")
    require(gap9.get("FIBER_CONNECTIVITY_CAPACITY_FIELD") == FIBER_STATUS, "Batch009 fiber status drifted")
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

    # Batch010 shadow causal-chain population must remain shadow and blocked.
    counts = batch010_status.get("counts")
    results10 = batch010_status.get("results")
    require(isinstance(counts, dict) and isinstance(results10, dict), "Batch010 status incomplete")
    require(counts == {
        "typed_claims": 10,
        "t5_candidate_proposals": 3,
        "relief_paths": 5,
        "beneficiary_relationship_evaluations": 4,
        "qualified_beneficiary_relationships": 0,
    }, "Batch010 population counts drifted")
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
        require(row.get("canonical_constraint_id") is None, f"candidate {row.get('constraint_candidate_id')} unexpectedly canonicalized")
        require(row.get("ordinary_t6_eligible") is False, f"candidate {row.get('constraint_candidate_id')} unexpectedly ordinary-T6 eligible")
        require(
            set(row.get("ineligibility_reasons", []))
            == {RAW_MATERIALIZATION_BLOCKER, ADMISSION_BLOCKER},
            f"candidate {row.get('constraint_candidate_id')} blocker set drifted",
        )
        require(set(row.get("claim_ids", [])).issubset(claim_ids), f"candidate {row.get('constraint_candidate_id')} references unknown claim")

    relief_rows = relief.get("relief_paths")
    require(isinstance(relief_rows, list) and len(relief_rows) == 5, "Batch010 relief-path count drifted")
    unique_ids(relief_rows, "relief_path_id", "relief path")
    for row in relief_rows:
        require(row.get("constraint_candidate_id") in candidate_ids, f"relief path {row.get('relief_path_id')} references unknown candidate")
        require(row.get("invalidates_constraint") is False, f"relief path {row.get('relief_path_id')} automatically invalidates constraint")
        require(set(row.get("support_claim_ids", [])).issubset(claim_ids), f"relief path {row.get('relief_path_id')} references unknown claim")

    beneficiary_source_rows = beneficiary_sources.get("sources")
    require(isinstance(beneficiary_source_rows, list) and len(beneficiary_source_rows) == 6, "Batch010 beneficiary source count drifted")
    unique_ids(beneficiary_source_rows, "source_id", "beneficiary source")
    require(beneficiary_sources.get("source_content_persisted") is False, "Batch010 beneficiary source content falsely persisted")
    for source in beneficiary_source_rows:
        require(source.get("available_at") == source.get("acquired_at"), f"beneficiary source availability drift for {source.get('source_id')}")
        require(source.get("historical_backdating_authorized") is False, f"beneficiary source backdating unexpectedly authorized for {source.get('source_id')}")
        require(source.get("ordinary_raw_lineage_eligible") is False, f"beneficiary source ordinary lineage unexpectedly ready for {source.get('source_id')}")

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

    # Raw-store contract stays private and complete.
    boundary = raw_contract.get("public_repository_boundary")
    contract = raw_contract.get("artifact_contract")
    require(isinstance(boundary, dict) and isinstance(contract, dict), "raw-store contract incomplete")
    require(boundary.get("raw_source_bytes_allowed_in_public_repo") is False, "raw bytes unexpectedly allowed in public repo")
    require(boundary.get("private_raw_root_required") is True, "private raw root requirement removed")
    require(boundary.get("network_acquisition_performed_by_store") is False, "raw store unexpectedly performs network acquisition")
    required = set(contract.get("ordinary_t2_eligibility_requires", []))
    require(required == {
        "VALID_RAW_ARTIFACT_BYTES",
        "MATCHING_ARTIFACT_SHA256",
        "SOURCE_ID",
        "SOURCE_VERSION_ID",
        "ACQUIRED_AT",
        "AVAILABLE_AT",
        "ELIGIBLE_PROCESSING_DISPOSITION",
        "DECLARED_RELEASE_MEMBERSHIP",
    }, f"ordinary T2 eligibility contract drifted: {sorted(required)}")

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

    manifests = discover_manifests()
    manifest_members = 0
    shared_pin_divergences = 0
    for path in manifests:
        members, divergences = validate_manifest(path)
        manifest_members += members
        shared_pin_divergences += divergences

    latest_batch, latest_master_path, latest_master = discover_latest_master()
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
    require(
        batch_from_name(manifests[-1], MANIFEST_RE) == latest_batch,
        "latest successor manifest/master batch mismatch",
    )

    print("CONSTRAINT_FIRST_SLICE_INTEGRATION_VALIDATION=PASS")
    print(f"SLICE_ID={SLICE_ID}")
    print(f"ORIGINAL_REGISTERED_SOURCE_COUNT={len(registry_ids)}")
    print(f"FIBER_EXTENSION_SOURCE_COUNT={len(extension_ids)}")
    print(f"BATCH010_CLAIMS={len(claim_ids)}")
    print(f"BATCH010_CANDIDATES={len(candidate_ids)}")
    print(f"BATCH010_BENEFICIARY_EVALUATIONS={len(relationship_rows)}")
    print(f"CAPTURE_COMPLETED_AT={completed_at}")
    print(f"MANIFESTS_VALIDATED={len(manifests)}")
    print(f"MANIFEST_MEMBERS_VALIDATED={manifest_members}")
    print(f"HISTORICAL_SHARED_PIN_DIVERGENCES={shared_pin_divergences}")
    print(f"LATEST_SUCCESSOR_BATCH={latest_batch:03d}")
    print(f"LATEST_MASTER={latest_master_path.name}")
    print("IMPLEMENTATION_ADMITTED=NO")
    print("REAL_NINE_SOURCE_MATERIALIZATION=NO")
    print("QUALIFIED_BENEFICIARIES=0")
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
