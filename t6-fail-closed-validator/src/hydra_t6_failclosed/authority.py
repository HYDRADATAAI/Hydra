"""Concrete fail-closed authority-envelope validation."""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from .documents import canonical_json_bytes
from .models import AuthorityResult, Issue, sorted_issues


AUTHORITY_SCHEMA = "hydra-t6-runtime-authority/v1"
OPERATION = "hydra.t6.failclosed_validate"
REQUIRED_SCOPE = "t6.validate_candidate_handoff"
DECISION = "AUTHORIZE_FAIL_CLOSED_VALIDATION"
MAX_REVOCATION_AGE = timedelta(hours=24)
HEX64 = set("0123456789abcdef")


class SignatureVerifier(Protocol):
    def verify(self, *, key_id: str, message: bytes, signature: str, method: str) -> bool: ...


class HMACSHA256Verifier:
    """Verifies HMAC-SHA256 envelopes against explicitly injected trusted keys."""

    def __init__(self, trusted_keys: Mapping[str, bytes]) -> None:
        self._keys = {str(key): bytes(value) for key, value in trusted_keys.items()}

    def verify(self, *, key_id: str, message: bytes, signature: str, method: str) -> bool:
        if method != "HMAC-SHA256" or key_id not in self._keys or not _is_hex64(signature):
            return False
        expected = hmac.new(self._keys[key_id], message, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)


def sign_hmac_sha256(envelope: Mapping[str, Any], *, key: bytes) -> str:
    return hmac.new(key, authority_signing_bytes(envelope), hashlib.sha256).hexdigest()


def authority_signing_bytes(envelope: Mapping[str, Any]) -> bytes:
    unsigned = {key: value for key, value in envelope.items() if key != "signature"}
    return canonical_json_bytes(unsigned)


