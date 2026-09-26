"""Fail-closed admission gate for a native T5-to-T6 implementation binding."""

from __future__ import annotations

import hmac
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from .authority import SignatureVerifier
from .documents import canonical_json_bytes, parse_json_document
from .handoff import CANDIDATE_SCHEMA, HANDOFF_SCHEMA
from .models import Issue, sorted_issues


IMPLEMENTATION_MANIFEST_SCHEMA = "hydra-t5-t6-native-binding-implementation/v1"
ADMISSION_RECEIPT_SCHEMA = "hydra-t5-t6-native-binding-admission/v1"
ADMISSION_DECISION = "ADMIT_NATIVE_T5_T6_BINDING"
ADMISSION_OPERATION = "hydra.t5_t6.native_binding_admission"
ADMISSION_SCOPE = "pipeline.t5_to_t6.native_binding"
ADMISSION_AUTHORITY_ROLE = "IMPLEMENTATION_CONTRACT"
PRODUCER_STAGE = "PIPELINE_T5_CONSTRAINT_FORMATION"
CONSUMER_STAGE = "PIPELINE_T6_CANONICAL_CANDIDATE_GOVERNANCE"
MAX_REVOCATION_AGE = timedelta(hours=24)
HEX64 = set("0123456789abcdef")

_MANIFEST_KEYS = {
    "schema_version",
    "implementation_id",
    "implementation_version",
    "artifact_sha256",
    "test_evidence_sha256",
    "producer_stage",
    "consumer_stage",
    "handoff_schema",
    "candidate_schema",
    "semantic_authority_pins",
    "runtime_activation_requested",
    "canonical_promotion_requested",
    "live_source_requested",
}
_RECEIPT_KEYS = {
    "schema_version",
    "admission_id",
    "authority_role",
    "decision",
    "operation",
    "scopes",
    "implementation_id",
    "bindings",
    "producer_stage",
    "consumer_stage",
    "issued_at",
    "expires_at",
    "revocation",
    "supersession",
    "limitations",
    "key_id",
    "signature_method",
    "signature",
}
_LIMITATIONS = {
    "runtime_activation_authorized": False,
    "canonical_promotion_authorized": False,
    "live_source_authorized": False,
    "model_training_authorized": False,
    "trading_authorized": False,
}


@dataclass(frozen=True)
class NativeBindingAdmissionResult:
    admitted: bool
    reason: str
    implementation_id: str = ""
    manifest_sha256: str = ""
    receipt_sha256: str = ""
    issues: tuple[Issue, ...] = ()
    runtime_activation_authorized: bool = False
    canonical_promotion_authorized: bool = False
    live_source_authorized: bool = False
    model_training_authorized: bool = False
    trading_authorized: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "admitted": self.admitted,
            "canonical_promotion_authorized": self.canonical_promotion_authorized,
            "implementation_id": self.implementation_id,
            "issues": [issue.to_dict() for issue in self.issues],
            "live_source_authorized": self.live_source_authorized,
            "model_training_authorized": self.model_training_authorized,
            "manifest_sha256": self.manifest_sha256,
            "reason": self.reason,
            "receipt_sha256": self.receipt_sha256,
            "runtime_activation_authorized": self.runtime_activation_authorized,
            "trading_authorized": self.trading_authorized,
        }


def admission_signing_bytes(receipt: Mapping[str, Any]) -> bytes:
    unsigned = {key: value for key, value in receipt.items() if key != "signature"}
    return canonical_json_bytes(unsigned)


def sign_native_binding_admission(receipt: Mapping[str, Any], *, key: bytes) -> str:
    import hashlib

    return hmac.new(key, admission_signing_bytes(receipt), hashlib.sha256).hexdigest()


