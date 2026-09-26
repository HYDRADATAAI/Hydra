#!/usr/bin/env python3
"""Cross-batch integration validator for the current Constraint first slice.

Read-only NYX guard. It validates successor continuity and current readiness
without adding domain evidence, minting authority, fetching source content, or
promoting blocked lanes.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("HYDRA_REPO_ROOT", Path(__file__).resolve().parents[1])).resolve()
SLICE = ROOT / "docs/constraint/first_slice/ai_data_center_power_infrastructure_v1"
VALIDATION = ROOT / "docs/constraint/validation"
ARCH = ROOT / "docs/constraint/architecture"
IMPL = ROOT / "docs/constraint/implementation"

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
}

MANIFESTS = [
    VALIDATION / f"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH00{n}_ARTIFACT_MANIFEST_V001_20260925.json"
    for n in range(3, 10)
]

SLICE_ID = "AI_DATA_CENTER_POWER_INFRASTRUCTURE_V1"
ADMISSION_BLOCKER = "CI-TEST-008-BLOCKER-001B-NATIVE-T5-T6-SIGNED-ADMISSION-RECEIPT-ABSENT"
RAW_MATERIALIZATION_BLOCKER = "PIT-002B-FIRST-SLICE-NINE-SOURCE-RAW-CAPTURE-MATERIALIZATION"
HISTORICAL_FIBER_BLOCKER = "SOURCE-GAP-FIBER-CONNECTIVITY-CAPACITY"
NEXT_REPO_LANE = "FIRST-SLICE-CONSTRAINT-AND-BENEFICIARY-CLAIM-POPULATION"
FIBER_STATUS = "POPULATED_BOUNDED_SITE_AND_PROVIDER_PROFILE"


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


def validate_manifest(manifest_path: Path) -> int:
    manifest = load_json(manifest_path)
    artifacts = manifest.get("artifacts")
    require(
        isinstance(artifacts, list) and artifacts,
        f"manifest artifacts missing: {manifest_path.name}",
    )
    count = 0
    for entry in artifacts:
        require(isinstance(entry, dict), f"invalid manifest entry: {manifest_path.name}")
        relative = entry.get("path")
        expected = entry.get("git_blob_sha")
        require(isinstance(relative, str) and relative, f"manifest path missing: {manifest_path.name}")
        require(
            isinstance(expected, str) and len(expected) == 40,
            f"manifest git_blob_sha invalid: {relative}",
        )
        artifact = ROOT / relative
        require(artifact.is_file(), f"manifest member missing: {relative}")
        actual = git_blob_sha(artifact)
        require(
            actual == expected,
            f"manifest blob mismatch: {relative}: expected={expected} actual={actual}",
        )
        count += 1
    return count


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
    current_gap = docs["batch009_gap"]
    current_master = docs["batch009_master"]
    fiber_sources = docs["batch009_fiber_sources"]
    fiber_evidence = docs["batch009_fiber_evidence"]
    fiber_field = docs["batch009_fiber_field"]
    fiber_graph = docs["batch009_fiber_graph"]

    # Stable first-slice identity across every domain artifact.
    for name, doc in (
        ("source_registry", registry),
        ("pit_capture", capture),
        ("temporal_audit", temporal),
        ("batch006_gap", batch006_gap),
        ("availability", availability),
        ("batch009_gap", current_gap),
        ("batch009_fiber_sources", fiber_sources),
        ("batch009_fiber_evidence", fiber_evidence),
        ("batch009_fiber_field", fiber_field),
        ("batch009_fiber_graph", fiber_graph),
    ):
        require(doc.get("slice_id") == SLICE_ID, f"{name} slice_id drifted")

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
    nerc = overrides[0]
    require(nerc.get("source_id") == "SRC-NERC-LTRA-2025", "unexpected temporal override source")
    require(nerc.get("successor_value") == "2026-01", "NERC publication correction drifted")
    require(nerc.get("assessment_year") == "2025", "NERC assessment year drifted")

    # Historical Batch006 state must remain truthful: fiber was still open there.
    historical_gap_results = batch006_gap.get("results")
    require(isinstance(historical_gap_results, dict), "Batch006 results missing")
    require(
        historical_gap_results.get("SWITCHGEAR_LEAD_TIME_FIELD") == "POPULATED_APPROXIMATE_REGIONAL",
        "switchgear status drifted",
    )
    require(
        historical_gap_results.get("LAND_PERMITTING_STATUS_FIELD") == "POPULATED_BOUNDED_FEDERAL_SCOPE",
        "land status drifted",
    )
    require(
        historical_gap_results.get("FIBER_CONNECTIVITY_CAPACITY_FIELD") == "SOURCE_GAP",
        "Batch006 historical fiber gap was rewritten",
    )
    require(historical_gap_results.get("SOURCE_GAP_FIELDS_REMAINING") == 1, "Batch006 source-gap count drifted")
    require(
        historical_gap_results.get("FIRST_SERIOUS_CONSTRAINT_RUN") == "BLOCKED",
        "Batch006 falsely claims serious-run readiness",
    )

    # Batch009 legitimately closes the original fiber source gap, but only at bounded scope.
    current_gap_results = current_gap.get("results")
    require(isinstance(current_gap_results, dict), "Batch009 source-gap results missing")
    require(
        current_gap_results.get("FIBER_CONNECTIVITY_CAPACITY_FIELD") == FIBER_STATUS,
        "Batch009 fiber status drifted",
    )
    require(
        current_gap_results.get("ORIGINAL_FROZEN_SOURCE_GAP_FIELDS_REMAINING") == 0,
        "Batch009 original source-gap count is not zero",
    )
    require(
        current_gap_results.get("DOMAIN_DATA_POPULATED") == "PARTIAL",
        "Batch009 falsely claims complete domain population",
    )
    require(
        current_gap_results.get("BENEFICIARY_LAYER_POPULATED") == "NO",
        "Batch009 falsely claims beneficiary population",
    )
    require(
        current_gap_results.get("FIRST_SLICE_REAL_RAW_ARTIFACTS_MATERIALIZED") == "NO",
        "Batch009 falsely claims raw materialization",
    )
    require(
        current_gap_results.get("IMPLEMENTATION_ADMISSION_READY") == "NO",
        "Batch009 falsely claims implementation admission",
    )
    require(
        current_gap_results.get("FIRST_SERIOUS_CONSTRAINT_RUN") == "BLOCKED",
        "Batch009 falsely claims serious-run readiness",
    )
    require(current_gap.get("closed_blocker") == HISTORICAL_FIBER_BLOCKER, "Batch009 closed blocker drifted")
    require(
        set(current_gap.get("remaining_blockers", []))
        == {RAW_MATERIALIZATION_BLOCKER, ADMISSION_BLOCKER},
        "Batch009 current remaining blockers drifted",
    )
    require(current_gap.get("next_repo_executable_lane") == NEXT_REPO_LANE, "Batch009 next executable lane drifted")
    require(current_gap.get("predecessor_artifacts_rewritten") is False, "Batch009 rewrote predecessor state")

    # Fiber closure must not collapse site access and provider capacity into a universal site claim.
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
    require(
        all("NOT" in str(item.get("semantic_limit", "")) or "DOES NOT" in str(item.get("semantic_limit", "")) for item in observations),
        "fiber evidence semantic limits are missing",
    )

    edges = fiber_graph.get("edge_updates")
    require(isinstance(edges, list) and len(edges) == 1, "fiber graph overlay must contain one edge update")
    edge = edges[0]
    require(edge.get("predecessor_status") == "UNPOPULATED_SOURCE_GAP", "fiber graph predecessor status drifted")
    require(edge.get("successor_status") == "SUPPORTED_BOUNDED_SITE_PROVIDER_SCOPE", "fiber graph scope drifted")
    require(
        "EXACT UNIVERSAL SITE CAPACITY IS NOT ASSERTED" in str(edge.get("semantic_limit", "")),
        "fiber graph universal-capacity guard missing",
    )

    # Native T5->T6 admission remains fail-closed.
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
    require(admission.get("first_serious_constraint_run") == "BLOCKED", "admission status falsely claims serious-run readiness")

    # Batch008 closed the store mechanism, not the original nine-source materialization.
    raw_results = raw_status.get("results")
    require(isinstance(raw_results, dict), "Batch008 raw results missing")
    require(raw_results.get("PRIVATE_RAW_STORE_IMPLEMENTED") == "YES", "private raw store not marked implemented")
    require(raw_results.get("NINE_REAL_SOURCE_ARTIFACTS_MATERIALIZED") == "NO", "real raw sources falsely marked materialized")
    require(raw_results.get("NETWORK_ACQUISITION_AUTHORIZED") == "NO", "network acquisition unexpectedly authorized")
    require(raw_results.get("PUBLIC_RAW_SOURCE_CONTENT_PUBLISHED") == "NO", "raw third-party source content unexpectedly public")
    require(raw_results.get("FIRST_SERIOUS_CONSTRAINT_RUN") == "BLOCKED", "raw status falsely claims serious-run readiness")
    require(raw_status.get("next_population_blocker") == RAW_MATERIALIZATION_BLOCKER, "Batch008 next population blocker drifted")

    # Batch008 historical blocker set must remain intact; Batch009 closes fiber by successor.
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

    # Current master is Batch009.
    readiness = current_master.get("readiness")
    require(isinstance(readiness, dict), "Batch009 master readiness missing")
    require(readiness["IMPLEMENTATION_ADMITTED"].get("status") == "NO", "current master falsely admits implementation")
    require(readiness["IMPLEMENTATION_ADMITTED"].get("blocker") == ADMISSION_BLOCKER, "current master admission blocker drifted")
    require(readiness["ORIGINAL_FIRST_SLICE_SOURCE_GAPS_CLOSED"].get("status") == "YES", "current master did not close original source gaps")
    require(readiness["PRIVATE_RAW_ARTIFACT_STORE_READY"].get("status") == "YES", "current master lost raw-store readiness")
    require(readiness["FIRST_SLICE_RAW_ARTIFACTS_MATERIALIZED"].get("status") == "NO", "current master falsely marks raw sources materialized")
    require(readiness["FIRST_SLICE_RAW_ARTIFACTS_MATERIALIZED"].get("blocker") == RAW_MATERIALIZATION_BLOCKER, "current master raw blocker drifted")
    require(readiness["DOMAIN_DATA_POPULATED"].get("status") == "PARTIAL", "current master falsely claims complete domain population")
    require(readiness["FULL_CONSTRAINT_RUN_READY"].get("status") == "NO", "current master falsely claims full-run readiness")
    require(current_master.get("first_serious_constraint_run") == "BLOCKED", "current master falsely claims serious-run readiness")
    require(current_master.get("next_repo_executable_lane") == NEXT_REPO_LANE, "current master next executable lane drifted")

    # Raw-store contract stays private and complete.
    boundary = raw_contract.get("public_repository_boundary")
    contract = raw_contract.get("artifact_contract")
    require(isinstance(boundary, dict) and isinstance(contract, dict), "raw-store contract incomplete")
    require(boundary.get("raw_source_bytes_allowed_in_public_repo") is False, "raw bytes unexpectedly allowed in public repo")
    require(boundary.get("private_raw_root_required") is True, "private raw root requirement removed")
    require(boundary.get("network_acquisition_performed_by_store") is False, "raw store unexpectedly performs network acquisition")
    required = set(contract.get("ordinary_t2_eligibility_requires", []))
    expected_required = {
        "VALID_RAW_ARTIFACT_BYTES",
        "MATCHING_ARTIFACT_SHA256",
        "SOURCE_ID",
        "SOURCE_VERSION_ID",
        "ACQUIRED_AT",
        "AVAILABLE_AT",
        "ELIGIBLE_PROCESSING_DISPOSITION",
        "DECLARED_RELEASE_MEMBERSHIP",
    }
    require(required == expected_required, f"ordinary T2 eligibility contract drifted: {sorted(required)}")

    manifest_members = sum(validate_manifest(path) for path in MANIFESTS)

    print("CONSTRAINT_FIRST_SLICE_INTEGRATION_VALIDATION=PASS")
    print(f"SLICE_ID={SLICE_ID}")
    print(f"ORIGINAL_REGISTERED_SOURCE_COUNT={len(registry_ids)}")
    print(f"FIBER_EXTENSION_SOURCE_COUNT={len(extension_ids)}")
    print(f"CAPTURE_COMPLETED_AT={completed_at}")
    print(f"MANIFESTS_VALIDATED={len(MANIFESTS)}")
    print(f"MANIFEST_MEMBERS_VALIDATED={manifest_members}")
    print("ORIGINAL_FIRST_SLICE_SOURCE_GAPS_CLOSED=YES")
    print(f"FIBER_CONNECTIVITY_CAPACITY_STATUS={FIBER_STATUS}")
    print("IMPLEMENTATION_ADMITTED=NO")
    print("REAL_NINE_SOURCE_MATERIALIZATION=NO")
    print("FIRST_SERIOUS_CONSTRAINT_RUN=BLOCKED")
    print(f"REMAINING_BLOCKERS={RAW_MATERIALIZATION_BLOCKER};{ADMISSION_BLOCKER}")
    print(f"NEXT_REPO_EXECUTABLE_LANE={NEXT_REPO_LANE}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print("CONSTRAINT_FIRST_SLICE_INTEGRATION_VALIDATION=FAIL")
        print(f"ERROR={exc}")
        raise SystemExit(1)
