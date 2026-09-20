"""Human-readable review report for the separate campus coordinate dataset."""

import os
from typing import Dict

from campus_graph import CampusGraph
from coordinate_validation import (
    DEFAULT_COORDINATE_PATH,
    graph_geographic_report,
    load_coordinate_dataset,
    validate_coordinate_dataset,
)


def build_report(graph: CampusGraph, dataset: Dict) -> str:
    validation = validate_coordinate_dataset(graph, dataset)
    geographic = graph_geographic_report(graph, dataset)
    nodes = dataset.get("nodes", {})
    verified = [node_id for node_id, record in nodes.items() if record.get("verified")]
    high = [node_id for node_id, record in nodes.items() if record.get("confidence") == "high"]
    medium = [node_id for node_id, record in nodes.items() if record.get("confidence") == "medium"]
    low = [node_id for node_id, record in nodes.items() if record.get("confidence") == "low"]
    missing = [
        node_id for node_id, record in nodes.items()
        if record.get("latitude") is None or record.get("longitude") is None
    ]

    lines = [
        "Coordinate Review Report",
        "========================",
        "",
        f"Total nodes: {len(graph.nodes)}",
        f"Populated coordinates: {validation['complete_nodes']}",
        f"Verified: {len(verified)}",
        f"High confidence: {len(high)}",
        f"Medium confidence: {len(medium)}",
        f"Low confidence: {len(low)}",
        f"Needs review: {len(missing) + len(validation['warnings'])}",
        f"Missing: {len(missing)}",
        f"Duplicate coordinate warnings: {sum('Duplicate coordinate' in warning for warning in validation['warnings'])}",
        f"Out-of-bounds warnings: {sum('outside the configured campus review bounds' in warning for warning in validation['warnings'])}",
        f"Geographic edges checked: {geographic['checked_edges']}",
        f"Edges awaiting coordinates: {len(geographic['missing_coordinate_edges'])}",
        "",
        "Unresolved nodes",
        "----------------",
    ]
    if missing:
        for node_id in missing:
            node = graph.nodes[node_id]
            lines.append(f"{node_id} | {node.name} | {node.category} | missing | needs_review")
    else:
        lines.append("None")

    if validation["errors"]:
        lines.extend(["", "Validation errors", "-----------------"])
        lines.extend(validation["errors"])
    if validation["warnings"]:
        lines.extend(["", "Validation warnings", "-------------------"])
        lines.extend(validation["warnings"])
    return "\n".join(lines) + "\n"


def main():
    package_dir = os.path.dirname(__file__)
    graph = CampusGraph(os.path.join(package_dir, "data", "campus_data.json"))
    dataset = load_coordinate_dataset(DEFAULT_COORDINATE_PATH)
    print(build_report(graph, dataset), end="")


if __name__ == "__main__":
    main()
