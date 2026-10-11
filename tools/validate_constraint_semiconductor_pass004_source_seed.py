"""Check Pass004 seed references and boundaries, not runtime admission."""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1"
PREFIX = "HYDRA_CONSTRAINT_SEMICONDUCTOR_PASS004_"
SLICE = "SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1"
FIELD_FILE = "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH017_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_FIELD_REQUIREMENTS_V001_20260926.json"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def timestamp(value):
    require(isinstance(value, str), "timestamp must be a string")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(result.tzinfo is not None and result.utcoffset() is not None, "timezone required")
    return result


def index(rows, field):
    require(isinstance(rows, list) and bool(rows), "non-empty row list required")
    result = {}
    for row in rows:
        require(isinstance(row, dict), "row object required")
        key = row.get(field)
        require(isinstance(key, str) and key.strip() == key and bool(key), "non-empty ID required")
        require(key not in result, "duplicate " + field)
        result[key] = row
    return result


def refs(value, allowed):
    require(isinstance(value, list) and bool(value), "non-empty reference list required")
    require(all(isinstance(v, str) and v in allowed for v in value), "unknown reference")
    require(len(value) == len(set(value)), "duplicate references")


def validate(registry, evidence, overlay, field_names):
    schemas = (
        "hydra-constraint-first-slice-source-registry-extension/v1",
        "hydra-constraint-first-slice-evidence-seed/v1",
        "hydra-constraint-first-slice-field-population-overlay/v1",
    )
    for document, schema in zip((registry, evidence, overlay), schemas):
        require(document.get("schema_version") == schema, "reused transport drift")
        require(document.get("slice_id") == SLICE, "slice drift")
    require(registry.get("source_content_persisted") is False, "raw capture falsely claimed")
    require(registry.get("runtime_live_source_authority_used") is False, "live authority falsely claimed")
    require(evidence.get("strict_original_as_of_ready") is False, "seed falsely replay-ready")
    require(overlay.get("runtime_admitted") is False, "runtime admission falsely claimed")
    require(overlay.get("strict_original_as_of_ready") is False, "overlay falsely replay-ready")
    require(overlay.get("required_cases_executed") == 0, "semantic case execution falsely claimed")

    sources = index(registry.get("sources"), "source_id")
    observations = index(evidence.get("observations"), "evidence_id")
    for source in sources.values():
        require(source.get("source_version_id") is None and source.get("artifact_sha256") is None,
                "unmaterialized source identity invented")
        for field in ("historical_backdating_authorized", "ordinary_raw_lineage_eligible", "strict_original_as_of_eligible"):
            require(source.get(field) is False, "source eligibility falsely promoted")
        require(timestamp(source["available_at"]) >= timestamp(source["acquired_at"]), "source backdated")
        require(timestamp(source["acquired_at"]).date().isoformat() == registry["as_of"], "review date drift")
        require(source.get("publication_date_precision") == "DAY", "publication precision drift")
        require(source.get("availability_basis") == "CONSERVATIVE_MANUAL_WEB_EXTRACT_REVIEW_COMPLETION_NOT_RAW_CAPTURE",
                "review time mislabeled as raw acquisition")

    for observation in observations.values():
        sid = observation.get("source_id")
        require(isinstance(sid, str) and sid in sources, "unknown source")
        require(observation.get("source_version_ids") is None, "source-version closure invented")
        require(observation.get("effective_from") is None and observation.get("effective_to") is None,
                "operational interval fabricated")
        require(observation.get("admissibility") == "REVIEWED_SEED_NOT_STRICT_REPLAY_READY", "observation promoted")
        require(observation.get("contradiction_state") == "UNASSESSED_IN_SEED", "conflict review invented")
        require(timestamp(observation["available_at"]) >= timestamp(sources[sid]["available_at"]), "observation backdated")
        require(timestamp(observation["observed_at"]) >= timestamp(sources[sid]["acquired_at"]), "observation review backdated")

    # This pass has no measured throughput, yield, resolved identities or raw
    # source versions. Refuse promotion of those unknowns within this receipt.
    unresolved = overlay.get("unresolved_fields")
    require(isinstance(unresolved, list) and all(isinstance(v, str) and v in field_names for v in unresolved),
            "invalid unresolved-field list")
    mandatory_unknowns = {"entity_id", "facility_id", "facility_owner_id", "geography_id", "product_id",
                         "supplier_id", "customer_id", "source_version_ids", "installed_capacity", "operational_capacity",
                         "available_capacity", "effective_capacity", "reserved_capacity", "booked_capacity",
                         "yield_value", "qualification_complete", "confidence_value"}
    require(mandatory_unknowns <= set(unresolved), "unknown boundary removed")
    updates = overlay.get("field_updates")
    require(isinstance(updates, list) and bool(updates), "field updates required")
    seen = set()
    for row in updates:
        require(isinstance(row, dict), "field update object required")
        field = row.get("field_name")
        require(isinstance(field, str) and field in field_names, "field outside Batch017")
        require(field not in mandatory_unknowns, "unknown field populated without evidence")
        refs(row.get("evidence_ids"), observations)
        require(isinstance(row.get("scope"), str) and bool(row["scope"]), "scope required")
        key = (row["scope"], field)
        require(key not in seen, "duplicate scoped field")
        seen.add(key)
        require(row.get("successor_status") == "POPULATED_REVIEWED_SEED_NOT_ADMITTED", "field falsely admitted")
        for eid in row["evidence_ids"]:
            require(timestamp(row["available_at"]) >= timestamp(observations[eid]["available_at"]), "field backdated")
    counts = overlay.get("counts")
    require(isinstance(counts, dict), "counts required")
    require(counts == {"registered_sources": len(sources), "reviewed_evidence_observations": len(observations),
                       "field_updates": len(updates), "canonical_entities_minted": 0, "canonical_facilities_minted": 0,
                       "canonical_constraints_formed": 0, "qualified_beneficiaries": 0}, "population count drift")
    return counts


def load_inputs():
    documents = [json.loads((BASE / (PREFIX + kind + "_20260926.json")).read_text())
                 for kind in ("SOURCE_REGISTRY", "EVIDENCE_SEED", "FIELD_POPULATION_OVERLAY")]
    fields = json.loads((BASE / FIELD_FILE).read_text())
    return (*documents, {row["field_name"] for row in fields["fields"]})


if __name__ == "__main__":
    try:
        counts = validate(*load_inputs())
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("SEMICONDUCTOR_PASS004_SEED=FAIL: " + str(exc))
        raise SystemExit(1)
    print("SEMICONDUCTOR_PASS004_SEED=PASS")
    print(json.dumps(counts, sort_keys=True))
    print("STRICT_REPLAY_AND_RUNTIME_ADMISSION=BLOCKED")
