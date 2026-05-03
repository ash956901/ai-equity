"""Phase 2: multi-hop graph traversal tool over relation_edges."""

from __future__ import annotations

from collections import deque
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.tools import tool

from src.db.database import get_db
from src.db.models import RelationEdge


@tool
def traverse_graph(
    start_type: str,
    start_id: str,
    predicates: Optional[str] = None,
    depth: int = 2,
    max_results: int = 50,
) -> List[Dict[str, Any]]:
    """Multi-hop traversal of the relation_edges knowledge graph.

    Args:
        start_type: Entity type of the starting node (company, theme, policy,
            event, sector, commodity, ...).
        start_id: Entity id (UUID for company, code for theme/policy/commodity).
        predicates: Optional comma-separated predicate filter (default = all).
        depth: BFS depth, capped to 4. depth=1 returns immediate neighbours.
        max_results: Maximum nodes to return.
    """
    if depth < 1:
        depth = 1
    if depth > 4:
        depth = 4

    pred_list = (
        [p.strip() for p in predicates.split(",") if p.strip()] if predicates else None
    )

    db = next(get_db())
    try:
        visited: set[Tuple[str, str]] = {(start_type, str(start_id))}
        frontier: deque[Tuple[str, str, int, List[str]]] = deque()
        frontier.append((start_type, str(start_id), 0, []))
        results: List[Dict[str, Any]] = []

        while frontier and len(results) < max_results:
            node_type, node_id, dist, path = frontier.popleft()
            if dist >= depth:
                continue

            query = db.query(RelationEdge).filter(
                RelationEdge.subject_type == node_type,
                RelationEdge.subject_id == node_id,
            )
            if pred_list:
                query = query.filter(RelationEdge.predicate.in_(pred_list))
            edges = query.limit(max_results * 2).all()
            for edge in edges:
                key = (edge.object_type, edge.object_id)
                if key in visited:
                    continue
                visited.add(key)
                step = f"{edge.subject_type}:{edge.subject_id} -[{edge.predicate}]-> {edge.object_type}:{edge.object_id}"
                new_path = path + [step]
                results.append(
                    {
                        "depth": dist + 1,
                        "path": new_path,
                        "node_type": edge.object_type,
                        "node_id": edge.object_id,
                        "predicate": edge.predicate,
                        "weight": float(edge.weight) if edge.weight is not None else None,
                        "source": edge.source,
                    }
                )
                if dist + 1 < depth:
                    frontier.append((edge.object_type, edge.object_id, dist + 1, new_path))
                if len(results) >= max_results:
                    break
        return results
    finally:
        db.close()
