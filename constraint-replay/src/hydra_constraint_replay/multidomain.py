from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from .query import ConstraintReplayQueryService, READ_ONLY_CAPABILITIES


MULTIDOMAIN_CONTRACT_VERSION = "hydra-constraint-multidomain-readonly/v1"
MULTIDOMAIN_MODE = "READ_ONLY_MULTIDOMAIN_HISTORICAL"
DEFAULT_MULTIDOMAIN_MANIFEST_PATH = (
    "constraint-replay/runtime/"
    "HYDRA_CONSTRAINT_BATCH017_MULTIDOMAIN_READONLY_MANIFEST_20260926.json"
)

SOURCE_PAIRS = (
    (
        "batch001",
        "constraint-geopolitical-policy/data/sourced_historical_cases.json",
        "constraint-physical-dependency/data/sourced_policy_case_physical_graph.json",
    ),
    (
        "batch002",
        "constraint-geopolitical-policy/data/"
        "HYDRA_CONSTRAINT_GEOPOLITICAL_POLICY_BATCH002_SOURCED_HISTORICAL_CASES_20260925.json",
        "constraint-physical-dependency/data/"
        "HYDRA_CONSTRAINT_PHYSICAL_POLICY_GRAPH_BATCH002_SOURCED_20260925.json",
    ),
    (
        "batch003",
        "constraint-geopolitical-policy/data/"
        "HYDRA_CONSTRAINT_GEOPOLITICAL_POLICY_BATCH003_SOURCED_HISTORICAL_CASES_20260925.json",
        "constraint-physical-dependency/data/"
        "HYDRA_CONSTRAINT_PHYSICAL_POLICY_GRAPH_BATCH003_SOURCED_20260925.json",
    ),
    (
        "batch004",
        "constraint-geopolitical-policy/data/"
        "HYDRA_CONSTRAINT_GEOPOLITICAL_POLICY_BATCH004_SOURCED_HISTORICAL_CASES_20260925.json",
        "constraint-physical-dependency/data/"
        "HYDRA_CONSTRAINT_PHYSICAL_POLICY_GRAPH_BATCH004_SOURCED_20260925.json",
    ),
)


class MultiDomainQueryError(ValueError):
    pass


