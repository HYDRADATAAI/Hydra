from __future__ import annotations

from copy import deepcopy
from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any

from .multidomain import ConstraintMultiDomainQueryService
from .query import READ_ONLY_CAPABILITIES


OPERATING_CONTRACT_VERSION = "hydra-constraint-operating-report/v1"
OPERATING_MODE = "READ_ONLY_CONSTRAINT_OPERATING"
DEFAULT_OPERATING_MANIFEST_PATH = (
    "constraint-replay/operating/"
    "HYDRA_CONSTRAINT_BATCH018_OPERATING_MANIFEST_20260926.json"
)

STATUS_VALUES = {"FULL","THIN","EMPTY","MISSING","DUPLICATE_STALE"}

UNEVALUABLE_REASON_BY_CASE = {
    "us-chips-act-2022": "OPEN_EXPLICIT_HORIZON",
    "wto-china-rare-earths-resource-dispute-2014-2015":
        "CONTESTED_IMPLEMENTATION_COMPLIANCE",
    "japan-korea-export-control-relations-2019":
        "CONFLICTING_OFFICIAL_NORMALIZATION_CHARACTERIZATION",
    "eastern-mediterranean-offshore-drilling-dispute-2019-2020":
        "UNRESOLVED_LEGAL_TERRITORIAL_RESOURCE_DISPUTE",
    "eu-cbam-transitional-phase-2023":
        "INCOMPLETE_MODELED_ECONOMIC_OUTCOME_WINDOW",
}


class OperatingReportError(ValueError):
    pass


def _git_blob_sha(path: Path) -> str:
    payload=path.read_bytes()
    return sha1(f"blob {len(payload)}\0".encode()+payload).hexdigest()


def _stable_digest(value: Any) -> str:
    return sha256(
        json.dumps(value,sort_keys=True,separators=(",",":"),default=str).encode()
    ).hexdigest()


