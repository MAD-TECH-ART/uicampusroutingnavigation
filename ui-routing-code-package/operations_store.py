"""Persistent storage for reviewed campus operations data."""

import json
import os
import sqlite3
from typing import Any, Dict, Optional


DEFAULT_DATABASE_PATH = os.path.join(os.path.dirname(__file__), "data", "operations.sqlite3")


class OperationsStore:
    """Store reviewed coordinate records in a small local SQLite database."""

    def __init__(self, database_path: Optional[str] = None) -> None:
        self.database_path = database_path or os.getenv("UI_OPERATIONS_DB", DEFAULT_DATABASE_PATH)
        os.makedirs(os.path.dirname(self.database_path), exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS coordinate_records (
                    node_id TEXT PRIMARY KEY,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    accuracy REAL,
                    timestamp REAL NOT NULL,
                    source TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    confidence TEXT NOT NULL,
                    notes TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def list_coordinates(self) -> Dict[str, Dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT node_id, latitude, longitude, accuracy, timestamp, source, source_type, confidence, notes, updated_at "
                "FROM coordinate_records ORDER BY node_id"
            ).fetchall()
        return {row["node_id"]: dict(row) for row in rows}

    def save_coordinate(self, node_id: str, record: Dict[str, Any]) -> Dict[str, Any]:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO coordinate_records
                    (node_id, latitude, longitude, accuracy, timestamp, source, source_type, confidence, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(node_id) DO UPDATE SET
                    latitude = excluded.latitude,
                    longitude = excluded.longitude,
                    accuracy = excluded.accuracy,
                    timestamp = excluded.timestamp,
                    source = excluded.source,
                    source_type = excluded.source_type,
                    confidence = excluded.confidence,
                    notes = excluded.notes,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    node_id,
                    record["latitude"],
                    record["longitude"],
                    record.get("accuracy"),
                    record["timestamp"],
                    record["source"],
                    record["source_type"],
                    record["confidence"],
                    record.get("notes", ""),
                ),
            )
        return self.list_coordinates()[node_id]

    def delete_coordinate(self, node_id: str) -> bool:
        with self._connect() as connection:
            result = connection.execute("DELETE FROM coordinate_records WHERE node_id = ?", (node_id,))
        return result.rowcount > 0

    def export_json(self) -> str:
        return json.dumps({"coordinate_source": "operations_store", "nodes": self.list_coordinates()}, indent=2)
