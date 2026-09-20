"""FastAPI entry point for the campus navigation and operations service."""

import hmac
import logging
import os
from time import perf_counter
from typing import Literal, Optional

from pydantic import BaseModel, Field

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from live_conditions import TIME_PROFILES
from operations_store import OperationsStore
from routing_service import RoutingService


logger = logging.getLogger("ui_campus_navigation.api")
app = FastAPI(title="UI Campus Navigation System API", version="1.1.0")
routing_service = RoutingService()
operations_store = OperationsStore()

default_origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "null",
]
configured_origins = os.getenv("UI_CORS_ORIGINS")
allowed_origins = [origin.strip() for origin in configured_origins.split(",") if origin.strip()] if configured_origins else default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "PUT", "DELETE"],
    allow_headers=["Accept", "Content-Type", "X-Operations-Key"],
)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    started = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled request error: %s %s", request.method, request.url.path)
        raise
    elapsed_ms = (perf_counter() - started) * 1000
    logger.info("%s %s -> %s (%.1f ms)", request.method, request.url.path, response.status_code, elapsed_ms)
    response.headers["X-Process-Time-ms"] = f"{elapsed_ms:.1f}"
    return response


class CoordinateRecord(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy: Optional[float] = Field(default=None, ge=0)
    timestamp: float
    source: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    confidence: Literal["low", "medium", "high"]
    notes: str = ""


def require_operations_access(x_operations_key: Optional[str] = Header(default=None)) -> None:
    expected_key = os.getenv("UI_OPERATIONS_KEY")
    if not expected_key:
        raise HTTPException(status_code=503, detail="Operations API is not configured.")
    if not x_operations_key or not hmac.compare_digest(x_operations_key, expected_key):
        raise HTTPException(status_code=401, detail="A valid operations key is required.")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/operations/coordinates", dependencies=[Depends(require_operations_access)])
def list_operation_coordinates():
    return {"nodes": operations_store.list_coordinates()}


@app.put("/api/operations/coordinates/{node_id}", dependencies=[Depends(require_operations_access)])
def save_operation_coordinate(node_id: str, record: CoordinateRecord):
    if node_id not in routing_service.graph.nodes:
        raise HTTPException(status_code=404, detail=f"Unknown campus node: {node_id}")
    saved = operations_store.save_coordinate(node_id, record.model_dump())
    return {"node_id": node_id, "record": saved}


@app.delete("/api/operations/coordinates/{node_id}", dependencies=[Depends(require_operations_access)])
def delete_operation_coordinate(node_id: str):
    if not operations_store.delete_coordinate(node_id):
        raise HTTPException(status_code=404, detail=f"No stored coordinate for node: {node_id}")
    return {"deleted": True, "node_id": node_id}


@app.get("/api/route")
def route(
    start: str = Query(..., min_length=1),
    destination: str = Query(..., min_length=1),
    algorithm: Literal["dijkstra", "astar"] = "dijkstra",
    time_profile: Literal["off_peak", "class_change", "meal_time", "night"] = "off_peak",
    route_preference: Literal["shortest_distance", "fewest_stops", "accessible"] = "shortest_distance",
):
    if start not in routing_service.graph.nodes:
        raise HTTPException(status_code=404, detail=f"Unknown start node: {start}")
    if destination not in routing_service.graph.nodes:
        raise HTTPException(status_code=404, detail=f"Unknown destination node: {destination}")
    if time_profile not in TIME_PROFILES:
        raise HTTPException(status_code=422, detail=f"Unsupported time profile: {time_profile}")

    try:
        return routing_service.calculate_route(
            start=start,
            destination=destination,
            algorithm=algorithm,
            time_profile=time_profile,
            route_preference=route_preference,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
