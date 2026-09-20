"""Benchmark and correctness validation for Dijkstra versus A*."""

import math
import os
import time
from typing import Dict, Iterable, List, Optional, Tuple

from astar import astar_search
from campus_graph import CampusGraph
from dijkstra import dijkstra_search

RouteRequest = Tuple[str, str]


def _timed_search(search, graph: CampusGraph, source: str, target: str,
                  congestion_model=None, time_profile: str = "off_peak") -> Dict:
    started = time.perf_counter_ns()
    result = search(graph, source, target, congestion_model, time_profile)
    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
    return {
        "path": result.path,
        "distance": result.distance,
        "nodes_expanded": result.nodes_expanded,
        "execution_time_ms": elapsed_ms,
    }


def benchmark_routes(graph: CampusGraph, routes: Iterable[RouteRequest],
                     congestion_model=None, time_profile: str = "off_peak") -> List[Dict]:
    """Benchmark both algorithms for identical route requests and conditions."""
    benchmark = []
    for source, target in routes:
        benchmark.append({
            "start": source,
            "destination": target,
            "results": {
                "dijkstra": _timed_search(
                    dijkstra_search, graph, source, target,
                    congestion_model, time_profile
                ),
                "astar": _timed_search(
                    astar_search, graph, source, target,
                    congestion_model, time_profile
                ),
            },
        })
    return benchmark


def validate_routes(graph: CampusGraph, routes: Iterable[RouteRequest],
                    congestion_model=None, time_profile: str = "off_peak",
                    tolerance: float = 1e-9) -> List[Dict]:
    """Run and validate both algorithms, raising a diagnostic on mismatch."""
    results = benchmark_routes(graph, routes, congestion_model, time_profile)
    for record in results:
        dijkstra_result = record["results"]["dijkstra"]
        astar_result = record["results"]["astar"]
        source = record["start"]
        target = record["destination"]

        if dijkstra_result["path"] is None or astar_result["path"] is None:
            raise AssertionError(
                f"Unreachable validation route {source} -> {target}: "
                f"Dijkstra={dijkstra_result['path']}, A*={astar_result['path']}"
            )
        if not math.isclose(
            dijkstra_result["distance"], astar_result["distance"],
            rel_tol=tolerance, abs_tol=tolerance
        ):
            raise AssertionError(
                f"Cost mismatch for {source} -> {target}: "
                f"Dijkstra={dijkstra_result['distance']}, "
                f"A*={astar_result['distance']}"
            )
        if dijkstra_result["path"][-1] != target or astar_result["path"][-1] != target:
            raise AssertionError(
                f"Destination not reached for {source} -> {target}: "
                f"Dijkstra={dijkstra_result['path']}, A*={astar_result['path']}"
            )
        if dijkstra_result["path"] != astar_result["path"]:
            raise AssertionError(
                f"Path mismatch for {source} -> {target}: "
                f"Dijkstra={dijkstra_result['path']}, A*={astar_result['path']}"
            )
    return results


if __name__ == "__main__":
    package_dir = os.path.dirname(__file__)
    graph = CampusGraph(os.path.join(package_dir, "data", "campus_data.json"))
    representative_routes = [
        ("MAIN_GATE", "QUEEN_IDIA"),
        ("MELLANBY", "FAC_TECH"),
        ("KUTI", "STADIUM"),
        ("FAC_DENTISTRY", "BOTANICAL"),
    ]
    benchmark = validate_routes(graph, representative_routes)
    for route in benchmark:
        print(f"\n{route['start']} -> {route['destination']}")
        for algorithm, result in route["results"].items():
            print(
                f"  {algorithm:8s}: {result['distance']:.3f} m, "
                f"{result['nodes_expanded']} expanded, "
                f"{result['execution_time_ms']:.3f} ms"
            )