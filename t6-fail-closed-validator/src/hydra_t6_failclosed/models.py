"""Shared immutable result types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class Issue:
    code: str
    message: str
    path: str = "$"
    candidate_id: str = ""
    evidence: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "code": self.code,
            "evidence": dict(self.evidence),
            "message": self.message,
            "path": self.path,
        }


@dataclass(frozen=True)
class AuthorityResult:
    valid: bool
    reason: str
    issues: tuple[Issue, ...] = ()


def sorted_issues(issues: list[Issue] | tuple[Issue, ...]) -> tuple[Issue, ...]:
    return tuple(sorted(issues, key=lambda item: (item.code, item.candidate_id, item.path, item.message)))
