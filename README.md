<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://kick.com/img/kick-logo.svg">
    <img src="https://kick.com/img/kick-logo.svg" alt="Kick SDK" width="280">
  </picture>
</p>

<h1 align="center">Kick Python SDK</h1>

<p align="center">
  <strong>Programmatic access to Kick.com — channels, livestreams, clips, chat, and more.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/tests-25%2F25-brightgreen" alt="Tests">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="Code style">
</p>

---

## Features

- **TLS Fingerprinting** — Cloudflare bypass via `tls_client` Chrome 124 impersonation
- **Kasada Protection** — SHA-256 proof-of-work header generation
- **CSRF Handling** — Automatic Laravel Sanctum token management
- **Public API** — Categories, channel info, clips, trending tags
- **Authenticated API** — Follow/unfollow, profile updates, moderation rules
- **Real-time Chat** — Pusher WebSocket client for live messaging
- **Data Models** — Typed dataclasses from real API responses
- **Email Utilities** — TempMail, IMAP, and Gmail inbox readers

## Installation

```bash
pip install tls_client websocket-client requests
git clone https://github.com/3z/kick-python-sdk.git
cd kick-python-sdk
```

## Quick Start

### Public API (No Auth)

```python
from kick_sdk import KickClient

client = KickClient()

# Browse categories
categories = client.livestreams.get_categories()
for cat in categories:
    print(f"  {cat.name} ({cat.slug})")

# Get channel info
channel = client.channels.get("xqc")
print(f"{channel.slug}: id={channel.id}  banned={channel.is_banned}")
```

### Authenticated API

```python
from kick_sdk import KickClient

client = KickClient(access_token="USER_ID|TOKEN")

# Your profile
me = client.users.get_me()
print(f"Logged in as {me.username}  channel: {me.channel.slug}")

# Follow / unfollow
client.channels.follow(668)      # xQc
client.channels.unfollow(668)

# Profile
client.users.update_profile({"bio": "Hello Kick!"})

# Content
clips    = client.livestreams.get_clips()
tags     = client.livestreams.get_trending_tags()
rules    = client.chat.get_moderation_rules()
subs     = client.get_subscription_plan()
upload   = client.get_presigned_post()
```

## API Coverage

| Method | Endpoint | Returns |
|---|---|---|
| `client.livestreams.get_categories()` | `GET /api/v1/categories` | `list[Category]` |
| `client.livestreams.get_subcategories()` | `GET /api/v1/subcategories` | `dict` |
| `client.livestreams.get_clips()` | `GET /api/v2/clips` | `dict` |
| `client.livestreams.get_trending_tags()` | `GET /api/v2/tags/trending` | `list` |
| `client.channels.get(slug)` | `GET /api/v2/channels/{slug}` | `Channel` |
| `client.channels.follow(id)` | `POST /api/v1/channels/user/subscribe` | `FollowResult` |
| `client.channels.unfollow(id)` | `POST /api/v1/channels/user/unsubscribe` | `FollowResult` |
| `client.channels.get_following()` | `GET /api/v2/channels/followed` | `dict` |
| `client.channels.get_feed()` | `GET /api/v2/channels/feed-activities` | `list` |
| `client.users.get_me()` | `GET /api/v1/user` | `User` |
| `client.users.update_profile(data)` | `POST /api/v2/update_profile` | `dict` |
| `client.users.get_silenced()` | `GET /api/v2/silenced-users` | `dict` |
| `client.chat.get_moderation_rules()` | `GET /api/v2/moderation-rules` | `list` |
| `client.get_resource_urls()` | `GET /api/v1/resource-urls` | `dict` |
| `client.get_presigned_post()` | `GET /api/v2/presigned-post` | `dict` |
| `client.get_subscription_plan()` | `GET /api/v1/subscriptions/plan` | `dict` |
| `client.get_payment_history()` | `GET /api/v1/subscriptions/payments-history` | `dict` |
| `client.get_goal_emotes()` | `GET /api/v2/channel-goal-emotes` | `list` |

## Data Models

```python
@dataclass
class User:
    id: int
    username: str
    email: Optional[str]
    bio: Optional[str]
    profile_pic: Optional[str]
    channel: Optional[StreamerChannel]
    instagram: Optional[str]
    twitter: Optional[str]
    youtube: Optional[str]
    discord: Optional[str]
    tiktok: Optional[str]
    is_affiliate: bool
    is_over_18: bool

@dataclass
class Channel:
    id: int
    user_id: int
    slug: str
    is_banned: bool
    playback_url: Optional[str]
    vod_enabled: bool
    subscription_enabled: bool
    followers_count: int

@dataclass
class Category:
    id: int
    name: str
    slug: str
    icon: str

@dataclass
class Clip:
    id: str
    title: str
    channel_id: int
    clip_url: str
    thumbnail_url: str
    duration: int
    views: int
    likes: int
    is_mature: bool

@dataclass
class FollowResult:
    success: bool
    message: str
```

## Architecture

```
kick_sdk/
├── __init__.py              # Public surface
├── client.py                # KickClient entry point
├── session.py               # TLS spoofing + CSRF + Kasada
├── auth.py                  # Token management + Google OAuth
├── signup.py                # Email registration flow
├── models.py                # Typed dataclasses
├── email_utils.py           # TempMail, IMAP, Gmail
├── kasada_solver.py         # SHA-256 PoW + header generation
├── api/
│   ├── channels.py          # Follow, unfollow, info
│   ├── livestreams.py       # Categories, clips, tags
│   ├── chat.py              # Messages, moderation
│   └── users.py             # Profile, silenced
└── websocket/
    └── pusher.py            # Real-time chat WebSocket
```

## Security Layers

| Layer | Implementation |
|---|---|
| Cloudflare WAF | `tls_client` Chrome 124 TLS fingerprint |
| CSRF Protection | `XSRF-TOKEN` cookie → `X-XSRF-TOKEN` header |
| Kasada MobileShield | SHA-256 PoW solver (`kasada_solver.py`) |
| API Authentication | Bearer token in `Authorization` header |

## Token Format

```
{user_id}|{token_string}
```

Store the token and pass it to `KickClient(access_token=...)`. It persists across sessions.

## Tests

```bash
python -m pytest tests/test_sdk.py -v
```

25 tests covering session management, public API, auth endpoints, email utilities, and Kasada solver.

## License

MIT — see [LICENSE](LICENSE)
