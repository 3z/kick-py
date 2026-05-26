"""Email inbox readers for verification code extraction."""

import time, re, imaplib, email as email_lib, random, string
from typing import Optional
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
        """Create a new disposable email address.

        Returns:
            Email address string.
        """
        for api_base in ["https://api.mail.gw", "https://api.mail.tm"]:
            try:
                r = self._session.get(f"{api_base}/domains", timeout=10)
                domains = r.json()
                domain = domains["hydra:member"][0]["domain"]
                username = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
                password = "".join(random.choices(string.ascii_letters + string.digits, k=16))
                addr = f"{username}@{domain}"
                r = self._session.post(f"{api_base}/accounts", json={"address": addr, "password": password})
                if r.status_code == 201:
                    r2 = self._session.post(f"{api_base}/token", json={"address": addr, "password": password})
                    self._token = r2.json()["token"]
                    self._session.headers["Authorization"] = f"Bearer {self._token}"
                    self.address = addr
                    self._api_base = api_base
                    return addr
            except Exception:
                continue
        raise RuntimeError("Failed to create temp email")

    def get_messages(self) -> list:
        """Get all messages in the inbox."""
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
        self, timeout: int = 120, poll_interval: int = 5, code_patterns: list = None,
    ) -> Optional[str]:
        """Wait for a verification code to arrive in the inbox.

        Args:
            timeout: Maximum seconds to wait.
            poll_interval: Seconds between inbox checks.
            code_patterns: List of regex patterns for code extraction.

        Returns:
            Verification code string, or None if timeout.
        """
        if code_patterns is None:
            code_patterns = [
                r"code\D*?(\d{4,8})", r"Code\D*?(\d{4,8})",
                r"(\d{6})", r"OTP\D*?(\d{4,8})",
            ]
        deadline = time.time() + timeout
        seen_ids = set()
        while time.time() < deadline:
            for msg in self.get_messages():
                mid = msg.get("id", "")
                if mid in seen_ids: continue
                seen_ids.add(mid)
                full = self.get_message(mid)
                if full:
                    text = full.get("text", "") or full.get("html", "")
                    for pat in code_patterns:
                        m = re.search(pat, text, re.IGNORECASE)
                        if m: return m.group(1)
            time.sleep(poll_interval)
        return None

    def close(self):
        """Close the HTTP session."""
        self._session.close()


class IMAPInbox:
    """Read emails from any IMAP server (Gmail, Outlook, etc.)."""

    def __init__(self, host: str, email_addr: str, password: str, port: int = 993):
        """Create an IMAP inbox reader.

        Args:
            host: IMAP server hostname.
            email_addr: Email address.
            password: App password or account password.
            port: IMAP port (default 993 for SSL).
        """
        self.host = host
        self.email = email_addr
        self.password = password
        self.port = port
        self._conn: Optional[imaplib.IMAP4_SSL] = None

    def connect(self):
        """Connect to the IMAP server."""
        self._conn = imaplib.IMAP4_SSL(self.host, self.port)
        self._conn.login(self.email, self.password)
        self._conn.select("INBOX")

    def search_emails(
        self, from_addr: str = None, subject_contains: str = None, unseen_only: bool = True,
    ) -> list:
        """Search for emails matching criteria."""
        if not self._conn: self.connect()
        criteria = []
        if unseen_only: criteria.append("UNSEEN")
        if from_addr: criteria.append(f'FROM "{from_addr}"')
        if subject_contains: criteria.append(f'SUBJECT "{subject_contains}"')
        search_str = " ".join(criteria) if criteria else "ALL"
        _, data = self._conn.search(None, search_str)
        return data[0].split() if data[0] else []

    def get_email_body(self, msg_id: bytes) -> str:
        """Extract the plain text body from an email."""
        if not self._conn: self.connect()
        _, data = self._conn.fetch(msg_id, "(RFC822)")
        msg = email_lib.message_from_bytes(data[0][1])
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try: body += part.get_payload(decode=True).decode("utf-8", errors="replace")
                    except: pass
        else:
            try: body = msg.get_payload(decode=True).decode("utf-8", errors="replace")
            except: pass
        return body

    def wait_for_code(
        self, timeout: int = 120, poll_interval: int = 10,
        from_addr: str = "kick.com", code_patterns: list = None,
    ) -> Optional[str]:
        """Wait for a verification code via IMAP.

        Args:
            timeout: Maximum seconds to wait.
            poll_interval: Seconds between checks.
            from_addr: Sender address to filter by.
            code_patterns: Regex patterns for code extraction.

        Returns:
            Verification code string, or None if timeout.
        """
        if code_patterns is None:
            code_patterns = [r"code\D*?(\d{4,8})", r"(\d{6})", r"OTP\D*?(\d{4,8})"]
        deadline = time.time() + timeout
        seen = set()
        while time.time() < deadline:
            for mid in self.search_emails(from_addr=from_addr, unseen_only=True):
                if mid in seen: continue
                seen.add(mid)
                body = self.get_email_body(mid)
                for pat in code_patterns:
                    m = re.search(pat, body, re.IGNORECASE)
                    if m: return m.group(1)
            time.sleep(poll_interval)
        return None

    def close(self):
        """Close the IMAP connection."""
        if self._conn: self._conn.logout()


class GmailInbox(IMAPInbox):
    """Gmail inbox reader (requires an app password)."""

    def __init__(self, email_addr: str, app_password: str):
        """Create a Gmail inbox reader.

        Args:
            email_addr: Gmail address.
            app_password: Gmail app password.
        """
        super().__init__(host="imap.gmail.com", email_addr=email_addr, password=app_password, port=993)
