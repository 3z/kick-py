"""Kick API HTTP session with TLS spoofing, CSRF, and Kasada."""

import time
import tls_client
from urllib.parse import unquote
from typing import Optional
import sys

sys.path.insert(0, "/root/kick/kasada_solver")
from solver import KasadaClient


class KickSession:
    """Manages HTTP session with TLS fingerprinting for Cloudflare bypass,
    automatic CSRF token handling, and Kasada anti-bot headers."""

    BASE_URL = "https://kick.com"
    CLIENT_ID = "chrome_124"

    def __init__(self, device_info: dict = None, user_agent: str = None):
        """Create a new Kick API session.

        Args:
            device_info: Dict of device properties for Kasada fingerprinting.
            user_agent: Browser User-Agent string.
        """
        self._session = tls_client.Session(
            client_identifier=self.CLIENT_ID,
            random_tls_extension_order=True,
        )
        self._session.headers.update(
            {
                "User-Agent": user_agent
                or (
                    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.6367.179 Mobile Safari/537.36"
                ),
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
                "Origin": self.BASE_URL,
                "Referer": self.BASE_URL + "/",
            }
        )
        self.kasada = KasadaClient()
        if device_info:
            self.kasada.device_info = device_info
        self._xsrf_token: Optional[str] = None
        self._access_token: Optional[str] = None
        self._init_done = False

    def _ensure_init(self):
        """Lazily initialize the session with Cloudflare cookies and CSRF token."""
        if self._init_done:
            return
        self._session.get(self.BASE_URL + "/")
        self._session.get(self.BASE_URL + "/sanctum/csrf-cookie")
        for cookie in self._session.cookies:
            if cookie.name == "XSRF-TOKEN":
                self._xsrf_token = unquote(cookie.value)
                break
        if self._xsrf_token:
            self._session.headers["X-XSRF-TOKEN"] = self._xsrf_token
        self._init_done = True

    def set_access_token(self, token: str):
        """Set the Kick access token for authenticated requests."""
        self._access_token = token

    def _headers(self, extra: dict = None) -> dict:
        """Build request headers including auth and content type."""
        hdrs = {"Content-Type": "application/json"}
        if self._access_token:
            hdrs["Authorization"] = f"Bearer {self._access_token}"
        if extra:
            hdrs.update(extra)
        return hdrs

    def get(self, path: str, params: dict = None) -> dict:
        """Send a GET request to the Kick API."""
        self._ensure_init()
        url = self.BASE_URL + path
        r = self._session.get(url, headers=self._headers())
        self._maybe_update_kasada(r)
        return self._parse(r)

    def post(self, path: str, data: dict = None) -> dict:
        """Send a POST request to the Kick API."""
        self._ensure_init()
        url = self.BASE_URL + path
        r = self._session.post(url, json=data or {}, headers=self._headers())
        self._maybe_update_kasada(r)
        return self._parse(r)

    def put(self, path: str, data: dict = None) -> dict:
        """Send a PUT request to the Kick API."""
        self._ensure_init()
        url = self.BASE_URL + path
        r = self._session.put(url, json=data or {}, headers=self._headers())
        self._maybe_update_kasada(r)
        return self._parse(r)

    def delete(self, path: str) -> dict:
        """Send a DELETE request to the Kick API."""
        self._ensure_init()
        url = self.BASE_URL + path
        r = self._session.delete(url, headers=self._headers())
        self._maybe_update_kasada(r)
        return self._parse(r)

    def raw_get(self, url: str) -> "tls_client.Response":
        """Raw GET request — returns the response object directly."""
        self._ensure_init()
        return self._session.get(url, headers=self._headers())

    def raw_post(self, url: str, data: dict = None) -> "tls_client.Response":
        """Raw POST request — returns the response object directly."""
        self._ensure_init()
        return self._session.post(url, json=data or {}, headers=self._headers())

    def _parse(self, response):
        """Parse a response, returning JSON (dict or list) or an error dict."""
        try:
            data = response.json()
        except Exception:
            data = {"_raw": response.text, "_status": response.status_code}
        if response.status_code >= 400:
            if isinstance(data, dict):
                data["_status"] = response.status_code
                data["_error"] = data.get("message", "Unknown error")
            elif isinstance(data, list):
                return {
                    "_status": response.status_code,
                    "_error": "Request failed",
                    "data": data,
                }
            else:
                return {"_status": response.status_code, "_error": str(data)}
            return data
        return data

    def _maybe_update_kasada(self, response):
        """Update Kasada state from response headers if present."""
        try:
            headers = dict(response.headers)
            if any("kpsdk" in k.lower() for k in headers):
                self.kasada.update(headers)
        except Exception:
            pass

    @property
    def cookies(self) -> dict:
        """Get all cookies in the session."""
        return {c.name: c.value for c in self._session.cookies}

    def close(self):
        """Close the underlying HTTP session."""
        self._session.close()
