"""User profile operations."""

from ..models import User


class UserAPI:
    def __init__(self, session):
        self._s = session

    def get_me(self) -> User:
        """Get own user profile."""
        data = self._s.get("/api/v1/user")
        return User.from_dict(data)

    def update_profile(self, data: dict) -> dict:
        """Update own profile fields."""
        return self._s.post("/api/v2/update_profile", data)

    def get_silenced(self) -> dict:
        """Get silenced/blocked users."""
        return self._s.get("/api/v2/silenced-users")

    def get_livestreams(self) -> list:
        """Get user's livestreams."""
        return self._s.get("/api/v1/user/livestreams")
