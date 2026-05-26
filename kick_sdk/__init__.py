"""Kick.com Python SDK — programmatic access to Kick's API."""

from .client import KickClient
from .session import KickSession
from .models import (
    User, Channel, Category, Subcategory, Clip,
    ModerationRule, GoalEmote, TrendingTag,
    FollowResult, AuthTokens, ChatMessage,
    StreamerChannel,
)
from .email_utils import TempMailInbox, IMAPInbox, GmailInbox

__version__ = "0.2.0"
__all__ = [
    "KickClient", "KickSession",
    "User", "Channel", "Category", "Subcategory", "Clip",
    "ModerationRule", "GoalEmote", "TrendingTag",
    "FollowResult", "AuthTokens", "ChatMessage",
    "StreamerChannel",
    "TempMailInbox", "IMAPInbox", "GmailInbox",
]
