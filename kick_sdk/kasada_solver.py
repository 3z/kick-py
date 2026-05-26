"""
Kasada MobileShield SDK Solver (a-1.21.0)
Reverse-engineered from com.kick.mobile v40.18.1 Android APK.

Implements SHA-256 PoW, device info encoding, client token parsing,
and state machine for x-kpsdk-ct, x-kpsdk-h, x-kpsdk-cd, x-kpsdk-dv headers.
"""

import hashlib
import base64
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import unquote

# -------- Constants from the SDK (org.h.s.*) --------
SDK_VERSION = "a-1.21.0"
XOR_KEY = "6831442c-526a-4cb3-b1f7-d92c925f15eb"
DEFAULT_HASH = "01"
DIFFICULTY = 5.0  # 10 / 2
POW_TARGET = 4_503_599_627_370_496.0  # 4.503599627370496E15

DEFAULT_DEVICE_INFO = {
    "brand": "google",
    "model": "Pixel 8 Pro",
    "sdkInt": "34",
    "device": "husky",
    "product": "husky",
    "webViewVersion": "124.0.6367.179",
}

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro Build/UP1A.231105.001; wv) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 "
    "Chrome/124.0.6367.179 Mobile Safari/537.36"
)


# -------- Crypto Utilities (org.h.s.v, org.h.s.o, org.h.s.w) --------

def xor_bytes(data: bytes, key: bytes) -> bytes:
    return bytes(data[i] ^ key[i % len(key)] for i in range(len(data)))


def encode_device_info(device_info: dict) -> str:
    """Encode device info for x-kpsdk-dv header (o0.a, v.a).
    JSON -> XOR with XOR_KEY -> Base64 (NO_WRAP)."""
    json_str = json.dumps(device_info, separators=(",", ":"), ensure_ascii=True)
    encrypted = xor_bytes(json_str.encode("utf-8"), XOR_KEY.encode("utf-8"))
    return base64.b64encode(encrypted).decode("ascii")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hex_first_n_to_int(hex_str: str, n: int = 13) -> int:
    return int(hex_str[:n], 16)


# -------- Proof-of-Work (org.h.s.o.a) --------

def compute_pow(work_time_ms: int, pow_id: str) -> "tuple[str, list[int]]":
    """Compute Kasada SHA-256 proof-of-work.
    2 iterations, each finds a nonce where first 13 hex chars of
    SHA256(nonce + ", " + current_hash) produce a value <= 9e14.
    Returns (final_hash_hex, [nonce1, nonce2])."""
    input_str = f"tp-v2-input, {work_time_ms}, {pow_id}"
    current_hash_hex = sha256_hex(input_str.encode("utf-8"))
    answers = []

    for _ in range(2):
        nonce = 0
        while True:
            nonce += 1
            data = f"{nonce}, {current_hash_hex}"
            h = sha256_hex(data.encode("utf-8"))
            value = hex_first_n_to_int(h, 13)
            if POW_TARGET / (value + 1) >= DIFFICULTY:
                answers.append(nonce)
                current_hash_hex = h
                break

    return current_hash_hex, answers


# -------- Token Parsing (org.h.s.m, org.h.s.o0.a) --------

def parse_ctoken_response(ct_header: str) -> dict:
    """Parse x-kpsdk-ct response header.
    Format: header:status:ctoken:...:serverTimeMs[:encryptedOffset]"""
    if not ct_header:
        return {}
    parts = ct_header.split(":")
    result = {"header": parts[0] if len(parts) > 0 else None,
              "status": parts[1] if len(parts) > 1 else None}
    if len(parts) > 2:
        encoded = parts[2].replace("+", "%2b")
        try:
            result["ctoken"] = unquote(encoded)
        except Exception:
            result["ctoken"] = encoded
    if len(parts) > 6:
        try:
            result["server_time_ms"] = int(parts[6])
        except ValueError:
            pass
    if len(parts) > 7:
        result["encrypted_offset"] = parts[7]
    return result


