"""Pure Python Kick account registration via email."""

import time
from typing import Optional
from .session import KickSession


class KickSignup:
    """Handles Kick email-based account registration."""

    def __init__(self, session: KickSession = None):
        """Create a signup handler.

        Args:
            session: Existing KickSession or None to create a new one.
        """
        self._s = session or KickSession()
        self._temp_token: Optional[str] = None

    def request_verification(self, email: str) -> dict:
        """Request an email verification code.

        Args:
            email: Email address to send the code to.

        Returns:
            Response dict. 204 means code queued for delivery.
        """
        return self._s.post("/api/v1/signup/verify/email", {"email": email})

    def verify_code(self, email: str, code: str) -> dict:
        """Verify the email verification code.

        On success, stores the temporary token for subsequent steps.

        Args:
            email: Email address used for verification.
            code: Verification code from the email inbox.

        Returns:
            Response dict with verification result.
        """
        result = self._s.post(
            "/api/v1/signup/verify/code", {"email": email, "code": code}
        )
        token = result.get("token") or result.get("access_token")
        if token:
            self._temp_token = token
            self._s.set_access_token(token)
        return result

    def set_username(self, username: str) -> dict:
        """Set the username for the new account.

        Args:
            username: Desired Kick username.

        Returns:
            Response dict.
        """
        return self._s.post("/api/v1/signup/verify/username", {"username": username})

    def agree_terms(self) -> dict:
        """Accept the Kick terms of service.

        Returns:
            Response dict.
        """
        return self._s.post("/api/v1/signup/agreed-terms", {})

    def complete_signup(self) -> dict:
        """Complete the registration and retrieve the access token.

        Returns:
            Response dict with access_token on success.
        """
        result = self._s.post("/api/v1/signup/complete", {})
        token = result.get("access_token") or result.get("token")
        if token:
            self._s.set_access_token(token)
        return result

    def full_flow(self, email: str, username: str, code: str) -> dict:
        """Run the complete registration flow with a pre-received code.

        Args:
            email: Email address for the account.
            username: Desired Kick username.
            code: Verification code from the email inbox.

        Returns:
            Dict with access_token on success, or error details.
        """
        result = self.verify_code(email, code)
        if result.get("_status", 200) >= 400:
            return {"error": "Code verification failed", "detail": result}

        result = self.set_username(username)
        if result.get("_status", 200) >= 400:
            return {"error": "Username setup failed", "detail": result}

        result = self.agree_terms()
        if result.get("_status", 200) >= 400:
            return {"error": "Terms agreement failed", "detail": result}

        result = self.complete_signup()
        if result.get("_status", 200) >= 400:
            return {"error": "Signup completion failed", "detail": result}

        access_token = result.get("access_token") or result.get("token")
        if access_token:
            return {"access_token": access_token, "email": email, "username": username}

        return {"error": "No access token in response", "detail": result}

    def close(self):
        """Close the underlying HTTP session."""
        self._s.close()