def validate_native_binding_admission(
    *,
    implementation_manifest: bytes | bytearray | str | Mapping[str, Any] | None,
    admission_receipt: bytes | bytearray | str | Mapping[str, Any] | None,
    verifier: SignatureVerifier | None,
    now: datetime,
) -> NativeBindingAdmissionResult:
    manifest_doc = parse_json_document(implementation_manifest, label="$.implementation_manifest")
    manifest_issues = list(manifest_doc.issues)
    manifest_issues.extend(_validate_manifest(manifest_doc.value))
    implementation_id = ""
    if manifest_doc.value is not None and isinstance(manifest_doc.value.get("implementation_id"), str):
        implementation_id = str(manifest_doc.value["implementation_id"])

    if manifest_issues:
        return NativeBindingAdmissionResult(
            admitted=False,
            reason="BLOCKED_IMPLEMENTATION_MANIFEST_INVALID",
            implementation_id=implementation_id,
            manifest_sha256=manifest_doc.raw_sha256,
            issues=sorted_issues(manifest_issues),
        )

    if admission_receipt is None:
        return NativeBindingAdmissionResult(
            admitted=False,
            reason="BLOCKED_AUTHORITY_RECEIPT_ABSENT",
            implementation_id=implementation_id,
            manifest_sha256=manifest_doc.raw_sha256,
            issues=(
                Issue(
                    "native_binding_admission_receipt_missing",
                    "an explicit signed implementation-admission receipt is required",
                    "$.admission_receipt",
                ),
            ),
        )

    receipt_doc = parse_json_document(admission_receipt, label="$.admission_receipt")
    receipt_issues = list(receipt_doc.issues)
    if receipt_doc.value is not None:
        receipt_issues.extend(
            _validate_receipt(
                receipt_doc.value,
                manifest=manifest_doc.value or {},
                manifest_sha256=manifest_doc.raw_sha256,
                verifier=verifier,
                now=now,
            )
        )

    if receipt_issues:
        return NativeBindingAdmissionResult(
            admitted=False,
            reason="BLOCKED_AUTHORITY_RECEIPT_INVALID",
            implementation_id=implementation_id,
            manifest_sha256=manifest_doc.raw_sha256,
            receipt_sha256=receipt_doc.raw_sha256,
            issues=sorted_issues(receipt_issues),
        )

    return NativeBindingAdmissionResult(
        admitted=True,
        reason="ADMITTED_EXACT_ARTIFACT",
        implementation_id=implementation_id,
        manifest_sha256=manifest_doc.raw_sha256,
        receipt_sha256=receipt_doc.raw_sha256,
    )


def _validate_manifest(value: Mapping[str, Any] | None) -> list[Issue]:
    issues: list[Issue] = []
    if value is None:
        return issues
    missing = sorted(_MANIFEST_KEYS - set(value))
    extra = sorted(set(value) - _MANIFEST_KEYS)
    for field in missing:
        issues.append(Issue("implementation_manifest_field_missing", f"required field {field!r} is missing", f"$.implementation_manifest.{field}"))
    for field in extra:
        issues.append(Issue("implementation_manifest_extra_field", f"unsupported field {field!r}", f"$.implementation_manifest.{field}"))
    if value.get("schema_version") != IMPLEMENTATION_MANIFEST_SCHEMA:
        issues.append(Issue("implementation_manifest_schema_unsupported", "implementation manifest schema is unsupported", "$.implementation_manifest.schema_version"))
    for field in ("implementation_id", "implementation_version"):
        if not isinstance(value.get(field), str) or not str(value[field]).strip():
            issues.append(Issue("implementation_manifest_identity_invalid", f"{field} must be a non-empty string", f"$.implementation_manifest.{field}"))
    for field in ("artifact_sha256", "test_evidence_sha256"):
        if not _is_hex64(value.get(field)):
            issues.append(Issue("implementation_manifest_digest_invalid", f"{field} must be a lowercase SHA-256 digest", f"$.implementation_manifest.{field}"))
    if value.get("producer_stage") != PRODUCER_STAGE:
        issues.append(Issue("implementation_manifest_producer_invalid", "producer_stage must be the frozen T5 stage", "$.implementation_manifest.producer_stage"))
    if value.get("consumer_stage") != CONSUMER_STAGE:
        issues.append(Issue("implementation_manifest_consumer_invalid", "consumer_stage must be the frozen T6 stage", "$.implementation_manifest.consumer_stage"))
    if value.get("handoff_schema") != HANDOFF_SCHEMA:
        issues.append(Issue("implementation_manifest_handoff_schema_invalid", "handoff_schema must match the admitted candidate handoff schema", "$.implementation_manifest.handoff_schema"))
    if value.get("candidate_schema") != CANDIDATE_SCHEMA:
        issues.append(Issue("implementation_manifest_candidate_schema_invalid", "candidate_schema must match the admitted candidate schema", "$.implementation_manifest.candidate_schema"))
    pins = value.get("semantic_authority_pins")
    if not isinstance(pins, Mapping) or set(pins) != {"thread1", "thread2", "thread3"}:
        issues.append(Issue("implementation_manifest_authority_pins_invalid", "semantic_authority_pins must contain exactly thread1/thread2/thread3", "$.implementation_manifest.semantic_authority_pins"))
    elif any(not isinstance(pin, str) or not pin.strip() for pin in pins.values()):
        issues.append(Issue("implementation_manifest_authority_pins_invalid", "all semantic authority pins must be non-empty strings", "$.implementation_manifest.semantic_authority_pins"))
    for field in ("runtime_activation_requested", "canonical_promotion_requested", "live_source_requested"):
        if value.get(field) is not False:
            issues.append(Issue("implementation_manifest_scope_escalation", f"{field} must be false for admission-only review", f"$.implementation_manifest.{field}"))
    return issues


