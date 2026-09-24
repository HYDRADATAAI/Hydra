"""Dormant adapter shape for a future validation-only Thread F harness."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .service import FailClosedValidator


@dataclass(frozen=True)
class DormantAdapterResult:
    accepted: bool
    output: Mapping[str, Any] = field(default_factory=dict)
    error: str | None = None


class DormantThreadFAdapter:
    """Never self-registers; execution stays locked until a later shadow-proof gate."""

    def __init__(self, validator: FailClosedValidator) -> None:
        self._validator = validator

    def prepare(self, binding: Any) -> None:
        if getattr(binding, "readiness", None) != "dormant":
            raise PermissionError("T6 adapter requires readiness=dormant")

    def execute(self, binding: Any, payload: Mapping[str, Any]) -> DormantAdapterResult:
        del binding, payload
        return DormantAdapterResult(False, error="T6 shadow execution is not authorized by implementation authority")
