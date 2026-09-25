from __future__ import annotations

from datetime import date
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from .graph import DependencyGraph
from .models import Edge, Node, Provenance, Snapshot
from .validation import validate_graph


class SourcedGraphValidationError(ValueError):
    pass


def _date(value: str | None) -> date | None:
    return None if value is None else date.fromisoformat(value)


def _number(raw: dict[str, Any], field: str) -> float | None:
    value=raw.get(field)
    if value is None:
        return None
    if isinstance(value,bool) or not isinstance(value,(int,float)):
        raise SourcedGraphValidationError(f"{raw.get('node_id') or raw.get('edge_id')}: {field} must be numeric")
    return float(value)


def _fraction(raw: dict[str, Any], field: str) -> float | None:
    value=_number(raw,field)
    if value is not None and not 0 <= value <= 1:
        raise SourcedGraphValidationError(f"{raw.get('node_id') or raw.get('edge_id')}: {field} outside [0,1]")
    return value


def _nonnegative(raw: dict[str, Any], field: str) -> float | None:
    value=_number(raw,field)
    if value is not None and value < 0:
        raise SourcedGraphValidationError(f"{raw.get('node_id') or raw.get('edge_id')}: negative {field}")
    return value


def _nonnegative_int(raw: dict[str, Any], field: str) -> int | None:
    value=raw.get(field)
    if value is None:
        return None
    if isinstance(value,bool) or not isinstance(value,int) or value < 0:
        raise SourcedGraphValidationError(f"{raw.get('edge_id')}: {field} must be a nonnegative integer")
    return value


def _validate_bundle(bundle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if bundle.get("evidence_digest_scope") != "sha256(normalized_evidence UTF-8)":
        raise SourcedGraphValidationError("unsupported evidence digest scope")

    sources: dict[str, dict[str, Any]]={}
    for source in bundle.get("sources", []):
        sid=source.get("source_id")
        if not sid or sid in sources:
            raise SourcedGraphValidationError(f"duplicate or missing source_id: {sid!r}")
        normalized=source.get("normalized_evidence", "")
        expected="sha256:"+sha256(normalized.encode("utf-8")).hexdigest()
        if source.get("evidence_hash") != expected:
            raise SourcedGraphValidationError(f"{sid}: evidence digest mismatch")
        if not str(source.get("source_url", "")).startswith("https://"):
            raise SourcedGraphValidationError(f"{sid}: non-HTTPS source")
        for field in ("retrieved_at","known_at","published_at"):
            if source.get(field):
                _date(source[field])
        sources[sid]=source

    ids=set()
    for node in bundle.get("nodes", []):
        nid=node.get("node_id")
        if not nid or nid in ids:
            raise SourcedGraphValidationError(f"duplicate or missing node_id: {nid!r}")
        ids.add(nid)
        _date(node["valid_from"])
        if node.get("valid_to"):
            _date(node["valid_to"])
        _date(node["known_at"])
        _nonnegative(node,"capacity_nameplate")
        _nonnegative(node,"capacity_usable")
        _fraction(node,"utilization")
        _fraction(node,"market_share")
        unit=node.get("capacity_unit")
        if unit is not None and (not isinstance(unit,str) or not unit.strip()):
            raise SourcedGraphValidationError(f"{nid}: capacity_unit must be a non-empty string")
        refs=node.get("source_ids", [])
        if not refs:
            raise SourcedGraphValidationError(f"{nid}: no source_ids")
        for sid in refs:
            if sid not in sources:
                raise SourcedGraphValidationError(f"{nid}: unknown source {sid}")
            if _date(sources[sid]["known_at"]) > _date(node["known_at"]):
                raise SourcedGraphValidationError(f"{nid}: source {sid} known after node")

    edge_ids=set()
    for edge in bundle.get("edges", []):
        eid=edge.get("edge_id")
        if not eid or eid in edge_ids:
            raise SourcedGraphValidationError(f"duplicate or missing edge_id: {eid!r}")
        edge_ids.add(eid)
        if edge.get("source_id") not in ids or edge.get("target_id") not in ids:
            raise SourcedGraphValidationError(f"{eid}: dangling endpoint")
        _date(edge["valid_from"])
        if edge.get("valid_to"):
            _date(edge["valid_to"])
        _date(edge["known_at"])
        _fraction(edge,"share")
        _nonnegative(edge,"capacity")
        _nonnegative_int(edge,"substitution_time_days")
        unit=edge.get("capacity_unit")
        if unit is not None and (not isinstance(unit,str) or not unit.strip()):
            raise SourcedGraphValidationError(f"{eid}: capacity_unit must be a non-empty string")
        refs=edge.get("source_ids", [])
        if not refs:
            raise SourcedGraphValidationError(f"{eid}: no source_ids")
        for sid in refs:
            if sid not in sources:
                raise SourcedGraphValidationError(f"{eid}: unknown source {sid}")
            if _date(sources[sid]["known_at"]) > _date(edge["known_at"]):
                raise SourcedGraphValidationError(f"{eid}: source {sid} known after edge")
    return sources


def load_sourced_policy_case_graph(path: str | Path) -> DependencyGraph:
    bundle=json.loads(Path(path).read_text(encoding="utf-8"))
    sources=_validate_bundle(bundle)

    def provenance(source_ids: list[str]) -> tuple[Provenance, ...]:
        out=[]
        for sid in source_ids:
            s=sources[sid]
            out.append(Provenance(
                source_id=sid,
                source_url=s["source_url"],
                publisher=s["publisher"],
                retrieved_at=_date(s["retrieved_at"]),
                known_at=_date(s["known_at"]),
                published_at=_date(s.get("published_at")),
                evidence_hash=s["evidence_hash"],
            ))
        return tuple(out)

    nodes=[]
    for raw in bundle.get("nodes", []):
        snap=Snapshot(
            valid_from=_date(raw["valid_from"]),
            valid_to=_date(raw.get("valid_to")),
            known_at=_date(raw["known_at"]),
            capacity_nameplate=_number(raw,"capacity_nameplate"),
            capacity_usable=_number(raw,"capacity_usable"),
            capacity_unit=raw.get("capacity_unit"),
            utilization=_number(raw,"utilization"),
            market_share=_number(raw,"market_share"),
            attributes={"source_ids": tuple(raw["source_ids"])},
        )
        nodes.append(Node(
            node_id=raw["node_id"],
            kind=raw["kind"],
            name=raw["name"],
            country_code=raw.get("country_code"),
            snapshots=(snap,),
            provenance=provenance(raw["source_ids"]),
        ))

    edges=[]
    for raw in bundle.get("edges", []):
        edges.append(Edge(
            edge_id=raw["edge_id"],
            source_id=raw["source_id"],
            target_id=raw["target_id"],
            relation=raw["relation"],
            valid_from=_date(raw["valid_from"]),
            valid_to=_date(raw.get("valid_to")),
            known_at=_date(raw["known_at"]),
            share=_number(raw,"share"),
            capacity=_number(raw,"capacity"),
            capacity_unit=raw.get("capacity_unit"),
            substitution_time_days=_nonnegative_int(raw,"substitution_time_days"),
            attributes={"source_ids": tuple(raw["source_ids"])},
            provenance=provenance(raw["source_ids"]),
        ))

    graph=DependencyGraph(nodes,edges)
    errors=validate_graph(graph)
    if errors:
        raise SourcedGraphValidationError("; ".join(errors))
    return graph
