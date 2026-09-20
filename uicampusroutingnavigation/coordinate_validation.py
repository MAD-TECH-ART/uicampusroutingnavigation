"""Validation and consistency reporting for reviewed geographic coordinates."""

import json
import math
import os
from typing import Dict, Optional

from campus_graph import CampusGraph

DEFAULT_COORDINATE_PATH = os.path.join(
    os.path.dirname(__file__), "data", "campus_coordinates.json"
)
DEFAULT_CAMPUS_REVIEW_BOUNDS = {
    "min_lat": 7.4377245,
    "max_lat": 7.4585,
    "min_lng": 3.8867116,
    "max_lng": 3.9067116,
}


def load_coordinate_dataset(path: str = DEFAULT_COORDINATE_PATH) -> Dict:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def validate_coordinate_dataset(
    graph: CampusGraph, dataset: Dict, campus_bounds: Optional[Dict[str, float]] = None
) -> Dict:
    campus_bounds = campus_bounds or DEFAULT_CAMPUS_REVIEW_BOUNDS
    errors = []
    warnings = []
    nodes = dataset.get("nodes") if isinstance(dataset, dict) else None
    metadata = dataset.get("metadata") if isinstance(dataset, dict) else None
    if not isinstance(nodes, dict):
        return {"valid": False, "errors": ["Dataset must contain a nodes object."], "warnings": []}
    if not isinstance(metadata, dict) or metadata.get("coordinate_system") != "WGS84":
        errors.append("Dataset metadata.coordinate_system must be WGS84.")

    expected = set(graph.nodes)
    actual = set(nodes)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing:
        errors.append(f"Missing node IDs: {', '.join(missing)}")
    if unknown:
        errors.append(f"Unknown node IDs: {', '.join(unknown)}")

    complete = {}
    for node_id, record in nodes.items():
        if not isinstance(record, dict):
            errors.append(f"{node_id}: record must be an object.")
            continue
        latitude = record.get("latitude")
        longitude = record.get("longitude")
        if latitude is None and longitude is None:
            continue
        if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
            errors.append(f"{node_id}: latitude and longitude must both be numeric or null.")
            continue
        if not math.isfinite(latitude) or not math.isfinite(longitude):
            errors.append(f"{node_id}: coordinates must be finite.")
            continue
        if not -90 <= latitude <= 90:
            errors.append(f"{node_id}: latitude is outside -90..90.")
        if not -180 <= longitude <= 180:
            errors.append(f"{node_id}: longitude is outside -180..180.")
        if not record.get("source") or not record.get("source_type"):
            errors.append(f"{node_id}: coordinate provenance is required.")
        if record.get("confidence") not in {"low", "medium", "high"}:
            errors.append(f"{node_id}: confidence must be low, medium, high, or null.")
        complete[node_id] = (latitude, longitude)

    duplicate_coordinates = {}
    for node_id, coordinate in complete.items():
        duplicate_coordinates.setdefault(coordinate, []).append(node_id)
    for coordinate, node_ids in duplicate_coordinates.items():
        if len(node_ids) > 1:
            warnings.append(f"Duplicate coordinate {coordinate} used by: {', '.join(sorted(node_ids))}")

    if campus_bounds:
        for node_id, (latitude, longitude) in complete.items():
            if not (
                campus_bounds["min_lat"] <= latitude <= campus_bounds["max_lat"]
                and campus_bounds["min_lng"] <= longitude <= campus_bounds["max_lng"]
            ):
                warnings.append(f"{node_id}: coordinate is outside the configured campus review bounds.")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "expected_nodes": len(expected),
        "coordinate_records": len(actual),
        "complete_nodes": len(complete),
        "missing_nodes": len(expected - set(complete)),
        "reviewed_nodes": sum(bool(nodes[node_id].get("verified")) for node_id in nodes if isinstance(nodes[node_id], dict)),
        "high_confidence": sum(nodes[node_id].get("confidence") == "high" for node_id in nodes if isinstance(nodes[node_id], dict)),
    }


def haversine_meters(first: Dict[str, float], second: Dict[str, float]) -> float:
    radius = 6_371_000
    lat1, lon1 = math.radians(first["latitude"]), math.radians(first["longitude"])
    lat2, lon2 = math.radians(second["latitude"]), math.radians(second["longitude"])
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1
    value = math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(value))


def graph_geographic_report(graph: CampusGraph, dataset: Dict) -> Dict:
    nodes = dataset.get("nodes", {})
    distances = []
    missing_edges = []
    for source, neighbors in graph.adjacency.items():
        for destination, graph_weight in neighbors:
            if source >= destination:
                continue
            first, second = nodes.get(source, {}), nodes.get(destination, {})
            if first.get("latitude") is None or second.get("latitude") is None:
                missing_edges.append({"from": source, "to": destination})
                continue
            distance = haversine_meters(first, second)
            distances.append({
                "from": source,
                "to": destination,
                "geographic_distance_m": distance,
                "existing_graph_weight": graph_weight,
                "ratio_to_graph_weight": distance / graph_weight if graph_weight else None,
            })
    return {"checked_edges": len(distances), "missing_coordinate_edges": missing_edges, "edges": distances}
