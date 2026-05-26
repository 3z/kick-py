"""
Email utilities for reading verification codes from email inboxes.
Supports mail.tm / mail.gw disposable emails, IMAP, and Gmail API.
"""

import time
import re
import json
import imaplib
import email as email_lib
from email.header import decode_header
from typing import Optional, Callable
import requests


class TempMailInbox:
    """Disposable email inbox via mail.gw / mail.tm API."""

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "Mozilla/5.0"})
        self.address = ""
        self._token = ""
        self._api_base = ""

    def create(self) -> str:
        """Create a new disposable email address."""
        for api_base in ["https://api.mail.gw", "https://api.mail.tm"]:
            try:
                r = self._session.get(f"{api_base}/domains", timeout=10)
                domains = r.json()
                domain = domains["hydra:member"][0]["domain"]

                import random, string
                username = "".join(
                    random.choices(string.ascii_lowercase + string.digits, k=10)
                )
                password = "".join(
                    random.choices(string.ascii_letters + string.digits, k=16)
                )
                addr = f"{username}@{domain}"

                r = self._session.post(
                    f"{api_base}/accounts",
                    json={"address": addr, "password": password},
                )
                if r.status_code == 201:
                    r2 = self._session.post(
                        f"{api_base}/token",
                        json={"address": addr, "password": password},
                    )
                    self._token = r2.json()["token"]
                    self._session.headers[
                        "Authorization"
                    ] = f"Bearer {self._token}"
                    self.address = addr
                    self._api_base = api_base
                    return addr
            except Exception:
                continue
        raise RuntimeError("Failed to create temp email")

    def get_messages(self) -> list:
        """Get all messages in inbox."""
        if not self._token:
            return []
        r = self._session.get(f"{self._api_base}/messages")
        if r.status_code == 200:
            return r.json().get("hydra:member", [])
        return []

    def get_message(self, msg_id: str) -> Optional[dict]:
        """Get a specific message by ID."""
        if not self._token:
            return None
        r = self._session.get(f"{self._api_base}/messages/{msg_id}")
        if r.status_code == 200:
            return r.json()
        return None

    def wait_for_code(
        self,
        timeout: int = 120,
        poll_interval: int = 5,
        code_patterns: list = None,
    ) -> Optional[str]:
        """Wait for a verification code to arrive."""
        if code_patterns is None:
            code_patterns = [
                r"code\D*?(\d{4,8})",
                r"Code\D*?(\d{4,8})",
                r"CODE\D*?(\d{4,8})",
                r"(\d{6})",
                r"(\d{4})",
                r"verification\D*?(\d+)",
                r"OTP\D*?(\d{4,8})",
            ]

        deadline = time.time() + timeout
        seen_ids = set()

        while time.time() < deadline:
            msgs = self.get_messages()
            for msg in msgs:
                msg_id = msg.get("id", "")
                if msg_id in seen_ids:
                    continue
                seen_ids.add(msg_id)

                full = self.get_message(msg_id)
                if full:
                    text = full.get("text", "") or full.get("html", "")
                    for pat in code_patterns:
                        m = re.search(pat, text, re.IGNORECASE)
                        if m:
                            return m.group(1)

                    # Also check subject
                    subject = full.get("subject", "")
                    for pat in code_patterns:
                        m = re.search(pat, subject, re.IGNORECASE)
                        if m:
                            return m.group(1)

            time.sleep(poll_interval)

        return None

    def close(self):
        self._session.close()


class IMAPInbox:
    """Read emails from any IMAP server."""

    def __init__(
        self, host: str, email_addr: str, password: str, port: int = 993
    ):
        self.host = host
        self.email = email_addr
        self.password = password
        self.port = port
        self._conn: Optional[imaplib.IMAP4_SSL] = None

    def connect(self):
        """Connect to IMAP server."""
        self._conn = imaplib.IMAP4_SSL(self.host, self.port)
        self._conn.login(self.email, self.password)
        self._conn.select("INBOX")

    def search_emails(
        self, from_addr: str = None, subject_contains: str = None, unseen_only: bool = True
    ) -> list:
        """Search for emails matching criteria."""
        if not self._conn:
            self.connect()

        criteria = []
        if unseen_only:
            criteria.append("UNSEEN")
        if from_addr:
            criteria.append(f'FROM "{from_addr}"')
        if subject_contains:
            criteria.append(f'SUBJECT "{subject_contains}"')

        search_str = " ".join(criteria) if criteria else "ALL"
        _, data = self._conn.search(None, search_str)
        return data[0].split() if data[0] else []

    def get_email_body(self, msg_id: bytes) -> str:
        """Extract text body from an email."""
        if not self._conn:
            self.connect()

        _, data = self._conn.fetch(msg_id, "(RFC822)")
        raw = data[0][1]
        msg = email_lib.message_from_bytes(raw)

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                if ctype == "text/plain":
                    try:
                        body += part.get_payload(decode=True).decode(
                            "utf-8", errors="replace"
                        )
                    except Exception:
                        pass
        else:
            try:
                body = msg.get_payload(decode=True).decode("utf-8", errors="replace")
            except Exception:
                pass
        return body

    def wait_for_code(
        self,
        timeout: int = 120,
        poll_interval: int = 10,
        from_addr: str = "kick.com",
        subject_contains: str = None,
        code_patterns: list = None,
    ) -> Optional[str]:
        """Wait for verification code via IMAP."""
        if code_patterns is None:
            code_patterns = [
                r"code\D*?(\d{4,8})",
                r"(\d{6})",
                r"(\d{4})",
                r"OTP\D*?(\d{4,8})",
            ]

        deadline = time.time() + timeout
        seen = set()

        while time.time() < deadline:
            msg_ids = self.search_emails(
                from_addr=from_addr, subject_contains=subject_contains, unseen_only=True
            )
            for mid in msg_ids:
                if mid in seen:
                    continue
                seen.add(mid)
                body = self.get_email_body(mid)
                for pat in code_patterns:
                    m = re.search(pat, body, re.IGNORECASE)
                    if m:
                        return m.group(1)
            time.sleep(poll_interval)

        return None

    def close(self):
        if self._conn:
            self._conn.logout()
            self._conn = None


class GmailInbox:
    """Read Gmail inbox via IMAP (needs app password)."""

    def __init__(self, email_addr: str, app_password: str):
        self._imap = IMAPInbox(
            host="imap.gmail.com",
            email_addr=email_addr,
            password=app_password,
            port=993,
        )

    def wait_for_code(self, timeout: int = 120, **kwargs) -> Optional[str]:
        return self._imap.wait_for_code(timeout=timeout, **kwargs)

    def close(self):
        self._imap.close()
