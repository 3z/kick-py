<p align="center">
  <img src="https://kick.com/img/kick-logo.svg" alt="Kick SDK" width="320">
</p>

<h1 align="center">Kick Python SDK</h1>

<p align="center">
  <strong>Pure Python client for the Kick.com API</strong><br>
  No browser required — Cloudflare bypass, Kasada solver, email signup, real-time chat
</p>

<p align="center">
  <a href="#installation"><img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python"></a>
  <a href="#license"><img src="https://img.shields.io/badge/license-MIT-green" alt="License"></a>
  <a href="#tested"><img src="https://img.shields.io/badge/tests-25%2F25%20passing-brightgreen" alt="Tests"></a>
</p>

---

## Features

- **Pure Python** — No browser, no Selenium, no Playwright. Just `tls_client`.
- **Cloudflare Bypass** — TLS fingerprint spoofing via Chrome 124 impersonation.
- **Kasada Solver** — SHA-256 proof-of-work header generation (server-validated).
- **Email Signup** — Full registration flow: request code → verify → set username → complete.
- **Authenticated API** — Follow/unfollow, chat, profile updates, clips, subscriptions.
- **Real-time Chat** — Pusher WebSocket client for live chat messages.
- **Data Models** — Proper dataclasses built from real API responses.
- **Email Utilities** — TempMail, IMAP, and Gmail inbox readers for verification codes.
- **Batch Operations** — Mass account creation and parallel API operations.

## Installation

```bash
pip install tls_client
git clone https://github.com/your-username/kick-sdk.git
cd kick-sdk
```

Requirements:
- Python 3.10+
- `tls_client` — TLS fingerprint spoofing
- `websocket-client` — Pusher WebSocket chat
- `requests` — Email API utilities

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
print(f"  {channel.slug}: id={channel.id}, banned={channel.is_banned}")
print(f"  Playback: {channel.playback_url}")
```

### Authenticated API

```python
from kick_sdk import KickClient

TOKEN = "367971611|WVud8x3i2lMvN39c5yDJLA6siGu0hiDlhM46rFft"
client = KickClient(access_token=TOKEN)

# User profile
me = client.users.get_me()
print(f"Logged in as: {me.username} (id={me.id})")
print(f"Channel: {me.channel.slug}")

# Follow / unfollow
client.channels.follow(668)    # Follow xQc
client.channels.unfollow(668)  # Unfollow

# Update profile
client.users.update_profile({"bio": "Hello world!"})

# Content
clips = client.livestreams.get_clips()
tags = client.livestreams.get_trending_tags()
rules = client.chat.get_moderation_rules()

# Utility
urls = client.get_resource_urls()        # CDN URLs
upload = client.get_presigned_post()     # S3 upload
plans = client.get_subscription_plan()   # Subs
```

### Email Signup

```python
from kick_sdk import KickClient
from kick_sdk.email_utils import TempMailInbox

# Create temp email
inbox = TempMailInbox()
email = inbox.create()

client = KickClient()

# Request verification code
result = client._session.post("/api/v1/signup/verify/email", {"email": email})
# → 204 No Content (code sent to inbox)

# Wait for code
code = inbox.wait_for_code(timeout=120)
print(f"Code: {code}")

# Verify code
result = client._session.post("/api/v1/signup/verify/code", {
    "email": email, "code": code
})

# Complete signup
client._session.post("/api/v1/signup/verify/username", {"username": "myuser"})
client._session.post("/api/v1/signup/agreed-terms", {})
result = client._session.post("/api/v1/signup/complete", {})

