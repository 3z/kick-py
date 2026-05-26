"""
Pusher WebSocket client for Kick real-time chat.

Implements the Pusher protocol (v5) used by Kick's chat system.
Connects to wss://ws-{cluster}.pusher.com:443/app/{apiKey}
"""

import json
import time
import threading
import hashlib
import hmac
import uuid
from typing import Callable, Optional
import websocket


class PusherEvent:
    """A Pusher channel event."""

    def __init__(self, data: dict):
        self.event = data.get("event", "")
        self.channel = data.get("channel", "")
        self.data = json.loads(data.get("data", "{}")) if isinstance(
            data.get("data"), str
        ) else data.get("data", {})
        self.user_id = data.get("user_id", "")

    def __repr__(self):
        return f"PusherEvent({self.event}, ch={self.channel})"


class PusherClient:
    """Pusher WebSocket client for Kick chat."""

    PUSHER_HOST = "ws-{cluster}.pusher.com"
    PUSHER_PORT = 443
    PROTOCOL_VERSION = 5
    CLIENT_NAME = "java-client"

    def __init__(
        self,
        api_key: str,
        cluster: str = "us2",
        auth_endpoint: str = None,
        access_token: str = None,
        
    ):
        self.api_key = api_key
        self.cluster = cluster
        self.auth_endpoint = auth_endpoint
        self.access_token = access_token

        self._ws: Optional[websocket.WebSocketApp] = None
        self._socket_id: Optional[str] = None
        self._connected = False
        self._channels: dict = {}
        self._thread: Optional[threading.Thread] = None
        self._callbacks: dict = {}
        self._connection_callbacks: list = []
        self._error_callbacks: list = []

    # ---- Connection ----

    def connect(self) -> bool:
        """Connect to Pusher WebSocket."""
        url = self._build_url()
        self._ws = websocket.WebSocketApp(
            url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )
        self._thread = threading.Thread(target=self._ws.run_forever, kwargs={
            "ping_interval": 30,
            "ping_timeout": 10,
        })
        self._thread.daemon = True
        self._thread.start()

        # Wait for connection
        for _ in range(50):
            if self._connected:
                return True
            time.sleep(0.1)
        return False

    def disconnect(self):
        """Disconnect from Pusher."""
        if self._ws:
            self._ws.close()
        self._connected = False
        self._socket_id = None

    def _build_url(self) -> str:
        host = self.PUSHER_HOST.format(cluster=self.cluster)
        return (
            f"wss://{host}:{self.PUSHER_PORT}/app/{self.api_key}"
            f"?client={self.CLIENT_NAME}"
            f"&protocol={self.PROTOCOL_VERSION}"
        )

    def _on_open(self, ws):
        pass

    def _on_message(self, ws, message: str):
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            return

        event_name = data.get("event", "")

        if event_name == "pusher:connection_established":
            self._connected = True
            self._socket_id = data.get("data", "{}")
            if isinstance(self._socket_id, str):
                self._socket_id = json.loads(self._socket_id).get("socket_id", "")
            for cb in self._connection_callbacks:
                cb(data)
            return

        if event_name == "pusher:error":
            for cb in self._error_callbacks:
                cb(data)
            return

        if event_name == "pusher_internal:subscription_succeeded":
            channel = data.get("channel", "")
            if channel in self._channels:
                for cb in self._channels[channel].get("_on_subscribed", []):
                    cb(data)
            return

        # Dispatch to channel callbacks
        channel = data.get("channel", "")
        if channel in self._channels:
            event = PusherEvent(data)
            # Call global channel callback
            for cb in self._channels[channel].get("_on_event", []):
                cb(event)
            # Call event-specific callback
            for cb in self._channels[channel].get(event_name, []):
                cb(event)

    def _on_error(self, ws, error):
        for cb in self._error_callbacks:
            cb({"error": str(error)})

    def _on_close(self, ws, close_status_code, close_msg):
        self._connected = False

    # ---- Channel Management ----

    def subscribe(self, channel_name: str) -> str:
        """Subscribe to a channel. Returns channel name."""
        if channel_name not in self._channels:
            self._channels[channel_name] = {"_on_event": [], "_on_subscribed": []}

        if channel_name.startswith("private-") or channel_name.startswith("presence-"):
            auth = self._get_auth(channel_name)
            self._send({
                "event": "pusher:subscribe",
                "data": {"channel": channel_name, "auth": auth},
            })
        else:
            self._send({
                "event": "pusher:subscribe",
                "data": {"channel": channel_name},
            })

        # Wait for subscription
        for _ in range(30):
            pass  # subscription is acknowledged asynchronously
            time.sleep(0.1)

        return channel_name

    def unsubscribe(self, channel_name: str):
        """Unsubscribe from a channel."""
        self._send({
            "event": "pusher:unsubscribe",
            "data": {"channel": channel_name},
        })
        self._channels.pop(channel_name, None)

    def trigger(self, channel_name: str, event_name: str, data: dict):
        """Send a client event (must start with 'client-')."""
        if not event_name.startswith("client-"):
            raise ValueError("Client events must start with 'client-'")
        self._send({
            "event": event_name,
            "channel": channel_name,
            "data": json.dumps(data),
        })

    def _send(self, data: dict):
        if self._ws:
            self._ws.send(json.dumps(data))

    def _get_auth(self, channel_name: str) -> str:
        """Generate auth signature for private/presence channels."""
        if self.auth_endpoint and self.access_token:
            import requests
            r = requests.post(
                self.auth_endpoint,
                json={
                    "socket_id": self._socket_id,
                    "channel_name": channel_name,
                },
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
            if r.status_code == 200:
                return r.json().get("auth", "")
            return ""
        # Without auth endpoint, return empty (won't work for private channels)
        return ""

    # ---- Event Handlers ----

    def on_connected(self, callback: Callable):
        """Called when connection is established."""
        self._connection_callbacks.append(callback)

    def on_error(self, callback: Callable):
        """Called on connection errors."""
        self._error_callbacks.append(callback)

    def on_message(self, channel_name: str, callback: Callable):
        """Called on any message in a channel."""
        if channel_name not in self._channels:
            self._channels[channel_name] = {"_on_event": [], "_on_subscribed": []}
        self._channels[channel_name]["_on_event"].append(callback)

    def on_event(self, channel_name: str, event_name: str, callback: Callable):
        """Called on a specific event in a channel."""
        if channel_name not in self._channels:
            self._channels[channel_name] = {"_on_event": [], "_on_subscribed": []}
        if event_name not in self._channels[channel_name]:
            self._channels[channel_name][event_name] = []
        self._channels[channel_name][event_name].append(callback)

    def on_subscribed(self, channel_name: str, callback: Callable):
        """Called when subscription to a channel succeeds."""
        if channel_name not in self._channels:
            self._channels[channel_name] = {"_on_event": [], "_on_subscribed": []}
        self._channels[channel_name]["_on_subscribed"].append(callback)

    @property
    def socket_id(self) -> Optional[str]:
        return self._socket_id

    @property
    def is_connected(self) -> bool:
        return self._connected
