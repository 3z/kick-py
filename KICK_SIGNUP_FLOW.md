# Kick.com - Signup Flow & API Documentation

## Account Created
```
Token: 367971611|WVud8x3i2lMvN39c5yDJLA6siGu0hiDlhM46rFft
User:  radbrahshop (id: 109161301)
Email: radbrahshop@gmail.com
DOB:   2000-05-26
```

## Registration Flow

### Step 1: Request Email Verification
```http
POST https://kick.com/api/v1/signup/verify/email
Content-Type: application/json
X-XSRF-TOKEN: {csrf_token}

{"email": "user@gmail.com"}
```
Response: `204 No Content` (email verification code sent to inbox)

### Step 2: Verify Code
```http
POST https://kick.com/api/v1/signup/verify/code
Content-Type: application/json
X-XSRF-TOKEN: {csrf_token}

{"email": "user@gmail.com", "code": "123456"}
```
Response: `200` with temp token

### Step 3: Set Username
```http
POST https://kick.com/api/v1/signup/verify/username
Content-Type: application/json
X-XSRF-TOKEN: {csrf_token}

{"username": "desired_username"}
```
Response: `204 No Content`

### Step 4: Agree to Terms
```http
POST https://kick.com/api/v1/signup/agreed-terms
Content-Type: application/json
X-XSRF-TOKEN: {csrf_token}

{}
```
Response: `200`

### Step 5: Complete Signup
```http
POST https://kick.com/api/v1/signup/complete
Content-Type: application/json
X-XSRF-TOKEN: {csrf_token}

{}
```
Response: `200` with `access_token`

### Alternative: Send Code (Rate Limited)
```http
POST https://kick.com/api/v1/signup/send/email
Content-Type: application/json

{"email": "user@gmail.com"}
```
Response: `429` (protected by Kasada, requires validated KP_UIDz cookie)

## Prerequisites for API Calls

1. **CSRF Token**: `GET https://kick.com/sanctum/csrf-cookie` sets `XSRF-TOKEN` cookie. Extract value and send as `X-XSRF-TOKEN` header.

2. **TLS Fingerprint**: Cloudflare blocks non-browser TLS fingerprints. Use `tls_client` with `chrome_124` client identifier.

3. **Kasada**: The `send/email` endpoint is Kasada-protected. Use `verify/email` instead (returns 204, same effect). Kasada is not enforced on verify endpoints.

4. **User Agent**: Must match a real device.
```
Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 Chrome/124.0.6367.179 Mobile Safari/537.36
```

## Authenticated API Endpoints (Confirmed Working)

### User Profile
```http
GET https://kick.com/api/v1/user
Authorization: Bearer {token}
```
Returns: User object with `id`, `email`, `username`, `bio`, `profilepic`, social links, `streamer_channel`

### Follow / Unfollow
```http
POST https://kick.com/api/v1/channels/user/subscribe
POST https://kick.com/api/v1/channels/user/unsubscribe
Authorization: Bearer {token}
Content-Type: application/json

{"channel_id": 668}
```
Returns: `{"status": true, "message": "You have successfully followed xqc"}`

### Following List
```http
GET https://kick.com/api/v2/channels/followed
Authorization: Bearer {token}
```
Returns: `{"channels": []}`

### Update Profile
```http
POST https://kick.com/api/v2/update_profile
Authorization: Bearer {token}
Content-Type: application/json

{"bio": "new bio", "instagram": "myinsta", ...}
```

### Silenced/Blocked Users
```http
GET https://kick.com/api/v2/silenced-users
Authorization: Bearer {token}
```

### Subscriptions
```http
GET https://kick.com/api/v1/subscriptions/plan
GET https://kick.com/api/v1/subscriptions/payments-history
Authorization: Bearer {token}
```

### Clips
```http
GET https://kick.com/api/v2/clips?sort=view&time=week
Authorization: Bearer {token}
```

### Channel Info (No Auth Needed)
```http
GET https://kick.com/api/v2/channels/{slug}
```
Returns: Channel with `id`, `slug`, `playback_url` (JWT token for Amazon IVS)

### Categories (No Auth Needed)
```http
GET https://kick.com/api/v1/categories
```
Returns: Array of `{id, name, slug, icon}` (6 categories)

### Subcategories
```http
GET https://kick.com/api/v1/subcategories
Authorization: Bearer {token}
```
Returns: Paginated subcategories with banners, viewer counts, tags

### Trending Tags
```http
GET https://kick.com/api/v2/tags/trending
Authorization: Bearer {token}
```

### Moderation Rules
```http
GET https://kick.com/api/v2/moderation-rules
Authorization: Bearer {token}
```
Returns: Array of rule classes with levels

### File Upload (S3 Presigned)
```http
GET https://kick.com/api/v2/presigned-post
Authorization: Bearer {token}
```
Returns: S3 upload form with credentials, policy, signature

### Goal Emotes
```http
GET https://kick.com/api/v2/channel-goal-emotes
Authorization: Bearer {token}
```

## Token Format
```
{user_id}|{token_string}
```
Example: `367971611|WVud8x3i2lMvN39c5yDJLA6siGu0hiDlhM46rFft`

The token is a static bearer token. It persists across sessions until revoked.

## Cloudflare Bypass

Kick uses Cloudflare WAF. The following works:
- `tls_client` Python library with `chrome_124` client identifier
- Proper browser-like headers (User-Agent, Accept, Accept-Language, Origin, Referer)
- CSRF token from `/sanctum/csrf-cookie` baked into each request

## Kasada / Anti-Bot

Kasada MobileShield SDK is present in the Android app but not enforced on:
- All GET endpoints
- Most POST endpoints
- `verify/email`, `verify/code`, `verify/username`, `agreed-terms`, `complete`

Only `send/email` and `send/sms` require validated Kasada session (KP_UIDz cookie).
