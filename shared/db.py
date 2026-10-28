"""Database repository functions for mock SQLite and Azure SQL."""

from __future__ import annotations

import json
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from shared.config import APP_MODE, get_secret


ITEM_FIELDS = (
    "Type", "Title", "Description", "Category", "Location", "ItemDate",
    "ImageUrl", "Tags", "Caption", "ReporterName", "ReporterEmail", "Status",
)
ITEM_STATUSES = {"open", "matched", "returned"}
MATCH_STATUSES = {"suggested", "confirmed", "rejected"}

_MOCK_SCHEMA = """
CREATE TABLE IF NOT EXISTS Items (
    ItemId INTEGER PRIMARY KEY AUTOINCREMENT,
    Type TEXT NOT NULL CHECK (Type IN ('lost', 'found')),
    Title TEXT NOT NULL,
    Description TEXT,
    Category TEXT NOT NULL,
    Location TEXT,
    ItemDate TEXT,
    ImageUrl TEXT,
    Tags TEXT,
    Caption TEXT,
    ReporterName TEXT,
    ReporterEmail TEXT,
    Status TEXT NOT NULL DEFAULT 'open',
    CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS Matches (
    MatchId INTEGER PRIMARY KEY AUTOINCREMENT,
    LostItemId INTEGER NOT NULL REFERENCES Items(ItemId),
    FoundItemId INTEGER NOT NULL REFERENCES Items(ItemId),
    Score REAL NOT NULL,
    Status TEXT NOT NULL DEFAULT 'suggested',
    CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (LostItemId, FoundItemId)
);
CREATE INDEX IF NOT EXISTS IX_Items_Type_Status ON Items(Type, Status);
"""


def _mock_db_path() -> Path:
    """Return the overridable SQLite path used only in mock mode."""
    configured = os.getenv("LOSTFOUND_DB_PATH", "")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[1] / "instance" / "lostfound_mock.db"


def _value(data: dict[str, Any], field: str, default: Any = None) -> Any:
    """Read either a database-style or lower-case form key from input data."""
    return data.get(field, data.get(field.lower(), default))


def _serialise_tags(value: Any) -> str:
    """Store tags as a JSON list while accepting an existing string value."""
    if value is None:
        return "[]"
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
            if isinstance(decoded, list):
                return json.dumps(decoded)
        except json.JSONDecodeError:
            return json.dumps([tag.strip() for tag in value.split(",") if tag.strip()])
        return json.dumps([value])
    return json.dumps(list(value))


def _decode_row(row: Any, columns: tuple[str, ...] | None = None) -> dict[str, Any]:
    """Convert a SQLite row or pyodbc row into a plain template-friendly dict."""
    if isinstance(row, sqlite3.Row):
        result = dict(row)
    else:
        column_names = columns or tuple(column[0] for column in row.cursor_description)
        result = dict(zip(column_names, row))
    tags = result.get("Tags")
    if isinstance(tags, str):
        try:
            result["Tags"] = json.loads(tags)
        except json.JSONDecodeError:
            result["Tags"] = [tag.strip() for tag in tags.split(",") if tag.strip()]
    return result


def _execute(cursor: Any, query: str, parameters: tuple[Any, ...] | list[Any] = ()) -> Any:
    """Execute parameterized SQL with the calling convention of the active driver."""
    values = tuple(parameters)
    if APP_MODE == "mock":
        return cursor.execute(query, values)
    return cursor.execute(query, *values)


@contextmanager
def _connection() -> Iterator[Any]:
    """Open one short-lived connection and always close it after the operation."""
    if APP_MODE == "mock":
        path = _mock_db_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
    else:
        try:
            import pyodbc
        except ImportError as error:
            raise RuntimeError("pyodbc is required for local and cloud database modes") from error
        pyodbc.pooling = False
        connection = None
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                connection = pyodbc.connect(get_secret("SqlConnectionString"), timeout=30)
                break
            except Exception as error:  # Azure serverless databases can be waking up.
                last_error = error
                if attempt < 2:
                    time.sleep(10)
        if connection is None:
            raise RuntimeError("Could not connect to Azure SQL after three attempts") from last_error
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db() -> None:
    """Create the SQLite schema for mock mode; Azure SQL is provisioned separately."""
    if APP_MODE != "mock":
        return
    with _connection() as connection:
        connection.executescript(_MOCK_SCHEMA)


def create_item(data: dict) -> int:
    """Persist an item and return its generated item ID."""
    item_type = _value(data, "Type")
    if item_type not in {"lost", "found"}:
        raise ValueError("Type must be 'lost' or 'found'")
    title = str(_value(data, "Title", "")).strip()
    category = str(_value(data, "Category", "")).strip()
    if not title or not category:
        raise ValueError("Title and Category are required")
    values = [
        item_type, title, _value(data, "Description"), category, _value(data, "Location"),
        _value(data, "ItemDate"), _value(data, "ImageUrl"),
        _serialise_tags(_value(data, "Tags", [])), _value(data, "Caption"),
        _value(data, "ReporterName"), _value(data, "ReporterEmail"),
        _value(data, "Status", "open"),
    ]
    if values[-1] not in ITEM_STATUSES:
        raise ValueError("Invalid item status")
    placeholders = ", ".join("?" for _ in ITEM_FIELDS)
    columns = ", ".join(ITEM_FIELDS)
    with _connection() as connection:
        cursor = connection.cursor()
        if APP_MODE == "mock":
            _execute(cursor, f"INSERT INTO Items ({columns}) VALUES ({placeholders})", values)
            return int(cursor.lastrowid)
        _execute(
            cursor, f"INSERT INTO Items ({columns}) OUTPUT INSERTED.ItemId VALUES ({placeholders})", values
        )
        return int(cursor.fetchone()[0])


