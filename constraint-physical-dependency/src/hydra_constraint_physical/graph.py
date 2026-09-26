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
            if n.snapshots:
                if snaps:
                    nodes.append(Node(n.node_id,n.kind,n.name,n.country_code,snaps,n.provenance))
                continue

            # Identity-only nodes have no validity interval. In a knowledge-
            # bounded replay they must have provenance that was actually
            # knowable by the cutoff; otherwise the identity is UNKNOWN.
            if knowledge_cutoff is not None:
                if not n.provenance:
                    continue
                if min(p.known_at for p in n.provenance) > knowledge_cutoff:
                    continue
            nodes.append(n)

        ids={n.node_id for n in nodes}
        edges=[e for e in self.edges.values()
               if e.source_id in ids and e.target_id in ids and e.active_as_of(when,knowledge_cutoff)]
        return DependencyGraph(nodes,edges)

    def reference_state_as_of(
        self,
        entity_id: str,
        when: date,
        knowledge_cutoff: date | None = None,
    ) -> str:
        """Return PRESENT, ABSENT, or UNKNOWN without collapsing missing history.

        UNKNOWN means the graph lacks historically admissible evidence for a
        substantive presence/absence conclusion at the requested cutoff.
        ABSENT is returned only when a historically knowable validity interval
        places the reference outside its effective period.
        """
        if entity_id in self.nodes:
            node=self.nodes[entity_id]
            if node.snapshots:
                known=[
                    s for s in node.snapshots
                    if knowledge_cutoff is None
                    or (s.known_at is not None and s.known_at <= knowledge_cutoff)
                ]
                if not known:
                    return "UNKNOWN"
                if any(
                    s.valid_from <= when and (s.valid_to is None or when < s.valid_to)
                    for s in known
                ):
                    return "PRESENT"
                if any(s.valid_from > when for s in known):
                    return "ABSENT"
                if any(s.valid_to is not None and s.valid_to <= when for s in known):
                    return "ABSENT"
                return "UNKNOWN"

            if not node.provenance:
                return "UNKNOWN"
            if knowledge_cutoff is None:
                return "PRESENT"
            return (
                "PRESENT"
                if min(p.known_at for p in node.provenance) <= knowledge_cutoff
                else "UNKNOWN"
            )

        if entity_id in self.edges:
            edge=self.edges[entity_id]
            if knowledge_cutoff is not None:
                if edge.known_at is None or edge.known_at > knowledge_cutoff:
                    return "UNKNOWN"
            if edge.valid_from <= when and (edge.valid_to is None or when < edge.valid_to):
                return "PRESENT"
            return "ABSENT"

        return "UNKNOWN"

    def resolve_reference(
        self,
        entity_id: str,
        when: date | None = None,
        knowledge_cutoff: date | None = None,
    ) -> tuple[str, Node | Edge] | None:
        """Resolve a canonical physical node/edge ID, optionally point-in-time.

        Cross-domain consumers should use this boundary rather than reach
        directly into the graph's internal node/edge dictionaries.
        """
        if knowledge_cutoff is not None and when is None:
            raise ValueError("knowledge_cutoff requires when")
        view = self if when is None else self.as_of(when, knowledge_cutoff)
        if entity_id in view.nodes:
            return ("node", view.nodes[entity_id])
        if entity_id in view.edges:
            return ("edge", view.edges[entity_id])
        return None

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
