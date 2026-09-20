# UI Campus Navigation System

## Overview
This repository contains a University of Ibadan campus navigation prototype designed as a simple browser-first route planner. The main app helps a user choose a start and destination, estimate travel time, and view a route on the campus map with a live current-time ETA.

The browser UI is intentionally focused on the actual product flow: it renders a campus map with open-source map tiles, lets the user pick a route, optionally uses the device's current location, and shows walking or driving travel times without requiring a paid API key.

## The problem this project solves
University of Ibadan is large enough that students, visitors, and staff can struggle to find buildings and plan an efficient route between them. The project keeps the experience inside a single browser UI and makes the route clear, quick, and usable without extra setup or account configuration.

## What has been done
- Built a browser-first campus navigation interface for University of Ibadan.
- Kept the single-trip navigation workflow simple and focused.
- Added walking and driving travel modes.
- Added one GPS control, Use my location, with location handling kept on the device.
- Added current time and estimated arrival display based on the computed route duration.
- Switched the user-facing map to a no-key Leaflet + OpenStreetMap stack.
- Kept the route planner within the page and removed the stale Geo review / traffic / time-of-day clutter.
- Preserved the campus graph and Python routing logic as background/reference material.
- Added a reproducible build flow through build_demo.py.

## Current product scope
- Free campus route planning without API keys
- Single-trip route planning between campus places
- One browser GPS action: Use my location
- Real-time current time and ETA display
- Travel mode choices: Walking and Driving
- Campus map rendering with route highlights and route details

## What is intentionally removed
- Geo-review / coordinate review workflow is not part of the main app flow
- Traffic update controls and reset controls were removed
- Time-of-day controls were removed from the main navigation experience
- Extra technical review sections were cleaned out so the interface stays focused on route planning

## Folder structure
- [README.md](README.md) — project overview and preview instructions
- [UI_Campus_Routing_Interactive_Demo-1.html](UI_Campus_Routing_Interactive_Demo-1.html) — static legacy demo version
- [ui-routing-code-package/](ui-routing-code-package/) — app source and route logic
  - [ui-routing-code-package/ui_routing_demo.html](ui-routing-code-package/ui_routing_demo.html) — generated active browser app
  - [ui-routing-code-package/demo_template.html](ui-routing-code-package/demo_template.html) — source template for the active app
  - [ui-routing-code-package/api.py](ui-routing-code-package/api.py) — FastAPI service
  - [ui-routing-code-package/astar.py](ui-routing-code-package/astar.py) — A* search
  - [ui-routing-code-package/dijkstra.py](ui-routing-code-package/dijkstra.py) — Dijkstra search
  - [ui-routing-code-package/campus_graph.py](ui-routing-code-package/campus_graph.py) — campus graph model
  - [ui-routing-code-package/live_conditions.py](ui-routing-code-package/live_conditions.py) — congestion and time-profile model
  - [ui-routing-code-package/data/](ui-routing-code-package/data/) — campus graph, place, and route data

## Preview in Chrome
From the workspace root, run:

1. Open a terminal in the project folder.
2. Start a static server:
   python -m http.server 8002
3. Open Chrome and visit:
   http://localhost:8002/ui-routing-code-package/ui_routing_demo.html

No API key is required for the default browser preview because the app uses Leaflet + OpenStreetMap tiles and browser geolocation.

## Notes
This project is a prototype campus-navigation system and not a production GIS platform. The app stays browser-first, keeps the route flow simple, and avoids API-key lock-in while still delivering the route-search experience the user needs.
