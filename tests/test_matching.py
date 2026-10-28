"""Tests for mock-mode repositories and explainable match scoring."""

from __future__ import annotations

import importlib

import pytest


@pytest.fixture()
def mock_db(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_MODE", "mock")
    monkeypatch.setenv("LOSTFOUND_DB_PATH", str(tmp_path / "lostfound.db"))
    from shared import config, db, matching

    importlib.reload(config)
    importlib.reload(db)
    importlib.reload(matching)
    db.init_db()
    return db, matching


def item(item_type: str, **overrides):
    """Create minimum valid item data for tests."""
    data = {
        "Type": item_type,
        "Title": f"{item_type.title()} item",
        "Description": "Test item",
        "Category": "Bottle",
        "Location": "Library",
        "ItemDate": "2026-10-20",
        "Tags": ["bottle", "blue"],
        "ReporterEmail": "demo@student.local",
    }
    data.update(overrides)
    return data


def test_score_uses_tags_category_and_location(mock_db):
    _, matching = mock_db
    assert matching.score(item("lost"), item("found")) == 1.0
    assert matching.score(item("lost", Tags=["keys"]), item("found", Tags=["bottle"], Category="Keys", Location="Hostel")) == 0.0


def test_qualifying_opposite_items_are_stored_as_matches(mock_db):
    db, matching = mock_db
    lost_id = db.create_item(item("lost"))
    found_id = db.create_item(item("found", Title="Found blue bottle"))

    suggestions = matching.find_and_store_matches(found_id)

    assert len(suggestions) == 1
    assert suggestions[0]["Score"] == 1.0
    assert db.list_matches()[0]["LostItemId"] == lost_id
    assert db.get_item(lost_id)["Status"] == "matched"


def test_filters_stats_and_delete_return_image_url(mock_db):
    db, _ = mock_db
    item_id = db.create_item(item("lost", Category="Keys", ImageUrl="/local_uploads/keys.jpg"))

    assert db.list_items(category="Keys")[0]["ItemId"] == item_id
    assert db.get_stats() == {"lost": 1, "found": 0, "returned": 0, "by_category": {"Keys": 1}}
    assert db.delete_item(item_id) == "/local_uploads/keys.jpg"
    assert db.get_item(item_id) is None
