"""Kick.com Python SDK — main client class."""

from typing import Optional
from .session import KickSession
from .auth import KickAuth
from .api.channels import ChannelAPI
from .api.livestreams import LivestreamAPI
from .api.chat import ChatAPI
from .api.users import UserAPI


class KickClient:
    """Main entry point for the Kick.com API.

    Usage:
        # Public (no auth)
        client = KickClient()
        cats = client.livestreams.get_categories()
        channel = client.channels.get("xqc")

        # Authenticated
        client = KickClient(access_token="USER_ID|TOKEN")
        me = client.users.get_me()
        client.channels.follow(668)
    """

    def __init__(
        self,
        proxy: str = None,
        device_info: dict = None,
        user_agent: str = None,
        access_token: str = None,
    ):
        """Create a new Kick API client.

        Args:
            proxy: HTTP/HTTPS proxy URL.
            device_info: Dict of device properties for Kasada fingerprinting.
            user_agent: Browser User-Agent string.
            access_token: Kick access token for authenticated requests.
        """
        self._session = KickSession(device_info=device_info, user_agent=user_agent)
        if proxy:
            self._session._session.proxies = {"http": proxy, "https": proxy}
        if access_token:
            self._session.set_access_token(access_token)

        self._auth = KickAuth(self._session)
        self._channels = ChannelAPI(self._session)
        self._livestreams = LivestreamAPI(self._session)
        self._chat = ChatAPI(self._session)
        self._users = UserAPI(self._session)

    # -- Properties -------------------------------------------------------

    @property
    def auth(self) -> KickAuth:
        """Authentication handler (Google OAuth, token management)."""
        return self._auth

    @property
    def channels(self) -> ChannelAPI:
        """Channel operations: get, follow, unfollow, feed."""
        return self._channels

    @property
    def livestreams(self) -> LivestreamAPI:
        """Content discovery: categories, clips, trending tags."""
        return self._livestreams

    @property
    def chat(self) -> ChatAPI:
        """Chat operations: messages, bans, moderation rules."""
        return self._chat

    @property
    def users(self) -> UserAPI:
        """User operations: profile, updates, silenced users."""
        return self._users

    @property
    def access_token(self) -> Optional[str]:
        """The current access token, or None if not authenticated."""
        return self._session._access_token

    @property
    def is_authenticated(self) -> bool:
        """True if an access token is set."""
        return self._session._access_token is not None

    @property
    def cookies(self) -> dict:
        """Session cookies for debugging."""
        return self._session.cookies

    # -- Auth -------------------------------------------------------------

    def login(self, access_token: str):
        """Set an existing access token for authenticated requests."""
        self._session.set_access_token(access_token)

    def login_with_google(self, google_id_token: str) -> dict:
        """Login with a Google ID token (OAuth → Firebase → Kick)."""
        return self._auth.login_with_google_id_token(google_id_token)

    def login_with_firebase(self, firebase_id_token: str) -> dict:
        """Login with a Firebase ID token."""
        return self._auth.login_with_firebase_token(firebase_id_token)

    # -- Utility API ------------------------------------------------------

    def get_resource_urls(self) -> dict:
        """Get CDN and asset URLs used by Kick."""
        return self._session.get("/api/v1/resource-urls")

    def get_presigned_post(self) -> dict:
        """Get an S3 presigned upload URL for file uploads."""
        return self._session.get("/api/v2/presigned-post")

    def get_goal_emotes(self) -> list:
        """Get available channel goal emotes."""
        return self._session.get("/api/v2/channel-goal-emotes")

    def get_subscription_plan(self) -> dict:
        """Get subscription plan information."""
        return self._session.get("/api/v1/subscriptions/plan")

    def get_payment_history(self) -> dict:
        """Get payment history."""
        return self._session.get("/api/v1/subscriptions/payments-history")

    # -- Session ----------------------------------------------------------

    @property
    def session(self) -> KickSession:
        """The underlying KickSession for low-level API access."""
        return self._session

    def close(self):
        """Close the underlying HTTP session."""
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
