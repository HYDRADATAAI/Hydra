from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


class OutcomeEvidenceError(ValueError):
    pass


class EvidenceRole(str, Enum):
    HISTORICAL_HYPOTHESIS = "HISTORICAL_HYPOTHESIS"
    OUTCOME = "OUTCOME"


@dataclass(frozen=True)
class EnrichmentSource:
    source_id: str
    role: EvidenceRole
    publisher: str
    url: str
    published_at: datetime
    available_at: datetime
    normalized_evidence: str
    evidence_digest: str
    observed_at: datetime | None = None


@dataclass(frozen=True)
class OutcomeMetric:
    metric_id: str
    source_id: str
    observed_at: datetime
    metric: str
    value: float
    unit: str


@dataclass(frozen=True)
class OutcomeSeriesPoint:
    period: str
    value: float


@dataclass(frozen=True)
class OutcomeSeries:
    series_id: str
    source_id: str
    unit: str
    points: tuple[OutcomeSeriesPoint, ...]


@dataclass(frozen=True)
class CaseOutcomeEnrichment:
    case_id: str
    historical_hypothesis_source_ids: tuple[str, ...]
    outcome_source_ids: tuple[str, ...]
    hypothesis_available_at: datetime
    hypothesis_statement: str
    metrics: tuple[OutcomeMetric, ...]
    time_series: tuple[OutcomeSeries, ...] = ()
    qualitative_outcomes: tuple[dict[str, str], ...] = ()


def _dt(value: str, label: str) -> datetime:
    try:
        ts=datetime.fromisoformat(value.replace("Z","+00:00"))
    except Exception as exc:
        raise OutcomeEvidenceError(f"{label}: invalid timestamp") from exc
    if ts.tzinfo is None or ts.utcoffset() is None:
        raise OutcomeEvidenceError(f"{label}: timezone-aware timestamp required")
    return ts


def _number(value: Any, label: str) -> float:
    if isinstance(value,bool) or not isinstance(value,(int,float)):
        raise OutcomeEvidenceError(f"{label}: numeric value required")
    return float(value)


