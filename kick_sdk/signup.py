"""
Pure Python Kick account registration via email.
Uses tls_client for Cloudflare bypass, no browser required.

Flow:
    1. POST /api/v1/signup/verify/email -> sends verification code to email
    2. Check inbox -> get code
    3. POST /api/v1/signup/verify/code -> verify code, get temp token
    4. POST /api/v1/signup/verify/username -> set username
    5. POST /api/v1/signup/agreed-terms -> accept TOS  
    6. POST /api/v1/signup/complete -> get access_token

Requires a real email inbox (temp email domains are blocked by Kick).
Use email_utils.py for TempMailInbox, IMAPInbox, or GmailInbox.
"""

import time
from typing import Optional
from .session import KickSession


class KickSignup:
    """Pure Python Kick account registration."""

    def __init__(self, session: KickSession = None):
        self._s = session or KickSession()
        self._temp_token: Optional[str] = None

    def request_verification(self, email: str) -> dict:
        """Request email verification code.
        
        Returns dict with status. 204 = email queued for sending.
        """
        return self._s.post("/api/v1/signup/verify/email", {"email": email})

    def verify_code(self, email: str, code: str) -> dict:
        """Verify the email code.
        
        On success, stores the temporary token for subsequent steps.
        Returns dict with verification result.
        """
        result = self._s.post("/api/v1/signup/verify/code", {
            "email": email,
            "code": code,
        })
        # Extract temp token if present
        token = result.get("token") or result.get("access_token")
        if token:
            self._temp_token = token
            self._s.set_access_token(token)
        return result

    def set_username(self, username: str) -> dict:
        """Set username for the new account."""
        return self._s.post("/api/v1/signup/verify/username", {
            "username": username,
        })

    def agree_terms(self) -> dict:
        """Agree to terms of service."""
        return self._s.post("/api/v1/signup/agreed-terms", {})

    def complete_signup(self) -> dict:
        """Complete the registration.
        
        Returns dict with access_token on success.
        """
        result = self._s.post("/api/v1/signup/complete", {})
        token = result.get("access_token") or result.get("token")
        if token:
            self._s.set_access_token(token)
        return result

    def full_flow(
        self,
        email: str,
        username: str,
        code: str,
    ) -> dict:
        """Complete registration flow with an already-received code.
        
        Args:
            email: Email address for the account
            username: Desired Kick username
            code: Verification code received via email
            
        Returns:
            dict with access_token on success, or error details
        """
        # Step 1: Verify code
        result = self.verify_code(email, code)
        if result.get("_status", 200) >= 400:
            return {"error": "Code verification failed", "detail": result}

        # Step 2: Set username
        result = self.set_username(username)
        if result.get("_status", 200) >= 400:
            return {"error": "Username setup failed", "detail": result}

        # Step 3: Agree to terms
        result = self.agree_terms()
        if result.get("_status", 200) >= 400:
            return {"error": "Terms agreement failed", "detail": result}

        # Step 4: Complete
        result = self.complete_signup()
        if result.get("_status", 200) >= 400:
            return {"error": "Signup completion failed", "detail": result}

        access_token = result.get("access_token") or result.get("token")
        if access_token:
            return {
                "access_token": access_token,
                "email": email,
                "username": username,
            }

        return {"error": "No access token in response", "detail": result}

    def close(self):
        self._s.close()
