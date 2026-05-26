"""Kick authentication: token management and Google OAuth flow."""

import json
import time
from typing import Optional
import tls_client

FIREBASE_API_KEY = "AIzaSyBt03MQfMaVa2QNnADsIUgT1LBOOx7SET0"
GOOGLE_CLIENT_ID = (
    "582091208538-bkth7bpk2po5d70rar2735dsfjd7crts" ".apps.googleusercontent.com"
)
GOOGLE_REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"


class KickAuth:
    """Authentication handler for Kick accounts."""

    def __init__(self, session: "KickSession"):
        """Internal. Use KickClient.auth instead."""
        self._session = session

    def google_oauth_url(self, state: str = "kick_login") -> str:
        """Generate a Google OAuth consent URL.

        Returns:
            URL string to open in a browser.
        """
        params = {
            "client_id": GOOGLE_CLIENT_ID,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "state": state,
        }
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        return f"https://accounts.google.com/o/oauth2/v2/auth?{qs}"

    def google_exchange_code(self, code: str) -> dict:
        """Exchange a Google OAuth authorization code for tokens."""
        import requests

        r = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
                "code": code,
            },
        )
        return r.json()

    def google_refresh_token(self, refresh_token: str) -> dict:
        """Refresh a Google access token."""
        import requests

        r = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        return r.json()

    def firebase_signin_with_google(self, google_id_token: str) -> dict:
        """Exchange a Google ID token for a Firebase ID token."""
        fb = tls_client.Session(client_identifier=self._session.CLIENT_ID)
        r = fb.post(
            f"https://identitytoolkit.googleapis.com/v1/"
            f"accounts:signInWithIdp?key={FIREBASE_API_KEY}",
            json={
                "postBody": f"id_token={google_id_token}" f"&providerId=google.com",
                "requestUri": "https://kick.com",
                "returnSecureToken": True,
            },
        )
        return r.json()

    def exchange_firebase_token(self, firebase_id_token: str) -> dict:
        """Exchange a Firebase ID token for a Kick access token."""
        return self._session.post(
            "/api/v1/google-mobile-login", {"token": firebase_id_token}
        )

    def get_kick_token(self, google_id_token: str) -> Optional[dict]:
        """Full OAuth flow: Google ID token → Firebase → Kick access token."""
        fb_result = self.firebase_signin_with_google(google_id_token)
        if "idToken" not in fb_result:
            return {
                "error": fb_result.get("error", {}).get(
                    "message", "Firebase auth failed"
                ),
                "_raw": fb_result,
            }

        firebase_token = fb_result["idToken"]
        kick_result = self.exchange_firebase_token(firebase_token)
        if kick_result.get("_status", 200) >= 400:
            return kick_result

        access_token = kick_result.get("access_token", kick_result.get("token", ""))
        if access_token:
            self._session.set_access_token(access_token)
        return kick_result

    def login_with_google_id_token(self, google_id_token: str) -> dict:
        """Login using an existing Google ID token."""
        return self.get_kick_token(google_id_token)

    def login_with_firebase_token(self, firebase_id_token: str) -> dict:
        """Login using an existing Firebase ID token."""
        r = self._session.post(
            "/api/v1/google-mobile-login", {"token": firebase_id_token}
        )
        if r.get("_status", 200) >= 400:
            return r
        access_token = r.get("access_token", r.get("token", ""))
        if access_token:
            self._session.set_access_token(access_token)
        return r

    def verify_token(self) -> dict:
        """Verify that the current access token is valid."""
        return self._session.get("/api/v1/account")

    def get_profile(self) -> dict:
        """Get the authenticated user's profile."""
        return self._session.get("/api/v2/user")
