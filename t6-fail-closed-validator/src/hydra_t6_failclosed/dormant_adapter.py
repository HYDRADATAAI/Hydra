"""Dormant adapter for future validation-only integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .service import FailClosedValidator


@dataclass(frozen=True)
class DormantAdapterResult:
    """Result returned while runtime execution remains intentionally disabled."""

    accepted: bool
    output: Mapping[str, Any] = field(default_factory=dict)
    error: str | None = None


class DormantValidationAdapter:
    """Keeps the validator unregistered and refuses runtime execution."""

    def __init__(self, validator: FailClosedValidator) -> None:
        self._validator = validator

    def prepare(self, binding: Any) -> None:
        """Require an explicitly dormant binding before any integration step."""
        if getattr(binding, "readiness", None) != "dormant":
            raise PermissionError("validator adapter requires readiness=dormant")

    def execute(self, binding: Any, payload: Mapping[str, Any]) -> DormantAdapterResult:
        """Reject execution until a separate activation authority exists."""
        del binding, payload
        return DormantAdapterResult(
            False,
            error="shadow execution is not authorized by implementation authority",
        )
