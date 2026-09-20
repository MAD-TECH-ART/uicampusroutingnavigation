"""Download named OpenStreetMap features for the University of Ibadan map.

The output is a geographic display layer only. It is deliberately separate
from campus_data.json and must not be used as routing nodes automatically.
"""

import argparse
import json
import math
import os
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Dict, Iterable, Optional, Tuple


BASE_DIR = os.path.dirname(__file__)
OUTPUT_PATH = os.path.join(BASE_DIR, "data", "campus_places.json")
OSM_MAP_URL = "https://api.openstreetmap.org/api/0.6/map"
CAMPUS_BOUNDS = {
    "min_lat": 7.4377245,
    "max_lat": 7.4585,
    "min_lng": 3.8867116,
    "max_lng": 3.9067116,
}


def source_url(element_type: str, element_id: str) -> str:
    return f"https://www.openstreetmap.org/{element_type}/{element_id}"


def _tags(element: ET.Element) -> Dict[str, str]:
    return {
        tag.get("k"): tag.get("v")
        for tag in element.findall("tag")
        if tag.get("k") and tag.get("v")
    }


def _average(points: Iterable[Tuple[float, float]]) -> Optional[Tuple[float, float]]:
    values = list(points)
    if not values:
        return None
    return (
        sum(latitude for latitude, _ in values) / len(values),
        sum(longitude for _, longitude in values) / len(values),
    )


def parse_named_places(xml_data: bytes) -> list:
    root = ET.fromstring(xml_data)
    nodes = {
        element.get("id"): (float(element.get("lat")), float(element.get("lon")))
        for element in root.findall("node")
    }
    ways = {}
    for element in root.findall("way"):
        points = [nodes[ref.get("ref")] for ref in element.findall("nd") if ref.get("ref") in nodes]
        center = _average(points)
        if center:
            ways[element.get("id")] = center

    places = []
    for element_type in ("node", "way", "relation"):
        for element in root.findall(element_type):
            tags = _tags(element)
            name = tags.get("name")
            if not name:
                continue
            if element_type == "node":
                center = nodes.get(element.get("id"))
            elif element_type == "way":
                center = ways.get(element.get("id"))
            else:
                member_points = [
                    ways[member.get("ref")]
                    for member in element.findall("member")
                    if member.get("type") == "way" and member.get("ref") in ways
                ]
                center = _average(member_points)
            if not center:
                continue
            places.append({
                "id": f"{element_type}/{element.get('id')}",
                "name": name,
                "latitude": round(center[0], 7),
                "longitude": round(center[1], 7),
                "feature_type": element_type,
                "category": tags.get("amenity") or tags.get("building") or tags.get("landuse") or tags.get("tourism") or tags.get("shop") or tags.get("leisure") or "place",
                "source": "OpenStreetMap",
                "source_url": source_url(element_type, element.get("id")),
                "tags": tags,
            })
    return sorted(places, key=lambda place: (place["name"].casefold(), place["id"]))


def download_map(bounds: Dict[str, float] = CAMPUS_BOUNDS) -> bytes:
    bbox = ",".join(str(bounds[key]) for key in ("min_lng", "min_lat", "max_lng", "max_lat"))
    request = urllib.request.Request(
        f"{OSM_MAP_URL}?bbox={bbox}",
        headers={"User-Agent": "UI-Campus-Router/1.0 (campus research layer)"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def build_dataset(xml_data: bytes) -> Dict:
    places = parse_named_places(xml_data)
    validate_places(places)
    names = {}
    for place in places:
        names.setdefault(place["name"].casefold(), 0)
        names[place["name"].casefold()] += 1
    outside_bounds = [
        place for place in places
        if not (
            CAMPUS_BOUNDS["min_lat"] <= place["latitude"] <= CAMPUS_BOUNDS["max_lat"]
            and CAMPUS_BOUNDS["min_lng"] <= place["longitude"] <= CAMPUS_BOUNDS["max_lng"]
        )
    ]
    return {
        "metadata": {
            "source": "OpenStreetMap API 0.6 map extract",
            "status": "display_research_only",
            "coordinate_system": "WGS84",
            "campus_bounds": CAMPUS_BOUNDS,
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
            "note": "Named features are displayed on the map but are not routing nodes or approved survey coordinates.",
            "named_feature_count": len(places),
            "duplicate_name_count": sum(count > 1 for count in names.values()),
            "representative_points_outside_bounds": len(outside_bounds),
        },
        "places": places,
    }


def validate_places(places: Iterable[Dict]) -> None:
    """Reject incomplete geographic records before they reach the map."""
    invalid = []
    for place in places:
        latitude = place.get("latitude")
        longitude = place.get("longitude")
        if (
            not isinstance(latitude, (int, float))
            or not isinstance(longitude, (int, float))
            or not math.isfinite(latitude)
            or not math.isfinite(longitude)
        ):
            invalid.append(place.get("id", "unknown"))
    if invalid:
        raise ValueError(
            "Campus places must have finite numeric latitude and longitude: "
            + ", ".join(invalid)
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=OUTPUT_PATH)
    args = parser.parse_args()
    dataset = build_dataset(download_map())
    with open(args.output, "w", encoding="utf-8") as file:
        json.dump(dataset, file, indent=2, ensure_ascii=True)
        file.write("\n")
    print(f"Wrote {len(dataset['places'])} named campus places to {args.output}")


if __name__ == "__main__":
    main()