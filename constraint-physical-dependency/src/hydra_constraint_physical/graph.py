from __future__ import annotations
from collections import defaultdict, deque
from datetime import date
from math import fsum
from .models import Edge, Node

class DependencyGraph:
    def __init__(self, nodes: list[Node] | None = None, edges: list[Edge] | None = None):
        self.nodes = {n.node_id: n for n in (nodes or [])}
        self.edges = {e.edge_id: e for e in (edges or [])}

    def as_of(self, when: date, knowledge_cutoff: date | None = None) -> "DependencyGraph":
        nodes = []
        for n in self.nodes.values():
            snaps = tuple(s for s in n.snapshots if s.active_as_of(when, knowledge_cutoff))
            if snaps or not n.snapshots:
                nodes.append(Node(n.node_id,n.kind,n.name,n.country_code,snaps,n.provenance))
        ids={n.node_id for n in nodes}
        edges=[e for e in self.edges.values()
               if e.source_id in ids and e.target_id in ids and e.active_as_of(when,knowledge_cutoff)]
        return DependencyGraph(nodes,edges)

    def trace(self, start_id: str, max_depth: int = 12) -> list[list[Edge]]:
        outgoing=defaultdict(list)
        for e in self.edges.values(): outgoing[e.source_id].append(e)
        out=[]; q=deque([(start_id,[],{start_id})])
        while q:
            cur,path,seen=q.popleft()
            if path: out.append(path)
            if len(path)>=max_depth: continue
            for e in outgoing[cur]:
                if e.target_id not in seen:
                    q.append((e.target_id,path+[e],seen|{e.target_id}))
        return out

    def hhi(self, node_id: str, relation: str | None = None) -> float | None:
        shares=[e.share for e in self.edges.values()
                if e.target_id==node_id and e.share is not None and (relation is None or e.relation==relation)]
        if not shares: return None
        total=fsum(shares)
        if total <= 0: return None
        normalized=[s/total for s in shares]
        return fsum(s*s for s in normalized)

    def loss_impact(self, removed_node_id: str) -> set[str]:
        outgoing=defaultdict(list)
        for e in self.edges.values(): outgoing[e.source_id].append(e.target_id)
        affected=set(); q=deque([removed_node_id])
        while q:
            cur=q.popleft()
            for nxt in outgoing[cur]:
                if nxt not in affected and nxt != removed_node_id:
                    affected.add(nxt); q.append(nxt)
        return affected

    def substitutes(self, node_id: str) -> list[Edge]:
        return [e for e in self.edges.values()
                if e.source_id==node_id and e.relation in {"substitutable_by","substitute"}]