def decrypt_offset(encrypted: str, ctoken: str) -> Optional[int]:
    """Decrypt server offset from x-kpsdk-ct (o0.a)."""
    if not encrypted or not ctoken:
        return None
    try:
        idx = encrypted.rfind("-")
        if idx < 0:
            return None
        num_str = encrypted[idx + 1:]
        decrypted = xor_bytes(num_str.encode("utf-8"), ctoken.encode("utf-8"))
        return int(decrypted.decode("utf-8"))
    except Exception:
        return None


# -------- State Machine (org.h.s.g0, org.h.s.i4, org.h.s.r0) --------

@dataclass
class KasadaState:
    """Kasada SDK session state across requests."""
    hash_value: str = DEFAULT_HASH
    ctoken: Optional[str] = None
    header: Optional[str] = None
    status: Optional[str] = None
    server_time_ms: int = 0
    local_time_on_parse: int = 0
    delta: int = 0
    expiry_ms: int = 0
    replay_offset: int = 0

    def is_initialized(self) -> bool:
        return self.ctoken is not None

    def update_from_response_headers(self, response_headers: dict):
        """Process x-kpsdk-ct, x-kpsdk-h, x-kpsdk-fc from server response."""
        new_ct = response_headers.get("x-kpsdk-ct")
        new_hash = response_headers.get("x-kpsdk-h")

        if new_ct:
            parsed = parse_ctoken_response(new_ct)
            self.header = parsed.get("header")
            self.status = parsed.get("status")
            self.ctoken = parsed.get("ctoken")
            if parsed.get("server_time_ms"):
                self.server_time_ms = parsed["server_time_ms"]
            self.local_time_on_parse = int(time.time() * 1000)
            if self.server_time_ms > 0:
                self.delta = self.local_time_on_parse - self.server_time_ms
            if parsed.get("encrypted_offset") and self.ctoken:
                off = decrypt_offset(parsed["encrypted_offset"], self.ctoken)
                if off is not None:
                    self.replay_offset = off

        if new_hash:
            self.hash_value = new_hash


# -------- Header Generation (org.h.s.o0.a) --------

def generate_headers(
    state: KasadaState,
    device_info: dict = None,
    user_agent: str = None,
) -> dict:
    """Generate full Kasada headers for a protected request."""
    if device_info is None:
        device_info = DEFAULT_DEVICE_INFO
    if user_agent is None:
        user_agent = DEFAULT_USER_AGENT

    headers = {"x-kpsdk-v": SDK_VERSION}
    if state.ctoken:
        headers["x-kpsdk-ct"] = state.ctoken

    # PoW computation
    pow_id = uuid.uuid4().hex[:32]
    utc_now = datetime.now(timezone.utc)
    utc_ms = int(utc_now.timestamp() * 1000)
    work_time = utc_ms - state.delta

    start_time = time.perf_counter()
    final_hash, answers = compute_pow(work_time, pow_id)
    end_time = time.perf_counter()
    duration_ms = (end_time - start_time) * 1000.0

    cd = (
        '{"workTime":' + str(work_time) +
        ',"id":"' + pow_id + '"' +
        ',"answers":' + str(answers) +
        ',"d":' + str(state.delta) +
        ',"rst":' + str(state.local_time_on_parse) +
        ',"st":' + str(state.server_time_ms) +
        ',"duration":' + str(duration_ms) +
        '}'
    )

    headers["x-kpsdk-cd"] = cd
    headers["x-kpsdk-h"] = state.hash_value
    headers["x-kpsdk-dv"] = encode_device_info(device_info)
    headers["User-Agent"] = user_agent
    return headers


# -------- High-Level Client --------

