from __future__ import annotations

from copy import deepcopy
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping


QUERY_CONTRACT_VERSION = "hydra-constraint-readonly-query/v1"
QUERY_MODE = "READ_ONLY_HISTORICAL_REPLAY"
DEFAULT_RUN_PATH = (
    "constraint-replay/runs/"
    "HYDRA_CONSTRAINT_BATCH015_CLASSIFIED_REPLAY_E2E_RUN_20260926.json"
)
DEFAULT_MANIFEST_PATH = (
    "constraint-replay/runs/"
    "HYDRA_CONSTRAINT_BATCH015_CLASSIFIED_REPLAY_E2E_MANIFEST_20260926.json"
)

READ_ONLY_CAPABILITIES = {
    "canonical_promotion_authorized": False,
    "canonical_store_mutation_authorized": False,
    "external_actions_authorized": False,
    "model_training_authorized": False,
    "ranking_authorized": False,
    "trading_authorized": False,
}


class ConstraintQueryError(ValueError):
    pass


def _git_blob_sha(path: Path) -> str:
    payload = path.read_bytes()
    return sha1(f"blob {len(payload)}\0".encode() + payload).hexdigest()


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConstraintQueryError(f"{label} file is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConstraintQueryError(f"{label} file is not valid JSON: {path}") from exc
    if not isinstance(raw, dict):
        raise ConstraintQueryError(f"{label} must be a JSON object")
    return raw


class ConstraintReplayQueryService:
    """Read-only query surface over the frozen Batch 015 replay result.

    Construction validates the execution manifest and the exact Git-blob bytes
    it pins. The service performs no writes, registrations, rankings, canonical
    promotion, external effects, trading actions, or model-training actions.
    """

    def __init__(
        self,
        repo_root: str | Path,
        *,
        run_path: str = DEFAULT_RUN_PATH,
        manifest_path: str = DEFAULT_MANIFEST_PATH,
    ) -> None:
        self._root = Path(repo_root)
        self._run_relative = run_path
        self._manifest_relative = manifest_path
        self._run_path = self._root / run_path
        self._manifest_path = self._root / manifest_path

        self._run = _read_json(self._run_path, "Batch 015 run")
        self._manifest = _read_json(self._manifest_path, "Batch 015 manifest")
        self._integrity = self._validate_integrity()

        cases = self._run.get("cases")
        if not isinstance(cases, list) or not cases:
            raise ConstraintQueryError("Batch 015 run cases are missing")
        case_ids = [row.get("case_id") for row in cases if isinstance(row, dict)]
        if len(case_ids) != len(cases) or any(
            not isinstance(case_id, str) or not case_id for case_id in case_ids
        ):
            raise ConstraintQueryError("Batch 015 contains an invalid case identity")
        if len(case_ids) != len(set(case_ids)):
            raise ConstraintQueryError("Batch 015 contains duplicate case IDs")
        self._cases = tuple(deepcopy(cases))
        self._by_id = {row["case_id"]: row for row in self._cases}

    @property
    def run_digest(self) -> str:
        return str(self._run["run_digest_sha256"])

    def _validate_integrity(self) -> dict[str, Any]:
        run_digest = self._run.get("run_digest_sha256")
        manifest_digest = self._manifest.get("run_digest_sha256")
        if not isinstance(run_digest, str) or len(run_digest) != 64:
            raise ConstraintQueryError("Batch 015 run digest is invalid")
        if run_digest != manifest_digest:
            raise ConstraintQueryError("Batch 015 run/manifest digest mismatch")
        if self._run.get("run_status") != "PASS":
            raise ConstraintQueryError("Batch 015 run is not PASS")
        if self._run.get("run_kind") != "HYDRA_CONSTRAINT_CLASSIFIED_REPLAY_E2E":
            raise ConstraintQueryError("Batch 015 run kind is unsupported")

        output = self._manifest.get("output")
        if not isinstance(output, Mapping):
            raise ConstraintQueryError("Batch 015 manifest output pin is missing")
        if output.get("path") != self._run_relative:
            raise ConstraintQueryError("Batch 015 manifest output path mismatch")
        actual_output_sha = _git_blob_sha(self._run_path)
        if output.get("git_blob_sha") != actual_output_sha:
            raise ConstraintQueryError("Batch 015 run output Git blob pin mismatch")

        checked: list[dict[str, str]] = []
        for group_name in ("inputs", "ci_contracts"):
            group = self._manifest.get(group_name)
            if not isinstance(group, list) or not group:
                raise ConstraintQueryError(
                    f"Batch 015 manifest {group_name} pins are missing"
                )
            for item in group:
                if not isinstance(item, Mapping):
                    raise ConstraintQueryError(
                        f"Batch 015 manifest {group_name} entry is invalid"
                    )
                relative = item.get("path")
                expected = item.get("git_blob_sha")
                if not isinstance(relative, str) or not isinstance(expected, str):
                    raise ConstraintQueryError(
                        f"Batch 015 manifest {group_name} entry is incomplete"
                    )
                actual = _git_blob_sha(self._root / relative)
                if actual != expected:
                    raise ConstraintQueryError(
                        f"Batch 015 manifest pin mismatch for {relative}"
                    )
                checked.append({"path": relative, "git_blob_sha": actual})

        runner = self._manifest.get("runner")
        if not isinstance(runner, Mapping) or set(runner) != {"module", "cli"}:
            raise ConstraintQueryError("Batch 015 runner pins are invalid")
        for key in ("module", "cli"):
            item = runner[key]
            if not isinstance(item, Mapping):
                raise ConstraintQueryError(f"Batch 015 runner {key} pin is invalid")
            relative = item.get("path")
            expected = item.get("git_blob_sha")
            if not isinstance(relative, str) or not isinstance(expected, str):
                raise ConstraintQueryError(f"Batch 015 runner {key} pin is incomplete")
            actual = _git_blob_sha(self._root / relative)
            if actual != expected:
                raise ConstraintQueryError(
                    f"Batch 015 runner pin mismatch for {relative}"
                )
            checked.append({"path": relative, "git_blob_sha": actual})

        expected = self._manifest.get("expected")
        coverage = self._run.get("coverage")
        outcomes = self._run.get("outcomes")
        calibration = self._run.get("calibration")
        if not all(isinstance(value, Mapping) for value in (expected, coverage, outcomes, calibration)):
            raise ConstraintQueryError("Batch 015 aggregate sections are incomplete")
        aggregate_pairs = (
            ("case_count", coverage.get("case_count")),
            ("replay_cut_count", coverage.get("replay_cut_count")),
            ("classification_coverage", coverage.get("classification_coverage")),
            ("calibrated_case_count", coverage.get("calibrated_case_count")),
        )
        for key, actual in aggregate_pairs:
            if expected.get(key) != actual:
                raise ConstraintQueryError(
                    f"Batch 015 manifest expected {key} does not match run"
                )
        class_counts = outcomes.get("class_counts")
        if not isinstance(class_counts, Mapping):
            raise ConstraintQueryError("Batch 015 outcome class counts are missing")
        if expected.get("partial_realization_count") != class_counts.get(
            "PARTIAL_REALIZATION"
        ):
            raise ConstraintQueryError("Batch 015 partial-realization count mismatch")
        if expected.get("unevaluable_count") != class_counts.get("UNEVALUABLE"):
            raise ConstraintQueryError("Batch 015 unevaluable count mismatch")
        if expected.get("brier_score") != calibration.get("brier_score"):
            raise ConstraintQueryError("Batch 015 Brier-state mismatch")
        run_integrity = self._run.get("integrity")
        if not isinstance(run_integrity, Mapping):
            raise ConstraintQueryError("Batch 015 run integrity section is missing")
        required_green = {
            "replay_ready_case_set_equals_classified_case_set": True,
            "replay_ready_case_set_equals_promotion_case_set": True,
            "replay_source_bundle_pins_valid": True,
            "classified_artifact_pins_valid": True,
            "classification_blockers_remaining": 0,
            "calibrated_cases_present": 0,
        }
        for key, expected_value in required_green.items():
            if run_integrity.get(key) != expected_value:
                raise ConstraintQueryError(
                    f"Batch 015 integrity invariant failed: {key}"
                )
        if calibration.get("status") != "BLOCKED_NO_ADMISSIBLE_NUMERIC_CONFIDENCE":
            raise ConstraintQueryError("Batch 015 calibration state is unsupported")
        if calibration.get("calibrated_case_count") != 0:
            raise ConstraintQueryError("Batch 015 unexpectedly contains calibrated cases")

        return {
            "manifest_path": self._manifest_relative,
            "manifest_git_blob_sha": _git_blob_sha(self._manifest_path),
            "run_path": self._run_relative,
            "run_git_blob_sha": actual_output_sha,
            "run_digest_sha256": run_digest,
            "pinned_artifact_count": len(checked) + 1,
            "status": "PASS",
        }

    def _response(self, operation: str, result: Any) -> dict[str, Any]:
        return {
            "contract_version": QUERY_CONTRACT_VERSION,
            "mode": QUERY_MODE,
            "operation": operation,
            "source_run_digest_sha256": self.run_digest,
            "capabilities": dict(READ_ONLY_CAPABILITIES),
            "result": deepcopy(result),
        }

    def summary(self) -> dict[str, Any]:
        return self._response(
            "summary",
            {
                "coverage": self._run["coverage"],
                "outcomes": self._run["outcomes"],
                "lead_time_days": self._run["lead_time_days"],
                "calibration": self._run["calibration"],
                "integrity": self._run["integrity"],
            },
        )

    def integrity(self) -> dict[str, Any]:
        return self._response("integrity", self._integrity)

    def case(self, case_id: str) -> dict[str, Any]:
        if not isinstance(case_id, str) or not case_id:
            raise ConstraintQueryError("case_id must be a non-empty string")
        row = self._by_id.get(case_id)
        if row is None:
            raise ConstraintQueryError(f"unknown case_id: {case_id}")
        return self._response("case", row)

    def list_cases(
        self,
        *,
        outcome_class: str | None = None,
        calibrated: bool | None = None,
        min_lead_days: float | None = None,
        max_lead_days: float | None = None,
        calibration_blocker: str | None = None,
        sort_by: str = "case_id",
        limit: int | None = None,
    ) -> dict[str, Any]:
        if outcome_class is not None and outcome_class not in {
            "PARTIAL_REALIZATION",
            "UNEVALUABLE",
        }:
            raise ConstraintQueryError("unsupported outcome_class filter")
        if calibrated is not None and type(calibrated) is not bool:
            raise ConstraintQueryError("calibrated filter must be boolean")
        for label, value in (
            ("min_lead_days", min_lead_days),
            ("max_lead_days", max_lead_days),
        ):
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0
            ):
                raise ConstraintQueryError(f"{label} must be a non-negative number")
        if (
            min_lead_days is not None
            and max_lead_days is not None
            and min_lead_days > max_lead_days
        ):
            raise ConstraintQueryError("min_lead_days cannot exceed max_lead_days")
        if calibration_blocker is not None and (
            not isinstance(calibration_blocker, str) or not calibration_blocker
        ):
            raise ConstraintQueryError("calibration_blocker must be a non-empty string")
        if sort_by not in {"case_id", "lead_time_asc", "lead_time_desc"}:
            raise ConstraintQueryError("unsupported sort_by")
        if limit is not None and (
            isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100
        ):
            raise ConstraintQueryError("limit must be an integer in [1,100]")

        rows = list(self._cases)
        if outcome_class is not None:
            rows = [row for row in rows if row["outcome_class"] == outcome_class]
        if calibrated is not None:
            rows = [row for row in rows if row["calibrated"] is calibrated]
        if min_lead_days is not None:
            rows = [
                row
                for row in rows
                if row["evidence_availability_lead_days"] >= min_lead_days
            ]
        if max_lead_days is not None:
            rows = [
                row
                for row in rows
                if row["evidence_availability_lead_days"] <= max_lead_days
            ]
        if calibration_blocker is not None:
            rows = [
                row
                for row in rows
                if calibration_blocker in row["calibration_blockers"]
            ]

        if sort_by == "case_id":
            rows.sort(key=lambda row: row["case_id"])
        elif sort_by == "lead_time_asc":
            rows.sort(
                key=lambda row: (
                    row["evidence_availability_lead_days"],
                    row["case_id"],
                )
            )
        else:
            rows.sort(
                key=lambda row: (
                    -row["evidence_availability_lead_days"],
                    row["case_id"],
                )
            )

        total = len(rows)
        if limit is not None:
            rows = rows[:limit]

        return self._response(
            "list_cases",
            {
                "matched_count": total,
                "returned_count": len(rows),
                "cases": rows,
            },
        )

    def query(self, request: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(request, Mapping):
            raise ConstraintQueryError("query request must be an object")
        operation = request.get("operation")
        if operation == "summary":
            self._require_keys(request, {"operation"})
            return self.summary()
        if operation == "integrity":
            self._require_keys(request, {"operation"})
            return self.integrity()
        if operation == "case":
            self._require_keys(request, {"operation", "case_id"})
            return self.case(request.get("case_id"))
        if operation == "list_cases":
            allowed = {
                "operation",
                "outcome_class",
                "calibrated",
                "min_lead_days",
                "max_lead_days",
                "calibration_blocker",
                "sort_by",
                "limit",
            }
            self._require_subset(request, allowed)
            return self.list_cases(
                outcome_class=request.get("outcome_class"),
                calibrated=request.get("calibrated"),
                min_lead_days=request.get("min_lead_days"),
                max_lead_days=request.get("max_lead_days"),
                calibration_blocker=request.get("calibration_blocker"),
                sort_by=request.get("sort_by", "case_id"),
                limit=request.get("limit"),
            )
        raise ConstraintQueryError("unsupported or missing query operation")

    @staticmethod
    def _require_keys(request: Mapping[str, Any], expected: set[str]) -> None:
        actual = set(request)
        if actual != expected:
            raise ConstraintQueryError(
                f"query fields must be exactly {sorted(expected)}"
            )

    @staticmethod
    def _require_subset(request: Mapping[str, Any], allowed: set[str]) -> None:
        extra = set(request) - allowed
        if extra:
            raise ConstraintQueryError(
                f"unsupported query fields: {sorted(extra)}"
            )
