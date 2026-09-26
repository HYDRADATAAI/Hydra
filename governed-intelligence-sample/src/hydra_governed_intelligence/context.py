"""Integrity-checked evidence loading and policy-bound context decisions."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


POLICY_SCHEMA = "hydra-governed-intelligence-policy/v1"
DECISION_SCHEMA = "hydra-governed-intelligence-decision/v1"
PIPELINE_MANIFEST_SCHEMA = "hydra-market-pipeline-manifest/v1"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
TASK_PATTERN = re.compile(r"^[a-z0-9_]{1,64}$")
EVENT_FIELDS = {
    "currency",
    "event_id",
    "event_time_utc",
    "price",
    "raw_record_sha256",
    "source_file_sha256",
    "source_record_id",
    "source_row_number",
    "source_system",
    "symbol",
    "transform_version",
    "venue",
    "volume",
}


class ContractError(ValueError):
    """Raised when a request, policy, or document violates its contract."""


class IntegrityError(ValueError):
    """Raised when an artifact no longer matches its pinned digest or counts."""


@dataclass(frozen=True)
class Policy:
    allowed_tasks: tuple[str, ...]
    abstained_tasks: tuple[str, ...]
    refused_tasks: tuple[str, ...]
    max_context_records: int
    sha256: str


@dataclass(frozen=True)
class Evidence:
    directory: Path
    manifest: Mapping[str, Any]
    manifest_sha256: str
    accepted_events: tuple[Mapping[str, Any], ...]
    normalized_sha256: str
    quarantine_sha256: str


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_json_document(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_nonfinite,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ContractError) as exc:
        raise ContractError(f"invalid JSON document {path}: {exc}") from exc


def load_policy(path: str | Path) -> Policy:
    policy_path = Path(path)
    document = load_json_document(policy_path)
    if not isinstance(document, dict):
        raise ContractError("policy root must be an object")

    expected_fields = {
        "schema_version",
        "allowed_tasks",
        "abstained_tasks",
        "refused_tasks",
        "max_context_records",
        "model_execution_enabled",
    }
    if set(document) != expected_fields:
        raise ContractError("policy fields do not match the v1 contract")
    if document["schema_version"] != POLICY_SCHEMA:
        raise ContractError("unsupported policy schema")
    if document["model_execution_enabled"] is not False:
        raise ContractError("this sample prohibits model execution")
    if not isinstance(document["max_context_records"], int) or isinstance(
        document["max_context_records"], bool
    ):
        raise ContractError("max_context_records must be an integer")
    if not 1 <= document["max_context_records"] <= 20:
        raise ContractError("max_context_records must be between 1 and 20")

    task_groups = {}
    for field in ("allowed_tasks", "abstained_tasks", "refused_tasks"):
        values = document[field]
        if not isinstance(values, list) or not values:
            raise ContractError(f"{field} must be a non-empty list")
        if any(not isinstance(value, str) or not TASK_PATTERN.fullmatch(value) for value in values):
            raise ContractError(f"{field} contains an invalid task name")
        if values != sorted(set(values)):
            raise ContractError(f"{field} must be sorted and unique")
        task_groups[field] = tuple(values)

    combined = [value for values in task_groups.values() for value in values]
    if len(combined) != len(set(combined)):
        raise ContractError("policy task groups must be disjoint")
    if set(task_groups["allowed_tasks"]) != {
        "accepted_observation_summary",
        "quality_status",
    }:
        raise ContractError("v1 allowed task set changed")

    return Policy(
        allowed_tasks=task_groups["allowed_tasks"],
        abstained_tasks=task_groups["abstained_tasks"],
        refused_tasks=task_groups["refused_tasks"],
        max_context_records=document["max_context_records"],
        sha256=sha256_hex(policy_path.read_bytes()),
    )


def load_evidence(directory: str | Path) -> Evidence:
    root = Path(directory).resolve()
    manifest_path = root / "manifest.json"
    manifest = load_json_document(manifest_path)
    if not isinstance(manifest, dict):
        raise ContractError("pipeline manifest root must be an object")
    if manifest.get("schema_version") != PIPELINE_MANIFEST_SCHEMA:
        raise ContractError("unsupported pipeline manifest schema")

    outputs = manifest.get("outputs")
    if not isinstance(outputs, dict) or set(outputs) != {
        "normalized_events_csv",
        "normalized_events_jsonl",
        "quarantine_records_jsonl",
    }:
        raise ContractError("pipeline manifest output set changed")

    resolved_outputs: dict[str, Path] = {}
    for key, descriptor in outputs.items():
        if not isinstance(descriptor, dict):
            raise ContractError(f"manifest output {key} must be an object")
        filename = descriptor.get("file")
        digest = descriptor.get("sha256")
        if not isinstance(filename, str) or Path(filename).name != filename:
            raise ContractError(f"manifest output {key} has an unsafe file name")
        if not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest):
            raise ContractError(f"manifest output {key} has an invalid digest")
        path = (root / filename).resolve()
        if path.parent != root:
            raise ContractError(f"manifest output {key} escapes the artifact directory")
        try:
            actual_digest = sha256_hex(path.read_bytes())
        except OSError as exc:
            raise IntegrityError(f"unable to read manifest output {key}: {exc}") from exc
        if actual_digest != digest:
            raise IntegrityError(f"manifest digest mismatch for {filename}")
        resolved_outputs[key] = path

    accepted = _load_jsonl(resolved_outputs["normalized_events_jsonl"])
    quarantined = _load_jsonl(resolved_outputs["quarantine_records_jsonl"])
    if manifest.get("accepted_rows") != len(accepted):
        raise IntegrityError("accepted row count does not match the manifest")
    if manifest.get("quarantined_rows") != len(quarantined):
        raise IntegrityError("quarantined row count does not match the manifest")

    source_digest = manifest.get("source_file_sha256")
    if not isinstance(source_digest, str) or not SHA256_PATTERN.fullmatch(source_digest):
        raise ContractError("pipeline source digest is invalid")

    seen_ids: set[str] = set()
    for event in accepted:
        if set(event) != EVENT_FIELDS:
            raise ContractError("normalized event fields do not match the v1 contract")
        event_id = event.get("event_id")
        if not isinstance(event_id, str) or not SHA256_PATTERN.fullmatch(event_id):
            raise ContractError("normalized event_id is invalid")
        if event_id in seen_ids:
            raise IntegrityError("normalized event_id is duplicated")
        seen_ids.add(event_id)
        if event.get("source_file_sha256") != source_digest:
            raise IntegrityError("event source digest does not match the manifest")
        if not isinstance(event.get("symbol"), str) or not event["symbol"]:
            raise ContractError("normalized event symbol is invalid")

    return Evidence(
        directory=root,
        manifest=manifest,
        manifest_sha256=sha256_hex(manifest_path.read_bytes()),
        accepted_events=tuple(sorted(accepted, key=lambda record: record["event_id"])),
        normalized_sha256=outputs["normalized_events_jsonl"]["sha256"],
        quarantine_sha256=outputs["quarantine_records_jsonl"]["sha256"],
    )


def build_decision(
    request: Mapping[str, Any], *, evidence: Evidence, policy: Policy
) -> dict[str, Any]:
    _validate_request(request)
    task_type = request["task_type"]

    if task_type in policy.refused_tasks:
        return _decision(request, evidence, policy, "REFUSE", "action_not_authorized")
    if task_type in policy.abstained_tasks:
        return _decision(
            request,
            evidence,
            policy,
            "ABSTAIN",
            "production_evidence_unavailable",
        )
    if task_type not in policy.allowed_tasks:
        return _decision(request, evidence, policy, "ABSTAIN", "unsupported_task")

    if task_type == "quality_status":
        context = {
            "accepted_rows": evidence.manifest["accepted_rows"],
            "context_type": "quality_status",
            "pipeline_run_id": evidence.manifest["pipeline_run_id"],
            "quarantine_detail_included": False,
            "quarantined_rows": evidence.manifest["quarantined_rows"],
            "source_file_sha256": evidence.manifest["source_file_sha256"],
            "transform_version": evidence.manifest["transform_version"],
        }
        citation = {
            "artifact": "manifest.json",
            "artifact_sha256": evidence.manifest_sha256,
            "record_id": evidence.manifest["pipeline_run_id"],
        }
        return _decision(
            request,
            evidence,
            policy,
            "ADMIT",
            "governed_quality_summary_available",
            context=context,
            citations=[citation],
        )

    subject = request["subject"]
    if subject is None:
        return _decision(request, evidence, policy, "ABSTAIN", "subject_required")
    normalized_subject = subject.upper()
    matches = [
        dict(event)
        for event in evidence.accepted_events
        if event["symbol"] == normalized_subject
    ]
    if not matches:
        return _decision(request, evidence, policy, "ABSTAIN", "no_governed_evidence")

    selected = matches[: policy.max_context_records]
    citations = [
        {
            "artifact": "normalized_events.jsonl",
            "artifact_sha256": evidence.normalized_sha256,
            "record_id": event["event_id"],
            "record_sha256": sha256_hex(canonical_json_bytes(event)),
        }
        for event in selected
    ]
    context = {
        "context_type": "accepted_observation_summary",
        "records": selected,
        "requested_subject": subject,
        "resolved_subject": normalized_subject,
        "total_matching_records": len(matches),
        "truncated": len(matches) > len(selected),
    }
    return _decision(
        request,
        evidence,
        policy,
        "ADMIT",
        "governed_context_available",
        context=context,
        citations=citations,
    )


def verify_decision(
    decision: Mapping[str, Any], *, evidence: Evidence, policy: Policy
) -> None:
    if decision.get("schema_version") != DECISION_SCHEMA:
        raise IntegrityError("decision schema is invalid")
    if decision.get("policy_sha256") != policy.sha256:
        raise IntegrityError("decision policy binding is invalid")
    binding = decision.get("input_binding")
    if binding != {
        "pipeline_manifest_sha256": evidence.manifest_sha256,
        "pipeline_run_id": evidence.manifest["pipeline_run_id"],
    }:
        raise IntegrityError("decision input binding is invalid")
    if decision.get("model_execution") != {
        "authorized": False,
        "status": "NOT_EXECUTED",
    }:
        raise IntegrityError("decision must keep model execution disabled")
    if _contains_exact_key(decision, "raw_record"):
        raise IntegrityError("decision exposes a quarantined raw record")

    disposition = decision.get("disposition")
    context = decision.get("context")
    citations = decision.get("citations")
    if disposition not in {"ADMIT", "ABSTAIN", "REFUSE"}:
        raise IntegrityError("decision disposition is invalid")
    if not isinstance(citations, list):
        raise IntegrityError("decision citations must be a list")
    if disposition != "ADMIT":
        if context is not None or citations:
            raise IntegrityError("non-admitted decisions cannot carry context or citations")
        return
    if not isinstance(context, dict) or not citations:
        raise IntegrityError("admitted decisions require context and citations")

    events_by_id = {event["event_id"]: event for event in evidence.accepted_events}
    for citation in citations:
        if not isinstance(citation, dict):
            raise IntegrityError("citation must be an object")
        artifact = citation.get("artifact")
        if artifact == "manifest.json":
            if citation != {
                "artifact": "manifest.json",
                "artifact_sha256": evidence.manifest_sha256,
                "record_id": evidence.manifest["pipeline_run_id"],
            }:
                raise IntegrityError("manifest citation is invalid")
        elif artifact == "normalized_events.jsonl":
            event = events_by_id.get(citation.get("record_id"))
            if event is None:
                raise IntegrityError("citation record does not resolve")
            expected = {
                "artifact": "normalized_events.jsonl",
                "artifact_sha256": evidence.normalized_sha256,
                "record_id": event["event_id"],
                "record_sha256": sha256_hex(canonical_json_bytes(event)),
            }
            if citation != expected:
                raise IntegrityError("normalized-event citation is invalid")
        else:
            raise IntegrityError("citation references a non-admitted artifact")

    context_type = context.get("context_type")
    if context_type == "accepted_observation_summary":
        subject = decision.get("subject")
        if not isinstance(subject, str):
            raise IntegrityError("accepted observation context requires a subject")
        resolved_subject = subject.upper()
        matches = [
            dict(event)
            for event in evidence.accepted_events
            if event["symbol"] == resolved_subject
        ]
        selected = matches[: policy.max_context_records]
        expected_context = {
            "context_type": "accepted_observation_summary",
            "records": selected,
            "requested_subject": subject,
            "resolved_subject": resolved_subject,
            "total_matching_records": len(matches),
            "truncated": len(matches) > len(selected),
        }
        if context != expected_context:
            raise IntegrityError("accepted observation context is invalid")
        if [record["event_id"] for record in selected] != [
            citation["record_id"] for citation in citations
        ]:
            raise IntegrityError("context record order does not match citations")
    elif context_type == "quality_status":
        expected_context = {
            "accepted_rows": evidence.manifest["accepted_rows"],
            "context_type": "quality_status",
            "pipeline_run_id": evidence.manifest["pipeline_run_id"],
            "quarantine_detail_included": False,
            "quarantined_rows": evidence.manifest["quarantined_rows"],
            "source_file_sha256": evidence.manifest["source_file_sha256"],
            "transform_version": evidence.manifest["transform_version"],
        }
        if context != expected_context:
            raise IntegrityError("quality context is invalid")
        if len(citations) != 1 or citations[0]["artifact"] != "manifest.json":
            raise IntegrityError("quality context must cite only the manifest")
    else:
        raise IntegrityError("admitted context type is invalid")


def _decision(
    request: Mapping[str, Any],
    evidence: Evidence,
    policy: Policy,
    disposition: str,
    reason_code: str,
    *,
    context: Mapping[str, Any] | None = None,
    citations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "citations": citations or [],
        "context": dict(context) if context is not None else None,
        "disposition": disposition,
        "input_binding": {
            "pipeline_manifest_sha256": evidence.manifest_sha256,
            "pipeline_run_id": evidence.manifest["pipeline_run_id"],
        },
        "model_execution": {"authorized": False, "status": "NOT_EXECUTED"},
        "policy_sha256": policy.sha256,
        "reason_codes": [reason_code],
        "request_id": request["request_id"],
        "schema_version": DECISION_SCHEMA,
        "subject": request["subject"],
        "task_type": request["task_type"],
    }


def _validate_request(request: Mapping[str, Any]) -> None:
    if not isinstance(request, Mapping):
        raise ContractError("request must be an object")
    if set(request) != {"request_id", "task_type", "subject"}:
        raise ContractError("request fields do not match the v1 contract")
    if not isinstance(request["request_id"], str) or not REQUEST_ID_PATTERN.fullmatch(
        request["request_id"]
    ):
        raise ContractError("request_id is invalid")
    if not isinstance(request["task_type"], str) or not TASK_PATTERN.fullmatch(
        request["task_type"]
    ):
        raise ContractError("task_type is invalid")
    subject = request["subject"]
    if subject is not None and (
        not isinstance(subject, str) or not subject.strip() or len(subject) > 64
    ):
        raise ContractError("subject must be null or a non-empty string up to 64 characters")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise ContractError(f"unable to read JSONL artifact {path}: {exc}") from exc
    for line_number, line in enumerate(lines, start=1):
        if not line:
            raise ContractError(f"blank JSONL line in {path} at {line_number}")
        try:
            record = json.loads(
                line,
                object_pairs_hook=_unique_object,
                parse_constant=_reject_nonfinite,
            )
        except (json.JSONDecodeError, ContractError) as exc:
            raise ContractError(
                f"invalid JSONL record in {path} at {line_number}: {exc}"
            ) from exc
        if not isinstance(record, dict):
            raise ContractError(f"JSONL root must be an object in {path} at {line_number}")
        records.append(record)
    return records


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ContractError(f"non-finite JSON value: {value}")


def _contains_exact_key(value: Any, key: str) -> bool:
    if isinstance(value, Mapping):
        return key in value or any(_contains_exact_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_exact_key(item, key) for item in value)
    return False
