"""
astar.py
--------
A* shortest-path routing using the CampusGraph planar metre coordinates.

The implementation uses the same effective edge costs as dijkstra.py. Its
worst-case time and space complexity are O((V + E) log V) and O(V),
respectively, with a binary heap. Practical performance depends on how much
the heuristic reduces the search space; A* is not always faster than
Dijkstra.
"""

import heapq
import math
from typing import Dict, List, Optional, Tuple

from campus_graph import CampusGraph
from dijkstra import SearchResult, effective_edge_weight, reconstruct_path


def _heuristic_scale(graph: CampusGraph, congestion_model=None,
                     time_profile: str = "off_peak") -> float:
    """Find a global scale that makes coordinate distance admissible.

    For every traversable edge, effective cost must be at least the scale
    times its straight-line distance. The minimum such ratio therefore makes
    the scaled Euclidean heuristic a lower bound on every remaining route,
    including routes affected by the existing dynamic cost model.
    """
    scale = 1.0
    for a, neighbors in graph.adjacency.items():
        for b, base_weight in neighbors:
            coordinate_distance = math.hypot(
                graph.nodes[a].x - graph.nodes[b].x,
                graph.nodes[a].y - graph.nodes[b].y,
            )
            if coordinate_distance == 0:
                continue
            weight = effective_edge_weight(
                graph, a, b, base_weight, congestion_model, time_profile
            )
            if weight is not None:
                scale = min(scale, weight / coordinate_distance)
    return max(0.0, scale)


def astar_search(graph: CampusGraph, source: str, target: str,
                 congestion_model=None, time_profile: str = "off_peak") -> SearchResult:
    """Compute an optimal route and return path, cost, and expansion count.

    Invalid node IDs raise ValueError, matching Dijkstra. Unreachable targets
    return ``SearchResult(None, inf, expanded)``.
    """
    if source not in graph.nodes or target not in graph.nodes:
        raise ValueError("Source or target node does not exist in the graph.")

    heuristic_scale = _heuristic_scale(graph, congestion_model, time_profile)

    def heuristic(node_id: str) -> float:
        node = graph.nodes[node_id]
        destination = graph.nodes[target]
        return heuristic_scale * math.hypot(
            node.x - destination.x, node.y - destination.y
        )

    distances: Dict[str, float] = {nid: float("inf") for nid in graph.all_node_ids()}
    previous: Dict[str, Optional[str]] = {nid: None for nid in graph.all_node_ids()}
    distances[source] = 0.0

    expanded = set()
    pq: List[Tuple[float, float, str]] = [(heuristic(source), 0.0, source)]

    while pq:
        _priority, current_dist, current = heapq.heappop(pq)
        if current in expanded:
            continue
        expanded.add(current)

        if current == target:
            break

        for neighbor, base_weight in graph.neighbors(current):
            if neighbor in expanded:
                continue
            weight = effective_edge_weight(
                graph, current, neighbor, base_weight, congestion_model, time_profile
            )
            if weight is None:
                continue

            new_dist = current_dist + weight
            if new_dist < distances[neighbor]:
                distances[neighbor] = new_dist
                previous[neighbor] = current
                heapq.heappush(
                    pq, (new_dist + heuristic(neighbor), new_dist, neighbor)
                )

    if distances[target] == float("inf"):
        return SearchResult(None, float("inf"), len(expanded))

    return SearchResult(reconstruct_path(previous, target), distances[target], len(expanded))


def astar(graph: CampusGraph, source: str, target: str,
          congestion_model=None, time_profile: str = "off_peak") -> Tuple[Optional[List[str]], float]:
    """Return the original path/distance-shaped result used by Dijkstra."""
    result = astar_search(graph, source, target, congestion_model, time_profile)
    return result.path, result.distance
