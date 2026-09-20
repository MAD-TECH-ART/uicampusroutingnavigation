"""Build explicit OSM coordinate candidates for routing locations.

Candidates are evidence for review only. This module never modifies
campus_coordinates.json, campus_data.json, or routing behavior.
"""

import json
import os
import re
from typing import Dict, Iterable

from campus_graph import CampusGraph

BASE_DIR = os.path.dirname(__file__)
GRAPH_PATH = os.path.join(BASE_DIR, "data", "campus_data.json")
PLACES_PATH = os.path.join(BASE_DIR, "data", "campus_places.json")
COORDINATES_PATH = os.path.join(BASE_DIR, "data", "campus_coordinates.json")
OUTPUT_PATH = os.path.join(BASE_DIR, "data", "routing_coordinate_candidates.json")

# These aliases reflect spelling variants or explicit campus naming variants,
# rather than fuzzy similarity between unrelated facilities.
PLACE_ALIASES = {
    "CHAPEL": {"UI Chapel"},
    "MOSQUE": {"UI's Mosque"},
    "LIBRARY": {"Kenneth Dike", "Kenneth Dike Library"},
    "TRENCHARD": {"Tenchard Hall", "Trenchard Hall"},
    "HEALTH_CENTRE": {"University Health Service, Jaja Clinic, UI"},
    "ICT_CENTRE": {"University's ICT Centre"},
    "INST_AFR": {"Institute of African Studies and IFRA Nigeria"},
    "BOTANICAL": {"UI Botanical Gardens"},
    "AZIKIWE": {"Nnamdi Azizkwe Hall", "Nnamdi Azikiwe Hall"},
    "TAFAWA_PG": {"Tafabalewa Hall", "Tafawa Balewa Hall"},
}


def normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def build_candidates(graph: CampusGraph, places: Iterable[Dict], coordinate_dataset: Dict = None) -> Dict:
    places_by_name = {}
    for place in places:
        places_by_name.setdefault(normalized(place["name"]), []).append(place)
    candidates = {}
    verified_nodes = {
        node_id for node_id, record in (coordinate_dataset or {}).get("nodes", {}).items()
        if isinstance(record, dict) and record.get("verified")
    }
    for node_id, node in graph.nodes.items():
        if node_id in verified_nodes:
            continue
        names = {node.name, *PLACE_ALIASES.get(node_id, set())}
        matches = []
        for name in names:
            matches.extend(places_by_name.get(normalized(name), []))
        unique = {place["id"]: place for place in matches}
        if unique:
            candidates[node_id] = {
                "node_name": node.name,
                "status": "candidate",
                "review_required": True,
                "matches": [
                    {
                        "place_id": place["id"],
                        "name": place["name"],
                        "latitude": place["latitude"],
                        "longitude": place["longitude"],
                        "source_url": place["source_url"],
                    }
                    for place in sorted(unique.values(), key=lambda item: item["id"])
                ],
            }
    return {
        "metadata": {
            "source": "OpenStreetMap campus_places.json",
            "status": "candidate_review_only",
            "note": "Candidates are explicit name or alias matches and are not approved routing coordinates.",
            "candidate_node_count": len(candidates),
            "routing_node_count": len(graph.nodes),
            "verified_node_count": len(verified_nodes),
        },
        "nodes": candidates,
    }


def main():
    graph = CampusGraph(GRAPH_PATH)
    with open(PLACES_PATH, "r", encoding="utf-8") as file:
        places = json.load(file)["places"]
    with open(COORDINATES_PATH, "r", encoding="utf-8") as file:
        coordinate_dataset = json.load(file)
    dataset = build_candidates(graph, places, coordinate_dataset)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
        json.dump(dataset, file, indent=2, ensure_ascii=True)
        file.write("\n")
    print(f"Wrote {dataset['metadata']['candidate_node_count']} routing coordinate candidates")


if __name__ == "__main__":
    main()
