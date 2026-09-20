import os
import unittest

from campus_graph import CampusGraph
from coordinate_validation import (
    graph_geographic_report,
    load_coordinate_dataset,
    validate_coordinate_dataset,
)
from map_coordinates import get_real_map_coordinates


class CoordinateValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = os.path.dirname(__file__)
        cls.graph = CampusGraph(os.path.join(base, "data", "campus_data.json"))
        cls.dataset = load_coordinate_dataset()

    def test_partial_dataset_covers_graph_nodes_with_reviewed_coordinates(self):
        report = validate_coordinate_dataset(self.graph, self.dataset)
        self.assertTrue(report["valid"])
        self.assertEqual(report["expected_nodes"], 45)
        self.assertEqual(report["coordinate_records"], 45)
        self.assertEqual(report["complete_nodes"], 16)
        self.assertEqual(report["missing_nodes"], 29)

    def test_invalid_coordinates_are_reported(self):
        dataset = {"metadata": {"coordinate_system": "WGS84"}, "nodes": {
            "MAIN_GATE": {
                "latitude": 91,
                "longitude": 3,
                "source": "test",
                "source_type": "map",
                "confidence": "high",
                "verified": False,
            }
        }}
        report = validate_coordinate_dataset(self.graph, dataset)
        self.assertFalse(report["valid"])
        self.assertTrue(any("latitude" in error for error in report["errors"]))

    def test_graph_report_flags_edges_without_coordinates(self):
        report = graph_geographic_report(self.graph, self.dataset)
        self.assertEqual(report["checked_edges"], 8)
        self.assertEqual(len(report["missing_coordinate_edges"]), 46)

    def test_real_provider_reads_reviewed_coordinates(self):
        coordinates = get_real_map_coordinates(self.graph, self.dataset)
        self.assertEqual(len(coordinates), 16)
        self.assertEqual(coordinates["LIBRARY"], {"lat": 7.4467184, "lng": 3.8961037})

    def test_real_provider_reads_separate_dataset_records(self):
        dataset = {"nodes": {"MAIN_GATE": {"latitude": 7.4, "longitude": 3.9, "verified": True}}}
        coordinates = get_real_map_coordinates(self.graph, dataset)
        self.assertEqual(coordinates["MAIN_GATE"], {"lat": 7.4, "lng": 3.9})


if __name__ == "__main__":
    unittest.main()