def get_item(item_id: int) -> dict | None:
    """Return one item by ID, or None when it does not exist."""
    with _connection() as connection:
        cursor = _execute(connection.cursor(), "SELECT * FROM Items WHERE ItemId = ?", (item_id,))
        row = cursor.fetchone()
        columns = tuple(column[0] for column in cursor.description)
    return _decode_row(row, columns) if row else None


def list_items(
    type: str | None = None, category: str | None = None, keyword: str | None = None,
    status: str | None = None, reporter_email: str | None = None, limit: int = 50,
) -> list[dict]:
    """List items using optional safe filters and a bounded result count."""
    limit = max(1, min(int(limit), 200))
    clauses: list[str] = []
    values: list[Any] = []
    for column, value in (("Type", type), ("Category", category), ("Status", status), ("ReporterEmail", reporter_email)):
        if value:
            clauses.append(f"{column} = ?")
            values.append(value)
    if keyword:
        clauses.append("(Title LIKE ? OR Description LIKE ? OR Tags LIKE ?)")
        values.extend([f"%{keyword}%"] * 3)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    limit_clause = " LIMIT ?" if APP_MODE == "mock" else " OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY"
    with _connection() as connection:
        cursor = _execute(
            connection.cursor(), f"SELECT * FROM Items{where} ORDER BY CreatedAt DESC{limit_clause}", values + [limit]
        )
        rows = cursor.fetchall()
        columns = tuple(column[0] for column in cursor.description)
    return [_decode_row(row, columns) for row in rows]


def update_item_status(item_id: int, status: str) -> None:
    """Set an item status after validating the allowed transition target."""
    if status not in ITEM_STATUSES:
        raise ValueError("Invalid item status")
    with _connection() as connection:
        _execute(connection.cursor(), "UPDATE Items SET Status = ? WHERE ItemId = ?", (status, item_id))


def delete_item(item_id: int) -> str | None:
    """Delete one item and related matches, returning its image URL if present."""
    with _connection() as connection:
        cursor = connection.cursor()
        row = _execute(cursor, "SELECT ImageUrl FROM Items WHERE ItemId = ?", (item_id,)).fetchone()
        if not row:
            return None
        image_url = row[0]
        _execute(cursor, "DELETE FROM Matches WHERE LostItemId = ? OR FoundItemId = ?", (item_id, item_id))
        _execute(cursor, "DELETE FROM Items WHERE ItemId = ?", (item_id,))
        return image_url


def create_match(lost_id: int, found_id: int, score: float) -> int:
    """Create a suggested match and return its generated match ID."""
    if not 0 <= score <= 1:
        raise ValueError("Match score must be between 0 and 1")
    with _connection() as connection:
        cursor = connection.cursor()
        if APP_MODE == "mock":
            _execute(
                cursor,
                "INSERT INTO Matches (LostItemId, FoundItemId, Score) VALUES (?, ?, ?)",
                (lost_id, found_id, score),
            )
            return int(cursor.lastrowid)
        _execute(
            cursor,
            "INSERT INTO Matches (LostItemId, FoundItemId, Score) OUTPUT INSERTED.MatchId VALUES (?, ?, ?)",
            (lost_id, found_id, score),
        )
        return int(cursor.fetchone()[0])


def list_matches(item_id: int | None = None, status: str | None = None) -> list[dict]:
    """List matches, including concise details for their lost and found items."""
    clauses: list[str] = []
    values: list[Any] = []
    if item_id is not None:
        clauses.append("(m.LostItemId = ? OR m.FoundItemId = ?)")
        values.extend([item_id, item_id])
    if status:
        clauses.append("m.Status = ?")
        values.append(status)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    query = (
        "SELECT m.*, l.Title AS LostTitle, f.Title AS FoundTitle "
        "FROM Matches m JOIN Items l ON l.ItemId = m.LostItemId "
        "JOIN Items f ON f.ItemId = m.FoundItemId"
        f"{where} ORDER BY m.Score DESC, m.CreatedAt DESC"
    )
    with _connection() as connection:
        cursor = _execute(connection.cursor(), query, values)
        rows = cursor.fetchall()
        columns = tuple(column[0] for column in cursor.description)
    return [_decode_row(row, columns) for row in rows]


def update_match_status(match_id: int, status: str) -> None:
    """Set a match status after validating it."""
    if status not in MATCH_STATUSES:
        raise ValueError("Invalid match status")
    with _connection() as connection:
        _execute(connection.cursor(), "UPDATE Matches SET Status = ? WHERE MatchId = ?", (status, match_id))


def get_stats() -> dict:
    """Return dashboard totals and a category breakdown."""
    with _connection() as connection:
        cursor = connection.cursor()
        cursor = _execute(
            cursor,
            "SELECT Type, Status, COUNT(*) AS Count FROM Items GROUP BY Type, Status"
        )
        totals = cursor.fetchall()
        total_columns = tuple(column[0] for column in cursor.description)
        cursor = _execute(
            cursor,
            "SELECT Category, COUNT(*) AS Count FROM Items GROUP BY Category ORDER BY Category"
        )
        categories = cursor.fetchall()
        category_columns = tuple(column[0] for column in cursor.description)
    result = {"lost": 0, "found": 0, "returned": 0, "by_category": {}}
    for row in totals:
        decoded = _decode_row(row, total_columns)
        if decoded["Status"] == "returned":
            result["returned"] += decoded["Count"]
        elif decoded["Type"] in {"lost", "found"}:
            result[decoded["Type"]] += decoded["Count"]
    result["by_category"] = {
        _decode_row(row, category_columns)["Category"]: _decode_row(row, category_columns)["Count"]
        for row in categories
    }
    return result
