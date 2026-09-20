"""
dijkstra.py
-----------
Shortest-path routing for a single student/staff journey between two
campus locations, implemented from scratch using a binary heap (priority
queue) for O((V + E) log V) performance.

Supports an optional CongestionModel + time_profile so routing reflects
current conditions rather than a single static precomputed distance (see
live_conditions.py). When no model is supplied, behaviour is unchanged:
plain static base-distance shortest path.
"""

import heapq
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from campus_graph import CampusGraph


@dataclass
class SearchResult:
    """Detailed result from a shortest-path search."""

    path: Optional[List[str]]
    distance: float
    nodes_expanded: int


def effective_edge_weight(graph: CampusGraph, a: str, b: str, base_weight: float,
                          congestion_model=None, time_profile: str = "off_peak") -> Optional[float]:
    """Return the edge cost used by both Dijkstra and A*.

    Keeping this decision in one place ensures dynamic conditions and
    time-of-day profiles affect both algorithms identically.
    """
    if congestion_model is None:
        return base_weight
    return congestion_model.effective_weight(a, b, base_weight, time_profile)


def reconstruct_path(previous: Dict[str, Optional[str]], target: str) -> List[str]:
    path = []
    node = target
    while node is not None:
        path.append(node)
        node = previous[node]
    path.reverse()
    return path


def dijkstra_search(graph: CampusGraph, source: str, target: str,
                    congestion_model=None, time_profile: str = "off_peak") -> SearchResult:
    """
    Compute the shortest (or currently fastest, if a congestion_model is
    given) path between `source` and `target`.

    Args:
        congestion_model: an optional live_conditions.CongestionModel. When
            provided, edge weights are adjusted for the given time_profile
            and any active live-reported conditions; edges reported fully
            closed are skipped entirely.
        time_profile: one of live_conditions.TIME_PROFILES (ignored if no
            congestion_model is given).

    Returns a SearchResult. Dijkstra uses O((V + E) log V) time and O(V)
    space with the binary heap below.
    """
    if source not in graph.nodes or target not in graph.nodes:
        raise ValueError("Source or target node does not exist in the graph.")

    distances: Dict[str, float] = {nid: float("inf") for nid in graph.all_node_ids()}
    previous: Dict[str, Optional[str]] = {nid: None for nid in graph.all_node_ids()}
    distances[source] = 0.0

    visited = set()
    pq: List[Tuple[float, str]] = [(0.0, source)]

    while pq:
        current_dist, current = heapq.heappop(pq)

        if current in visited:
            continue
        visited.add(current)

        if current == target:
            break

        for neighbor, base_weight in graph.neighbors(current):
            if neighbor in visited:
                continue

            weight = effective_edge_weight(
                graph, current, neighbor, base_weight, congestion_model, time_profile
            )
            if weight is None:
                continue  # edge currently closed/impassable

            new_dist = current_dist + weight
            if new_dist < distances[neighbor]:
                distances[neighbor] = new_dist
                previous[neighbor] = current
                heapq.heappush(pq, (new_dist, neighbor))

    if distances[target] == float("inf"):
        return SearchResult(None, float("inf"), len(visited))

    return SearchResult(reconstruct_path(previous, target), distances[target], len(visited))


def dijkstra(graph: CampusGraph, source: str, target: str,
             congestion_model=None, time_profile: str = "off_peak") -> Tuple[Optional[List[str]], float]:
    """Preserve the original Dijkstra return format: ``(path, distance)``."""
    result = dijkstra_search(graph, source, target, congestion_model, time_profile)
    return result.path, result.distance


def path_to_names(graph: CampusGraph, path: List[str]) -> List[str]:
    return [graph.nodes[n].name for n in path]


if __name__ == "__main__":
    g = CampusGraph()

    tests = [
        ("MAIN_GATE", "QUEEN_IDIA"),
        ("MELLANBY", "FAC_TECH"),
        ("KUTI", "STADIUM"),
    ]

    AVG_WALK_SPEED_M_PER_MIN = 80  # ~4.8 km/h average walking speed

    print("=== Static (off-peak) routing, 45-location campus ===")
    for src, dst in tests:
        path, dist = dijkstra(g, src, dst)
        names = path_to_names(g, path)
        eta = dist / AVG_WALK_SPEED_M_PER_MIN
        print(f"\n{g.nodes[src].name} -> {g.nodes[dst].name}")
        print(f"  Route: {' -> '.join(names)}")
        print(f"  Distance: {dist:.0f} m | Est. walking time: {eta:.1f} min")

    print("\n=== Same trip under different live/time conditions ===")
    from live_conditions import CongestionModel
    model = CongestionModel()
    src, dst = "MAIN_GATE", "QUEEN_IDIA"
    for profile in ["off_peak", "class_change", "meal_time", "night"]:
        path, dist = dijkstra(g, src, dst, congestion_model=model, time_profile=profile)
        print(f"  {profile:14s}: {dist:.0f} effective-m via {len(path)} nodes")

    print("\n  With a simulated live obstruction reported on the route:")
    model.report_condition("SUB", "LIBRARY", multiplier=0.0, reason="path flooded")
    path, dist = dijkstra(g, src, dst, congestion_model=model, time_profile="off_peak")
    names = path_to_names(g, path)
    print(f"  Rerouted: {' -> '.join(names)} ({dist:.0f} effective-m)")