def _git_blob_sha(path: Path) -> str:
    payload = path.read_bytes()
    return sha1(f"blob {len(payload)}\0".encode() + payload).hexdigest()


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise MultiDomainQueryError(f"{label} file is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise MultiDomainQueryError(f"{label} file is not valid JSON: {path}") from exc
    if not isinstance(raw, dict):
        raise MultiDomainQueryError(f"{label} must be a JSON object")
    return raw


def _iso(value: Any) -> str | None:
    return None if value is None else value.isoformat()


class ConstraintMultiDomainQueryService:
    """Read-only orchestration over replay, policy events, and physical bindings.

    This layer owns no policy or physical schemas. It loads them through the
    authoritative package APIs and exposes only deterministic historical views.
    """

    def __init__(
        self,
        repo_root: str | Path,
        *,
        manifest_path: str = DEFAULT_MULTIDOMAIN_MANIFEST_PATH,
    ) -> None:
        self._root = Path(repo_root)
        self._manifest_relative = manifest_path
        self._manifest_path = self._root / manifest_path
        self._replay = ConstraintReplayQueryService(self._root)
        self._manifest = _read_json(self._manifest_path, "Batch 017 manifest")
        self._validate_manifest()
        self._load_domains()
        self._validate_join()

    def _imports(self):
        try:
            from hydra_constraint_physical import load_sourced_policy_case_graph
            from hydra_constraint_policy.case_studies import (
                events_from_sourced_case_bundle,
                load_sourced_case_bundle,
            )
            from hydra_constraint_policy.physical_adapter import (
                bind_event_to_physical_graph,
                trace_event_downstream,
            )
        except ImportError as exc:
            raise MultiDomainQueryError(
                "Batch 017 requires the stacked physical, policy, and replay packages"
            ) from exc
        return (
            load_sourced_policy_case_graph,
            load_sourced_case_bundle,
            events_from_sourced_case_bundle,
            bind_event_to_physical_graph,
            trace_event_downstream,
        )

    def _validate_manifest(self) -> None:
        if self._manifest.get("schema_version") != "1.0":
            raise MultiDomainQueryError("unsupported Batch 017 manifest schema")
        if self._manifest.get("contract_version") != MULTIDOMAIN_CONTRACT_VERSION:
            raise MultiDomainQueryError("unsupported Batch 017 contract version")
        if self._manifest.get("mode") != MULTIDOMAIN_MODE:
            raise MultiDomainQueryError("unsupported Batch 017 mode")
        if self._manifest.get("source_run_digest_sha256") != self._replay.run_digest:
            raise MultiDomainQueryError("Batch 017 source replay digest mismatch")

        manifest_pairs = self._manifest.get("source_pairs")
        if not isinstance(manifest_pairs, list) or len(manifest_pairs) != len(SOURCE_PAIRS):
            raise MultiDomainQueryError("Batch 017 source-pair manifest is incomplete")

        expected_pairs = {
            batch_id: (policy_path, physical_path)
            for batch_id, policy_path, physical_path in SOURCE_PAIRS
        }
        seen = set()
        for item in manifest_pairs:
            if not isinstance(item, Mapping):
                raise MultiDomainQueryError("Batch 017 source-pair entry is invalid")
            batch_id = item.get("batch_id")
            policy = item.get("policy")
            physical = item.get("physical")
            if batch_id not in expected_pairs or batch_id in seen:
                raise MultiDomainQueryError("Batch 017 source-pair identity is invalid")
            seen.add(batch_id)
            if not isinstance(policy, Mapping) or not isinstance(physical, Mapping):
                raise MultiDomainQueryError(f"{batch_id}: source-pair pins are invalid")
            expected_policy, expected_physical = expected_pairs[batch_id]
            if policy.get("path") != expected_policy or physical.get("path") != expected_physical:
                raise MultiDomainQueryError(f"{batch_id}: source-pair path mismatch")
            for label, entry in (("policy", policy), ("physical", physical)):
                relative = entry.get("path")
                expected_sha = entry.get("git_blob_sha")
                if not isinstance(relative, str) or not isinstance(expected_sha, str):
                    raise MultiDomainQueryError(
                        f"{batch_id}: {label} pin is incomplete"
                    )
                if _git_blob_sha(self._root / relative) != expected_sha:
                    raise MultiDomainQueryError(
                        f"{batch_id}: {label} Git blob pin mismatch"
                    )

        replay_manifest = self._manifest.get("replay_query_manifest")
        if not isinstance(replay_manifest, Mapping):
            raise MultiDomainQueryError("Batch 016 replay-query manifest pin is missing")
        relative = replay_manifest.get("path")
        expected_sha = replay_manifest.get("git_blob_sha")
        if not isinstance(relative, str) or not isinstance(expected_sha, str):
            raise MultiDomainQueryError("Batch 016 replay-query manifest pin is incomplete")
        if _git_blob_sha(self._root / relative) != expected_sha:
            raise MultiDomainQueryError("Batch 016 replay-query manifest pin mismatch")

        implementation = self._manifest.get("implementation")
        if not isinstance(implementation, Mapping):
            raise MultiDomainQueryError("Batch 017 implementation pins are missing")
        for key in ("module", "cli", "package_export"):
            item = implementation.get(key)
            if not isinstance(item, Mapping):
                raise MultiDomainQueryError(f"Batch 017 implementation pin missing: {key}")
            relative = item.get("path")
            expected_sha = item.get("git_blob_sha")
            if not isinstance(relative, str) or not isinstance(expected_sha, str):
                raise MultiDomainQueryError(f"Batch 017 implementation pin incomplete: {key}")
            if _git_blob_sha(self._root / relative) != expected_sha:
                raise MultiDomainQueryError(
                    f"Batch 017 implementation Git blob pin mismatch: {relative}"
                )

        contracts = self._manifest.get("contracts")
        if not isinstance(contracts, list) or len(contracts) != 2:
            raise MultiDomainQueryError("Batch 017 contract pins are incomplete")
        for item in contracts:
            if not isinstance(item, Mapping):
                raise MultiDomainQueryError("Batch 017 contract pin is invalid")
            relative = item.get("path")
            expected_sha = item.get("git_blob_sha")
            if not isinstance(relative, str) or not isinstance(expected_sha, str):
                raise MultiDomainQueryError("Batch 017 contract pin is incomplete")
            if _git_blob_sha(self._root / relative) != expected_sha:
                raise MultiDomainQueryError(
                    f"Batch 017 contract Git blob pin mismatch: {relative}"
                )

        if self._manifest.get("read_only_capabilities") != READ_ONLY_CAPABILITIES:
            raise MultiDomainQueryError("Batch 017 read-only capabilities mismatch")

        t6 = self._manifest.get("t6_boundary")
        if not isinstance(t6, Mapping):
            raise MultiDomainQueryError("Batch 017 T6 boundary is missing")
        if t6.get("status") != "DORMANT_NOT_ACTIVATED":
            raise MultiDomainQueryError("Batch 017 cannot activate T6")
        if t6.get("runtime_binding_created") is not False:
            raise MultiDomainQueryError("Batch 017 cannot create a T6 runtime binding")
        if t6.get("activation_authority_granted") is not False:
            raise MultiDomainQueryError("Batch 017 has no T6 activation authority")

    def _load_domains(self) -> None:
        (
            load_graph,
            load_bundle,
            events_from_bundle,
            bind_event,
            trace_event,
        ) = self._imports()
        self._bind_event = bind_event
        self._trace_event = trace_event

        self._case_records: dict[str, dict[str, Any]] = {}
        self._events_by_case: dict[str, list[Any]] = defaultdict(list)
        self._graph_by_case: dict[str, Any] = {}
        self._source_pair_by_case: dict[str, str] = {}

        for batch_id, policy_relative, physical_relative in SOURCE_PAIRS:
            bundle = load_bundle(self._root / policy_relative)
            graph = load_graph(self._root / physical_relative)
            events = events_from_bundle(bundle)

            for raw_case in bundle["cases"]:
                case_id = raw_case["case_id"]
                if case_id in self._case_records:
                    raise MultiDomainQueryError(f"duplicate policy case_id: {case_id}")
                self._case_records[case_id] = deepcopy(raw_case)
                self._graph_by_case[case_id] = graph
                self._source_pair_by_case[case_id] = batch_id

            for event in events:
                case_id = str(event.metadata.get("case_id", ""))
                if case_id not in self._case_records:
                    raise MultiDomainQueryError(
                        f"{event.event_id}: event references unknown case {case_id}"
                    )
                self._events_by_case[case_id].append(event)

        for case_id in self._events_by_case:
            self._events_by_case[case_id].sort(
                key=lambda event: (event.temporal.known_at, event.event_id)
            )

    def _validate_join(self) -> None:
        replay_rows = self._replay.list_cases()["result"]["cases"]
        replay_ids = {row["case_id"] for row in replay_rows}
        policy_ids = set(self._case_records)
        if replay_ids != policy_ids:
            missing = sorted(replay_ids - policy_ids)
            extra = sorted(policy_ids - replay_ids)
            raise MultiDomainQueryError(
                f"replay/policy case-set mismatch; missing={missing}, extra={extra}"
            )

        event_count = 0
        binding_count = 0
        unique_entities = set()
        for case_id in sorted(policy_ids):
            events = self._events_by_case.get(case_id, [])
            if not events:
                raise MultiDomainQueryError(f"{case_id}: no executable policy events")
            graph = self._graph_by_case[case_id]
            for event in events:
                event_count += 1
                bindings = self._bind_event(event, graph)
                if not bindings:
                    raise MultiDomainQueryError(
                        f"{event.event_id}: no canonical physical bindings"
                    )
                binding_count += len(bindings)
                unique_entities.update(binding.entity_id for binding in bindings)

        if event_count != 31:
            raise MultiDomainQueryError(
                f"expected 31 executable events, found {event_count}"
            )

        observation_count = sum(
            len(raw_case.get("observations", []))
            for raw_case in self._case_records.values()
        )
        expected = self._manifest.get("expected")
        if not isinstance(expected, Mapping):
            raise MultiDomainQueryError("Batch 017 expected-count contract is missing")
        actual_expected = {
            "case_count": len(policy_ids),
            "policy_event_count": event_count,
            "policy_observation_count": observation_count,
            "physical_binding_count": binding_count,
            "unique_bound_entity_count": len(unique_entities),
            "source_pair_count": len(SOURCE_PAIRS),
            "replay_cut_count": self._replay.summary()["result"]["coverage"]["replay_cut_count"],
            "partial_realization_count": self._replay.summary()["result"]["outcomes"]["class_counts"].get("PARTIAL_REALIZATION", 0),
            "unevaluable_count": self._replay.summary()["result"]["outcomes"]["class_counts"].get("UNEVALUABLE", 0),
            "calibrated_case_count": self._replay.summary()["result"]["coverage"]["calibrated_case_count"],
        }
        for key, actual in actual_expected.items():
            if expected.get(key) != actual:
                raise MultiDomainQueryError(
                    f"Batch 017 expected {key}={expected.get(key)!r}, found {actual!r}"
                )

        self._join_integrity = {
            "case_count": len(policy_ids),
            "event_count": event_count,
            "observation_count": observation_count,
            "physical_binding_count": binding_count,
            "unique_bound_entity_count": len(unique_entities),
            "replay_policy_case_sets_equal": True,
            "all_events_physically_bound": True,
            "source_pair_count": len(SOURCE_PAIRS),
            "status": "PASS",
        }

    def _response(self, operation: str, result: Any) -> dict[str, Any]:
        return {
            "contract_version": MULTIDOMAIN_CONTRACT_VERSION,
            "mode": MULTIDOMAIN_MODE,
            "operation": operation,
            "source_run_digest_sha256": self._replay.run_digest,
            "capabilities": dict(READ_ONLY_CAPABILITIES),
            "result": deepcopy(result),
        }

    def summary(self) -> dict[str, Any]:
        event_types = Counter()
        observation_count = 0
        for case_id, raw_case in self._case_records.items():
            observation_count += len(raw_case.get("observations", []))
            for event in self._events_by_case[case_id]:
                event_types[event.event_type.value] += 1

        return self._response(
            "summary",
            {
                "replay": self._replay.summary()["result"],
                "policy": {
                    "case_count": len(self._case_records),
                    "event_count": sum(
                        len(events) for events in self._events_by_case.values()
                    ),
                    "observation_count": observation_count,
                    "event_type_counts": dict(sorted(event_types.items())),
                },
                "physical": {
                    "binding_count": self._join_integrity["physical_binding_count"],
                    "unique_bound_entity_count": self._join_integrity[
                        "unique_bound_entity_count"
                    ],
                    "source_pair_count": len(SOURCE_PAIRS),
                },
                "join_integrity": self._join_integrity,
            },
        )

    def integrity(self) -> dict[str, Any]:
        return self._response(
            "integrity",
            {
                "replay": self._replay.integrity()["result"],
                "multidomain": self._join_integrity,
                "manifest_path": self._manifest_relative,
                "manifest_git_blob_sha": _git_blob_sha(self._manifest_path),
                "t6_status": "DORMANT_NOT_ACTIVATED",
            },
        )

    def case(self, case_id: str, *, max_depth: int = 3) -> dict[str, Any]:
        if case_id not in self._case_records:
            raise MultiDomainQueryError(f"unknown case_id: {case_id}")
        if isinstance(max_depth, bool) or not isinstance(max_depth, int) or not 0 <= max_depth <= 12:
            raise MultiDomainQueryError("max_depth must be an integer in [0,12]")

        replay = self._replay.case(case_id)["result"]
        raw_case = self._case_records[case_id]
        graph = self._graph_by_case[case_id]
        events = []

        for event in self._events_by_case[case_id]:
            bindings = self._bind_event(event, graph)
            traces = self._trace_event(event, graph, max_depth=max_depth)
            events.append({
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "claim_kind": event.claim_kind.value,
                "statement": event.statement,
                "known_at": _iso(event.temporal.known_at),
                "effective_at": _iso(event.temporal.effective_at),
                "observed_at": _iso(event.temporal.observed_at),
                "resolved_at": _iso(event.temporal.resolved_at),
                "physical_bindings": [
                    {
                        "relation_kind": binding.relation_kind,
                        "entity_id": binding.entity_id,
                        "reference_type": binding.reference_type,
                        "physical_kind": binding.physical_kind,
                        "confidence": binding.confidence,
                    }
                    for binding in bindings
                ],
                "downstream_edge_paths": {
                    entity_id: [list(path) for path in paths]
                    for entity_id, paths in sorted(traces.items())
                },
            })

        observations = sorted(
            (
                {
                    "observation_id": obs["observation_id"],
                    "known_at": obs["known_at"],
                    "observed_at": obs["observed_at"],
                    "source_ids": list(obs["source_ids"]),
                    "statement": obs["statement"],
                }
                for obs in raw_case.get("observations", [])
            ),
            key=lambda row: (row["known_at"], row["observation_id"]),
        )

        return self._response(
            "case",
            {
                "case_id": case_id,
                "source_pair": self._source_pair_by_case[case_id],
                "binding_status": raw_case["binding_status"],
                "replay": replay,
                "policy_events": events,
                "policy_observations": observations,
            },
        )

    def entity_usage(self, entity_id: str, *, max_depth: int = 3) -> dict[str, Any]:
        if not isinstance(entity_id, str) or not entity_id:
            raise MultiDomainQueryError("entity_id must be a non-empty string")
        if isinstance(max_depth, bool) or not isinstance(max_depth, int) or not 0 <= max_depth <= 12:
            raise MultiDomainQueryError("max_depth must be an integer in [0,12]")

        rows = []
        for case_id in sorted(self._case_records):
            graph = self._graph_by_case[case_id]
            for event in self._events_by_case[case_id]:
                matching = [
                    relation
                    for relation in event.relations
                    if relation.entity_id == entity_id
                ]
                if not matching:
                    continue
                bindings = {
                    binding.entity_id: binding
                    for binding in self._bind_event(event, graph)
                }
                binding = bindings.get(entity_id)
                if binding is None:
                    raise MultiDomainQueryError(
                        f"{event.event_id}: matching entity lost physical binding"
                    )
                traces = self._trace_event(event, graph, max_depth=max_depth)
                rows.append({
                    "case_id": case_id,
                    "event_id": event.event_id,
                    "event_type": event.event_type.value,
                    "known_at": _iso(event.temporal.known_at),
                    "relation_kinds": sorted({relation.kind for relation in matching}),
                    "confidence_values": sorted(
                        {float(relation.confidence) for relation in matching}
                    ),
                    "reference_type": binding.reference_type,
                    "physical_kind": binding.physical_kind,
                    "downstream_edge_paths": [
                        list(path) for path in traces.get(entity_id, ())
                    ],
                })

        if not rows:
            raise MultiDomainQueryError(f"unknown physical entity_id: {entity_id}")
        return self._response(
            "entity_usage",
            {
                "entity_id": entity_id,
                "usage_count": len(rows),
                "usages": rows,
            },
        )

    def list_cases(
        self,
        *,
        outcome_class: str | None = None,
        event_type: str | None = None,
        physical_entity_id: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        replay_response = self._replay.list_cases(outcome_class=outcome_class)
        candidate_ids = {
            row["case_id"] for row in replay_response["result"]["cases"]
        }

        if event_type is not None:
            if not isinstance(event_type, str) or not event_type:
                raise MultiDomainQueryError("event_type must be a non-empty string")
            event_ids = {
                case_id
                for case_id, events in self._events_by_case.items()
                if any(event.event_type.value == event_type for event in events)
            }
            candidate_ids &= event_ids

        if physical_entity_id is not None:
            if not isinstance(physical_entity_id, str) or not physical_entity_id:
                raise MultiDomainQueryError(
                    "physical_entity_id must be a non-empty string"
                )
            physical_ids = {
                case_id
                for case_id, events in self._events_by_case.items()
                if any(
                    relation.entity_id == physical_entity_id
                    for event in events
                    for relation in event.relations
                )
            }
            candidate_ids &= physical_ids

        if limit is not None and (
            isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100
        ):
            raise MultiDomainQueryError("limit must be an integer in [1,100]")

        rows = []
        replay_by = {
            row["case_id"]: row for row in replay_response["result"]["cases"]
        }
        for case_id in sorted(candidate_ids):
            events = self._events_by_case[case_id]
            entity_ids = sorted({
                relation.entity_id
                for event in events
                for relation in event.relations
            })
            rows.append({
                "case_id": case_id,
                "outcome_class": replay_by[case_id]["outcome_class"],
                "event_types": sorted({event.event_type.value for event in events}),
                "physical_entity_ids": entity_ids,
                "event_count": len(events),
                "observation_count": len(
                    self._case_records[case_id].get("observations", [])
                ),
            })

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
            raise MultiDomainQueryError("query request must be an object")
        operation = request.get("operation")

        if operation == "summary":
            self._require_exact(request, {"operation"})
            return self.summary()
        if operation == "integrity":
            self._require_exact(request, {"operation"})
            return self.integrity()
        if operation == "case":
            allowed = {"operation", "case_id", "max_depth"}
            self._require_subset(request, allowed)
            if "case_id" not in request:
                raise MultiDomainQueryError("case_id is required")
            return self.case(
                request["case_id"],
                max_depth=request.get("max_depth", 3),
            )
        if operation == "entity_usage":
            allowed = {"operation", "entity_id", "max_depth"}
            self._require_subset(request, allowed)
            if "entity_id" not in request:
                raise MultiDomainQueryError("entity_id is required")
            return self.entity_usage(
                request["entity_id"],
                max_depth=request.get("max_depth", 3),
            )
        if operation == "list_cases":
            allowed = {
                "operation",
                "outcome_class",
                "event_type",
                "physical_entity_id",
                "limit",
            }
            self._require_subset(request, allowed)
            return self.list_cases(
                outcome_class=request.get("outcome_class"),
                event_type=request.get("event_type"),
                physical_entity_id=request.get("physical_entity_id"),
                limit=request.get("limit"),
            )
        raise MultiDomainQueryError("unsupported or missing query operation")

    @staticmethod
    def _require_exact(request: Mapping[str, Any], expected: set[str]) -> None:
        if set(request) != expected:
            raise MultiDomainQueryError(
                f"query fields must be exactly {sorted(expected)}"
            )

    @staticmethod
    def _require_subset(request: Mapping[str, Any], allowed: set[str]) -> None:
        extra = set(request) - allowed
        if extra:
            raise MultiDomainQueryError(
                f"unsupported query fields: {sorted(extra)}"
            )
