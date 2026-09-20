import math
import unittest

from fastapi.testclient import TestClient

from api import app, routing_service
from astar import astar_search
from dijkstra import dijkstra_search


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_route_matches_existing_dijkstra(self):
        response = self.client.get(
            "/api/route",
            params={"start": "MAIN_GATE", "destination": "QUEEN_IDIA", "algorithm": "dijkstra"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        expected = dijkstra_search(routing_service.graph, "MAIN_GATE", "QUEEN_IDIA")
        self.assertEqual(payload["path"], expected.path)
        self.assertTrue(math.isclose(payload["distance"], expected.distance))
        self.assertEqual(payload["algorithm"], "dijkstra")
        self.assertEqual(len(payload["coordinates"]), len(payload["path"]))
        self.assertEqual(payload["coordinate_source"], "temporary_development_relative_planar")
        self.assertIn("temporary", payload["coordinate_status"])

    def test_route_matches_existing_astar(self):
        response = self.client.get(
            "/api/route",
            params={
                "start": "MAIN_GATE",
                "destination": "QUEEN_IDIA",
                "algorithm": "astar",
                "time_profile": "class_change",
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        expected = astar_search(
            routing_service.graph,
            "MAIN_GATE",
            "QUEEN_IDIA",
            time_profile="class_change",
        )
        self.assertEqual(payload["path"], expected.path)
        self.assertTrue(math.isclose(payload["route_cost"], expected.distance))
        self.assertEqual(payload["algorithm"], "astar")

    def test_route_response_contains_summary_and_direction_details(self):
        response = self.client.get(
            "/api/route",
            params={"start": "MAIN_GATE", "destination": "QUEEN_IDIA", "algorithm": "dijkstra"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("summary", payload)
        self.assertIn("MAIN_GATE", payload["summary"])
        self.assertIn("QUEEN_IDIA", payload["summary"])
        self.assertIn("total_distance_meters", payload)
        self.assertIn("estimated_walking_time_minutes", payload)
        self.assertTrue(len(payload["directions"]) >= 2)
        self.assertIn("instruction", payload["directions"][0])
        self.assertIn("distance_meters", payload["directions"][0])

    def test_route_preference_supports_fewest_stops(self):
        response = self.client.get(
            "/api/route",
            params={
                "start": "MAIN_GATE",
                "destination": "QUEEN_IDIA",
                "algorithm": "dijkstra",
                "route_preference": "fewest_stops",
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["route_preference"], "fewest_stops")
        self.assertGreaterEqual(payload["total_steps"], 1)
        self.assertGreaterEqual(len(payload["path"]), 2)

    def test_route_preference_supports_accessible_route(self):
        response = self.client.get(
            "/api/route",
            params={
                "start": "MAIN_GATE",
                "destination": "QUEEN_IDIA",
                "algorithm": "dijkstra",
                "route_preference": "accessible",
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["route_preference"], "accessible")
        self.assertIn("accessible", payload["summary"].lower())
        self.assertTrue(len(payload["path"]) >= 2)

    def test_invalid_inputs_are_controlled(self):
        unknown_node = self.client.get(
            "/api/route",
            params={"start": "UNKNOWN", "destination": "QUEEN_IDIA"},
        )
        invalid_algorithm = self.client.get(
            "/api/route",
            params={
                "start": "MAIN_GATE",
                "destination": "QUEEN_IDIA",
                "algorithm": "bellman_ford",
            },
        )
        malformed = self.client.get("/api/route", params={"start": "MAIN_GATE"})
        self.assertEqual(unknown_node.status_code, 404)
        self.assertEqual(invalid_algorithm.status_code, 422)
        self.assertEqual(malformed.status_code, 422)

    def test_development_cors_is_restricted(self):
        response = self.client.get(
            "/api/health", headers={"Origin": "http://localhost:5500"}
        )
        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://localhost:5500")
        self.assertNotIn("*", response.headers.get("access-control-allow-origin", ""))


if __name__ == "__main__":
    unittest.main()