def validate_authority(
    envelope: Mapping[str, Any] | None,
    *,
    verifier: SignatureVerifier | None,
    now: datetime,
    input_sha256: str,
    policy_sha256: str,
    output_schema_sha256: str,
    oracle_sha256: str,
) -> AuthorityResult:
    issues: list[Issue] = []
    if not isinstance(now, datetime):
        return AuthorityResult(False, "AUTHORITY_INVALID", (Issue("authority_now_invalid", "explicit now must be a datetime", "$.now"),))
    if now.tzinfo is None:
        return AuthorityResult(False, "AUTHORITY_INVALID", (Issue("authority_now_naive", "explicit now must include a timezone", "$.now"),))
    try:
        if now.utcoffset() is None:
            return AuthorityResult(False, "AUTHORITY_INVALID", (Issue("authority_now_naive", "explicit now must include a timezone", "$.now"),))
        now = now.astimezone(UTC)
    except Exception:
        return AuthorityResult(False, "AUTHORITY_INVALID", (Issue("authority_now_invalid", "explicit now has invalid timezone information", "$.now"),))
    if envelope is None:
        return AuthorityResult(False, "AUTHORITY_INVALID", (Issue("authority_missing", "authority envelope is absent", "$.authority"),))

    required = {
        "schema_version", "authority_id", "authority_name", "authority_role", "decision",
        "operation", "scopes", "issued_at", "expires_at", "bindings", "revocation",
        "supersession", "key_id", "signature_method", "signature",
    }
    allowed = required
    missing = sorted(required - set(envelope))
    extra = sorted(set(envelope) - allowed)
    for field in missing:
        issues.append(Issue("authority_field_missing", f"authority field {field!r} is required", f"$.authority.{field}"))
    for field in extra:
        issues.append(Issue("authority_extra_claim", f"authority claim {field!r} is unsupported", f"$.authority.{field}"))
    if issues:
        return AuthorityResult(False, "AUTHORITY_INVALID", sorted_issues(issues))

    if envelope.get("schema_version") != AUTHORITY_SCHEMA:
        issues.append(Issue("authority_schema_unsupported", "authority schema is unsupported", "$.authority.schema_version"))
    if envelope.get("decision") != DECISION:
        issues.append(Issue("authority_decision_mismatch", "authority decision does not permit fail-closed validation", "$.authority.decision"))
    if envelope.get("operation") != OPERATION:
        issues.append(Issue("authority_operation_mismatch", "authority operation does not match the validator operation", "$.authority.operation"))
    scopes = envelope.get("scopes")
    if not isinstance(scopes, list) or scopes != [REQUIRED_SCOPE]:
        issues.append(Issue("authority_scope_invalid", "authority scopes must be exactly the single validator scope", "$.authority.scopes"))
    for field in ("authority_id", "authority_name", "authority_role", "key_id"):
        if not isinstance(envelope.get(field), str) or not str(envelope[field]).strip():
            issues.append(Issue("authority_identity_invalid", f"{field} must be a non-empty string", f"$.authority.{field}"))

    bindings = envelope.get("bindings")
    expected_bindings = {
        "input_sha256": input_sha256,
        "oracle_sha256": oracle_sha256,
        "output_schema_sha256": output_schema_sha256,
        "policy_sha256": policy_sha256,
    }
    if not isinstance(bindings, Mapping) or set(bindings) != set(expected_bindings):
        issues.append(Issue("authority_bindings_invalid", "authority bindings must contain exactly the four required digests", "$.authority.bindings"))
    else:
        for key, expected in expected_bindings.items():
            actual = bindings.get(key)
            if actual != expected or not _is_hex64(str(actual)):
                issues.append(Issue("authority_binding_mismatch", f"authority binding {key} does not match", f"$.authority.bindings.{key}", evidence={"actual": actual, "expected": expected}))

    issued_at = _parse_time(envelope.get("issued_at"), "$.authority.issued_at", issues)
    expires_at = _parse_time(envelope.get("expires_at"), "$.authority.expires_at", issues)
    reason = "AUTHORITY_INVALID"
    if issued_at and expires_at:
        if issued_at >= expires_at:
            issues.append(Issue("authority_time_window_invalid", "issued_at must be before expires_at", "$.authority.expires_at"))
        elif now < issued_at:
            issues.append(Issue("authority_not_yet_valid", "authority was issued in the future", "$.authority.issued_at"))
        elif now >= expires_at:
            issues.append(Issue("authority_expired", "authority has expired", "$.authority.expires_at"))
            reason = "POLICY_EXPIRED"

    revocation = envelope.get("revocation")
    if not isinstance(revocation, Mapping):
        issues.append(Issue("authority_revocation_invalid", "revocation evidence must be an object", "$.authority.revocation"))
    else:
        rev_required = {"status", "checked_at", "source_id", "sequence"}
        if set(revocation) != rev_required:
            issues.append(Issue("authority_revocation_invalid", "revocation evidence has missing or unsupported fields", "$.authority.revocation"))
        status = revocation.get("status")
        if status == "revoked":
            issues.append(Issue("authority_revoked", "authority is revoked", "$.authority.revocation.status"))
            reason = "POLICY_REVOKED"
        elif status != "not_revoked":
            issues.append(Issue("authority_revocation_ambiguous", "revocation status must be not_revoked", "$.authority.revocation.status"))
        checked_at = _parse_time(revocation.get("checked_at"), "$.authority.revocation.checked_at", issues)
        if checked_at:
            if checked_at > now:
                issues.append(Issue("authority_revocation_future", "revocation check is in the future", "$.authority.revocation.checked_at"))
            elif now - checked_at > MAX_REVOCATION_AGE:
                issues.append(Issue("authority_revocation_stale", "revocation evidence is older than 24 hours", "$.authority.revocation.checked_at"))
            if issued_at and checked_at < issued_at:
                issues.append(Issue("authority_revocation_predates_issue", "revocation evidence predates the authority", "$.authority.revocation.checked_at"))
        if not isinstance(revocation.get("source_id"), str) or not revocation.get("source_id"):
            issues.append(Issue("authority_revocation_source_invalid", "revocation source_id is required", "$.authority.revocation.source_id"))
        if not isinstance(revocation.get("sequence"), int) or isinstance(revocation.get("sequence"), bool) or revocation.get("sequence", 0) < 0:
            issues.append(Issue("authority_revocation_sequence_invalid", "revocation sequence must be a non-negative integer", "$.authority.revocation.sequence"))

    supersession = envelope.get("supersession")
    if not isinstance(supersession, Mapping):
        issues.append(Issue("authority_supersession_invalid", "supersession evidence must be an object", "$.authority.supersession"))
    else:
        sup_required = {"status", "predecessor_id", "successor_id", "chain"}
        if set(supersession) != sup_required:
            issues.append(Issue("authority_supersession_invalid", "supersession evidence has missing or unsupported fields", "$.authority.supersession"))
        chain = supersession.get("chain")
        if not isinstance(chain, list) or any(not isinstance(item, str) or not item for item in chain):
            issues.append(Issue("authority_supersession_chain_invalid", "supersession chain must be a list of non-empty identifiers", "$.authority.supersession.chain"))
        elif len(chain) != len(set(chain)) or envelope.get("authority_id") in chain:
            issues.append(Issue("authority_supersession_cycle", "supersession chain is cyclic or duplicated", "$.authority.supersession.chain"))
        if supersession.get("status") != "current" or supersession.get("successor_id") is not None:
            issues.append(Issue("authority_superseded", "only an explicitly current authority may validate", "$.authority.supersession"))
        predecessor_id = supersession.get("predecessor_id")
        if predecessor_id is not None and (not isinstance(predecessor_id, str) or not predecessor_id):
            issues.append(Issue("authority_predecessor_invalid", "predecessor_id must be null or a non-empty identifier", "$.authority.supersession.predecessor_id"))
        elif isinstance(chain, list):
            if predecessor_id is None and chain:
                issues.append(Issue("authority_supersession_chain_ambiguous", "a chain without predecessor_id is ambiguous", "$.authority.supersession.chain"))
            elif predecessor_id is not None and (not chain or chain[-1] != predecessor_id):
                issues.append(Issue("authority_supersession_chain_ambiguous", "supersession chain must end at predecessor_id", "$.authority.supersession.chain"))

    method = str(envelope.get("signature_method", ""))
    key_id = str(envelope.get("key_id", ""))
    signature = str(envelope.get("signature", ""))
    if verifier is None:
        issues.append(Issue("authority_verifier_missing", "no signature verifier is configured", "$.authority.signature"))
    else:
        try:
            verified = verifier.verify(
                key_id=key_id,
                message=authority_signing_bytes(envelope),
                signature=signature,
                method=method,
            )
        except Exception:
            issues.append(Issue("authority_verifier_error", "signature verifier failed closed", "$.authority.signature"))
        else:
            if verified is not True:
                issues.append(Issue("authority_signature_invalid", "authority signature is invalid or key is untrusted", "$.authority.signature"))

    return AuthorityResult(not issues, "VALID" if not issues else reason, sorted_issues(issues))


def _parse_time(value: Any, path: str, issues: list[Issue]) -> datetime | None:
    if not isinstance(value, str):
        issues.append(Issue("authority_time_invalid", "timestamp must be an ISO-8601 string", path))
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        issues.append(Issue("authority_time_invalid", "timestamp is not valid ISO-8601", path))
        return None
    if parsed.tzinfo is None:
        issues.append(Issue("authority_time_invalid", "timestamp must include timezone information", path))
        return None
    return parsed.astimezone(UTC)


def _is_hex64(value: str) -> bool:
    return len(value) == 64 and set(value) <= HEX64
