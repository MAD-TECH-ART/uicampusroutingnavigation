"""
campus_graph.py
----------------
Data model for the University of Ibadan Campus Transportation Routing System.

The campus is represented as a weighted, undirected graph:
    - Nodes  -> key campus locations (halls of residence, faculties, institutes, landmarks)
    - Edges  -> walkable/driveable road segments, weighted by distance (metres)

Location and road data are NOT hardcoded in this file. They are loaded from
data/campus_data.json, so the network can be extended (new buildings, new
roads, corrected coordinates) by editing that file alone — no code changes
or redeployment needed. This addresses the earlier prototype's limitation
of a fixed, code-embedded set of 22 locations: the current dataset covers
45 locations spanning all 17 University of Ibadan faculties, several
institutes, halls of residence, and campus landmarks.

Coordinates are simplified planar (x, y) positions in metres, laid out to
reflect the real relative arrangement of locations on the University of
Ibadan main campus. They are approximations for demonstration purposes,
not surveyed GPS data (see Section 6 of the report / README for how to
replace them with real survey data).
"""

import json
import math
import os
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

DEFAULT_DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "campus_data.json")


@dataclass
class Node:
    id: str
    name: str
    category: str  # 'hall', 'faculty', 'institute', 'landmark', 'gate'
    x: float
    y: float
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class CampusGraph:
    """A weighted undirected graph representing the UI campus road network.

    By default, loads its location/road data from an external JSON file
    (data/campus_data.json) rather than from hardcoded values in this
    module. Pass a different `data_path` to load an alternative dataset
    (e.g. a partial map, or one with real surveyed coordinates), or call
    add_node/add_edge directly to build a graph programmatically.
    """

    def __init__(self, data_path: Optional[str] = None):
        self.nodes: Dict[str, Node] = {}
        self.adjacency: Dict[str, List[Tuple[str, float]]] = {}
        self.source_path = data_path or DEFAULT_DATA_PATH
        if os.path.exists(self.source_path):
            self._load_from_json(self.source_path)

    # ------------------------------------------------------------------ #
    # Graph construction
    # ------------------------------------------------------------------ #
    def add_node(self, node_id: str, name: str, category: str, x: float, y: float,
                 latitude: Optional[float] = None, longitude: Optional[float] = None):
        self._validate_geographic_coordinates(latitude, longitude)
        self.nodes[node_id] = Node(
            node_id, name, category, x, y, latitude, longitude
        )
        self.adjacency.setdefault(node_id, [])

    @staticmethod
    def _validate_geographic_coordinates(latitude, longitude):
        if (latitude is None) != (longitude is None):
            raise ValueError("latitude and longitude must be provided together")
        if latitude is None:
            return
        if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
            raise ValueError("latitude and longitude must be numeric")
        if not math.isfinite(latitude) or not math.isfinite(longitude):
            raise ValueError("latitude and longitude must be finite")
        if not -90 <= latitude <= 90:
            raise ValueError("latitude must be between -90 and 90")
        if not -180 <= longitude <= 180:
            raise ValueError("longitude must be between -180 and 180")

    def add_edge(self, a: str, b: str, weight: float = None):
        """Add an undirected edge. If weight is None, compute Euclidean distance."""
        if weight is None:
            weight = self._euclidean(a, b)
        self.adjacency[a].append((b, weight))
        self.adjacency[b].append((a, weight))

    def _euclidean(self, a: str, b: str) -> float:
        na, nb = self.nodes[a], self.nodes[b]
        return math.hypot(na.x - nb.x, na.y - nb.y)

    def neighbors(self, node_id: str):
        return self.adjacency.get(node_id, [])

    def all_node_ids(self):
        return list(self.nodes.keys())

    def find_by_name(self, partial_name: str) -> Optional[str]:
        """Look up a node id by a case-insensitive partial name match. Useful
        when integrating with external systems that refer to locations by
        name rather than by internal id."""
        needle = partial_name.strip().lower()
        for nid, node in self.nodes.items():
            if needle in node.name.lower():
                return nid
        return None

    # ------------------------------------------------------------------ #
    # Data loading
    # ------------------------------------------------------------------ #
    def _load_from_json(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for n in data["nodes"]:
            self.add_node(
                n["id"], n["name"], n["category"], n["x"], n["y"],
                n.get("latitude"), n.get("longitude")
            )
        for edge in data["edges"]:
            a, b = edge[0], edge[1]
            weight = edge[2] if len(edge) > 2 else None
            self.add_edge(a, b, weight)

    def reload(self):
        """Re-read the source JSON file. Call this after editing
        campus_data.json (e.g. adding a new building) to pick up changes
        without restarting the application — a step toward the system
        being updatable from a live facilities database rather than a
        static file."""
        self.nodes.clear()
        self.adjacency.clear()
        if os.path.exists(self.source_path):
            self._load_from_json(self.source_path)

    def summary(self):
        by_category = {}
        for n in self.nodes.values():
            by_category[n.category] = by_category.get(n.category, 0) + 1
        print(f"Campus graph: {len(self.nodes)} nodes, "
              f"{sum(len(v) for v in self.adjacency.values()) // 2} edges")
        for cat, count in sorted(by_category.items()):
            print(f"  {cat:10s}: {count}")

    def validate_graph(self):
        """Return a structured integrity report for the campus network."""
        issues = []
        warnings = []
        nodes = list(self.nodes)

        for node_id in nodes:
            degree = len(self.adjacency.get(node_id, []))
            if degree == 0:
                warnings.append(f"Node {node_id} is isolated and has no incident edges.")
            elif degree == 1:
                warnings.append(f"Node {node_id} is weakly connected and nearly isolated in the campus network.")

        for node_id in nodes:
            for neighbor, weight in self.adjacency.get(node_id, []):
                if weight <= 0:
                    issues.append(f"Non-positive edge weight detected on {node_id} -> {neighbor}: {weight}.")
                if node_id == neighbor:
                    issues.append(f"Self-loop detected on node {node_id}.")

        unique_edges = set()
        duplicate_edges = set()
        for node_id in nodes:
            for neighbor, weight in self.adjacency.get(node_id, []):
                edge = tuple(sorted((node_id, neighbor)))
                if edge in unique_edges:
                    duplicate_edges.add(edge)
                else:
                    unique_edges.add(edge)

        for edge in sorted(duplicate_edges):
            issues.append(f"Duplicate edge detected between {edge[0]} and {edge[1]}.")

        report = {
            "valid": not issues,
            "issues": issues,
            "warnings": warnings,
            "node_count": len(nodes),
            "edge_count": sum(len(v) for v in self.adjacency.values()) // 2,
            "isolated_nodes": [n for n in nodes if not self.adjacency.get(n)],
        }
        return report


if __name__ == "__main__":
    g = CampusGraph()
    g.summary()
    for nid, node in g.nodes.items():
        print(f"{nid:16s} {node.name:45s} ({node.category})")

