"""Livestream, category, and clip operations."""

from ..models import Category, Subcategory, Clip


class LivestreamAPI:
    def __init__(self, session):
        self._s = session

    def get_categories(self) -> list[Category]:
        """Get all top-level categories."""
        data = self._s.get("/api/v1/categories")
        return [Category.from_dict(d) for d in data] if isinstance(data, list) else []

    def get_subcategories(self) -> dict:
        """Get paginated subcategories with viewer counts."""
        return self._s.get("/api/v1/subcategories")

    def get_clips(self, sort: str = "view", time: str = "week") -> dict:
        """Get clips."""
        return self._s.get(f"/api/v2/clips?sort={sort}&time={time}")

    def get_trending_tags(self) -> list:
        """Get trending tags."""
        return self._s.get("/api/v2/tags/trending")
