"""Concrete fail-closed authority-envelope validation."""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from .documents import canonical_json_bytes, parse_json_document
from .models import AuthorityResult, Issue, sorted_issues


AUTHORITY_SCHEMA = "hydra-t6-runtime-authority/v1"
OPERATION = "hydra.t6.failclosed_validate"
REQUIRED_SCOPE = "t6.validate_candidate_handoff"
DECISION = "AUTHORIZE_FAIL_CLOSED_VALIDATION"
MAX_REVOCATION_AGE = timedelta(hours=24)
HEX64 = set("0123456789abcdef")


class SignatureVerifier(Protocol):
    def verify(self, *, key_id: str, message: bytes, signature: str, method: str) -> bool: ...

    def allows_role(self, key_id: str, role: str) -> bool: ...


class HMACSHA256Verifier:
    """Verifies HMAC-SHA256 envelopes using explicit keys and key-role grants."""

    def __init__(self, trusted_keys: Mapping[str, bytes], trusted_key_roles: Mapping[str, Iterable[str]] | None = None) -> None:
        if not isinstance(trusted_keys, Mapping):
            raise ValueError("trusted keys must be a mapping")
        if trusted_key_roles is not None and not isinstance(trusted_key_roles, Mapping):
            raise ValueError("trusted key roles must be a mapping")
        self._keys: dict[str, bytes] = {}
        for key_id, value in trusted_keys.items():
            if type(key_id) is not str or not key_id or key_id != key_id.strip():
                raise ValueError("trusted key IDs must be non-empty exact strings")
            if not isinstance(value, (bytes, bytearray)) or not value:
                raise ValueError("trusted key values must be non-empty bytes")
            self._keys[key_id] = bytes(value)
        self._roles: dict[str, frozenset[str]] = {}
        role_mapping = trusted_key_roles if trusted_key_roles is not None else {}
        for key_id, roles in role_mapping.items():
            if type(key_id) is not str or not key_id or key_id != key_id.strip() or key_id not in self._keys:
                raise ValueError("trusted role-map key IDs must match an exact trusted key ID")
            if isinstance(roles, (str, bytes, bytearray, Mapping)) or not isinstance(roles, Iterable):
                raise ValueError("trusted key roles must be an iterable of exact strings")
            grants: set[str] = set()
            for role in roles:
                if type(role) is not str or not role or role != role.strip():
                    raise ValueError("trusted roles must be non-empty exact strings")
                grants.add(role)
            if not grants:
                raise ValueError("trusted key role grants must not be empty")
            self._roles[key_id] = frozenset(grants)

    def allows_role(self, key_id: str, role: str) -> bool:
        return type(key_id) is str and type(role) is str and role in self._roles.get(key_id, frozenset())

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


