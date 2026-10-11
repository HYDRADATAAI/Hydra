"""Strictly typed additive V2 of the native T5-to-T6 bridge.

V2 preserves V1 mapping for valid inputs and rejects non-boolean eligibility
values before V1's truthiness coercion can change their meaning.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .native_t5_t6_bridge import (
    NativeT5T6BridgeError,
    build_native_t5_t6_handoff,
)


def build_native_t5_t6_handoff_v2(
    proposals: Mapping[str, Any],
    temporal_overlay: Mapping[str, Any],
    *,
    handoff_id: str,
    created_at: str,
) -> dict[str, Any]:
    """Build a V1-compatible handoff after enforcing exact eligibility booleans."""
    _require_boolean_eligibility(proposals, "proposals")
    _require_boolean_eligibility(temporal_overlay, "temporal_overlay")
    return build_native_t5_t6_handoff(
        proposals,
        temporal_overlay,
        handoff_id=handoff_id,
        created_at=created_at,
    )


def _require_boolean_eligibility(document: Mapping[str, Any], label: str) -> None:
    candidates = document.get("candidates")
    if not isinstance(candidates, list):
        return  # Let the V1 validator report the existing structural error.
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, Mapping) or "ordinary_t6_eligible" not in candidate:
            continue  # Let the V1 validator report the existing structural error.
        if not isinstance(candidate["ordinary_t6_eligible"], bool):
            raise NativeT5T6BridgeError(
                f"{label}.candidates[{index}].ordinary_t6_eligible must be a boolean"
            )