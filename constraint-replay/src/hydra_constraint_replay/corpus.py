from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path


REPLAY_READY_TIER = "REPLAY_READY_UNSCORED"


class CorpusValidationError(ValueError):
    pass


def _dt(value: str, label: str) -> datetime:
    try:
        ts=datetime.fromisoformat(value.replace("Z","+00:00"))
    except Exception as exc:
        raise CorpusValidationError(f"{label}: invalid timestamp") from exc
    if ts.tzinfo is None or ts.utcoffset() is None:
        raise CorpusValidationError(f"{label}: timezone-aware timestamp required")
    return ts


def _string_set(raw: dict, field: str, label: str) -> set[str]:
    value=raw.get(field)
    if not isinstance(value,list) or any(not isinstance(x,str) or not x for x in value):
        raise CorpusValidationError(f"{label}.{field}: list[str] required")
    if len(value)!=len(set(value)):
        raise CorpusValidationError(f"{label}.{field}: duplicate IDs")
    return set(value)


@dataclass(frozen=True)
class ReplayReadyCorpusSummary:
    case_count: int
    replay_cut_count: int
    event_id_count: int
    observation_id_count: int


def validate_replay_ready_record(record: dict) -> None:
    case_id=record.get("case_id")
    if not isinstance(case_id,str) or not case_id:
        raise CorpusValidationError("case_id required")
    if record.get("tier") != REPLAY_READY_TIER:
        raise CorpusValidationError(f"{case_id}: unsupported tier")
    if record.get("score_status") != "UNSCORED":
        raise CorpusValidationError(f"{case_id}: replay-ready corpus must remain UNSCORED")
    if "confidence_at_t" in record or "outcome_class" in record:
        raise CorpusValidationError(f"{case_id}: scored fields are forbidden in replay-ready tier")

    source_bundle=record.get("source_bundle")
    if not isinstance(source_bundle,str) or not source_bundle:
        raise CorpusValidationError(f"{case_id}: source_bundle required")
    sha=record.get("source_bundle_blob_sha")
    if not isinstance(sha,str) or len(sha)!=40 or any(c not in "0123456789abcdef" for c in sha.lower()):
        raise CorpusValidationError(f"{case_id}: source_bundle_blob_sha must be a 40-char git blob SHA")

    blockers=record.get("promotion_blockers")
    if not isinstance(blockers,list) or not blockers or any(not isinstance(x,str) or not x for x in blockers):
        raise CorpusValidationError(f"{case_id}: promotion_blockers required")

    cuts=record.get("replay_cuts")
    if not isinstance(cuts,list) or len(cuts)<2:
        raise CorpusValidationError(f"{case_id}: at least two replay cuts required")

    cut_ids=set()
    prior_t=None
    prior_eligible:set[str]=set()
    prior_available_obs:set[str]=set()
    event_universe=None
    observation_universe=None

    for i,cut in enumerate(cuts):
        label=f"{case_id}.replay_cuts[{i}]"
        cut_id=cut.get("cut_id")
        if not isinstance(cut_id,str) or not cut_id or cut_id in cut_ids:
            raise CorpusValidationError(f"{label}: unique cut_id required")
        cut_ids.add(cut_id)
        ts=_dt(cut.get("replay_t",""),f"{label}.replay_t")
        if prior_t is not None and ts <= prior_t:
            raise CorpusValidationError(f"{label}: replay cuts must be strictly increasing")
        prior_t=ts

        eligible=_string_set(cut,"eligible_event_ids",label)
        future=_string_set(cut,"future_event_ids",label)
        known_not_effective=_string_set(cut,"known_but_not_effective_event_ids",label)
        available_obs=_string_set(cut,"available_observation_ids",label)
        future_obs=_string_set(cut,"future_observation_ids",label)

        if eligible & future:
            raise CorpusValidationError(f"{label}: event cannot be both eligible and future")
        if not known_not_effective <= eligible:
            raise CorpusValidationError(f"{label}: known-but-not-effective must be eligible")
        if available_obs & future_obs:
            raise CorpusValidationError(f"{label}: observation cannot be both available and future")

        this_event_universe=eligible|future
        this_obs_universe=available_obs|future_obs
        if event_universe is None:
            event_universe=this_event_universe
            observation_universe=this_obs_universe
        elif this_event_universe != event_universe:
            raise CorpusValidationError(f"{label}: event universe changed across cuts")
        elif this_obs_universe != observation_universe:
            raise CorpusValidationError(f"{label}: observation universe changed across cuts")

        if i:
            if not prior_eligible <= eligible:
                raise CorpusValidationError(f"{label}: eligible events regressed")
            if not prior_available_obs <= available_obs:
                raise CorpusValidationError(f"{label}: available observations regressed")
        prior_eligible=eligible
        prior_available_obs=available_obs


def load_replay_ready_corpus(path: str | Path) -> list[dict]:
    records=[]
    seen=set()
    with Path(path).open("r",encoding="utf-8") as fh:
        for lineno,line in enumerate(fh,1):
            if not line.strip():
                continue
            try:
                record=json.loads(line)
            except json.JSONDecodeError as exc:
                raise CorpusValidationError(f"line {lineno}: invalid JSON") from exc
            validate_replay_ready_record(record)
            case_id=record["case_id"]
            if case_id in seen:
                raise CorpusValidationError(f"duplicate case_id: {case_id}")
            seen.add(case_id)
            records.append(record)
    if not records:
        raise CorpusValidationError("replay-ready corpus is empty")
    return records


def summarize_replay_ready_corpus(records: list[dict]) -> ReplayReadyCorpusSummary:
    event_ids=set()
    observation_ids=set()
    cuts=0
    for record in records:
        cuts+=len(record["replay_cuts"])
        first=record["replay_cuts"][0]
        event_ids.update(first["eligible_event_ids"])
        event_ids.update(first["future_event_ids"])
        observation_ids.update(first["available_observation_ids"])
        observation_ids.update(first["future_observation_ids"])
    return ReplayReadyCorpusSummary(
        case_count=len(records),
        replay_cut_count=cuts,
        event_id_count=len(event_ids),
        observation_id_count=len(observation_ids),
    )