def load_outcome_enrichment_bundle(
    path: str | Path,
) -> tuple[dict[str, EnrichmentSource], tuple[CaseOutcomeEnrichment, ...]]:
    raw=json.loads(Path(path).read_text(encoding="utf-8"))
    if raw.get("schema_version")!="1.0":
        raise OutcomeEvidenceError("unsupported enrichment schema")
    if raw.get("evidence_digest_scope")!="sha256(normalized_evidence UTF-8)":
        raise OutcomeEvidenceError("unsupported evidence digest scope")

    sources: dict[str,EnrichmentSource]={}
    for item in raw.get("sources",[]):
        sid=item.get("source_id")
        if not isinstance(sid,str) or not sid or sid in sources:
            raise OutcomeEvidenceError(f"duplicate or missing source_id: {sid!r}")
        role=EvidenceRole(item["role"])
        evidence=item.get("normalized_evidence")
        if not isinstance(evidence,str) or not evidence:
            raise OutcomeEvidenceError(f"{sid}: normalized_evidence required")
        expected="sha256:"+sha256(evidence.encode("utf-8")).hexdigest()
        if item.get("evidence_digest")!=expected:
            raise OutcomeEvidenceError(f"{sid}: evidence digest mismatch")
        url=item.get("url")
        if not isinstance(url,str) or not url.startswith("https://"):
            raise OutcomeEvidenceError(f"{sid}: HTTPS URL required")
        published=_dt(item["published_at"],f"{sid}.published_at")
        available=_dt(item["available_at"],f"{sid}.available_at")
        observed=_dt(item["observed_at"],f"{sid}.observed_at") if item.get("observed_at") else None
        if available < published:
            raise OutcomeEvidenceError(f"{sid}: available_at precedes published_at")
        if role==EvidenceRole.OUTCOME and observed is None:
            raise OutcomeEvidenceError(f"{sid}: outcome source requires observed_at")
        if role==EvidenceRole.HISTORICAL_HYPOTHESIS and observed is not None:
            raise OutcomeEvidenceError(f"{sid}: hypothesis source cannot carry observed_at")
        sources[sid]=EnrichmentSource(
            source_id=sid,
            role=role,
            publisher=item["publisher"],
            url=url,
            published_at=published,
            available_at=available,
            observed_at=observed,
            normalized_evidence=evidence,
            evidence_digest=expected,
        )

    cases=[]
    seen_cases=set()
    seen_metrics=set()
    seen_series=set()
    for item in raw.get("cases",[]):
        cid=item.get("case_id")
        if not isinstance(cid,str) or not cid or cid in seen_cases:
            raise OutcomeEvidenceError(f"duplicate or missing case_id: {cid!r}")
        seen_cases.add(cid)

        hypothesis_ids=tuple(item.get("historical_hypothesis_source_ids",[]))
        outcome_ids=tuple(item.get("outcome_source_ids",[]))
        if not hypothesis_ids:
            raise OutcomeEvidenceError(f"{cid}: hypothesis source required")
        if not outcome_ids:
            raise OutcomeEvidenceError(f"{cid}: outcome source required")
        if len(hypothesis_ids)!=len(set(hypothesis_ids)) or len(outcome_ids)!=len(set(outcome_ids)):
            raise OutcomeEvidenceError(f"{cid}: duplicate source IDs")
        for sid in hypothesis_ids:
            if sid not in sources or sources[sid].role!=EvidenceRole.HISTORICAL_HYPOTHESIS:
                raise OutcomeEvidenceError(f"{cid}: invalid hypothesis source {sid}")
        for sid in outcome_ids:
            if sid not in sources or sources[sid].role!=EvidenceRole.OUTCOME:
                raise OutcomeEvidenceError(f"{cid}: invalid outcome source {sid}")

        hypothesis_available=_dt(item["hypothesis_available_at"],f"{cid}.hypothesis_available_at")
        actual_hypothesis_available=max(sources[sid].available_at for sid in hypothesis_ids)
        if hypothesis_available != actual_hypothesis_available:
            raise OutcomeEvidenceError(f"{cid}: hypothesis_available_at does not match source availability")
        first_outcome_known=min(sources[sid].available_at for sid in outcome_ids)
        if hypothesis_available >= first_outcome_known:
            raise OutcomeEvidenceError(f"{cid}: hypothesis evidence is not prior to outcome evidence")

        statement=item.get("hypothesis_statement")
        if not isinstance(statement,str) or not statement:
            raise OutcomeEvidenceError(f"{cid}: hypothesis_statement required")

        metrics=[]
        for m in item.get("metrics",[]):
            mid=m.get("metric_id")
            if not isinstance(mid,str) or not mid or mid in seen_metrics:
                raise OutcomeEvidenceError(f"duplicate or missing metric_id: {mid!r}")
            seen_metrics.add(mid)
            sid=m.get("source_id")
            if sid not in outcome_ids:
                raise OutcomeEvidenceError(f"{cid}.{mid}: metric source not admitted for case")
            observed=_dt(m["observed_at"],f"{mid}.observed_at")
            source=sources[sid]
            if source.observed_at is not None and observed != source.observed_at:
                raise OutcomeEvidenceError(f"{mid}: observed_at differs from source")
            unit=m.get("unit")
            metric_name=m.get("metric")
            if not isinstance(unit,str) or not unit or not isinstance(metric_name,str) or not metric_name:
                raise OutcomeEvidenceError(f"{mid}: metric/unit required")
            metrics.append(OutcomeMetric(
                metric_id=mid,
                source_id=sid,
                observed_at=observed,
                metric=metric_name,
                value=_number(m.get("value"),f"{mid}.value"),
                unit=unit,
            ))

        series=[]
        for s in item.get("time_series",[]):
            series_id=s.get("series_id")
            if not isinstance(series_id,str) or not series_id or series_id in seen_series:
                raise OutcomeEvidenceError(f"duplicate or missing series_id: {series_id!r}")
            seen_series.add(series_id)
            sid=s.get("source_id")
            if sid not in outcome_ids:
                raise OutcomeEvidenceError(f"{cid}.{series_id}: series source not admitted for case")
            unit=s.get("unit")
            if not isinstance(unit,str) or not unit:
                raise OutcomeEvidenceError(f"{series_id}: unit required")
            points=[]
            periods=set()
            for p in s.get("points",[]):
                period=p.get("period")
                if not isinstance(period,str) or not period or period in periods:
                    raise OutcomeEvidenceError(f"{series_id}: unique period required")
                periods.add(period)
                points.append(OutcomeSeriesPoint(period=period,value=_number(p.get("value"),f"{series_id}.{period}")))
            if len(points)<2:
                raise OutcomeEvidenceError(f"{series_id}: at least two points required")
            series.append(OutcomeSeries(series_id=series_id,source_id=sid,unit=unit,points=tuple(points)))

        qualitative=[]
        for q in item.get("qualitative_outcomes",[]):
            sid=q.get("source_id")
            statement=q.get("statement")
            if sid not in outcome_ids or not isinstance(statement,str) or not statement:
                raise OutcomeEvidenceError(f"{cid}: invalid qualitative outcome")
            qualitative.append({"source_id":sid,"statement":statement})

        if not metrics and not series and not qualitative:
            raise OutcomeEvidenceError(f"{cid}: no outcome content")

        cases.append(CaseOutcomeEnrichment(
            case_id=cid,
            historical_hypothesis_source_ids=hypothesis_ids,
            outcome_source_ids=outcome_ids,
            hypothesis_available_at=hypothesis_available,
            hypothesis_statement=statement,
            metrics=tuple(metrics),
            time_series=tuple(series),
            qualitative_outcomes=tuple(qualitative),
        ))

    if not cases:
        raise OutcomeEvidenceError("enrichment bundle is empty")
    return sources,tuple(cases)
