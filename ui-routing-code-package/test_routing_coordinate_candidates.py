import unittest

from campus_graph import CampusGraph
from routing_coordinate_candidates import build_candidates


class RoutingCoordinateCandidateTests(unittest.TestCase):
    def test_explicit_matches_remain_unverified_candidates(self):
        graph = CampusGraph()
        places = [{
            "id": "way/1",
            "name": "Kenneth Dike",
            "latitude": 7.4467,
            "longitude": 3.8961,
            "source_url": "https://www.openstreetmap.org/way/1",
        }]
        dataset = build_candidates(graph, places)
        candidate = dataset["nodes"]["LIBRARY"]
        self.assertEqual(candidate["status"], "candidate")
        self.assertTrue(candidate["review_required"])
        self.assertEqual(candidate["matches"][0]["latitude"], 7.4467)

    def test_unmatched_nodes_are_not_fabricated(self):
        graph = CampusGraph()
        dataset = build_candidates(graph, [])
        self.assertNotIn("SENATE", dataset["nodes"])
        self.assertEqual(dataset["metadata"]["routing_node_count"], 45)


if __name__ == "__main__":
    unittest.main()
