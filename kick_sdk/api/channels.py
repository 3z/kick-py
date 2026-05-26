"""Channel operations: follow, unfollow, get info, search."""

from ..models import Channel, FollowResult


class ChannelAPI:
    def __init__(self, session):
        self._s = session

    def get(self, slug: str) -> Channel:
        """Get channel by slug."""
        data = self._s.get(f"/api/v2/channels/{slug}")
        return Channel.from_dict(data)

    def follow(self, channel_id: int) -> FollowResult:
        """Follow a channel."""
        data = self._s.post("/api/v1/channels/user/subscribe", {"channel_id": channel_id})
        return FollowResult.from_dict(data)

    def unfollow(self, channel_id: int) -> FollowResult:
        """Unfollow a channel."""
        data = self._s.post("/api/v1/channels/user/unsubscribe", {"channel_id": channel_id})
        return FollowResult.from_dict(data)

    def get_following(self) -> dict:
        """Get list of followed channels."""
        return self._s.get("/api/v2/channels/followed")

    def get_feed(self) -> list:
        """Get channel feed activities."""
        return self._s.get("/api/v2/channels/feed-activities")
