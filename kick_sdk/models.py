"""Data models for Kick API responses — built from real API responses."""

from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class Category:
    """Top-level Kick category."""

    id: int
    name: str
    slug: str
    icon: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "Category":
        """Create a Category from an API response dict."""
        return cls(
            id=d.get("id", 0), name=d.get("name", ""), slug=d.get("slug", ""), icon=d.get("icon", "")
        )


@dataclass
class Subcategory:
    """Kick subcategory with viewer count, banner, and tags."""

    id: int
    category_id: int
    name: str
    slug: str
    tags: List[str] = field(default_factory=list)
    viewers: int = 0
    is_mature: bool = False
    banner_url: str = ""
    category: Optional[Category] = None

    @classmethod
    def from_dict(cls, d: dict) -> "Subcategory":
        """Create a Subcategory from an API response dict."""
        banner = d.get("banner", {})
        cat = d.get("category", {})
        return cls(
            id=d.get("id", 0),
            category_id=d.get("category_id", 0),
            name=d.get("name", ""),
            slug=d.get("slug", ""),
            tags=d.get("tags", []),
            viewers=d.get("viewers", 0),
            is_mature=d.get("is_mature", False),
            banner_url=banner.get("url", ""),
            category=Category.from_dict(cat) if cat else None,
        )


@dataclass
class StreamerChannel:
    """A user's associated streamer channel."""

    id: int
    user_id: int
    slug: str
    is_banned: bool = False
    playback_url: Optional[str] = None
    vod_enabled: bool = False
    subscription_enabled: bool = False
    is_affiliate: bool = False
    can_host: bool = True
    followers_count: int = 0
    subscriber_count: int = 0

    @classmethod
    def from_dict(cls, d: dict) -> "StreamerChannel":
        """Create a StreamerChannel from an API response dict."""
        return cls(
            id=d.get("id", 0),
            user_id=d.get("user_id", 0),
            slug=d.get("slug", ""),
            is_banned=d.get("is_banned", False),
            playback_url=d.get("playback_url"),
            vod_enabled=d.get("vod_enabled", False),
            subscription_enabled=d.get("subscription_enabled", False),
            is_affiliate=d.get("is_affiliate", False),
            can_host=d.get("can_host", True),
            followers_count=d.get("followers_count", d.get("followersCount", 0)),
            subscriber_count=d.get("subscriber_badges", 0),
        )


@dataclass
class User:
    """A Kick user profile."""

    id: int
    username: str
    email: Optional[str] = None
    bio: Optional[str] = None
    profile_pic: Optional[str] = None
    country: Optional[str] = None
    birthdate: Optional[str] = None
    email_verified_at: Optional[str] = None
    created_at: Optional[str] = None
    agreed_to_terms: bool = False
    is_live: bool = False
    is_affiliate: bool = False
    is_over_18: bool = True
    age_verification_status: str = "NOT_REQUIRED"
    instagram: Optional[str] = None
    twitter: Optional[str] = None
    youtube: Optional[str] = None
    discord: Optional[str] = None
    tiktok: Optional[str] = None
    facebook: Optional[str] = None
    channel: Optional[StreamerChannel] = None

    @classmethod
    def from_dict(cls, d: dict) -> "User":
        """Create a User from an API response dict."""
        ch = d.get("streamer_channel", {})
        return cls(
            id=d.get("id", 0),
            username=d.get("username", ""),
            email=d.get("email"),
            bio=d.get("bio"),
            profile_pic=d.get("profilepic"),
            country=d.get("country"),
            birthdate=d.get("birthdate"),
            email_verified_at=d.get("email_verified_at"),
            created_at=d.get("created_at"),
            agreed_to_terms=d.get("agreed_to_terms", False),
            is_live=d.get("is_live", False),
            is_affiliate=d.get("is_affiliate", False),
            is_over_18=d.get("is_over_18", True),
            age_verification_status=d.get("age_verification_status", "NOT_REQUIRED"),
            instagram=d.get("instagram"),
            twitter=d.get("twitter"),
            youtube=d.get("youtube"),
            discord=d.get("discord"),
            tiktok=d.get("tiktok"),
            facebook=d.get("facebook"),
            channel=StreamerChannel.from_dict(ch) if ch else None,
        )


