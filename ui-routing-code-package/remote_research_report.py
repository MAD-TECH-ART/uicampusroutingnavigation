"""Human-readable report for cached remote coordinate research."""

import os

from coordinate_validation import DEFAULT_COORDINATE_PATH, load_coordinate_dataset
from campus_graph import CampusGraph
from remote_coordinate_research import DATA_PATH, load_cache


def build_report(graph, cache):
    queries = cache.get("queries", {})
    candidates = []
    for node_id, entry in queries.items():
        for result in entry.get("results", []):
            candidates.append((node_id, result))
    unresolved = [node_id for node_id in graph.nodes if node_id not in queries or not queries[node_id].get("results")]
    in_bounds = [result for _, result in candidates if result.get("within_review_bounds")]
    context_matches = [result for _, result in candidates if result.get("campus_context_match")]
    coordinate_dataset = load_coordinate_dataset(DEFAULT_COORDINATE_PATH)
    approved = [
        node_id for node_id, record in coordinate_dataset.get("nodes", {}).items()
        if isinstance(record, dict) and record.get("verified")
    ]
    geographic_unresolved = [
        node_id for node_id, record in coordinate_dataset.get("nodes", {}).items()
        if isinstance(record, dict)
        and (record.get("latitude") is None or record.get("longitude") is None)
    ]
    lines = [
        "Remote Coordinate Research Report",
        "=================================",
        "",
        f"Total nodes: {len(graph.nodes)}",
        f"Research attempted: {len(queries)}",
        f"Candidates found: {len(candidates)}",
        f"Verified in geographic dataset: {len(approved)}",
        f"Unresolved in geographic dataset: {len(geographic_unresolved)}",
        f"Within review bounds: {len(in_bounds)}",
        f"University of Ibadan context matches: {len(context_matches)}",
        f"Unresolved research-cache entries: {len(unresolved)}",
        "",
        "Candidates",
        "----------",
    ]
    for node_id, result in candidates:
        lines.append(
            f"{node_id} | {graph.nodes[node_id].name} | "
            f"{result['latitude']}, {result['longitude']} | "
            f"{result.get('confidence', 'unassigned')} | candidate | {result['source_url']}"
        )
    lines.extend(["", "Unresolved nodes", "----------------"])
    for node_id in unresolved:
        entry = queries.get(node_id, {})
        reason = entry.get("status", "not_researched")
        lines.append(f"{node_id} | {graph.nodes[node_id].name} | {reason}")
    return "\n".join(lines) + "\n"


def main():
    graph = CampusGraph(DATA_PATH)
    print(build_report(graph, load_cache()), end="")


if __name__ == "__main__":
    main()
