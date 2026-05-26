"""
Batch Kick account creation and management.
For mass account operations - signup, follow, chat, etc.
"""

import time
import json
from typing import Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed


class BatchCreator:
    """Batch account creation and operation manager."""

    def __init__(self, proxy_list: list = None, headless: bool = True):
        """
        Args:
            proxy_list: List of proxy dicts for rotation
            headless: Run browsers headless
        """
        self.proxies = proxy_list or []
        self.headless = headless
        self.accounts = []

    def create_accounts(
        self,
        google_credentials: list,
        usernames: list,
        max_workers: int = 5,
    ) -> list:
        """Create multiple Kick accounts in parallel.

        Args:
            google_credentials: List of (email, password, recovery_email) tuples
            usernames: List of desired Kick usernames  
            max_workers: Max parallel workers

        Returns:
            List of dicts with account info and tokens
        """
        from .oauth_automation import create_kick_account_google

        results = []

        def _create(idx):
            email, password, recovery = google_credentials[idx]
            username = usernames[idx] if idx < len(usernames) else None
            proxy = (
                {"server": self.proxies[idx % len(self.proxies)]}
                if self.proxies else None
            )

            result = create_kick_account_google(
                google_email=email,
                google_password=password,
                kick_username=username or f"user{int(time.time())}",
                recovery_email=recovery,
                proxy=proxy,
                headless=self.headless,
            )
            result["idx"] = idx
            result["email"] = email
            result["username"] = username
            return result

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_create, i): i
                for i in range(len(google_credentials))
            }
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    result = future.result(timeout=120)
                    results.append(result)
                    token = result.get("access_token", "")[:20]
                    status = "OK" if token else f"FAIL: {result.get('error', 'unknown')}"
                    print(f"[{idx}] {status}")
                except Exception as e:
                    results.append({"idx": idx, "error": str(e)})
                    print(f"[{idx}] ERROR: {e}")

        self.accounts = results
        return results

    def save_accounts(self, filepath: str):
        """Save account tokens to JSON file."""
        with open(filepath, "w") as f:
            json.dump(self.accounts, f, indent=2)

    def load_accounts(self, filepath: str):
        """Load account tokens from JSON file."""
        with open(filepath) as f:
            self.accounts = json.load(f)
        return self.accounts


class BatchOperator:
    """Perform batch operations with existing Kick accounts."""

    def __init__(self, accounts: list, proxy_list: list = None):
        """
        Args:
            accounts: List of dicts with 'access_token' key
            proxy_list: Optional proxy rotation
        """
        self.accounts = accounts
        self.proxies = proxy_list or []

    def for_each(self, action: Callable, max_workers: int = 5, **kwargs):
        """Run an action on each account in parallel.

        Args:
            action: Callable(client, account, **kwargs) -> result
            max_workers: Max parallel workers
            **kwargs: Passed to action
        """
        from .client import KickClient

        results = []

        def _run(idx):
            acct = self.accounts[idx]
            token = acct.get("access_token", "")
            if not token:
                return {"idx": idx, "error": "No access token"}

            proxy = (
                self.proxies[idx % len(self.proxies)]
                if self.proxies else None
            )

            client = KickClient(
                proxy=proxy,
                access_token=token,
            )

            try:
                result = action(client, acct, **kwargs)
                return {"idx": idx, "result": result}
            except Exception as e:
                return {"idx": idx, "error": str(e)}
            finally:
                client.close()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_run, i): i for i in range(len(self.accounts))}
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    result = future.result(timeout=60)
                    results.append(result)
                except Exception as e:
                    results.append({"idx": idx, "error": str(e)})

        return results

    def follow_all(self, channel_slug: str, max_workers: int = 5):
        """Make all accounts follow a channel."""
        def _follow(client, acct):
            channel = client.channels.get(channel_slug)
            channel_id = channel.get("id", 0)
            if channel_id:
                return client.channels.follow(channel_id)
            return {"error": "Channel not found"}
        return self.for_each(_follow, max_workers=max_workers)

    def chat_all(self, channel_slug: str, message: str, max_workers: int = 5):
        """Make all accounts send a chat message."""
        def _chat(client, acct):
            channel = client.channels.get(channel_slug)
            channel_id = channel.get("id", 0)
            if channel_id:
                return client.chat.send_message(channel_id, message)
            return {"error": "Channel not found"}
        return self.for_each(_chat, max_workers=max_workers)
