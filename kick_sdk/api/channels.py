"""Channel operations: follow, unfollow, get info."""

from ..models import Channel, FollowResult


class ChannelAPI:
    """Channel-related API methods."""

    def __init__(self, session):
        """Internal. Use KickClient.channels instead."""
        self._s = session

    def get(self, slug: str) -> Channel:
        """Get a channel by its slug.

        Args:
            slug: Channel slug (e.g. "xqc", "trainwreckstv")

        Returns:
            Channel object with id, playback_url, is_banned, etc.
        """
        data = self._s.get(f"/api/v2/channels/{slug}")
        return Channel.from_dict(data)

    def follow(self, channel_id: int) -> FollowResult:
        """Follow a channel.

        Args:
            channel_id: Numeric channel ID

        Returns:
            FollowResult with success status and message.
        """
        data = self._s.post("/api/v1/channels/user/subscribe", {"channel_id": channel_id})
        return FollowResult.from_dict(data)

    def unfollow(self, channel_id: int) -> FollowResult:
        """Unfollow a channel.

        Args:
            channel_id: Numeric channel ID

        Returns:
            FollowResult with success status and message.
        """
        data = self._s.post("/api/v1/channels/user/unsubscribe", {"channel_id": channel_id})
        return FollowResult.from_dict(data)

    def get_following(self) -> dict:
        """Get list of followed channels. Requires auth."""
        return self._s.get("/api/v2/channels/followed")

    def get_feed(self) -> list:
        """Get channel feed activities. Requires auth."""
        return self._s.get("/api/v2/channels/feed-activities")
