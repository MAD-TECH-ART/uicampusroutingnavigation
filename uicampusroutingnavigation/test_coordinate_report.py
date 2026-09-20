import os
import unittest

from campus_graph import CampusGraph
from coordinate_report import build_report
from coordinate_validation import load_coordinate_dataset


class CoordinateReportTests(unittest.TestCase):
    def test_partial_dataset_report_is_explicit(self):
        package_dir = os.path.dirname(__file__)
        graph = CampusGraph(os.path.join(package_dir, "data", "campus_data.json"))
        dataset = load_coordinate_dataset()
        report = build_report(graph, dataset)
        self.assertIn("Total nodes: 45", report)
        self.assertIn("Populated coordinates: 16", report)
        self.assertIn("Verified: 16", report)
        self.assertIn("Missing: 29", report)
        self.assertIn("Edges awaiting coordinates: 46", report)
        self.assertIn("MAIN_GATE | Main Gate (Oduduwa Rd)", report)


if __name__ == "__main__":
    unittest.main()
