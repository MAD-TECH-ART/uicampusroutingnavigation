"""Application service for exposing the existing routing engine."""

import math
import os
from typing import Dict, Optional

from astar import astar_search
from campus_graph import CampusGraph
from dijkstra import dijkstra_search
from live_conditions import TIME_PROFILES
from map_coordinates import get_coordinate_metadata, get_map_coordinates


SUPPORTED_ALGORITHMS = {"dijkstra", "astar"}
SUPPORTED_ROUTE_PREFERENCES = {"shortest_distance", "fewest_stops", "accessible"}


class RoutingService:
    """Coordinate validation, routing invocation, and API-ready formatting."""

    def __init__(self, graph: Optional[CampusGraph] = None):
        data_path = os.path.join(os.path.dirname(__file__), "data", "campus_data.json")
        self.graph = graph or CampusGraph(data_path)
        self.map_coordinates = get_map_coordinates(self.graph)
        self.coordinate_metadata = get_coordinate_metadata(self.graph)

    def _fewest_stops_route(self, start: str, destination: str):
        if start == destination:
            return [start], 0.0

        queue = [start]
        previous = {start: None}
        while queue:
            current = queue.pop(0)
            if current == destination:
                break
            for neighbor, _weight in self.graph.neighbors(current):
                if neighbor in previous:
                    continue
                previous[neighbor] = current
                queue.append(neighbor)

        if destination not in previous:
            raise LookupError(f"No route found from {start} to {destination}")

        path = []
        node = destination
        while node is not None:
            path.append(node)
            node = previous[node]
        path.reverse()
        total_distance = sum(
            self._edge_distance(path[i], path[i + 1]) for i in range(len(path) - 1)
        )
        return path, total_distance

    def _accessible_route(self, start: str, destination: str):
        """Prefer a simpler path with fewer turns and easier movement for accessibility."""
        path, total_distance = self._fewest_stops_route(start, destination)
        if len(path) <= 2:
            return path, total_distance

        filtered = [path[0]]
        for node in path[1:-1]:
            prev = filtered[-1]
            next_node = self._next_node_on_path(path, node)
            if next_node is None:
                continue
            if self._looks_like_simple_segment(prev, node, next_node):
                filtered.append(node)
        filtered.append(path[-1])
        if filtered[0] != start:
            filtered.insert(0, start)
        if filtered[-1] != destination:
            filtered.append(destination)

        total_distance = sum(
            self._edge_distance(filtered[i], filtered[i + 1]) for i in range(len(filtered) - 1)
        )
        return filtered, total_distance

    def _next_node_on_path(self, path, current):
        for idx, node in enumerate(path):
            if node == current and idx + 1 < len(path):
                return path[idx + 1]
        return None

    def _looks_like_simple_segment(self, prev, current, nxt):
        prev_node = self.graph.nodes[prev]
        current_node = self.graph.nodes[current]
        next_node = self.graph.nodes[nxt]
        dx1 = current_node.x - prev_node.x
        dy1 = current_node.y - prev_node.y
        dx2 = next_node.x - current_node.x
        dy2 = next_node.y - current_node.y
        if dx1 == 0 and dy1 == 0:
            return True
        if dx2 == 0 and dy2 == 0:
            return True
        angle = abs(math.degrees(math.atan2(dx1 * dy2 - dy1 * dx2, dx1 * dx2 + dy1 * dy2)))
        return angle <= 60

    def calculate_route(
        self,
        start: str,
        destination: str,
        algorithm: str = "dijkstra",
        time_profile: str = "off_peak",
        congestion_model=None,
        route_preference: str = "shortest_distance",
    ) -> Dict:
        if start not in self.graph.nodes:
            raise ValueError(f"Unknown start node: {start}")
        if destination not in self.graph.nodes:
            raise ValueError(f"Unknown destination node: {destination}")
        if algorithm not in SUPPORTED_ALGORITHMS:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        if time_profile not in TIME_PROFILES:
            raise ValueError(f"Unsupported time profile: {time_profile}")
        if route_preference not in SUPPORTED_ROUTE_PREFERENCES:
            raise ValueError(f"Unsupported route preference: {route_preference}")

        if route_preference == "fewest_stops":
            path, total_distance = self._fewest_stops_route(start, destination)
        elif route_preference == "accessible":
            path, total_distance = self._accessible_route(start, destination)
        else:
            search = astar_search if algorithm == "astar" else dijkstra_search
            result = search(
                self.graph,
                start,
                destination,
                congestion_model=congestion_model,
                time_profile=time_profile,
            )
            if result.path is None:
                raise LookupError(f"No route found from {start} to {destination}")
            path = result.path
            total_distance = float(result.distance)

        total_steps = max(len(path) - 1, 0)
        return {
            "start": self._location(start),
            "destination": self._location(destination),
            "algorithm": algorithm,
            "time_profile": time_profile,
            "route_preference": route_preference,
            "path": path,
            "path_names": [self.graph.nodes[node_id].name for node_id in path],
            "distance": total_distance,
            "total_distance_meters": round(total_distance, 1),
            "total_steps": total_steps,
            "route_cost": total_distance,
            "estimated_walking_time_minutes": total_distance / 80,
            "summary": self._route_summary(start, destination, path, total_distance, route_preference),
            "nodes_expanded": max(len(path), 0),
            "coordinates": [self.map_coordinates[node_id] for node_id in path],
            "coordinate_source": self.coordinate_metadata["source"],
            "coordinate_status": self.coordinate_metadata["label"],
            "directions": self._directions(path),
        }

    def _location(self, node_id: str) -> Dict[str, str]:
        node = self.graph.nodes[node_id]
        return {"id": node.id, "name": node.name, "category": node.category}

    def _route_summary(self, start: str, destination: str, path, total_distance: float, route_preference: str = "shortest_distance") -> str:
        start_name = self.graph.nodes[start].name
        destination_name = self.graph.nodes[destination].name
        legs = max(len(path) - 1, 0)
        if route_preference == "fewest_stops":
            preference_label = "fewest stops"
        elif route_preference == "accessible":
            preference_label = "accessible route"
        else:
            preference_label = "shortest distance"
        return (
            f"Route from {start} ({start_name}) to {destination} ({destination_name}) "
            f"using {preference_label}: {total_distance:.0f} meters over {legs} leg(s)."
        )

    def _edge_distance(self, source: str, target: str) -> float:
        for neighbor, weight in self.graph.adjacency.get(source, []):
            if neighbor == target:
                return float(weight)
        return float(self.graph._euclidean(source, target))

    def _directions(self, path):
        directions = []
        for index, node_id in enumerate(path):
            name = self.graph.nodes[node_id].name
            if index == 0:
                instruction = f"Start at {name}"
            elif index == len(path) - 1:
                instruction = f"Arrive at {name}"
            else:
                instruction = f"Continue to {name}"

            step_entry = {
                "step": index + 1,
                "node_id": node_id,
                "instruction": instruction,
            }
            if index < len(path) - 1:
                next_node_id = path[index + 1]
                step_entry["distance_meters"] = round(self._edge_distance(node_id, next_node_id), 1)
            directions.append(step_entry)
        return directions
