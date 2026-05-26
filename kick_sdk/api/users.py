"""User profile operations."""

from ..models import User


class UserAPI:
    """User-related API methods."""

    def __init__(self, session):
        """Internal. Use KickClient.users instead."""
        self._s = session

    def get_me(self) -> User:
        """Get the authenticated user's profile.

        Returns:
            User object with id, username, email, channel, socials.
        """
        data = self._s.get("/api/v1/user")
        return User.from_dict(data)

    def update_profile(self, data: dict) -> dict:
        """Update profile fields.

        Args:
            data: Dict of fields to update (bio, instagram, twitter, etc.)

        Returns:
            API response dict.
        """
        return self._s.post("/api/v2/update_profile", data)

    def get_silenced(self) -> dict:
        """Get silenced/blocked users list.

        Returns:
            Paginated dict of silenced users.
        """
        return self._s.get("/api/v2/silenced-users")

    def get_livestreams(self) -> list:
        """Get the authenticated user's livestreams.

        Returns:
            List of livestream objects.
        """
        return self._s.get("/api/v1/user/livestreams")
