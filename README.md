<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://kick.com/img/kick-logo.svg">
    <img src="https://kick.com/img/kick-logo.svg" width="300" alt="Kick">
  </picture>
</p>

<h1 align="center">Python SDK</h1>

<p align="center">
  <strong>A Python client for Kick.com — channels, livestreams, clips, chat, and more.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/tests-25%2F25-brightgreen" alt="Tests">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="Code style">
</p>

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Examples](#examples)
  - [Browsing Content](#browsing-content)
  - [Profile & Social](#profile--social)
  - [Following](#following)
  - [Chat & Moderation](#chat--moderation)
  - [Subscriptions & Payments](#subscriptions--payments)
  - [File Uploads](#file-uploads-s3-presigned)
  - [Real-time Chat (WebSocket)](#real-time-chat-websocket)
  - [Email Signup Flow](#email-signup-flow)
  - [Kasada Solver (Standalone)](#kasada-solver-standalone)
- [API Coverage](#api-coverage)
- [Data Models](#data-models)
- [Architecture](#architecture)
- [Security Layers](#security-layers)
- [Tests](#tests)
- [License](#license)

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
git clone https://github.com/3z/kick-py.git
cd kick-py
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

## Examples

### Browsing content

```python
from kick_sdk import KickClient

client = KickClient()

# Top categories
for cat in client.livestreams.get_categories():
    print(f"  {cat.name} ({cat.slug})  {cat.icon}")

# Channel details
channel = client.channels.get("xqc")
print(f"xQc: banned={channel.is_banned}  vod={channel.vod_enabled}")
print(f"playback: {channel.playback_url}")

# Trending tags
tags = client.livestreams.get_trending_tags()
print([t.display_label for t in tags[:10]])

# Popular clips
clips = client.livestreams.get_clips(sort="view", time="week")
```

### Profile & social

```python
client = KickClient(access_token="USER_ID|YOUR_TOKEN")

me = client.users.get_me()
print(f"@{me.username}  id={me.id}  affiliate={me.is_affiliate}")
print(f"channel: {me.channel.slug}  followers={me.channel.followers_count}")

# Update profile
client.users.update_profile({
    "bio": "Streaming games daily!",
    "instagram": "myinstagram",
    "twitter": "mytwitter",
    "youtube": "myyoutube",
    "discord": "mydiscord",
    "tiktok": "mytiktok",
    "facebook": "myfacebook",
})

# Silenced/blocked users
silenced = client.users.get_silenced()
```

### Following

```python
client = KickClient(access_token="USER_ID|YOUR_TOKEN")

# Follow channels
client.channels.follow(668)   # xQc
client.channels.follow(715)   # trainwreckstv

# List who you follow
following = client.channels.get_following()

# Unfollow
client.channels.unfollow(668)
```

### Chat & moderation

```python
client = KickClient(access_token="USER_ID|YOUR_TOKEN")

# Send a message
client.chat.send_message(channel_id=668, content="Great stream!")

# Moderation rules (auto-mod settings)
rules = client.chat.get_moderation_rules()
for r in rules:
    print(f"  {r.rule_class}: level={r.level}")

# Ban / unban (requires moderator)
client.chat.ban_user(channel_id=668, username="troll_user")
client.chat.unban_user(channel_id=668, username="troll_user")
```

### Subscriptions & payments

```python
client = KickClient(access_token="USER_ID|YOUR_TOKEN")

# Subscription plans
plans = client.get_subscription_plan()

# Payment history
history = client.get_payment_history()

# Channel goal emotes
emotes = client.get_goal_emotes()
```

### File uploads (S3 presigned)

```python
client = KickClient(access_token="USER_ID|YOUR_TOKEN")

presigned = client.get_presigned_post()
# Contains: action, fields for direct S3 upload
print(presigned["formAttributes"]["action"])
```

### Real-time chat (WebSocket)

```python
from kick_sdk.websocket import PusherClient

pusher = PusherClient(
    api_key="eb1d5f283801a755f7ab",
    cluster="us2",
    access_token="USER_ID|YOUR_TOKEN",
)

pusher.connect()
pusher.subscribe("chatroom.668")

@pusher.on_message("chatroom.668")
def on_chat(event):
    print(f"[{event.channel}] {event.data}")

# Send a message via REST
client.chat.send_message(channel_id=668, content="Hello from SDK!")

# Clean up
pusher.disconnect()
```

### Email signup flow

```python
from kick_sdk import KickClient
from kick_sdk.email_utils import GmailInbox

client = KickClient()
inbox = GmailInbox("you@gmail.com", "xxxx xxxx xxxx xxxx")

# Request verification
client._session.post("/api/v1/signup/verify/email", {"email": "you@gmail.com"})

# Wait for code
code = inbox.wait_for_code(timeout=120)
print(f"Code: {code}")

# Complete registration
client._session.post("/api/v1/signup/verify/code", {"email": "you@gmail.com", "code": code})
client._session.post("/api/v1/signup/verify/username", {"username": "myuser"})
client._session.post("/api/v1/signup/agreed-terms", {})
result = client._session.post("/api/v1/signup/complete", {})

print(f"Token: {result.get('access_token')}")
```

### Kasada solver (standalone)

```python
from kick_sdk.kasada_solver import KasadaClient

kasada = KasadaClient()

# Generate headers for a protected request
headers = kasada.get_headers()
# x-kpsdk-v, x-kpsdk-cd, x-kpsdk-ct, x-kpsdk-h, x-kpsdk-dv

# Update state from server response
kasada.update(response_headers)

# Persist state
data = kasada.to_dict()
# ... later ...
kasada = KasadaClient.from_dict(data)
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
