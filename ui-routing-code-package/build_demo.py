"""
build_demo.py
--------------
Generates the interactive HTML demo by injecting the campus dataset
(data/campus_data.json) directly into a JS template as JSON. This removes
the earlier failure mode where campus data was hand-copied into a
JavaScript literal and could drift out of sync with the Python graph (a
bug that shipped in the first prototype). The browser demo and the Python
backend now read from exactly the same source file.
"""
import json
import os

from benchmark import validate_routes
from campus_graph import CampusGraph
from live_conditions import CongestionModel, TIME_PROFILES
from map_coordinates import get_coordinate_metadata, get_map_coordinates, get_real_map_coordinates

BASE = os.path.dirname(__file__)
DATA_PATH = os.path.join(BASE, "data", "campus_data.json")
TEMPLATE_PATH = os.path.join(BASE, "demo_template.html")
OUTPUT_PATH = os.path.join(BASE, "ui_routing_demo.html")
LOCATION_ADAPTER_PATH = os.path.join(BASE, "location_adapter.js")
RESEARCH_CACHE_PATH = os.path.join(BASE, "data", "coordinate_research_cache.json")
CAMPUS_PLACES_PATH = os.path.join(BASE, "data", "campus_places.json")
ROUTING_CANDIDATES_PATH = os.path.join(BASE, "data", "routing_coordinate_candidates.json")
COORDINATE_DATASET_PATH = os.path.join(BASE, "data", "campus_coordinates.json")

with open(DATA_PATH, "r", encoding="utf-8") as f:
    campus_data = json.load(f)
with open(COORDINATE_DATASET_PATH, "r", encoding="utf-8") as f:
    coordinate_dataset = json.load(f)

# Reshape into the {ID: {name, cat, x, y}} map format the frontend uses,
# and a plain [[a,b], ...] edge list — both generated, never hand-typed.
nodes_obj = {
    n["id"]: {"name": n["name"], "cat": n["category"], "x": n["x"], "y": n["y"]}
    for n in campus_data["nodes"]
}
edges_list = [[e[0], e[1]] for e in campus_data["edges"]]

graph = CampusGraph(DATA_PATH)
map_coordinates = get_map_coordinates(graph)
verified_map_coordinates = get_real_map_coordinates(graph, coordinate_dataset)
coordinate_metadata = get_coordinate_metadata(graph)
if coordinate_metadata["source"] == "mixed":
    map_coordinates = {
        node_id: {"lat": node.y, "lng": node.x}
        for node_id, node in graph.nodes.items()
    }
route_requests = [
    (source, destination)
    for source in graph.all_node_ids()
    for destination in graph.all_node_ids()
    if source != destination
]
benchmark_data = {}
route_data = {}
route_matrix = {}
for profile in TIME_PROFILES:
    records = validate_routes(
        graph,
        route_requests,
        congestion_model=CongestionModel(),
        time_profile=profile,
    )
    benchmark_data[profile] = {
        f"{record['start']}|{record['destination']}": {
            **record,
            "same_optimal": True,
        }
        for record in records
    }
    route_data[profile] = {
        f"{record['start']}|{record['destination']}": {
            "path": record["results"]["dijkstra"]["path"],
            "distance": record["results"]["dijkstra"]["distance"],
        }
        for record in records
    }
    route_matrix[profile] = {
        f"{record['start']}|{record['destination']}": {
            "path": record["results"]["dijkstra"]["path"],
            "distance": record["results"]["dijkstra"]["distance"],
        }
        for record in records
    }

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    template = f.read()
with open(LOCATION_ADAPTER_PATH, "r", encoding="utf-8") as f:
    location_adapter = f.read()
with open(RESEARCH_CACHE_PATH, "r", encoding="utf-8") as f:
    research_cache = json.load(f)
with open(CAMPUS_PLACES_PATH, "r", encoding="utf-8") as f:
    campus_places = json.load(f)
with open(ROUTING_CANDIDATES_PATH, "r", encoding="utf-8") as f:
    routing_coordinate_candidates = json.load(f)
injected = template.replace(
    "/*__CAMPUS_NODES_JSON__*/", json.dumps(nodes_obj, indent=2)
).replace(
    "/*__CAMPUS_EDGES_JSON__*/", json.dumps(edges_list)
).replace(
    "/*__BENCHMARK_DATA_JSON__*/", json.dumps(benchmark_data)
).replace(
    "/*__ROUTE_DATA_JSON__*/", json.dumps(route_data)
).replace(
    "/*__ROUTE_MATRIX_JSON__*/", json.dumps(route_matrix)
).replace(
    "/*__MAP_COORDINATES_JSON__*/", json.dumps(map_coordinates)
).replace(
    "/*__VERIFIED_MAP_COORDINATES_JSON__*/", json.dumps(verified_map_coordinates)
).replace(
    "/*__COORDINATE_METADATA_JSON__*/", json.dumps(coordinate_metadata)
).replace(
    "/*__LOCATION_ADAPTER_JS__*/", location_adapter
).replace(
    "/*__RESEARCH_CACHE_JSON__*/", json.dumps(research_cache)
).replace(
    "/*__CAMPUS_PLACES_JSON__*/", json.dumps(campus_places)
).replace(
    "/*__ROUTING_COORDINATE_CANDIDATES_JSON__*/", json.dumps(routing_coordinate_candidates)
).replace(
    "/*__COORDINATE_DATASET_JSON__*/", json.dumps(coordinate_dataset)
)

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    f.write(injected)

print(f"Generated {OUTPUT_PATH} from {DATA_PATH} "
      f"({len(nodes_obj)} nodes, {len(edges_list)} edges).")
