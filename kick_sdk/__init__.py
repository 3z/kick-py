from .client import KickClient
from .models import (
    User, Channel, Category, Subcategory, Clip,
    ModerationRule, GoalEmote, TrendingTag,
    FollowResult, AuthTokens, ChatMessage,
    StreamerChannel,
)
from .session import KickSession
from .email_utils import TempMailInbox, IMAPInbox, GmailInbox

__version__ = "0.2.0"