@dataclass
class KasadaClient:
    state: KasadaState = field(default_factory=KasadaState)
    device_info: dict = field(default_factory=lambda: dict(DEFAULT_DEVICE_INFO))
    user_agent: str = DEFAULT_USER_AGENT

    def get_headers(self) -> dict:
        return generate_headers(self.state, self.device_info, self.user_agent)

    def update(self, response_headers: dict):
        self.state.update_from_response_headers(response_headers)

    def reset(self):
        self.state = KasadaState()

    def is_ready(self) -> bool:
        return self.state.is_initialized()

    def to_dict(self) -> dict:
        return {
            "hash_value": self.state.hash_value,
            "ctoken": self.state.ctoken,
            "header": self.state.header,
            "status": self.state.status,
            "server_time_ms": self.state.server_time_ms,
            "local_time_on_parse": self.state.local_time_on_parse,
            "delta": self.state.delta,
            "replay_offset": self.state.replay_offset,
            "device_info": self.device_info,
            "user_agent": self.user_agent,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "KasadaClient":
        c = cls()
        c.state.hash_value = data.get("hash_value", DEFAULT_HASH)
        c.state.ctoken = data.get("ctoken")
        c.state.header = data.get("header")
        c.state.status = data.get("status")
        c.state.server_time_ms = data.get("server_time_ms", 0)
        c.state.local_time_on_parse = data.get("local_time_on_parse", 0)
        c.state.delta = data.get("delta", 0)
        c.state.replay_offset = data.get("replay_offset", 0)
        if data.get("device_info"):
            c.device_info = data["device_info"]
        if data.get("user_agent"):
            c.user_agent = data["user_agent"]
        return c


# -------- Self-test --------

if __name__ == "__main__":
    print("=" * 60)
    print(f"Kasada SDK Solver v{SDK_VERSION}")
    print("=" * 60)

    # Test device info encoding
    dv = encode_device_info(DEFAULT_DEVICE_INFO)
    dec_bytes = base64.b64decode(dv)
    dec = xor_bytes(dec_bytes, XOR_KEY.encode()).decode()
    assert json.loads(dec) == DEFAULT_DEVICE_INFO
    print("[PASS] Device info encoding")

    # Test PoW correctness
    pow_id = "test_pow_id_1234567890abcdef"
    h, answers = compute_pow(1700000000000, pow_id)
    assert len(answers) == 2
    assert all(a > 0 for a in answers)
    print(f"[PASS] PoW: answers={answers}")

    # Verify PoW
    input_str = f"tp-v2-input, 1700000000000, {pow_id}"
    ch = sha256_hex(input_str.encode())
    for nonce in answers:
        h2 = sha256_hex(f"{nonce}, {ch}".encode())
        v = hex_first_n_to_int(h2, 13)
        assert POW_TARGET / (v + 1) >= DIFFICULTY, f"PoW failed at nonce={nonce}"
        ch = h2
    print("[PASS] PoW verification")

    # Test header generation
    state = KasadaState()
    headers = generate_headers(state)
    assert "x-kpsdk-v" in headers
    assert "x-kpsdk-cd" in headers
    assert "x-kpsdk-dv" in headers
    assert "x-kpsdk-h" in headers
    assert headers["x-kpsdk-h"] == "01"
    assert "x-kpsdk-ct" not in headers  # no token yet
    print("[PASS] Header generation (fresh state)")

    # Test state update
    state.update_from_response_headers({
        "x-kpsdk-ct": "ABCD:OK:test_token_123:x:y:z:1740",
        "x-kpsdk-h": "a1b2c3",
    })
    assert state.ctoken == "test_token_123"
    assert state.hash_value == "a1b2c3"
    print("[PASS] State update from response")

    # Test with token
    headers2 = generate_headers(state)
    assert headers2.get("x-kpsdk-ct") == "test_token_123"
    assert headers2["x-kpsdk-h"] == "a1b2c3"
    print("[PASS] Header generation (with token)")

    # Test client API
    client = KasadaClient()
    assert not client.is_ready()
    client.update({"x-kpsdk-ct": "AA:OK:sometoken::0:1720000000"})
    assert client.is_ready()
    print("[PASS] Client API")

    # Test serialization
    data = client.to_dict()
    client2 = KasadaClient.from_dict(data)
    assert client2.state.ctoken == "sometoken"
    print("[PASS] Serialization round-trip")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)
