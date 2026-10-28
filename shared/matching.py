"""Simple, explainable scoring for lost-and-found suggestions."""

from __future__ import annotations

import json
from typing import Any

from shared import db


MATCH_THRESHOLD = 0.4


def _tags(item: dict[str, Any]) -> set[str]:
    """Normalise tags from either a database list or stored JSON/text value."""
    values = item.get("Tags", item.get("tags", [])) or []
    if isinstance(values, str):
        try:
            values = json.loads(values)
        except json.JSONDecodeError:
            values = values.split(",")
    return {str(value).strip().casefold() for value in values if str(value).strip()}


def score(item_a: dict, item_b: dict) -> float:
    """Return the weighted tag, category, and location similarity score."""
    tags_a, tags_b = _tags(item_a), _tags(item_b)
    union = tags_a | tags_b
    jaccard = len(tags_a & tags_b) / len(union) if union else 0.0
    category_a = str(item_a.get("Category", item_a.get("category", ""))).strip().casefold()
    category_b = str(item_b.get("Category", item_b.get("category", ""))).strip().casefold()
    location_a = str(item_a.get("Location", item_a.get("location", ""))).strip().casefold()
    location_b = str(item_b.get("Location", item_b.get("location", ""))).strip().casefold()
    return round(0.6 * jaccard + 0.3 * float(bool(category_a and category_a == category_b)) + 0.1 * float(bool(location_a and location_a == location_b)), 4)


def find_and_store_matches(new_item_id: int) -> list[dict]:
    """Store qualifying opposite-type matches and return the suggestions created."""
    new_item = db.get_item(new_item_id)
    if not new_item or new_item["Status"] != "open":
        return []
    opposite_type = "found" if new_item["Type"] == "lost" else "lost"
    existing_pairs = {
        (match["LostItemId"], match["FoundItemId"])
        for match in db.list_matches()
    }
    suggestions: list[dict] = []
    for candidate in db.list_items(type=opposite_type, status="open", limit=200):
        candidate_score = score(new_item, candidate)
        if candidate_score < MATCH_THRESHOLD:
            continue
        lost_id = new_item_id if new_item["Type"] == "lost" else candidate["ItemId"]
        found_id = candidate["ItemId"] if new_item["Type"] == "lost" else new_item_id
        if (lost_id, found_id) in existing_pairs:
            continue
        match_id = db.create_match(lost_id, found_id, candidate_score)
        suggestions.append({"MatchId": match_id, "Item": candidate, "Score": candidate_score})
    if suggestions:
        db.update_item_status(new_item_id, "matched")
        for suggestion in suggestions:
            db.update_item_status(suggestion["Item"]["ItemId"], "matched")
    return suggestions
