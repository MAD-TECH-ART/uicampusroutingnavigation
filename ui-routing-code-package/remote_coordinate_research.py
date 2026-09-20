"""Rate-limited remote coordinate research using Nominatim candidates.

This utility never writes approved coordinates to campus_coordinates.json. It
caches responses for review and keeps candidate/verified states separate.
"""

import argparse
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Dict, Iterable

from campus_graph import CampusGraph
from coordinate_validation import DEFAULT_CAMPUS_REVIEW_BOUNDS

BASE_DIR = os.path.dirname(__file__)
DATA_PATH = os.path.join(BASE_DIR, "data", "campus_data.json")
CACHE_PATH = os.path.join(BASE_DIR, "data", "coordinate_research_cache.json")
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


def load_cache(path: str = CACHE_PATH) -> Dict:
    if not os.path.exists(path):
        return {"metadata": {"source": "OpenStreetMap Nominatim"}, "queries": {}}
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def search_query(node_name: str) -> str:
    return f"{node_name}, University of Ibadan, Nigeria"


def in_review_bounds(latitude: float, longitude: float) -> bool:
    bounds = DEFAULT_CAMPUS_REVIEW_BOUNDS
    return (
        bounds["min_lat"] <= latitude <= bounds["max_lat"]
        and bounds["min_lng"] <= longitude <= bounds["max_lng"]
    )


def query_nominatim(query: str) -> list:
    params = urllib.parse.urlencode({"q": query, "format": "jsonv2", "limit": 5})
    request = urllib.request.Request(
        f"{NOMINATIM_URL}?{params}",
        headers={"User-Agent": "A14-University-of-Ibadan-Campus-Routing/1.0"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def normalize_results(query: str, results: Iterable[Dict]) -> list:
    candidates = []
    for result in results:
        try:
            latitude = float(result["lat"])
            longitude = float(result["lon"])
        except (KeyError, TypeError, ValueError):
            continue
        display_name = result.get("display_name", "")
        candidates.append({
            "osm_type": result.get("osm_type"),
            "osm_id": result.get("osm_id"),
            "source_url": (
                f"https://www.openstreetmap.org/{result.get('osm_type')}/{result.get('osm_id')}"
            ),
            "latitude": latitude,
            "longitude": longitude,
            "display_name": display_name,
            "category": result.get("category"),
            "type": result.get("type"),
            "boundingbox": result.get("boundingbox"),
            "campus_context_match": "university of ibadan" in display_name.lower(),
            "within_review_bounds": in_review_bounds(latitude, longitude),
            "verified": False,
            "status": "candidate",
            "notes": "Candidate only; human review required before approval.",
        })
    return candidates


def research_nodes(graph: CampusGraph, cache: Dict, node_ids: Iterable[str], delay_seconds: float = 1.0) -> Dict:
    queries = cache.setdefault("queries", {})
    for node_id in node_ids:
        if node_id in queries and queries[node_id].get("status") in {"candidate_found", "no_result"}:
            continue
        node = graph.nodes[node_id]
        query = search_query(node.name)
        try:
            raw_results = query_nominatim(query)
            candidates = normalize_results(query, raw_results)
            queries[node_id] = {
                "query": query,
                "source_url": f"{NOMINATIM_URL}?{urllib.parse.urlencode({'q': query, 'format': 'jsonv2', 'limit': 5})}",
                "queried_at": datetime.now(timezone.utc).isoformat(),
                "status": "candidate_found" if candidates else "no_result",
                "results": candidates,
            }
        except Exception as error:
            queries[node_id] = {
                "query": query,
                "queried_at": datetime.now(timezone.utc).isoformat(),
                "status": "request_failed",
                "error": str(error),
                "results": [],
            }
        if delay_seconds > 0:
            time.sleep(delay_seconds)
    cache["metadata"]["last_research_at"] = datetime.now(timezone.utc).isoformat()
    return cache


def save_cache(cache: Dict, path: str = CACHE_PATH):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(cache, file, indent=2)
        file.write("\n")


def summarize(cache: Dict) -> str:
    entries = cache.get("queries", {}).values()
    candidate_count = sum(bool(entry.get("results")) for entry in entries)
    result_count = sum(len(entry.get("results", [])) for entry in entries)
    return f"Research entries: {len(cache.get('queries', {}))}\nNodes with candidates: {candidate_count}\nCandidate results: {result_count}\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node", action="append", dest="node_ids", help="Research one node ID; repeatable.")
    parser.add_argument("--all", action="store_true", help="Research uncached nodes sequentially.")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between uncached requests in seconds.")
    args = parser.parse_args()
    graph = CampusGraph(DATA_PATH)
    cache = load_cache()
    if args.all or args.node_ids:
        node_ids = args.node_ids or graph.all_node_ids()
        unknown = sorted(set(node_ids) - set(graph.nodes))
        if unknown:
            raise SystemExit(f"Unknown node IDs: {', '.join(unknown)}")
        save_cache(research_nodes(graph, cache, node_ids, max(1.0, args.delay)))
    print(summarize(cache), end="")


if __name__ == "__main__":
    main()
