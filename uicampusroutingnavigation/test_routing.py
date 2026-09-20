import math
import os
import unittest

from astar import astar_search
from benchmark import validate_routes
from campus_graph import CampusGraph
from dijkstra import dijkstra_search
from live_conditions import CongestionModel
from map_coordinates import (
    COORDINATE_SOURCE,
    MIXED_COORDINATE_SOURCE,
    REAL_COORDINATE_SOURCE,
    TEMPORARY_COORDINATE_SOURCE,
    get_coordinate_metadata,
    get_map_coordinates,
)


class RoutingAlgorithmTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data_path = os.path.join(os.path.dirname(__file__), "data", "campus_data.json")
        cls.graph = CampusGraph(data_path)

    def test_representative_routes_match(self):
        routes = [
            ("MAIN_GATE", "QUEEN_IDIA"),
            ("MELLANBY", "FAC_TECH"),
            ("KUTI", "STADIUM"),
        ]
        records = validate_routes(self.graph, routes)
        self.assertEqual(len(records), len(routes))

    def test_dynamic_conditions_use_same_costs(self):
        model = CongestionModel()
        model.report_condition("SUB", "LIBRARY", 0.0, "flooded path")
        dijkstra_result = dijkstra_search(
            self.graph, "MAIN_GATE", "QUEEN_IDIA", model, "class_change"
        )
        astar_result = astar_search(
            self.graph, "MAIN_GATE", "QUEEN_IDIA", model, "class_change"
        )
        self.assertTrue(math.isclose(dijkstra_result.distance, astar_result.distance))
        self.assertEqual(dijkstra_result.path, astar_result.path)

    def test_unreachable_target_is_reported(self):
        graph = CampusGraph()
        graph.add_node("A", "A", "landmark", 0, 0)
        graph.add_node("B", "B", "landmark", 1, 0)
        self.assertIsNone(astar_search(graph, "A", "B").path)
        self.assertIsNone(dijkstra_search(graph, "A", "B").path)

    def test_map_coordinates_are_separate_and_deterministic(self):
        coordinates = get_map_coordinates(self.graph)
        self.assertEqual(COORDINATE_SOURCE, "temporary_development_relative_planar")
        self.assertEqual(set(coordinates), set(self.graph.nodes))
        self.assertEqual(coordinates["MAIN_GATE"], {"lat": 0, "lng": 0})
        self.assertEqual(coordinates, get_map_coordinates(self.graph))

    def test_real_coordinates_and_temporary_fallback_are_explicit(self):
        graph = CampusGraph()
        graph.add_node("REAL", "Real", "landmark", 10, 20, 7.3775, 3.9470)
        graph.add_node("TEMP", "Temporary", "landmark", 30, 40)
        coordinates = get_map_coordinates(graph)
        metadata = get_coordinate_metadata(graph)

        self.assertEqual(coordinates["REAL"], {"lat": 7.3775, "lng": 3.9470})
        self.assertEqual(coordinates["TEMP"], {"lat": 40, "lng": 30})
        self.assertEqual(metadata["source"], MIXED_COORDINATE_SOURCE)
        self.assertEqual(metadata["map_source"], TEMPORARY_COORDINATE_SOURCE)
        self.assertIn("REAL", metadata["real_node_ids"])
        self.assertIn("TEMP", metadata["temporary_node_ids"])
        self.assertNotEqual(metadata["source"], REAL_COORDINATE_SOURCE)

    def test_invalid_real_coordinate_data_is_rejected(self):
        graph = CampusGraph()
        with self.assertRaises(ValueError):
            graph.add_node("PARTIAL", "Partial", "landmark", 0, 0, latitude=7.0)
        with self.assertRaises(ValueError):
            graph.add_node("INVALID_LAT", "Invalid", "landmark", 0, 0, 91.0, 3.0)
        with self.assertRaises(ValueError):
            graph.add_node("INVALID_LNG", "Invalid", "landmark", 0, 0, 7.0, 181.0)

    def test_graph_integrity_validation_detects_weak_network_data(self):
        graph = CampusGraph()
        graph.add_node("A", "A", "landmark", 0, 0)
        graph.add_node("B", "B", "landmark", 1, 0)
        graph.add_node("C", "C", "landmark", 3, 0)
        graph.add_edge("A", "B", weight=1)
        graph.add_edge("B", "C", weight=0)

        report = graph.validate_graph()

        self.assertFalse(report["valid"])
        self.assertTrue(any("non-positive" in issue.lower() for issue in report["issues"]))
        self.assertTrue(any("isolated" in warning.lower() for warning in report["warnings"]))


if __name__ == "__main__":
    unittest.main()