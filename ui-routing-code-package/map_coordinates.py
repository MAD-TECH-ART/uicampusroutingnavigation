"""Map-coordinate adapter for the campus graph.

The routing graph stores deterministic relative planar coordinates in metres.
This module is the only place where those coordinates are adapted for the map
renderer. They are development coordinates, not surveyed University of Ibadan
GPS positions.
"""

import json
import os
from typing import Dict, Optional

from campus_graph import CampusGraph


REAL_COORDINATE_SOURCE = "real_geographic"
TEMPORARY_COORDINATE_SOURCE = "temporary_development_relative_planar"
MIXED_COORDINATE_SOURCE = "mixed"
COORDINATE_SOURCE = TEMPORARY_COORDINATE_SOURCE
REAL_COORDINATE_DATASET_PATH = os.path.join(
    os.path.dirname(__file__), "data", "campus_coordinates.json"
)


def get_node_map_coordinate(graph: CampusGraph, node_id: str) -> Dict[str, float]:
    """Resolve one node to geographic-shaped map coordinates.

    Real coordinates win when both are present. Otherwise the deterministic
    relative x/y values are adapted for the existing Leaflet CRS.Simple map.
    """
    node = graph.nodes[node_id]
    if node.latitude is not None and node.longitude is not None:
        return {"lat": node.latitude, "lng": node.longitude}
    return {"lat": node.y, "lng": node.x}


def get_coordinate_metadata(graph: CampusGraph) -> Dict:
    """Describe whether resolved campus coordinates are real or temporary."""
    real_node_ids = [
        node_id for node_id, node in graph.nodes.items()
        if node.latitude is not None and node.longitude is not None
    ]
    temporary_node_ids = [
        node_id for node_id in graph.nodes if node_id not in real_node_ids
    ]
    if not temporary_node_ids:
        source = REAL_COORDINATE_SOURCE
        label = "GPS coordinates"
    elif not real_node_ids:
        source = TEMPORARY_COORDINATE_SOURCE
        label = "temporary development coordinates"
    else:
        source = MIXED_COORDINATE_SOURCE
        label = "temporary development coordinates (real data incomplete)"
    return {
        "source": source,
        "label": label,
        "is_real": source == REAL_COORDINATE_SOURCE,
        "map_source": TEMPORARY_COORDINATE_SOURCE if source == MIXED_COORDINATE_SOURCE else source,
        "real_node_ids": real_node_ids,
        "temporary_node_ids": temporary_node_ids,
    }


def load_real_coordinate_dataset(path: str = REAL_COORDINATE_DATASET_PATH) -> Dict:
    """Load the separate reviewed coordinate dataset without changing graph data."""
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def get_real_map_coordinates(
    graph: CampusGraph, dataset: Optional[Dict] = None
) -> Dict[str, Dict[str, float]]:
    """Resolve dataset coordinates for nodes with complete real pairs only."""
    dataset = dataset or load_real_coordinate_dataset()
    records = dataset.get("nodes", {})
    return {
        node_id: {"lat": record["latitude"], "lng": record["longitude"]}
        for node_id, record in records.items()
        if node_id in graph.nodes
        and record.get("latitude") is not None
        and record.get("longitude") is not None
            and record.get("verified") is True
    }


def get_map_coordinates(graph: CampusGraph) -> Dict[str, Dict[str, float]]:
    """Return Leaflet-compatible coordinates without changing the graph.

    Leaflet's ``CRS.Simple`` uses ``lat``/``lng`` as abstract map axes here.
    Replace this function with a loader for surveyed geographic coordinates
    when the real campus dataset is available; callers do not need to change.
    """
    return {
        node_id: get_node_map_coordinate(graph, node_id)
        for node_id in graph.nodes
    }