@dataclass
class Channel:
    """A Kick channel."""

    id: int
    user_id: int
    slug: str
    is_banned: bool = False
    playback_url: Optional[str] = None
    vod_enabled: bool = False
    subscription_enabled: bool = False
    is_affiliate: bool = False
    can_host: bool = True
    followers_count: int = 0

    @classmethod
    def from_dict(cls, d: dict) -> "Channel":
        """Create a Channel from an API response dict."""
        return cls(
            id=d.get("id", 0),
            user_id=d.get("user_id", 0),
            slug=d.get("slug", ""),
            is_banned=d.get("is_banned", False),
            playback_url=d.get("playback_url"),
            vod_enabled=d.get("vod_enabled", False),
            subscription_enabled=d.get("subscription_enabled", False),
            is_affiliate=d.get("is_affiliate", False),
            can_host=d.get("can_host", True),
            followers_count=d.get("followers_count", d.get("followersCount", 0)),
        )


@dataclass
class Clip:
    """A Kick clip."""

    id: str
    title: str
    channel_id: int
    user_id: int
    clip_url: str = ""
    thumbnail_url: str = ""
    duration: int = 0
    views: int = 0
    likes: int = 0
    liked: bool = False
    is_mature: bool = False
    created_at: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "Clip":
        """Create a Clip from an API response dict."""
        return cls(
            id=d.get("id", ""),
            title=d.get("title", ""),
            channel_id=d.get("channel_id", 0),
            user_id=d.get("user_id", 0),
            clip_url=d.get("clip_url", ""),
            thumbnail_url=d.get("thumbnail_url", ""),
            duration=d.get("duration", 0),
            views=d.get("views", 0),
            likes=d.get("likes", 0),
            liked=d.get("liked", False),
            is_mature=d.get("is_mature", False),
            created_at=d.get("created_at", ""),
        )


@dataclass
class ModerationRule:
    """A chat moderation rule class."""

    rule_class: str
    level: int
    levels: List[int] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "ModerationRule":
        """Create a ModerationRule from an API response dict."""
        return cls(
            rule_class=d.get("class", ""),
            level=d.get("level", 0),
            levels=d.get("levels", []),
        )


@dataclass
class GoalEmote:
    """A channel goal emote."""

    id: str
    name: str
    path: str

    @classmethod
    def from_dict(cls, d: dict) -> "GoalEmote":
        """Create a GoalEmote from an API response dict."""
        return cls(id=d.get("id", ""), name=d.get("name", ""), path=d.get("path", ""))


@dataclass
class TrendingTag:
    """A trending stream tag."""

    display_label: str

    @classmethod
    def from_dict(cls, d: dict) -> "TrendingTag":
        """Create a TrendingTag from an API response dict."""
        return cls(display_label=d.get("display_label", ""))


@dataclass
class AuthTokens:
    """Authentication tokens returned after login."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 0

    @classmethod
    def from_dict(cls, d: dict) -> "AuthTokens":
        """Create AuthTokens from an API response dict."""
        return cls(
            access_token=d.get("access_token", d.get("token", "")),
            token_type=d.get("token_type", "Bearer"),
            expires_in=d.get("expires_in", 0),
        )


@dataclass
class FollowResult:
    """Result of a follow/unfollow operation."""

    success: bool
    message: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "FollowResult":
        """Create a FollowResult from an API response dict."""
        return cls(
            success=d.get("status", d.get("unfollowed", False)),
            message=d.get("message", ""),
        )


@dataclass
class ChatMessage:
    """A chat message."""

    id: str = ""
    channel_id: int = 0
    user_id: int = 0
    username: str = ""
    content: str = ""
    created_at: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "ChatMessage":
        """Create a ChatMessage from an API response dict."""
        sender = d.get("sender", d.get("user", {}))
        return cls(
            id=str(d.get("id", "")),
            channel_id=d.get("channel_id", 0),
            user_id=sender.get("id", d.get("user_id", 0)),
            username=sender.get("username", ""),
            content=d.get("content", d.get("message", "")),
            created_at=d.get("created_at", ""),
        )
