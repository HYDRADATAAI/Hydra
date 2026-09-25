from __future__ import annotations
from .graph import DependencyGraph

ALLOWED_RELATIONS={
 "located_at","extracted_by","feeds","processed_by","transported_via","requires",
 "manufactures","used_in","depends_on","constrains","substitutable_by","substitute",
 "benefits","controlled_by","supplies"
}

def validate_graph(graph: DependencyGraph) -> list[str]:
    errors=[]
    for e in graph.edges.values():
        if e.source_id not in graph.nodes: errors.append(f"{e.edge_id}: missing source {e.source_id}")
        if e.target_id not in graph.nodes: errors.append(f"{e.edge_id}: missing target {e.target_id}")
        if e.relation not in ALLOWED_RELATIONS: errors.append(f"{e.edge_id}: unknown relation {e.relation}")
        if e.valid_to is not None and e.valid_to <= e.valid_from:
            errors.append(f"{e.edge_id}: invalid validity interval")
        if e.share is not None and not 0 <= e.share <= 1:
            errors.append(f"{e.edge_id}: share outside [0,1]")
        if e.capacity is not None and e.capacity < 0:
            errors.append(f"{e.edge_id}: negative capacity")
        if e.substitution_time_days is not None and e.substitution_time_days < 0:
            errors.append(f"{e.edge_id}: negative substitution time")
        if not e.provenance:
            errors.append(f"{e.edge_id}: missing provenance")
    for n in graph.nodes.values():
        for s in n.snapshots:
            if s.valid_to is not None and s.valid_to <= s.valid_from:
                errors.append(f"{n.node_id}: invalid snapshot interval")
            if s.capacity_nameplate is not None and s.capacity_nameplate < 0:
                errors.append(f"{n.node_id}: negative nameplate capacity")
            if s.capacity_usable is not None and s.capacity_usable < 0:
                errors.append(f"{n.node_id}: negative usable capacity")
            if s.capacity_nameplate is not None and s.capacity_usable is not None and s.capacity_usable > s.capacity_nameplate:
                errors.append(f"{n.node_id}: usable capacity exceeds nameplate")
    return errors
