#!/usr/bin/env python3
"""
Mass Kick account creator using Gmail dot trick.
Generates thousands of unique emails from a single Gmail inbox.

Usage:
    python mass_create.py --email you@gmail.com --app-pass "xxxx xxxx xxxx xxxx"
    
The dot trick: Gmail ignores dots. you@gmail.com == y.ou@gmail.com == yo.u@gmail.com
For an N-char username, you get 2^(N-1) unique aliases - all routing to your inbox.
Kick sees each as a different email. IMAP reads codes from one inbox.

Set a PROXY for IP rotation. Uses threading for parallel creation.
"""

import imaplib
import email as em
import re
import time
import json
import argparse
import threading
import random
import string
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Optional
import sys
sys.path.insert(0, '.')
from kick_sdk import KickClient

PROXY = "http://xEYW3UUOmisnY04i:6CfKk1cJerTS3Y0Y_streaming-1@geo.iproyal.com:12321"


@dataclass
class CreatorState:
    """Shared state across threads."""
    email: str
    app_pass: str
    proxy: str
    variant: int = 0
    tokens: list = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)
    imap_lock: threading.Lock = field(default_factory=threading.Lock)
    seen_ids: set = field(default_factory=set)


def dot_alias(base_email: str, variant: int) -> str:
    """Generate Gmail dot-trick alias from variant number.
    Variant bits control dot placement. 2^(len-1) combinations."""
    name, domain = base_email.split('@')
    chars = list(name)
    for i in range(len(name) - 1, 0, -1):
        if variant & 1:
            chars.insert(i, '.')
        variant >>= 1
    # Skip variant 0 (same as base, no dots)
    if ''.join(chars) == name and variant == 0:
        return dot_alias(base_email, 1)
    return ''.join(chars) + '@' + domain


def random_username() -> str:
    """Generate a random Kick username."""
    adj = random.choice(['cool','fast','wild','calm','dark','bold','epic','rare',
        'loud','pure','free','wise','keen','vibe','zen','ace','pro','max','neo'])
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    return f"{adj}{suffix}"


def wait_for_code(state: CreatorState, target_email: str, timeout: int = 120) -> Optional[str]:
    """Wait for verification code via IMAP. Thread-safe."""
    deadline = time.time() + timeout
    
    # Connect to IMAP once per thread group, or share connection
    with state.imap_lock:
        conn = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        conn.login(state.email, state.app_pass)
    
    try:
        while time.time() < deadline:
            conn.select("INBOX")
            status, msgs = conn.search(None, '(UNSEEN FROM "kick.com")')
            msg_ids = msgs[0].split() if msgs[0] else []
            
            for mid in msg_ids:
                mid_str = mid.decode()
                with state.lock:
                    if mid_str in state.seen_ids:
                        continue
                    state.seen_ids.add(mid_str)
                
                _, data = conn.fetch(mid, "(RFC822)")
                msg = em.message_from_bytes(data[0][1])
                subject = msg.get("Subject", "")
                
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            try:
                                body = part.get_payload(decode=True).decode('utf-8', errors='replace')
                            except:
                                pass
                else:
                    try:
                        body = msg.get_payload(decode=True).decode('utf-8', errors='replace')
                    except:
                        pass
                
                # Find code in body
                codes = re.findall(r'\b(\d{4,8})\b', body)
                if codes:
                    code = codes[0]
                    # Check if email is for our target
                    if target_email.lower() in body.lower() or any(
                        # Dot aliases may have the code in a generic template
                        'verification' in body.lower() and 'kick' in body.lower()
                        for _ in [1]
                    ):
                        return code
                    # Also check subject for code
                    subject_codes = re.findall(r'\b(\d{4,8})\b', subject)
                    if subject_codes:
                        return subject_codes[0]
            
            time.sleep(3)
    finally:
        conn.logout()
    
    return None


def create_account(state: CreatorState, variant: int) -> Optional[dict]:
    """Create a single Kick account."""
    alias = dot_alias(state.email, variant)
    username = random_username()
    
    print(f"  [{variant}] {alias} -> {username}", end='', flush=True)
    
    try:
        client = KickClient(proxy=state.proxy)
        
        # Step 1: Request verification
        r = client._session.post("/api/v1/signup/verify/email", {"email": alias})
        st = r.get('_status', 200) if isinstance(r, dict) else 200
        if st != 204:
            print(f" verify/email:{st}")
            client.close()
            return None
        
        # Step 2: Wait for code
        code = wait_for_code(state, alias, timeout=120)
        if not code:
            print(f" no code")
            client.close()
            return None
        
        print(f" code={code}", end='', flush=True)
        
        # Step 3: Verify code
        r = client._session.post("/api/v1/signup/verify/code", {
            "email": alias, "code": code
        })
        st = r.get('_status', 200) if isinstance(r, dict) else 200
        if st >= 400:
            print(f" verify:{st}")
            client.close()
            return None
        
        # Step 4: Set username
        r = client._session.post("/api/v1/signup/verify/username", {"username": username})
        st = r.get('_status', 200) if isinstance(r, dict) else 200
        
        # Step 5: Agree terms
        r = client._session.post("/api/v1/signup/agreed-terms", {})
        st = r.get('_status', 200) if isinstance(r, dict) else 200
        
        # Step 6: Complete
        r = client._session.post("/api/v1/signup/complete", {})
        token = None
        if isinstance(r, dict):
            token = r.get('access_token') or r.get('token')
        
        if token:
            print(f" ✓ TOKEN={token[:30]}...")
            client.close()
            return {
                "email": alias,
                "username": username,
                "token": token,
                "variant": variant,
            }
        else:
            print(f" no_token")
            client.close()
            return None
            
    except Exception as e:
        print(f" ERR:{e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Mass Kick account creator")
    parser.add_argument("--email", required=True, help="Gmail address")
    parser.add_argument("--app-pass", required=True, help="Gmail app password")
    parser.add_argument("--count", type=int, default=10, help="Number of accounts to create")
    parser.add_argument("--threads", type=int, default=3, help="Concurrent threads")
    parser.add_argument("--proxy", default=PROXY, help="Proxy URL")
    parser.add_argument("--output", default="kick_accounts.json", help="Output file")
    args = parser.parse_args()

    state = CreatorState(
        email=args.email,
        app_pass=args.app_pass,
        proxy=args.proxy,
    )

    print(f"Creating {args.count} accounts...")
    print(f"Email: {args.email}")
    print(f"Threads: {args.threads}")
    print(f"Proxy: {args.proxy}")
    print()

    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = {
            executor.submit(create_account, state, i + 1): i + 1
            for i in range(args.count)
        }
        for future in as_completed(futures):
            result = future.result()
            if result:
                with state.lock:
                    state.tokens.append(result)

    # Save results
    with open(args.output, 'w') as f:
        json.dump(state.tokens, f, indent=2)

    print(f"\nCreated {len(state.tokens)}/{args.count} accounts")
    print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()
