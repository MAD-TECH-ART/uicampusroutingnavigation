import unittest

from campus_graph import CampusGraph
from remote_coordinate_research import in_review_bounds, normalize_results, search_query


class RemoteCoordinateResearchTests(unittest.TestCase):
    def test_query_uses_human_name_and_campus_context(self):
        graph = CampusGraph()
        self.assertEqual(
            search_query(graph.nodes["LIBRARY"].name),
            "Kenneth Dike Library, University of Ibadan, Nigeria",
        )

    def test_nominatim_result_becomes_unverified_candidate(self):
        results = normalize_results(
            "test",
            [{
                "osm_type": "way",
                "osm_id": 123,
                "lat": "7.4466",
                "lon": "3.8961",
                "display_name": "Kenneth Dike, University of Ibadan, Nigeria",
                "category": "amenity",
                "type": "library",
            }],
        )
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0]["verified"])
        self.assertTrue(results[0]["campus_context_match"])
        self.assertTrue(in_review_bounds(results[0]["latitude"], results[0]["longitude"]))


if __name__ == "__main__":
    unittest.main()