print(f"Token: {result.get('access_token')}")
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   KickClient                        │
├─────────────────────────────────────────────────────┤
│  session.py     TLS spoofing + CSRF + Kasada        │
│  auth.py        OAuth flow + token management       │
│  signup.py      Email registration flow             │
│  models.py      Data classes (User, Channel, etc.)  │
├─────────────────────────────────────────────────────┤
│  api/                                               │
│  ├── channels.py    Follow, unfollow, channel info  │
│  ├── livestreams.py Categories, clips, tags         │
│  ├── chat.py        Messages, moderation            │
│  └── users.py       Profile, blocked users          │
├─────────────────────────────────────────────────────┤
│  websocket/                                         │
│  └── pusher.py      Real-time chat WebSocket        │
├─────────────────────────────────────────────────────┤
│  email_utils.py    TempMail, IMAP, Gmail inbox      │
│  batch.py          Mass account operations          │
└─────────────────────────────────────────────────────┘
```

## API Coverage

### Public Endpoints (No Auth)

| Endpoint | Method | Returns |
|---|---|---|
| `client.livestreams.get_categories()` | GET /api/v1/categories | `list[Category]` |
| `client.channels.get(slug)` | GET /api/v2/channels/{slug} | `Channel` |

### Authenticated Endpoints

| Endpoint | Method | Returns |
|---|---|---|
| `client.users.get_me()` | GET /api/v1/user | `User` |
| `client.users.update_profile(data)` | POST /api/v2/update_profile | `dict` |
| `client.users.get_silenced()` | GET /api/v2/silenced-users | `dict` |
| `client.users.get_livestreams()` | GET /api/v1/user/livestreams | `list` |
| `client.channels.follow(channel_id)` | POST /api/v1/channels/user/subscribe | `FollowResult` |
| `client.channels.unfollow(channel_id)` | POST /api/v1/channels/user/unsubscribe | `FollowResult` |
| `client.channels.get_following()` | GET /api/v2/channels/followed | `dict` |
| `client.channels.get_feed()` | GET /api/v2/channels/feed-activities | `list` |
| `client.livestreams.get_subcategories()` | GET /api/v1/subcategories | `dict` |
| `client.livestreams.get_clips()` | GET /api/v2/clips | `dict` |
| `client.livestreams.get_trending_tags()` | GET /api/v2/tags/trending | `list` |
| `client.chat.get_moderation_rules()` | GET /api/v2/moderation-rules | `list` |
| `client.get_resource_urls()` | GET /api/v1/resource-urls | `dict` |
| `client.get_presigned_post()` | GET /api/v2/presigned-post | `dict` |
| `client.get_subscription_plan()` | GET /api/v1/subscriptions/plan | `dict` |
| `client.get_payment_history()` | GET /api/v1/subscriptions/payments-history | `dict` |
| `client.get_goal_emotes()` | GET /api/v2/channel-goal-emotes | `list` |

## Data Models

```python
@dataclass
class User:
    id: int
    username: str
    email: Optional[str]
    bio: Optional[str]
    profile_pic: Optional[str]
    birthdate: Optional[str]
    channel: Optional[StreamerChannel]
    instagram: Optional[str]
    twitter: Optional[str]
    youtube: Optional[str]
    discord: Optional[str]
    tiktok: Optional[str]
    facebook: Optional[str]
    is_affiliate: bool
    is_over_18: bool

@dataclass
class Channel:
    id: int
    user_id: int
    slug: str
    is_banned: bool
    playback_url: Optional[str]  # Amazon IVS JWT
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

## Token Format

```
{user_id}|{token_string}
```

Example: `367971611|WVud8x3i2lMvN39c5yDJLA6siGu0hiDlhM46rFft`

The token is a static Bearer token that persists across sessions. Store and reuse it.

## Registration Flow

Detailed in [`KICK_SIGNUP_FLOW.md`](../KICK_SIGNUP_FLOW.md).

```
1. POST /api/v1/signup/verify/email  → 204 (code sent to inbox)
2. Check inbox                        → get 4-6 digit code
3. POST /api/v1/signup/verify/code    → 200 (temp token)
4. POST /api/v1/signup/verify/username → 204
5. POST /api/v1/signup/agreed-terms   → 200
6. POST /api/v1/signup/complete       → 200 (access_token)
```

> **Note:** Kick blocks disposable email domains (oakon.com, guerrillamailblock.com, etc.). Use a real email inbox. The SDK provides `email_utils.py` with `TempMailInbox`, `IMAPInbox`, and `GmailInbox` for reading verification codes.

## Security Layers (Bypassed)

| Layer | How We Handle It |
|---|---|
| **Cloudflare WAF** | `tls_client` with `chrome_124` TLS fingerprint |
| **CSRF Protection** | `XSRF-TOKEN` cookie → `X-XSRF-TOKEN` header |
| **Kasada MobileShield** | SHA-256 PoW solver generates valid `x-kpsdk-*` headers |
| **API Auth** | Bearer token in `Authorization` header |

## Tests

```bash
# Unit + API tests (no auth needed)
python tests/test_sdk.py

# Full integration test (needs real token)
python -c "
from kick_sdk import KickClient
client = KickClient(access_token='YOUR_TOKEN')
me = client.users.get_me()
print(f'OK: {me.username}')
"
```

**25/25 tests passing** — session, CSRF, Kasada PoW, public API, authenticated API, email utils, models.

## Project Structure

```
kick-sdk/
├── kick_sdk/
│   ├── __init__.py          # Public API
│   ├── client.py            # KickClient
│   ├── session.py           # TLS + CSRF + Kasada
│   ├── auth.py              # OAuth + token management
│   ├── signup.py            # Email registration
│   ├── models.py            # Data classes
│   ├── email_utils.py       # Inbox readers
│   ├── batch.py             # Mass operations
│   ├── api/
│   │   ├── channels.py
│   │   ├── livestreams.py
│   │   ├── chat.py
│   │   └── users.py
│   └── websocket/
│       └── pusher.py
├── kasada_solver/
│   └── solver.py            # SHA-256 PoW + header gen
├── tests/
│   ├── test_sdk.py          # Unit tests
│   └── test_integration.py  # Integration demo
├── KICK_SIGNUP_FLOW.md      # Signup flow documentation
└── README.md
```

## License

MIT

---

<p align="center">
  <sub>Built by reverse engineering the com.kick.mobile v40.18.1 APK.</sub><br>
  <sub>For educational and interoperability purposes only.</sub>
</p>
