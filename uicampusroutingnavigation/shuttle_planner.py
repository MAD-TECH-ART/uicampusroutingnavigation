"""
shuttle_planner.py
-------------------
Multi-stop shuttle route planning.

A single campus shuttle bus must start at a depot (e.g. Main Gate), visit a
set of requested stops (halls / faculties), and return to the depot,
covering the shortest possible total distance. This is a small instance of
the Travelling Salesman Problem (TSP), which is NP-hard in general.

For a class-project scale (campus has a few dozen key stops), we use:
    1. A Nearest-Neighbour construction heuristic (fast, greedy).
    2. A 2-opt local search improvement pass (removes route crossings).

Distances between stops use Dijkstra shortest-path distances on the road
graph (not straight-line distance), so the route respects actual roads.
"""

from typing import List, Tuple, Dict
from campus_graph import CampusGraph
from dijkstra import dijkstra


def build_distance_matrix(graph: CampusGraph, stops: List[str],
                           congestion_model=None, time_profile: str = "off_peak") -> Dict[Tuple[str, str], float]:
    """Precompute shortest-path distance between every pair of stops.
    Pass a congestion_model to plan around current/time-of-day conditions
    instead of static base distances."""
    matrix = {}
    for i, a in enumerate(stops):
        for b in stops[i + 1:]:
            _, dist = dijkstra(graph, a, b, congestion_model=congestion_model, time_profile=time_profile)
            matrix[(a, b)] = dist
            matrix[(b, a)] = dist
    return matrix


def route_length(route: List[str], matrix: Dict[Tuple[str, str], float]) -> float:
    return sum(matrix[(route[i], route[i + 1])] for i in range(len(route) - 1))


def nearest_neighbor_route(depot: str, stops: List[str], matrix: Dict[Tuple[str, str], float]) -> List[str]:
    """Greedy construction: always go to the closest unvisited stop next."""
    unvisited = set(stops)
    route = [depot]
    current = depot

    while unvisited:
        next_stop = min(unvisited, key=lambda s: matrix[(current, s)])
        route.append(next_stop)
        unvisited.remove(next_stop)
        current = next_stop

    route.append(depot)  # return to depot
    return route


def two_opt(route: List[str], matrix: Dict[Tuple[str, str], float]) -> List[str]:
    """Improve a route by reversing segments that remove path crossings."""
    best = route[:]
    improved = True

    while improved:
        improved = False
        for i in range(1, len(best) - 2):
            for j in range(i + 1, len(best) - 1):
                if j - i == 1:
                    continue
                new_route = best[:i] + best[i:j][::-1] + best[j:]
                if route_length(new_route, matrix) < route_length(best, matrix):
                    best = new_route
                    improved = True
    return best


def plan_shuttle_route(graph: CampusGraph, depot: str, stops: List[str],
                        congestion_model=None, time_profile: str = "off_peak"):
    """
    Full pipeline: build distance matrix -> nearest-neighbour -> 2-opt.
    Returns the optimized stop order and total distance. Pass a
    congestion_model + time_profile to plan around current conditions
    instead of static distances (see live_conditions.py).
    """
    all_points = [depot] + stops
    matrix = build_distance_matrix(graph, all_points, congestion_model, time_profile)

    initial = nearest_neighbor_route(depot, stops, matrix)
    optimized = two_opt(initial, matrix)

    return {
        "initial_route": initial,
        "initial_distance": route_length(initial, matrix),
        "optimized_route": optimized,
        "optimized_distance": route_length(optimized, matrix),
    }


if __name__ == "__main__":
    g = CampusGraph()

    depot = "MAIN_GATE"
    # A morning shuttle run picking up students from halls spread across the
    # now-45-location campus, heading toward the medical/faculty cluster.
    stops = ["MELLANBY", "KUTI", "SULTAN_BELLO", "QUEEN_IDIA", "AWOLOWO_PG", "FAC_TECH", "ALEX_BROWN"]

    result = plan_shuttle_route(g, depot, stops)

    def names(route):
        return " -> ".join(g.nodes[n].name for n in route)

    print("=== Shuttle Route Planning (static / off-peak distances) ===")
    print(f"Depot: {g.nodes[depot].name}")
    print(f"Stops requested: {[g.nodes[s].name for s in stops]}\n")

    print("Initial (Nearest-Neighbour) route:")
    print(f"  {names(result['initial_route'])}")
    print(f"  Total distance: {result['initial_distance']:.0f} m\n")

    print("Optimized (2-opt) route:")
    print(f"  {names(result['optimized_route'])}")
    print(f"  Total distance: {result['optimized_distance']:.0f} m\n")

    saved = result["initial_distance"] - result["optimized_distance"]
    pct = (saved / result["initial_distance"]) * 100 if result["initial_distance"] else 0
    print(f"Improvement: {saved:.0f} m saved ({pct:.1f}% reduction)")

    print("\n=== Same shuttle run planned for class-change hour conditions ===")
    from live_conditions import CongestionModel
    model = CongestionModel()
    result_peak = plan_shuttle_route(g, depot, stops, congestion_model=model, time_profile="class_change")
    print(f"  Optimized route: {names(result_peak['optimized_route'])}")
    print(f"  Total effective distance: {result_peak['optimized_distance']:.0f} (vs {result['optimized_distance']:.0f} off-peak)")
