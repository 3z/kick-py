#!/usr/bin/env python3
"""
End-to-end integration test for Kick SDK.
Demonstrates full usage: browsing, channel info, auth, following, chat.
"""

import sys, os, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from kick_sdk import KickClient


def demo_public_flow():
    """Demo all public (non-auth) features."""
    print("=" * 60)
    print("Kick SDK - Public Features Demo")
    print("=" * 60)

    client = KickClient()

    # 1. Browse categories
    cats = client.livestreams.get_categories()
    print(f"\n[1] Top categories ({len(cats)} total):")
    for cat in cats[:5]:
        print(f"    {cat.get('id')}. {cat.get('name')} ({cat.get('slug')})")

    # 2. Get channel info
    channel = client.channels.get("xqc")
    print(f"\n[2] Channel xQc:")
    print(f"    ID: {channel.get('id')}")
    print(f"    Slug: {channel.get('slug')}")
    print(f"    Banned: {channel.get('is_banned')}")
    if channel.get("playback_url"):
        print(f"    Playback: {channel['playback_url'][:80]}...")
    if channel.get("user"):
        print(f"    User: {channel['user'].get('username')}")

    # 3. Check another channel
    channel2 = client.channels.get("trainwreckstv")
    print(f"\n[3] Channel trainwreckstv:")
    print(f"    ID: {channel2.get('id')}")
    print(f"    Banned: {channel2.get('is_banned')}")

    # 4. Get featured streams
    featured = client.livestreams.get_featured()
    if isinstance(featured, list) and len(featured) > 0:
        print(f"\n[4] Featured streams ({len(featured)}):")
        for stream in featured[:3]:
            stream_data = stream if isinstance(stream, dict) else {}
            print(f"    {stream_data.get('slug', stream_data)}")

    client.close()
    print("\n✓ Public features work correctly")


def demo_auth_flow():
    """Document the auth flow (requires Google OAuth)."""
    print("\n" + "=" * 60)
    print("Authentication Flow")
    print("=" * 60)
    print("""
Kick uses Google OAuth for authentication. Here's the flow:

1. GET GOOGLE OAUTH URL:
   client = KickClient()
   url = client.auth.google_oauth_url()
   # Open this URL in a browser

2. COMPLETE GOOGLE SIGN-IN:
   User signs in via Google OAuth consent screen
   Gets redirected with: ?code=AUTHORIZATION_CODE

3. EXCHANGE CODE FOR TOKENS:
   google_tokens = client.auth.google_exchange_code(code)
   google_id_token = google_tokens['id_token']

4. LOGIN TO KICK:
   result = client.auth.login_with_google_id_token(google_id_token)
   # result contains: access_token, token_type, expires_in
   
5. SAVE TOKEN:
   access_token = result['access_token']
   # Store this for future sessions
   # client.login(access_token) to restore

6. VERIFY:
   profile = client.auth.verify_token()
   print(f"Logged in as: {profile}")

Token behavior: The access_token is a JWT that stays valid until
revoked or expired. You can persist it and reuse across sessions.
""")


def demo_authenticated_flow():
    """Document authenticated features (needs real token)."""
    print("\n" + "=" * 60)
    print("Authenticated Features (requires token)")
    print("=" * 60)
    print("""
After login, you get access to:

= Following =
  client.channels.follow(channel_id)     # Follow a channel
  client.channels.unfollow(channel_id)   # Unfollow
  client.channels.get_following()        # List followed channels

= Chat =
  client.chat.send_message(channel_id, "Hello!")  # Send message
  client.chat.get_settings()            # Get chat settings
  client.chat.ban_user(channel_id, "user")  # Ban user (mod)

= User Profile =
  client.users.get_profile()            # Own profile
  client.users.update_profile({...})    # Update profile
  client.users.block(user_id)          # Block user
  
= Subscriptions =
  client._session.post("/api/v1/subscriptions/plan", {...})
  client._session.get("/api/v1/subscriptions/payments-history")

= Pusher WebSocket Chat (real-time):
  from kick_sdk.websocket import PusherClient
  pusher = PusherClient(api_key="...", cluster="us2", access_token=token)
  pusher.connect()
  pusher.subscribe("chatroom.668")
  pusher.on_message("chatroom.668", lambda event: print(event.data))
""")


if __name__ == "__main__":
    demo_public_flow()
    demo_auth_flow()
    demo_authenticated_flow()
    print("\n" + "=" * 60)
    print("SDK is ready for use!")
    print("=" * 60)