def _validate_receipt(
    value: Mapping[str, Any],
    *,
    manifest: Mapping[str, Any],
    manifest_sha256: str,
    verifier: SignatureVerifier | None,
    now: datetime,
) -> list[Issue]:
    issues: list[Issue] = []
    missing = sorted(_RECEIPT_KEYS - set(value))
    extra = sorted(set(value) - _RECEIPT_KEYS)
    for field in missing:
        issues.append(Issue("admission_receipt_field_missing", f"required field {field!r} is missing", f"$.admission_receipt.{field}"))
    for field in extra:
        issues.append(Issue("admission_receipt_extra_field", f"unsupported field {field!r}", f"$.admission_receipt.{field}"))
    if issues:
        return issues

    if value.get("schema_version") != ADMISSION_RECEIPT_SCHEMA:
        issues.append(Issue("admission_receipt_schema_unsupported", "admission receipt schema is unsupported", "$.admission_receipt.schema_version"))
    admission_id = value.get("admission_id")
    if not isinstance(admission_id, str) or not admission_id.strip():
        issues.append(Issue("admission_receipt_identity_invalid", "admission_id must be a non-empty string", "$.admission_receipt.admission_id"))
    if value.get("authority_role") != ADMISSION_AUTHORITY_ROLE:
        issues.append(Issue("admission_receipt_role_invalid", "authority_role must be IMPLEMENTATION_CONTRACT", "$.admission_receipt.authority_role"))
    if value.get("decision") != ADMISSION_DECISION:
        issues.append(Issue("admission_receipt_decision_invalid", "decision does not admit the native T5-to-T6 binding", "$.admission_receipt.decision"))
    if value.get("operation") != ADMISSION_OPERATION:
        issues.append(Issue("admission_receipt_operation_invalid", "operation does not match the admission gate", "$.admission_receipt.operation"))
    if value.get("scopes") != [ADMISSION_SCOPE]:
        issues.append(Issue("admission_receipt_scope_invalid", "scopes must contain exactly the native T5-to-T6 admission scope", "$.admission_receipt.scopes"))
    if value.get("implementation_id") != manifest.get("implementation_id"):
        issues.append(Issue("admission_receipt_implementation_mismatch", "receipt implementation_id does not match the manifest", "$.admission_receipt.implementation_id"))
    if value.get("producer_stage") != PRODUCER_STAGE or value.get("consumer_stage") != CONSUMER_STAGE:
        issues.append(Issue("admission_receipt_stage_pair_invalid", "receipt must preserve the frozen T5-to-T6 stage pair", "$.admission_receipt"))

    bindings = value.get("bindings")
    expected_bindings = {
        "manifest_sha256": manifest_sha256,
        "artifact_sha256": manifest.get("artifact_sha256"),
        "test_evidence_sha256": manifest.get("test_evidence_sha256"),
    }
    if not isinstance(bindings, Mapping) or set(bindings) != set(expected_bindings):
        issues.append(Issue("admission_receipt_bindings_invalid", "bindings must contain exactly manifest/artifact/test-evidence digests", "$.admission_receipt.bindings"))
    else:
        for field, expected in expected_bindings.items():
            actual = bindings.get(field)
            if actual != expected or not _is_hex64(actual):
                issues.append(Issue("admission_receipt_binding_mismatch", f"{field} does not match the implementation manifest", f"$.admission_receipt.bindings.{field}", evidence={"actual": actual, "expected": expected}))

    limitations = value.get("limitations")
    if not isinstance(limitations, Mapping) or dict(limitations) != _LIMITATIONS:
        issues.append(Issue("admission_receipt_scope_escalation", "admission may not authorize runtime activation, canonical promotion, live sources, model training, or trading", "$.admission_receipt.limitations"))

    issued_at = _parse_time(value.get("issued_at"), "$.admission_receipt.issued_at", issues)
    expires_at = _parse_time(value.get("expires_at"), "$.admission_receipt.expires_at", issues)
    if now.tzinfo is None:
        issues.append(Issue("admission_now_naive", "explicit now must include timezone information", "$.now"))
    else:
        now = now.astimezone(UTC)
        if issued_at and expires_at:
            if issued_at >= expires_at:
                issues.append(Issue("admission_time_window_invalid", "issued_at must be before expires_at", "$.admission_receipt.expires_at"))
            elif now < issued_at:
                issues.append(Issue("admission_not_yet_valid", "admission receipt is not yet valid", "$.admission_receipt.issued_at"))
            elif now >= expires_at:
                issues.append(Issue("admission_expired", "admission receipt has expired", "$.admission_receipt.expires_at"))

    revocation = value.get("revocation")
    if not isinstance(revocation, Mapping) or set(revocation) != {"status", "checked_at", "source_id", "sequence"}:
        issues.append(Issue("admission_revocation_invalid", "revocation evidence is incomplete or unsupported", "$.admission_receipt.revocation"))
    else:
        if revocation.get("status") != "not_revoked":
            issues.append(Issue("admission_revoked_or_ambiguous", "admission must be explicitly not_revoked", "$.admission_receipt.revocation.status"))
        checked_at = _parse_time(revocation.get("checked_at"), "$.admission_receipt.revocation.checked_at", issues)
        if checked_at and issued_at and checked_at < issued_at:
            issues.append(Issue("admission_revocation_predates_issue", "revocation evidence predates the admission receipt", "$.admission_receipt.revocation.checked_at"))
        if checked_at and now.tzinfo is not None:
            if checked_at > now:
                issues.append(Issue("admission_revocation_future", "revocation check is in the future", "$.admission_receipt.revocation.checked_at"))
            elif now - checked_at > MAX_REVOCATION_AGE:
                issues.append(Issue("admission_revocation_stale", "revocation evidence is older than 24 hours", "$.admission_receipt.revocation.checked_at"))
        if not isinstance(revocation.get("source_id"), str) or not revocation.get("source_id"):
            issues.append(Issue("admission_revocation_source_invalid", "revocation source_id is required", "$.admission_receipt.revocation.source_id"))
        if not isinstance(revocation.get("sequence"), int) or isinstance(revocation.get("sequence"), bool) or revocation.get("sequence", -1) < 0:
            issues.append(Issue("admission_revocation_sequence_invalid", "revocation sequence must be a non-negative integer", "$.admission_receipt.revocation.sequence"))

    supersession = value.get("supersession")
    if not isinstance(supersession, Mapping) or set(supersession) != {"status", "predecessor_id", "successor_id", "chain"}:
        issues.append(Issue("admission_supersession_invalid", "supersession evidence is incomplete or unsupported", "$.admission_receipt.supersession"))
    else:
        chain = supersession.get("chain")
        if supersession.get("status") != "current" or supersession.get("successor_id") is not None:
            issues.append(Issue("admission_superseded", "only an explicitly current admission receipt may admit an implementation", "$.admission_receipt.supersession"))
        if not isinstance(chain, list) or any(not isinstance(item, str) or not item for item in chain) or len(chain) != len(set(chain)):
            issues.append(Issue("admission_supersession_chain_invalid", "supersession chain must be an acyclic list of identifiers", "$.admission_receipt.supersession.chain"))
        elif isinstance(admission_id, str) and admission_id in chain:
            issues.append(Issue("admission_supersession_cycle", "supersession chain may not contain the current admission_id", "$.admission_receipt.supersession.chain"))
        predecessor_id = supersession.get("predecessor_id")
        if predecessor_id is None and chain:
            issues.append(Issue("admission_supersession_chain_ambiguous", "a non-empty chain requires predecessor_id", "$.admission_receipt.supersession"))
        elif predecessor_id is not None and (not isinstance(predecessor_id, str) or not predecessor_id):
            issues.append(Issue("admission_predecessor_invalid", "predecessor_id must be null or a non-empty string", "$.admission_receipt.supersession.predecessor_id"))
        elif predecessor_id is not None and (not chain or chain[-1] != predecessor_id):
            issues.append(Issue("admission_supersession_chain_ambiguous", "supersession chain must end at predecessor_id", "$.admission_receipt.supersession.chain"))

    key_id = value.get("key_id")
    method = value.get("signature_method")
    signature = value.get("signature")
    if not isinstance(key_id, str) or not key_id:
        issues.append(Issue("admission_key_id_invalid", "key_id is required", "$.admission_receipt.key_id"))
    if not isinstance(method, str) or not method:
        issues.append(Issue("admission_signature_method_invalid", "signature_method is required", "$.admission_receipt.signature_method"))
    if not isinstance(signature, str) or not signature:
        issues.append(Issue("admission_signature_missing", "signature is required", "$.admission_receipt.signature"))
    elif verifier is None:
        issues.append(Issue("admission_verifier_missing", "no signature verifier is configured", "$.admission_receipt.signature"))
    elif not verifier.verify(
        key_id=str(key_id),
        message=admission_signing_bytes(value),
        signature=str(signature),
        method=str(method),
    ):
        issues.append(Issue("admission_signature_invalid", "admission signature is invalid or key is untrusted", "$.admission_receipt.signature"))
    return issues


def _parse_time(value: Any, path: str, issues: list[Issue]) -> datetime | None:
    if not isinstance(value, str):
        issues.append(Issue("admission_time_invalid", "timestamp must be an ISO-8601 string", path))
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        issues.append(Issue("admission_time_invalid", "timestamp is not valid ISO-8601", path))
        return None
    if parsed.tzinfo is None:
        issues.append(Issue("admission_time_invalid", "timestamp must include timezone information", path))
        return None
    return parsed.astimezone(UTC)


def _is_hex64(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= HEX64
