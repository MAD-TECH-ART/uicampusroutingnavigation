"""
live_conditions.py
-------------------
Addresses the "static, preconfigured travel metrics" limitation of the
original prototype.

The original system used a fixed distance as the only edge weight, computed
once from coordinates and never updated. In reality, the time it takes to
cross campus varies with pedestrian congestion, time of day, weather, and
temporary obstructions (construction, events, flooding of a path, etc.).

This module introduces a CongestionModel that sits between the static graph
distance and the routing algorithms:

    base distance (metres)  ->  CongestionModel  ->  effective travel weight

There is no live sensor feed wired up in this prototype (University of
Ibadan does not currently expose one), so the model is driven by:
    1. A time-of-day profile (rule-based, e.g. higher pedestrian density
       around class-change hours), and
    2. An optional manual/live override per edge, via `report_condition()`,
       which is the integration point a real sensor feed, crowd-sourced
       report, or facilities-management system would call into.

This keeps the architecture honest: it does not pretend to have live IoT
sensors it doesn't have, but it removes the "everything is a fixed
precomputed number" limitation, and it defines the exact interface real
sensor data would plug into later (see `report_condition`).
"""

import random
import time as _time
from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional

EdgeKey = Tuple[str, str]  # always stored as a sorted tuple (a, b) with a < b


def _key(a: str, b: str) -> EdgeKey:
    return (a, b) if a < b else (b, a)


# ---------------------------------------------------------------------
# Time-of-day congestion profiles
# ---------------------------------------------------------------------
# Multiplier applied to base walking distance/time. 1.0 = free-flow.
# These are rule-based approximations (typical class-change and meal-time
# crowding), not measured data — clearly labelled as such below.
TIME_PROFILES = {
    "off_peak":      1.00,   # e.g. mid-morning lull, late evening
    "class_change":  1.35,   # top/bottom of the hour, corridors and SUB fill up
    "meal_time":     1.20,   # cafeteria / SUB area congestion around meal hours
    "night":         0.90,   # fewer pedestrians, slightly faster through-traffic
}

# Locations where pedestrian congestion concentrates disproportionately
# during "class_change" / "meal_time" (near lecture theatres, SUB, cafeterias).
HIGH_TRAFFIC_NODES = {"SUB", "LIBRARY", "SENATE", "FAC_ARTS", "FAC_SCI", "TRENCHARD"}


@dataclass
class LiveReport:
    multiplier: float          # >1.0 = slower than free-flow, <1.0 = faster
    reason: str                # e.g. "construction", "flooded path", "crowd"
    reported_at: float = field(default_factory=_time.time)
    ttl_seconds: float = 1800  # live reports expire after 30 minutes by default

    def is_active(self) -> bool:
        return (_time.time() - self.reported_at) < self.ttl_seconds


class CongestionModel:
    """
    Computes an effective travel weight for an edge given:
      - the edge's static base distance,
      - the current time-of-day profile, and
      - any active manually-reported / sensor-reported condition.

    This is the extension point for real-time data: a future integration
    (GPS-tracked shuttle occupancy, a crowd-reporting app, a facilities
    maintenance feed for road closures) would call `report_condition()`
    exactly the way the simulated demo in this project does.
    """

    def __init__(self):
        self._live_reports: Dict[EdgeKey, LiveReport] = {}

    # ------------------------------------------------------------------ #
    # Integration point for real (or simulated) live data
    # ------------------------------------------------------------------ #
    def report_condition(self, a: str, b: str, multiplier: float, reason: str,
                          ttl_seconds: float = 1800):
        """Register a live condition on edge (a, b). `multiplier` scales the
        base distance: 1.6 means 'currently ~60% slower than normal' (e.g. a
        crowd or minor obstruction); 0.0 would mean the path is impassable
        (a full closure) -- callers should treat that as 'exclude this edge'.
        """
        self._live_reports[_key(a, b)] = LiveReport(multiplier, reason, ttl_seconds=ttl_seconds)

    def clear_condition(self, a: str, b: str):
        self._live_reports.pop(_key(a, b), None)

    def active_conditions(self) -> Dict[EdgeKey, LiveReport]:
        expired = [k for k, r in self._live_reports.items() if not r.is_active()]
        for k in expired:
            del self._live_reports[k]
        return dict(self._live_reports)

    # ------------------------------------------------------------------ #
    # Weight computation
    # ------------------------------------------------------------------ #
    def effective_weight(self, a: str, b: str, base_distance: float,
                          time_profile: str = "off_peak") -> Optional[float]:
        """Returns the effective travel weight for edge (a,b), or None if
        the edge is currently impassable (a reported full closure)."""
        report = self._live_reports.get(_key(a, b))
        if report and report.is_active():
            if report.multiplier <= 0:
                return None  # closed / impassable
            return base_distance * report.multiplier

        profile_multiplier = TIME_PROFILES.get(time_profile, 1.0)
        if time_profile in ("class_change", "meal_time") and (a in HIGH_TRAFFIC_NODES or b in HIGH_TRAFFIC_NODES):
            profile_multiplier *= 1.15  # extra crowding right at hotspot nodes
        return base_distance * profile_multiplier

    # ------------------------------------------------------------------ #
    # Simulation helper (stands in for a live sensor/crowd-report feed)
    # ------------------------------------------------------------------ #
    def simulate_live_conditions(self, graph, num_events: int = 3, seed: Optional[int] = None):
        """Randomly reports a small number of transient conditions (e.g.
        localized crowding or a minor obstruction) across the graph, to
        demonstrate how the system behaves once real-time input exists.
        This is explicitly a SIMULATION for demo purposes, not real data.
        """
        rng = random.Random(seed)
        all_edges = [(a, b) for a in graph.adjacency for b, _w in graph.adjacency[a] if a < b]
        chosen = rng.sample(all_edges, min(num_events, len(all_edges)))
        reasons = ["pedestrian crowd", "minor obstruction", "vendor stall", "ongoing repairs"]
        for a, b in chosen:
            multiplier = round(rng.uniform(1.3, 2.2), 2)
            self.report_condition(a, b, multiplier, rng.choice(reasons), ttl_seconds=1800)
        return self.active_conditions()


if __name__ == "__main__":
    from campus_graph import CampusGraph

    g = CampusGraph()
    model = CongestionModel()

    print("=== Time-of-day profile comparison (Main Gate -> Faculty of Arts edge N/A directly; using SUB->LIBRARY) ===")
    base = None
    for a, w in g.neighbors("SUB"):
        if a == "LIBRARY":
            base = w
    for profile in TIME_PROFILES:
        eff = model.effective_weight("SUB", "LIBRARY", base, profile)
        print(f"  {profile:14s}: {eff:.0f} m (base {base:.0f} m)")

    print("\n=== Simulated live conditions ===")
    events = model.simulate_live_conditions(g, num_events=4, seed=42)
    for (a, b), report in events.items():
        print(f"  {g.nodes[a].name} <-> {g.nodes[b].name}: x{report.multiplier} ({report.reason})")
