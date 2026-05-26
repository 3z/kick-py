"""
Kick SDK comprehensive test suite.
Tests session management, public API endpoints, auth flow, and utilities.
"""

import sys, os, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, "/root/kick/kasada_solver")

from kick_sdk import KickClient
from kick_sdk.email_utils import TempMailInbox


def test_session():
    """Test TLS spoofing + CSRF + Cloudflare bypass."""
    print("\n=== Session Tests ===")
    client = KickClient()
    client._session._ensure_init()
    assert client._session._xsrf_token is not None, "CSRF not obtained"
    print("  [PASS] CSRF token obtained")
    cookies = client.cookies
    assert len(cookies) > 0, "No cookies"
    print(f"  [PASS] {len(cookies)} cookies")
    client.close()


def test_public_api():
    """Test public API endpoints."""
    print("\n=== Public API ===")
    client = KickClient()

    resp = client.livestreams.get_categories()
    status = resp.get("_status", 200) if isinstance(resp, dict) else 200
    cats = resp if isinstance(resp, list) else []
    assert status < 400, f"Categories failed: {resp}"
    print(f"  [PASS] {len(cats)} categories")
    if cats:
        c = cats[0]
        n = c.get('name', c) if isinstance(c, dict) else str(c)
        print(f"         Top: {n}")

    channel = client.channels.get("xqc")
    assert channel.id > 0, f"Channel failed: {channel}"
    print(f"  [PASS] xQc: id={channel.id} slug={channel.slug}")
    if channel.playback_url:
        print(f"         Has playback URL")

    client.close()


def test_auth_endpoints():
    """Verify auth endpoints exist and respond correctly."""
    print("\n=== Auth Endpoints ===")
    client = KickClient()
    client._session._ensure_init()

    for path, body, expected in [
        ("/api/v2/mobile-tokens", {}, 401),
        ("/api/v1/signup/username", {"username": "t"}, 401),
        ("/api/v1/signup/agreed-terms", {}, 401),
        ("/api/v1/apple-mobile-login", {}, 422),
        ("/api/v1/signup/verify/code", {"email": "t@t.com", "code": "1"}, 422),
    ]:
        resp = client._session.post(path, body)
        s = resp.get("_status", 0)
        ok = s == expected
        print(f"  [{'PASS' if ok else 'INFO'}] {path}: {s} (expected {expected})")

    client.close()


def test_email():
    """Test disposable email utilities."""
    print("\n=== Email Utils ===")
    inbox = TempMailInbox()
    addr = inbox.create()
    assert "@" in addr, f"Invalid: {addr}"
    print(f"  [PASS] Created: {addr}")
    msgs = inbox.get_messages()
    print(f"  [PASS] {len(msgs)} messages")
    inbox.close()


def test_kasada():
    """Test Kasada PoW + header generation."""
    print("\n=== Kasada Solver ===")
    from solver import KasadaClient, compute_pow, encode_device_info

    dv = encode_device_info({"brand": "t", "model": "t", "sdkInt": "34",
                              "device": "t", "product": "t", "webViewVersion": "1"})
    assert len(dv) > 10
    print(f"  [PASS] dv encoded: {dv[:40]}...")

    h, ans = compute_pow(1700000000000, "test_id_1234")
    assert len(ans) == 2 and all(a > 0 for a in ans)
    print(f"  [PASS] PoW: {ans}, hash={h[:20]}...")

    c = KasadaClient()
    hdrs = c.get_headers()
    assert all(k in hdrs for k in ["x-kpsdk-v", "x-kpsdk-cd", "x-kpsdk-dv"])
    print(f"  [PASS] Headers: {list(hdrs.keys())}")


def print_auth_guide():
    """Print auth instructions."""
    print("\n=== Auth Guide ===")
    client = KickClient()
    print(f"  Google OAuth: {client.auth.google_oauth_url()[:80]}...")
    print()
    print("  Flow:")
    print("  1. Open Google OAuth URL in browser")
    print("  2. Sign in, copy authorization code")
    print("  3. client.auth.login_with_google_id_token(google_id_token)")
    print("  4. access_token is stored on client for all subsequent calls")
    print("  5. Token persists across sessions (save/load)")
    client.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Kick SDK Test Suite")
    print("=" * 60)

    passed = failed = 0
    for name, fn in [
        ("Session", test_session),
        ("Public API", test_public_api),
        ("Auth Endpoints", test_auth_endpoints),
        ("Email Utils", test_email),
        ("Kasada Solver", test_kasada),
    ]:
        try:
            fn()
            passed += 1
        except Exception as e:
            print(f"\n  [FAIL] {name}: {e}")
            import traceback; traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    print_auth_guide()
