"""Image tagging abstraction for Azure AI Vision and deterministic mock data."""

from __future__ import annotations

import os

from shared.config import APP_MODE, get_secret


def _mock_tags(category_hint: str) -> list[str]:
    """Return predictable tags that make mock-mode demonstrations meaningful."""
    category = (category_hint or "item").strip().lower()
    aliases = {"id card": "card", "electronics": "electronic device", "books": "book"}
    return [aliases.get(category, category), "lost and found"]


def analyze_image(image_bytes: bytes, category_hint: str = "") -> dict:
    """Return Vision tags/caption without requiring Azure during local mock tests."""
    if APP_MODE == "mock":
        tags = _mock_tags(category_hint)
        return {"tags": tags, "caption": f"A {tags[0]} reported to lost and found."}
    try:
        from azure.ai.vision.imageanalysis import ImageAnalysisClient
        from azure.ai.vision.imageanalysis.models import VisualFeatures
        from azure.core.credentials import AzureKeyCredential
    except ImportError as error:
        raise RuntimeError("Azure AI Vision packages are not installed") from error
    features = [VisualFeatures.TAGS]
    if os.getenv("VISION_CAPTION", "off").lower() == "on":
        features.append(VisualFeatures.CAPTION)
    client = ImageAnalysisClient(
        endpoint=get_secret("VisionEndpoint"),
        credential=AzureKeyCredential(get_secret("VisionKey")),
    )
    result = client.analyze(image_data=image_bytes, visual_features=features)
    tags = [tag.name for tag in (result.tags.list if result.tags else []) if tag.confidence >= 0.7]
    caption = result.caption.text if result.caption else ""
    return {"tags": tags, "caption": caption}
