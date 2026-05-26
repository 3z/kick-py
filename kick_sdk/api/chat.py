"""Chat operations: messages, moderation, settings."""


class ChatAPI:
    """Chat-related API methods."""

    def __init__(self, session):
        """Internal. Use KickClient.chat instead."""
        self._s = session

    def send_message(self, channel_id: int, content: str) -> dict:
        """Send a chat message.

        Args:
            channel_id: Numeric channel ID
            content: Message text

        Returns:
            API response dict.
        """
        return self._s.post("/api/v2/messages/send", {
            "channel_id": channel_id,
            "content": content,
        })

    def get_messages(self, channel_id: int) -> dict:
        """Get chat messages for a channel.

        Args:
            channel_id: Numeric channel ID

        Returns:
            Dict with messages.
        """
        return self._s.post("/api/v2/messages", {"channel_id": channel_id})

    def ban_user(self, channel_id: int, username: str) -> dict:
        """Ban a user from chat (requires moderator).

        Args:
            channel_id: Numeric channel ID
            username: Username to ban

        Returns:
            API response dict.
        """
        return self._s.post("/api/v1/chat/ban", {
            "channel_id": channel_id,
            "username": username,
        })

    def unban_user(self, channel_id: int, username: str) -> dict:
        """Unban a user from chat (requires moderator).

        Args:
            channel_id: Numeric channel ID
            username: Username to unban

        Returns:
            API response dict.
        """
        return self._s.post("/api/v1/chat/unban", {
            "channel_id": channel_id,
            "username": username,
        })

    def get_moderation_rules(self) -> list:
        """Get moderation rule classes and levels.

        Returns:
            List of ModerationRule dicts.
        """
        return self._s.get("/api/v2/moderation-rules")