class ConstraintOperatingReportService:
    """Deterministic operating/readiness view over Batch 017 orchestration."""

    def __init__(
        self,
        repo_root: str | Path,
        *,
        manifest_path: str = DEFAULT_OPERATING_MANIFEST_PATH,
    ) -> None:
        self._root = Path(repo_root)
        self._manifest_relative = manifest_path
        self._manifest_path = self._root / manifest_path
        try:
            self._manifest = json.loads(
                self._manifest_path.read_text(encoding="utf-8")
            )
        except FileNotFoundError as exc:
            raise OperatingReportError(
                f"Batch 018 manifest missing: {self._manifest_path}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise OperatingReportError("Batch 018 manifest is invalid JSON") from exc
        if not isinstance(self._manifest, dict):
            raise OperatingReportError("Batch 018 manifest must be an object")

        self._multidomain = ConstraintMultiDomainQueryService(self._root)
        self._validate_manifest()
        self._snapshot = self._build_snapshot()

    def _validate_manifest(self) -> None:
        if self._manifest.get("schema_version") != "1.0":
            raise OperatingReportError("unsupported Batch 018 manifest schema")
        if self._manifest.get("contract_version") != OPERATING_CONTRACT_VERSION:
            raise OperatingReportError("unsupported Batch 018 contract version")
        if self._manifest.get("mode") != OPERATING_MODE:
            raise OperatingReportError("unsupported Batch 018 operating mode")
        if self._manifest.get("source_run_digest_sha256") != self._multidomain.summary()["source_run_digest_sha256"]:
            raise OperatingReportError("Batch 018 source replay digest mismatch")
        if self._manifest.get("read_only_capabilities") != READ_ONLY_CAPABILITIES:
            raise OperatingReportError("Batch 018 read-only capabilities mismatch")

        implementation=self._manifest.get("implementation")
        if not isinstance(implementation,dict):
            raise OperatingReportError("Batch 018 implementation pins are missing")
        for key in ("module","cli"):
            item=implementation.get(key)
            if not isinstance(item,dict):
                raise OperatingReportError(f"Batch 018 implementation pin missing: {key}")
            relative=item.get("path")
            expected=item.get("git_blob_sha")
            if not isinstance(relative,str) or not isinstance(expected,str):
                raise OperatingReportError(f"Batch 018 implementation pin incomplete: {key}")
            if _git_blob_sha(self._root/relative)!=expected:
                raise OperatingReportError(
                    f"Batch 018 implementation Git blob pin mismatch: {relative}"
                )

        authority=self._manifest.get("source_authority")
        if not isinstance(authority,dict):
            raise OperatingReportError("Batch 018 source authority pins are missing")
        for key in ("multidomain_manifest","legacy_evaluation_report"):
            item=authority.get(key)
            if not isinstance(item,dict):
                raise OperatingReportError(f"Batch 018 source authority missing: {key}")
            relative=item.get("path")
            expected=item.get("git_blob_sha")
            if not isinstance(relative,str) or not isinstance(expected,str):
                raise OperatingReportError(f"Batch 018 source authority incomplete: {key}")
            if _git_blob_sha(self._root/relative)!=expected:
                raise OperatingReportError(
                    f"Batch 018 source authority Git blob pin mismatch: {relative}"
                )
        if authority["legacy_evaluation_report"].get("classification")!="DUPLICATE_STALE":
            raise OperatingReportError("Batch 018 legacy report classification changed")

        t6=self._manifest.get("t6_boundary")
        if not isinstance(t6,dict):
            raise OperatingReportError("Batch 018 T6 boundary is missing")
        if t6.get("status")!="DORMANT_NOT_ACTIVATED":
            raise OperatingReportError("Batch 018 cannot activate T6")
        if t6.get("runtime_binding_created") is not False:
            raise OperatingReportError("Batch 018 cannot create a T6 runtime binding")
        if t6.get("activation_authority_granted") is not False:
            raise OperatingReportError("Batch 018 has no T6 activation authority")

    def _readiness(
        self,
        *,
        dimension: str,
        status: str,
        scope: str,
        evidence: dict[str, Any],
        blocker: str | None = None,
        intentional: bool = False,
    ) -> dict[str, Any]:
        if status not in STATUS_VALUES:
            raise OperatingReportError(f"unsupported readiness status: {status}")
        row = {
            "dimension": dimension,
            "status": status,
            "scope": scope,
            "evidence": evidence,
            "intentional": intentional,
        }
        if blocker is not None:
            row["blocker"] = blocker
        return row

    def _build_snapshot(self) -> dict[str, Any]:
        joined = self._multidomain.summary()["result"]
        replay = joined["replay"]
        policy = joined["policy"]
        physical = joined["physical"]
        join = joined["join_integrity"]

        try:
            from hydra_constraint_policy.model import EventType
        except ImportError as exc:
            raise OperatingReportError(
                "Batch 018 requires the stacked policy package"
            ) from exc

        taxonomy = sorted(event.value for event in EventType)
        sourced = sorted(policy["event_type_counts"])
        missing_types = sorted(set(taxonomy) - set(sourced))

        unevaluable = self._multidomain.list_cases(
            outcome_class="UNEVALUABLE"
        )["result"]["cases"]
        unevaluable_rows = []
        for row in unevaluable:
            case_id = row["case_id"]
            reason = UNEVALUABLE_REASON_BY_CASE.get(case_id)
            if reason is None:
                raise OperatingReportError(
                    f"missing UNEVALUABLE reason mapping for {case_id}"
                )
            unevaluable_rows.append({
                "case_id": case_id,
                "reason_code": reason,
            })
        unevaluable_rows.sort(key=lambda row: row["case_id"])

        dimensions = [
            self._readiness(
                dimension="historical_case_classification",
                status="FULL",
                scope="CURRENT_22_CASE_REPLAY_CORPUS",
                evidence={
                    "classified_cases": replay["coverage"]["case_count"],
                    "classification_coverage": replay["coverage"][
                        "classification_coverage"
                    ],
                    "partial_realization": replay["outcomes"]["class_counts"].get(
                        "PARTIAL_REALIZATION",0
                    ),
                    "unevaluable": replay["outcomes"]["class_counts"].get(
                        "UNEVALUABLE",0
                    ),
                },
            ),
            self._readiness(
                dimension="deterministic_historical_replay_execution",
                status="FULL",
                scope="BATCH015_FROZEN_RUN",
                evidence={
                    "replay_cut_count": replay["coverage"]["replay_cut_count"],
                    "integrity": replay["integrity"],
                },
            ),
            self._readiness(
                dimension="policy_physical_binding",
                status="FULL",
                scope="CURRENT_22_CASE_CORPUS",
                evidence={
                    "policy_event_count": policy["event_count"],
                    "physical_binding_count": physical["binding_count"],
                    "unique_bound_entity_count": physical[
                        "unique_bound_entity_count"
                    ],
                    "all_events_physically_bound": join[
                        "all_events_physically_bound"
                    ],
                },
            ),
            self._readiness(
                dimension="read_only_query_access",
                status="FULL",
                scope="BATCH016_REPLAY_AND_BATCH017_MULTIDOMAIN",
                evidence={
                    "replay_query": True,
                    "multidomain_query": True,
                    "read_only_capabilities": deepcopy(READ_ONLY_CAPABILITIES),
                },
            ),
            self._readiness(
                dimension="policy_event_taxonomy_sourced_coverage",
                status="THIN" if missing_types else "FULL",
                scope="CURRENT_HISTORICAL_POLICY_CORPUS",
                evidence={
                    "taxonomy_event_type_count": len(taxonomy),
                    "sourced_event_type_count": len(sourced),
                    "missing_event_types": missing_types,
                    "event_type_counts": deepcopy(policy["event_type_counts"]),
                },
                blocker=(
                    "NO_SOURCED_SUPPLY_AFFECTING_CONFLICT_CASE"
                    if missing_types == ["SUPPLY_AFFECTING_CONFLICT"]
                    else None
                ),
            ),
            self._readiness(
                dimension="probabilistic_calibration",
                status="EMPTY",
                scope="CURRENT_22_CASE_CORPUS",
                evidence=deepcopy(replay["calibration"]),
                blocker="NO_ADMISSIBLE_NUMERIC_HISTORICAL_CONFIDENCE",
            ),
            self._readiness(
                dimension="live_current_data_ingestion",
                status="MISSING",
                scope="PUBLIC_CONSTRAINT_RUNTIME",
                evidence={
                    "historical_source_pairs": physical["source_pair_count"],
                    "live_ingestion_proof_present": False,
                },
                blocker="NO_LIVE_CURRENT_INGESTION_PROOF_IN_PUBLIC_RUNTIME",
            ),
            self._readiness(
                dimension="canonical_mutation_runtime",
                status="MISSING",
                scope="PUBLIC_CONSTRAINT_RUNTIME",
                evidence={
                    "canonical_store_mutation_authorized": False,
                    "canonical_promotion_authorized": False,
                },
                blocker="NO_CANONICAL_MUTATION_AUTHORITY",
                intentional=True,
            ),
            self._readiness(
                dimension="t6_activation",
                status="MISSING",
                scope="PUBLIC_T6_RUNTIME",
                evidence={
                    "status": "DORMANT_NOT_ACTIVATED",
                    "runtime_binding_created": False,
                    "activation_authority_granted": False,
                },
                blocker="T6_ACTIVATION_NOT_AUTHORIZED",
                intentional=True,
            ),
            self._readiness(
                dimension="legacy_replay_evaluation_report",
                status="DUPLICATE_STALE",
                scope="constraint-replay/EVALUATION_REPORT.md",
                evidence={
                    "legacy_claim":
                        "real historical gold corpus not yet populated",
                    "current_classified_case_count": replay["coverage"]["case_count"],
                },
                blocker="LEGACY_REPORT_PREDATES_BATCH005_TO_BATCH017_STATE",
            ),
        ]

        expected=self._manifest.get("expected")
        if not isinstance(expected,dict):
            raise OperatingReportError("Batch 018 expected-state contract is missing")
        actual_expected={
            "case_count": replay["coverage"]["case_count"],
            "replay_cut_count": replay["coverage"]["replay_cut_count"],
            "policy_event_count": policy["event_count"],
            "policy_observation_count": policy["observation_count"],
            "physical_binding_count": physical["binding_count"],
            "unique_bound_entity_count": physical["unique_bound_entity_count"],
            "source_pair_count": physical["source_pair_count"],
            "partial_realization_count": replay["outcomes"]["class_counts"].get("PARTIAL_REALIZATION",0),
            "unevaluable_count": replay["outcomes"]["class_counts"].get("UNEVALUABLE",0),
            "calibrated_case_count": replay["coverage"]["calibrated_case_count"],
            "taxonomy_event_type_count": len(taxonomy),
            "sourced_event_type_count": len(sourced),
            "missing_event_types": missing_types,
        }
        for key,actual in actual_expected.items():
            if expected.get(key)!=actual:
                raise OperatingReportError(
                    f"Batch 018 expected {key}={expected.get(key)!r}, found {actual!r}"
                )

        readiness_counts={}
        for row in dimensions:
            readiness_counts[row["status"]]=readiness_counts.get(row["status"],0)+1
        if expected.get("readiness_status_counts")!=readiness_counts:
            raise OperatingReportError(
                "Batch 018 readiness status-count contract mismatch"
            )

        gaps = [
            row for row in dimensions
            if row["status"] in {"THIN","EMPTY","MISSING","DUPLICATE_STALE"}
        ]

        body = {
            "schema_version": "1.0",
            "contract_version": OPERATING_CONTRACT_VERSION,
            "mode": OPERATING_MODE,
            "operating_status": "PASS_WITH_EXPLICIT_BLOCKERS",
            "source_run_digest_sha256": self._multidomain.summary()[
                "source_run_digest_sha256"
            ],
            "current_state": {
                "case_count": replay["coverage"]["case_count"],
                "replay_cut_count": replay["coverage"]["replay_cut_count"],
                "policy_event_count": policy["event_count"],
                "policy_observation_count": policy["observation_count"],
                "physical_binding_count": physical["binding_count"],
                "unique_bound_entity_count": physical[
                    "unique_bound_entity_count"
                ],
                "partial_realization_count": replay["outcomes"][
                    "class_counts"
                ].get("PARTIAL_REALIZATION",0),
                "unevaluable_count": replay["outcomes"][
                    "class_counts"
                ].get("UNEVALUABLE",0),
                "calibrated_case_count": replay["coverage"][
                    "calibrated_case_count"
                ],
                "source_pair_count": physical["source_pair_count"],
            },
            "unevaluable_cases": unevaluable_rows,
            "readiness_dimensions": dimensions,
            "gaps": gaps,
            "authority_boundary": {
                "capabilities": deepcopy(READ_ONLY_CAPABILITIES),
                "t6_status": "DORMANT_NOT_ACTIVATED",
                "live_external_actions": False,
            },
        }
        return {**body,"snapshot_digest_sha256":_stable_digest(body)}

    def snapshot(self) -> dict[str, Any]:
        return deepcopy(self._snapshot)

    def readiness(self) -> dict[str, Any]:
        return {
            "contract_version": OPERATING_CONTRACT_VERSION,
            "mode": OPERATING_MODE,
            "source_run_digest_sha256": self._snapshot[
                "source_run_digest_sha256"
            ],
            "snapshot_digest_sha256": self._snapshot[
                "snapshot_digest_sha256"
            ],
            "capabilities": deepcopy(READ_ONLY_CAPABILITIES),
            "result": deepcopy(self._snapshot["readiness_dimensions"]),
        }

    def gaps(self) -> dict[str, Any]:
        return {
            "contract_version": OPERATING_CONTRACT_VERSION,
            "mode": OPERATING_MODE,
            "source_run_digest_sha256": self._snapshot[
                "source_run_digest_sha256"
            ],
            "snapshot_digest_sha256": self._snapshot[
                "snapshot_digest_sha256"
            ],
            "capabilities": deepcopy(READ_ONLY_CAPABILITIES),
            "result": deepcopy(self._snapshot["gaps"]),
        }

    def dimension(self, dimension: str) -> dict[str, Any]:
        if not isinstance(dimension,str) or not dimension:
            raise OperatingReportError("dimension must be a non-empty string")
        for row in self._snapshot["readiness_dimensions"]:
            if row["dimension"] == dimension:
                return {
                    "contract_version": OPERATING_CONTRACT_VERSION,
                    "mode": OPERATING_MODE,
                    "source_run_digest_sha256": self._snapshot[
                        "source_run_digest_sha256"
                    ],
                    "snapshot_digest_sha256": self._snapshot[
                        "snapshot_digest_sha256"
                    ],
                    "capabilities": deepcopy(READ_ONLY_CAPABILITIES),
                    "result": deepcopy(row),
                }
        raise OperatingReportError(f"unknown operating dimension: {dimension}")
