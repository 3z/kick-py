"""Livestream, category, and clip operations."""

from ..models import Category


class LivestreamAPI:
    """Content discovery API methods."""

    def __init__(self, session):
        """Internal. Use KickClient.livestreams instead."""
        self._s = session

    def get_categories(self) -> "list[Category]":
        """Get all top-level categories.

        Returns:
            List of Category objects (id, name, slug, icon).
        """
        data = self._s.get("/api/v1/categories")
        return [Category.from_dict(d) for d in data] if isinstance(data, list) else []

    def get_subcategories(self) -> dict:
        """Get paginated subcategories with viewer counts and banners.

        Returns:
            Paginated dict with subcategory data.
        """
        return self._s.get("/api/v1/subcategories")

    def get_clips(self, sort: str = "view", time: str = "week") -> dict:
        """Get popular clips.

        Args:
            sort: Sort order ("view", "time")
            time: Time window ("week", "month", "all")

        Returns:
            Dict with clips data.
        """
        return self._s.get(f"/api/v2/clips?sort={sort}&time={time}")

    def get_trending_tags(self) -> list:
        """Get trending stream tags.

        Returns:
            List of trending tag dicts with display_label.
        """
        return self._s.get("/api/v2/tags/trending")
