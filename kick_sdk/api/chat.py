"""Chat operations."""


class ChatAPI:
    def __init__(self, session):
        self._s = session

    def send_message(self, channel_id: int, content: str) -> dict:
        """Send a chat message."""
        return self._s.post("/api/v2/messages/send", {
            "channel_id": channel_id,
            "content": content,
        })

    def get_messages(self, channel_id: int) -> dict:
        """Get chat messages."""
        return self._s.post("/api/v2/messages", {"channel_id": channel_id})

    def ban_user(self, channel_id: int, username: str) -> dict:
        """Ban a user from chat (mod only)."""
        return self._s.post("/api/v1/chat/ban", {
            "channel_id": channel_id,
            "username": username,
        })

    def unban_user(self, channel_id: int, username: str) -> dict:
        """Unban a user from chat (mod only)."""
        return self._s.post("/api/v1/chat/unban", {
            "channel_id": channel_id,
            "username": username,
        })

    def get_moderation_rules(self) -> list:
        """Get moderation rules."""
        return self._s.get("/api/v2/moderation-rules")
