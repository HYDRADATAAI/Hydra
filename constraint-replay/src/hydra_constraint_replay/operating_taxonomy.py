from __future__ import annotations

from copy import deepcopy
from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any

from .operating import ConstraintOperatingReportService, OperatingReportError
from .query import ConstraintReplayQueryService, READ_ONLY_CAPABILITIES


OPERATING_V2_CONTRACT_VERSION = "hydra-constraint-operating-report/v2"
OPERATING_V2_MODE = "READ_ONLY_CONSTRAINT_OPERATING_V2"
DEFAULT_OPERATING_V2_MANIFEST_PATH = (
    "constraint-replay/operating/"
    "HYDRA_CONSTRAINT_BATCH019_OPERATING_MANIFEST_20260926.json"
)


class OperatingTaxonomyClosureError(ValueError):
    pass


def _git_blob_sha(path: Path) -> str:
    payload=path.read_bytes()
    return sha1(f"blob {len(payload)}\0".encode()+payload).hexdigest()


def _stable_digest(value: Any) -> str:
    return sha256(
        json.dumps(value,sort_keys=True,separators=(",",":"),default=str).encode()
    ).hexdigest()


class ConstraintOperatingReportV2Service:
    """Batch 019 successor operating view with taxonomy supplement coverage.

    The frozen 22-case replay authority remains unchanged. A separately pinned
    policy/physical supplement is admitted only for policy EventType breadth.
    """

    def __init__(
        self,
        repo_root: str | Path,
        *,
        manifest_path: str = DEFAULT_OPERATING_V2_MANIFEST_PATH,
    ) -> None:
        self._root=Path(repo_root)
        self._manifest_relative=manifest_path
        self._manifest_path=self._root/manifest_path
        try:
            self._manifest=json.loads(
                self._manifest_path.read_text(encoding="utf-8")
            )
        except FileNotFoundError as exc:
            raise OperatingTaxonomyClosureError(
                f"Batch 019 manifest missing: {self._manifest_path}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise OperatingTaxonomyClosureError(
                "Batch 019 manifest is invalid JSON"
            ) from exc
        if not isinstance(self._manifest,dict):
            raise OperatingTaxonomyClosureError(
                "Batch 019 manifest must be an object"
            )

        self._base=ConstraintOperatingReportService(self._root)
        self._replay=ConstraintReplayQueryService(self._root)
        self._validate_manifest()
        self._supplement=self._load_and_validate_supplement()
        self._snapshot=self._build_snapshot()
        self._validate_committed_snapshot()

    def _validate_manifest(self) -> None:
        if self._manifest.get("schema_version")!="1.0":
            raise OperatingTaxonomyClosureError(
                "unsupported Batch 019 manifest schema"
            )
        if self._manifest.get("contract_version")!=OPERATING_V2_CONTRACT_VERSION:
            raise OperatingTaxonomyClosureError(
                "unsupported Batch 019 contract version"
            )
        if self._manifest.get("mode")!=OPERATING_V2_MODE:
            raise OperatingTaxonomyClosureError(
                "unsupported Batch 019 operating mode"
            )
        if self._manifest.get("source_run_digest_sha256")!=self._replay.run_digest:
            raise OperatingTaxonomyClosureError(
                "Batch 019 source replay digest mismatch"
            )
        if self._manifest.get("read_only_capabilities")!=READ_ONLY_CAPABILITIES:
            raise OperatingTaxonomyClosureError(
                "Batch 019 read-only capabilities mismatch"
            )

        for group_name in ("implementation","source_authority"):
            group=self._manifest.get(group_name)
            if not isinstance(group,dict) or not group:
                raise OperatingTaxonomyClosureError(
                    f"Batch 019 {group_name} pins are missing"
                )
            for key,item in group.items():
                if not isinstance(item,dict):
                    raise OperatingTaxonomyClosureError(
                        f"Batch 019 {group_name} pin invalid: {key}"
                    )
                relative=item.get("path")
                expected=item.get("git_blob_sha")
                if not isinstance(relative,str) or not isinstance(expected,str):
                    raise OperatingTaxonomyClosureError(
                        f"Batch 019 {group_name} pin incomplete: {key}"
                    )
                if _git_blob_sha(self._root/relative)!=expected:
                    raise OperatingTaxonomyClosureError(
                        f"Batch 019 {group_name} Git blob pin mismatch: {relative}"
                    )

        t6=self._manifest.get("t6_boundary")
        if not isinstance(t6,dict):
            raise OperatingTaxonomyClosureError(
                "Batch 019 T6 boundary missing"
            )
        if t6.get("status")!="DORMANT_NOT_ACTIVATED":
            raise OperatingTaxonomyClosureError(
                "Batch 019 cannot activate T6"
            )
        if t6.get("runtime_binding_created") is not False:
            raise OperatingTaxonomyClosureError(
                "Batch 019 cannot create a T6 runtime binding"
            )
        if t6.get("activation_authority_granted") is not False:
            raise OperatingTaxonomyClosureError(
                "Batch 019 has no T6 activation authority"
            )

    def _load_and_validate_supplement(self) -> dict[str,Any]:
        try:
            from hydra_constraint_physical import load_sourced_policy_case_graph
            from hydra_constraint_policy.case_studies import (
                events_from_sourced_case_bundle,
                load_sourced_case_bundle,
            )
            from hydra_constraint_policy.model import EventType
            from hydra_constraint_policy.physical_adapter import (
                bind_event_to_physical_graph,
            )
        except ImportError as exc:
            raise OperatingTaxonomyClosureError(
                "Batch 019 requires stacked physical, policy, and replay packages"
            ) from exc

        supplement=self._manifest.get("taxonomy_supplement")
        if not isinstance(supplement,dict):
            raise OperatingTaxonomyClosureError(
                "Batch 019 taxonomy supplement pins are missing"
            )
        policy= supplement.get("policy")
        physical=supplement.get("physical")
        if not isinstance(policy,dict) or not isinstance(physical,dict):
            raise OperatingTaxonomyClosureError(
                "Batch 019 supplement policy/physical pins are invalid"
            )
        for label,item in (("policy",policy),("physical",physical)):
            relative=item.get("path")
            expected=item.get("git_blob_sha")
            if not isinstance(relative,str) or not isinstance(expected,str):
                raise OperatingTaxonomyClosureError(
                    f"Batch 019 supplement {label} pin incomplete"
                )
            if _git_blob_sha(self._root/relative)!=expected:
                raise OperatingTaxonomyClosureError(
                    f"Batch 019 supplement {label} Git blob pin mismatch"
                )

        bundle=load_sourced_case_bundle(self._root/policy["path"])
        graph=load_sourced_policy_case_graph(self._root/physical["path"])
        events=events_from_sourced_case_bundle(bundle)

        if len(bundle["cases"])!=1 or len(events)!=1:
            raise OperatingTaxonomyClosureError(
                "Batch 019 taxonomy supplement must contain exactly one case/event"
            )
        case=bundle["cases"][0]
        event=events[0]
        if event.event_type is not EventType.SUPPLY_AFFECTING_CONFLICT:
            raise OperatingTaxonomyClosureError(
                "Batch 019 supplement does not close SUPPLY_AFFECTING_CONFLICT"
            )
        observations=case.get("observations",[])
        if len(observations)!=1:
            raise OperatingTaxonomyClosureError(
                "Batch 019 taxonomy supplement must contain one observation"
            )

        replay_ids={
            row["case_id"]
            for row in self._replay.list_cases()["result"]["cases"]
        }
        if case["case_id"] in replay_ids:
            raise OperatingTaxonomyClosureError(
                "Batch 019 supplement must not mutate frozen replay case membership"
            )

        bindings=bind_event_to_physical_graph(event,graph)
        if len(bindings)!=3:
            raise OperatingTaxonomyClosureError(
                f"Batch 019 expected 3 physical bindings, found {len(bindings)}"
            )

        expected=self._manifest.get("expected")
        if not isinstance(expected,dict):
            raise OperatingTaxonomyClosureError(
                "Batch 019 expected-state contract missing"
            )
        actual={
            "supplement_case_count":1,
            "supplement_event_count":1,
            "supplement_observation_count":1,
            "supplement_physical_binding_count":len(bindings),
        }
        for key,value in actual.items():
            if expected.get(key)!=value:
                raise OperatingTaxonomyClosureError(
                    f"Batch 019 expected {key}={expected.get(key)!r}, found {value!r}"
                )

        return {
            "case_id":case["case_id"],
            "event_id":event.event_id,
            "event_type":event.event_type.value,
            "observation_id":observations[0]["observation_id"],
            "physical_binding_count":len(bindings),
            "physical_entity_ids":sorted(binding.entity_id for binding in bindings),
            "replay_case_admitted":False,
        }

    def _build_snapshot(self) -> dict[str,Any]:
        snapshot=deepcopy(self._base.snapshot())
        snapshot["contract_version"]=OPERATING_V2_CONTRACT_VERSION
        snapshot["mode"]=OPERATING_V2_MODE

        dimensions=snapshot["readiness_dimensions"]
        taxonomy_row=next(
            row for row in dimensions
            if row["dimension"]=="policy_event_taxonomy_sourced_coverage"
        )
        event_counts=deepcopy(taxonomy_row["evidence"]["event_type_counts"])
        if "SUPPLY_AFFECTING_CONFLICT" in event_counts:
            raise OperatingTaxonomyClosureError(
                "Batch 019 supplement would duplicate already sourced conflict coverage"
            )
        event_counts["SUPPLY_AFFECTING_CONFLICT"]=1
        taxonomy_row["status"]="FULL"
        taxonomy_row["scope"]=(
            "CURRENT_HISTORICAL_POLICY_CORPUS_PLUS_BATCH019_TAXONOMY_SUPPLEMENT"
        )
        taxonomy_row["evidence"]={
            "taxonomy_event_type_count":18,
            "sourced_event_type_count":18,
            "missing_event_types":[],
            "event_type_counts":dict(sorted(event_counts.items())),
            "taxonomy_supplement_case_id":self._supplement["case_id"],
            "taxonomy_supplement_event_id":self._supplement["event_id"],
            "taxonomy_supplement_replay_case_admitted":False,
            "taxonomy_supplement_physical_binding_count":
                self._supplement["physical_binding_count"],
        }
        taxonomy_row.pop("blocker",None)

        snapshot["gaps"]=[
            row for row in dimensions
            if row["status"] in {"THIN","EMPTY","MISSING","DUPLICATE_STALE"}
        ]
        snapshot["taxonomy_supplement"]=deepcopy(self._supplement)
        snapshot["current_state"].update({
            "taxonomy_event_type_count":18,
            "taxonomy_sourced_event_type_count":18,
            "taxonomy_supplement_case_count":1,
            "taxonomy_supplement_event_count":1,
            "taxonomy_supplement_observation_count":1,
            "taxonomy_supplement_physical_binding_count":
                self._supplement["physical_binding_count"],
        })

        expected=self._manifest.get("expected")
        if not isinstance(expected,dict):
            raise OperatingTaxonomyClosureError(
                "Batch 019 expected-state contract missing"
            )
        readiness_counts={}
        for row in dimensions:
            readiness_counts[row["status"]]=readiness_counts.get(row["status"],0)+1
        actual={
            "base_case_count":snapshot["current_state"]["case_count"],
            "base_policy_event_count":snapshot["current_state"]["policy_event_count"],
            "base_policy_observation_count":
                snapshot["current_state"]["policy_observation_count"],
            "base_physical_binding_count":
                snapshot["current_state"]["physical_binding_count"],
            "taxonomy_event_type_count":18,
            "taxonomy_sourced_event_type_count":18,
            "missing_event_types":[],
            "readiness_status_counts":readiness_counts,
        }
        for key,value in actual.items():
            if expected.get(key)!=value:
                raise OperatingTaxonomyClosureError(
                    f"Batch 019 expected {key}={expected.get(key)!r}, found {value!r}"
                )

        snapshot.pop("snapshot_digest_sha256",None)
        snapshot["snapshot_digest_sha256"]=_stable_digest(snapshot)
        return snapshot

    def _validate_committed_snapshot(self) -> None:
        output=self._manifest.get("snapshot_output")
        if not isinstance(output,dict):
            raise OperatingTaxonomyClosureError(
                "Batch 019 snapshot output pin missing"
            )
        relative=output.get("path")
        expected_sha=output.get("git_blob_sha")
        expected_digest=output.get("snapshot_digest_sha256")
        if not isinstance(relative,str) or not isinstance(expected_sha,str):
            raise OperatingTaxonomyClosureError(
                "Batch 019 snapshot output pin incomplete"
            )
        path=self._root/relative
        if _git_blob_sha(path)!=expected_sha:
            raise OperatingTaxonomyClosureError(
                "Batch 019 snapshot Git blob pin mismatch"
            )
        try:
            committed=json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError,json.JSONDecodeError) as exc:
            raise OperatingTaxonomyClosureError(
                "Batch 019 committed snapshot unreadable"
            ) from exc
        if committed!=self._snapshot:
            raise OperatingTaxonomyClosureError(
                "Batch 019 committed snapshot differs from live operating state"
            )
        if expected_digest!=self._snapshot["snapshot_digest_sha256"]:
            raise OperatingTaxonomyClosureError(
                "Batch 019 snapshot digest pin mismatch"
            )

    def snapshot(self) -> dict[str,Any]:
        return deepcopy(self._snapshot)

    def readiness(self) -> dict[str,Any]:
        return {
            "contract_version":OPERATING_V2_CONTRACT_VERSION,
            "mode":OPERATING_V2_MODE,
            "source_run_digest_sha256":self._snapshot[
                "source_run_digest_sha256"
            ],
            "snapshot_digest_sha256":self._snapshot[
                "snapshot_digest_sha256"
            ],
            "capabilities":deepcopy(READ_ONLY_CAPABILITIES),
            "result":deepcopy(self._snapshot["readiness_dimensions"]),
        }

    def gaps(self) -> dict[str,Any]:
        return {
            "contract_version":OPERATING_V2_CONTRACT_VERSION,
            "mode":OPERATING_V2_MODE,
            "source_run_digest_sha256":self._snapshot[
                "source_run_digest_sha256"
            ],
            "snapshot_digest_sha256":self._snapshot[
                "snapshot_digest_sha256"
            ],
            "capabilities":deepcopy(READ_ONLY_CAPABILITIES),
            "result":deepcopy(self._snapshot["gaps"]),
        }

    def dimension(self, dimension: str) -> dict[str,Any]:
        if not isinstance(dimension,str) or not dimension:
            raise OperatingTaxonomyClosureError(
                "dimension must be a non-empty string"
            )
        for row in self._snapshot["readiness_dimensions"]:
            if row["dimension"]==dimension:
                return {
                    "contract_version":OPERATING_V2_CONTRACT_VERSION,
                    "mode":OPERATING_V2_MODE,
                    "source_run_digest_sha256":self._snapshot[
                        "source_run_digest_sha256"
                    ],
                    "snapshot_digest_sha256":self._snapshot[
                        "snapshot_digest_sha256"
                    ],
                    "capabilities":deepcopy(READ_ONLY_CAPABILITIES),
                    "result":deepcopy(row),
                }
        raise OperatingTaxonomyClosureError(
            f"unknown operating dimension: {dimension}"
        )