def _validate_authority_impl(
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

    schema_version = envelope.get("schema_version")
    if type(schema_version) is not str or schema_version != AUTHORITY_SCHEMA:
        issues.append(Issue("authority_schema_unsupported", "authority schema is unsupported", "$.authority.schema_version"))
    decision = envelope.get("decision")
    if type(decision) is not str or decision != DECISION:
        issues.append(Issue("authority_decision_mismatch", "authority decision does not permit fail-closed validation", "$.authority.decision"))
    operation = envelope.get("operation")
    if type(operation) is not str or operation != OPERATION:
        issues.append(Issue("authority_operation_mismatch", "authority operation does not match the validator operation", "$.authority.operation"))
    scopes = envelope.get("scopes")
    if type(scopes) is not list or len(scopes) != 1 or type(scopes[0]) is not str or scopes[0] != REQUIRED_SCOPE:
        issues.append(Issue("authority_scope_invalid", "authority scopes must be exactly the single validator scope", "$.authority.scopes"))
    for field in ("authority_id", "authority_name", "authority_role", "key_id"):
        if type(envelope.get(field)) is not str or not envelope[field].strip():
            issues.append(Issue("authority_identity_invalid", f"{field} must be a non-empty string", f"$.authority.{field}"))

    if envelope.get("authority_role") != "validator_authority":
        issues.append(Issue("authority_role_invalid", "authority_role must be validator_authority", "$.authority.authority_role"))

    method = envelope.get("signature_method")
    signature = envelope.get("signature")
    if type(method) is not str or not method:
        issues.append(Issue("authority_signature_method_invalid", "signature_method must be a non-empty string", "$.authority.signature_method"))
    if type(signature) is not str or not signature:
        issues.append(Issue("authority_signature_invalid", "signature must be a non-empty string", "$.authority.signature"))

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
            if type(actual) is not str or type(expected) is not str or actual != expected or not _is_hex64(actual):
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
        if type(status) is not str:
            issues.append(Issue("authority_revocation_ambiguous", "revocation status must be an exact string", "$.authority.revocation.status"))
        elif status == "revoked":
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
        if type(revocation.get("source_id")) is not str or not revocation.get("source_id"):
            issues.append(Issue("authority_revocation_source_invalid", "revocation source_id is required", "$.authority.revocation.source_id"))
        sequence = revocation.get("sequence")
        if type(sequence) is not int or sequence < 0:
            issues.append(Issue("authority_revocation_sequence_invalid", "revocation sequence must be a non-negative integer", "$.authority.revocation.sequence"))

    supersession = envelope.get("supersession")
    if not isinstance(supersession, Mapping):
        issues.append(Issue("authority_supersession_invalid", "supersession evidence must be an object", "$.authority.supersession"))
    else:
        sup_required = {"status", "predecessor_id", "successor_id", "chain"}
        if set(supersession) != sup_required:
            issues.append(Issue("authority_supersession_invalid", "supersession evidence has missing or unsupported fields", "$.authority.supersession"))
        chain = supersession.get("chain")
        if type(chain) is not list or any(type(item) is not str or not item for item in chain):
            issues.append(Issue("authority_supersession_chain_invalid", "supersession chain must be a list of non-empty identifiers", "$.authority.supersession.chain"))
        elif len(chain) != len(set(chain)) or envelope.get("authority_id") in chain:
            issues.append(Issue("authority_supersession_cycle", "supersession chain is cyclic or duplicated", "$.authority.supersession.chain"))
        status = supersession.get("status")
        if type(status) is not str or status != "current" or supersession.get("successor_id") is not None:
            issues.append(Issue("authority_superseded", "only an explicitly current authority may validate", "$.authority.supersession"))
        predecessor_id = supersession.get("predecessor_id")
        if predecessor_id is not None and (type(predecessor_id) is not str or not predecessor_id):
            issues.append(Issue("authority_predecessor_invalid", "predecessor_id must be null or a non-empty identifier", "$.authority.supersession.predecessor_id"))
        elif isinstance(chain, list):
            if predecessor_id is None and chain:
                issues.append(Issue("authority_supersession_chain_ambiguous", "a chain without predecessor_id is ambiguous", "$.authority.supersession.chain"))
            elif predecessor_id is not None and (not chain or chain[-1] != predecessor_id):
                issues.append(Issue("authority_supersession_chain_ambiguous", "supersession chain must end at predecessor_id", "$.authority.supersession.chain"))

    key_id_value = envelope.get("key_id")
    key_id = key_id_value if type(key_id_value) is str else ""
    role_value = envelope.get("authority_role")
    authority_role = role_value if type(role_value) is str else ""
    if verifier is None:
        issues.append(Issue("authority_verifier_missing", "no signature verifier is configured", "$.authority.signature"))
    else:
        try:
            allows_role = getattr(verifier, "allows_role", None)
            role_allowed = callable(allows_role) and allows_role(key_id, authority_role) is True
        except Exception:
            role_allowed = False
        if not role_allowed:
            issues.append(Issue("authority_key_role_untrusted", "the signing key is not trusted for the claimed authority role", "$.authority.authority_role"))
        else:
            try:
                verify = getattr(verifier, "verify", None)
                signature_valid = (
                    type(method) is str and bool(method)
                    and type(signature) is str and bool(signature)
                    and callable(verify)
                    and verify(key_id=key_id, message=authority_signing_bytes(envelope), signature=signature, method=method) is True
                )
            except Exception:
                issues.append(Issue("authority_verifier_error", "signature verifier failed closed", "$.authority.signature"))
            else:
                if not signature_valid:
                    issues.append(Issue("authority_signature_invalid", "authority signature is invalid or key is untrusted", "$.authority.signature"))

    return AuthorityResult(not issues, "VALID" if not issues else reason, sorted_issues(issues))


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
    try:
        if envelope is not None and not isinstance(envelope, Mapping):
            return AuthorityResult(
                False,
                "AUTHORITY_INVALID",
                (Issue("authority_input_invalid", "authority envelope must be a mapping", "$.authority"),),
            )
        if envelope is not None:
            document = parse_json_document(envelope, label="$.authority")
            if document.value is None or document.issues:
                return AuthorityResult(
                    False,
                    "AUTHORITY_INVALID",
                    (Issue("authority_input_invalid", "authority envelope could not be safely normalized", "$.authority"),),
                )
            envelope = document.value
        return _validate_authority_impl(
            envelope,
            verifier=verifier,
            now=now,
            input_sha256=input_sha256,
            policy_sha256=policy_sha256,
            output_schema_sha256=output_schema_sha256,
            oracle_sha256=oracle_sha256,
        )
    except Exception:
        return AuthorityResult(
            False,
            "AUTHORITY_INVALID",
            (Issue("authority_input_invalid", "authority envelope could not be safely inspected", "$.authority"),),
        )


def _parse_time(value: Any, path: str, issues: list[Issue]) -> datetime | None:
    if type(value) is not str:
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
    try:
        return parsed.astimezone(UTC)
    except (OverflowError, ValueError):
        issues.append(Issue("authority_time_invalid", "timestamp is outside the supported UTC range", path))
        return None


def _is_hex64(value: str) -> bool:
    return len(value) == 64 and set(value) <= HEX64
