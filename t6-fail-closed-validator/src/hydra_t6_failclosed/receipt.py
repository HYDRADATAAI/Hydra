"""Deterministic inert receipt construction and schema validation."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from .documents import canonical_json_bytes, sha256_hex
from .models import Issue, sorted_issues


RECEIPT_SCHEMA_ID = "hydra-t6-failclosed-decision-receipt/v2-draft"
RECEIPT_VERSION = "hydra-t6-failclosed-decision-receipt/v2"
ALLOWED_OUTCOMES = {"ABSTAIN", "QUARANTINE"}
ALLOWED_REASONS = {
    "NO_CANONICAL_PROMOTION_AUTHORITY", "NO_RANKING_AUTHORITY", "VALIDATION_OR_CONFLICT_FAILURE",
    "POLICY_EXPIRED", "POLICY_REVOKED", "AUTHORITY_INVALID",
}


class ReceiptSchemaError(ValueError):
    pass


def build_receipt(
    *,
    implementation_status: str,
    policy_sha256: str,
    authority_envelope_sha256: str,
    input_sha256: str,
    outcome: str,
    reason: str,
    candidate_ids: tuple[str, ...] | list[str],
    issues: tuple[Issue, ...] | list[Issue],
    schema: Mapping[str, Any],
) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "authority_envelope_sha256": authority_envelope_sha256,
        "candidate_ids": sorted(set(candidate_ids)),
        "canonical_store_mutation_authorized": False,
        "canonical_truth_selected": False,
        "external_actions": [],
        "gamma_unfrozen": False,
        "implementation_status": implementation_status,
        "input_sha256": input_sha256,
        "ml_training_authorized": False,
        "outcome": outcome,
        "policy_sha256": policy_sha256,
        "ranked_candidate_ids": [],
        "reason": reason,
        "schema_version": RECEIPT_VERSION,
        "trading_authorized": False,
        "violations": [issue.to_dict() for issue in sorted_issues(issues)],
    }
    if outcome not in ALLOWED_OUTCOMES or reason not in ALLOWED_REASONS:
        raise ReceiptSchemaError("receipt outcome or reason is outside the fail-closed contract")
    receipt["receipt_sha256"] = receipt_digest(receipt)
    validate_instance(receipt, schema)
    if receipt["receipt_sha256"] != receipt_digest(receipt):
        raise ReceiptSchemaError("receipt digest does not recompute")
    return receipt


def receipt_digest(receipt: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    return sha256_hex(canonical_json_bytes(payload))


def validate_receipt_schema_contract(schema: Mapping[str, Any]) -> None:
    if schema.get("$id") != RECEIPT_SCHEMA_ID or schema.get("type") != "object" or schema.get("additionalProperties") is not False:
        raise ReceiptSchemaError("receipt schema identity is not the bound v2 draft")
    properties = schema.get("properties")
    if not isinstance(properties, Mapping):
        raise ReceiptSchemaError("receipt schema properties are missing")
    required_const_false = {
        "canonical_store_mutation_authorized", "canonical_truth_selected", "gamma_unfrozen",
        "ml_training_authorized", "trading_authorized",
    }
    for field in required_const_false:
        rule = properties.get(field)
        if not isinstance(rule, Mapping) or rule.get("const") is not False:
            raise ReceiptSchemaError(f"receipt schema does not force {field} false")
    for field in ("external_actions", "ranked_candidate_ids"):
        rule = properties.get(field)
        if not isinstance(rule, Mapping) or rule.get("maxItems") != 0:
            raise ReceiptSchemaError(f"receipt schema does not force {field} empty")
    if set(properties.get("outcome", {}).get("enum", ())) != ALLOWED_OUTCOMES:
        raise ReceiptSchemaError("receipt schema outcome enum is unsafe")
    if set(properties.get("reason", {}).get("enum", ())) != ALLOWED_REASONS:
        raise ReceiptSchemaError("receipt schema reason enum is unsafe")


def validate_instance(instance: Any, schema: Mapping[str, Any], *, path: str = "$") -> None:
    errors: list[str] = []
    _validate(instance, schema, path, errors)
    if errors:
        raise ReceiptSchemaError("; ".join(errors))


def _validate(value: Any, schema: Mapping[str, Any], path: str, errors: list[str]) -> None:
    expected_type = schema.get("type")
    if expected_type and not _matches_type(value, str(expected_type)):
        errors.append(f"{path} must be {expected_type}")
        return
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path} must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path} is not in the allowed enum")
    if isinstance(value, str) and "pattern" in schema and re.fullmatch(str(schema["pattern"]), value) is None:
        errors.append(f"{path} does not match the required pattern")
    if isinstance(value, list):
        if "maxItems" in schema and len(value) > int(schema["maxItems"]):
            errors.append(f"{path} exceeds maxItems")
        if schema.get("uniqueItems") and len({canonical_json_bytes(item) for item in value}) != len(value):
            errors.append(f"{path} must contain unique items")
        item_schema = schema.get("items")
        if isinstance(item_schema, Mapping):
            for index, item in enumerate(value):
                _validate(item, item_schema, f"{path}[{index}]", errors)
    if isinstance(value, Mapping):
        required = schema.get("required", ())
        for key in required:
            if key not in value:
                errors.append(f"{path}.{key} is required")
        properties = schema.get("properties", {})
        if isinstance(properties, Mapping):
            if schema.get("additionalProperties") is False:
                for key in value:
                    if key not in properties:
                        errors.append(f"{path}.{key} is not allowed")
            for key, nested_schema in properties.items():
                if key in value and isinstance(nested_schema, Mapping):
                    _validate(value[key], nested_schema, f"{path}.{key}", errors)


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, Mapping)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "null":
        return value is None
    return False
