#!/usr/bin/env python3
"""
Kick.com mass account creator.

Uses a single headless browser session to complete Kasada/Cloudflare,
then creates accounts via fetch() from within the browser context.
IMAP reads verification codes from your Gmail inbox.
Dot-trick generates unlimited unique email aliases from one Gmail.

Usage:
    python create_accounts.py --email you@gmail.com --app-pass "xxxx" --count 100
"""

import imaplib, email as em, re, time, json, random, string, argparse
from typing import Optional
from playwright.sync_api import sync_playwright


def dot_alias(base: str, variant: int) -> str:
    name = base.split("@")[0]
    chars = list(name)
    v = variant
    for i in range(len(name) - 1, 0, -1):
        if v & 1: chars.insert(i, ".")
        v >>= 1
    if "".join(chars) == name: chars.insert(1, ".")
    return "".join(chars) + "@gmail.com"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--email", required=True)
    p.add_argument("--app-pass", required=True)
    p.add_argument("--count", type=int, default=10)
    p.add_argument("--output", default="kick_accounts.json")
    p.add_argument("--visible", action="store_true", help="Show browser window")
    args = p.parse_args()

    tokens = []
    seen_msg_ids = set()
    imap = None

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=not args.visible,
            args=["--no-sandbox", "--disable-dev-shm-usage",
                  "--disable-blink-features=AutomationControlled"]
        )
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/148.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
        )
        page = ctx.new_page()

        # Complete Kasada challenge
        print("Solving Kasada challenge...")
        page.goto("https://kick.com/149e9513-01fa-4fb0-aad4-566afd725d1b/2d206a39-8ed7-437e-a3be-862e0f06eea3/fp",
                  wait_until="domcontentloaded", timeout=30000)
        for _ in range(20):
            try:
                if "DONE" in page.evaluate("() => JSON.stringify(window.KPSDK || {})"): break
            except: pass
            time.sleep(0.5)
        print("  ✓ Kasada ready")

        # Get CSRF
        page.goto("https://kick.com/sanctum/csrf-cookie", wait_until="domcontentloaded")
        time.sleep(0.5)

        # Connect IMAP
        imap = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        imap.login(args.email, args.app_pass)
        imap.select("INBOX")
        print("  ✓ IMAP connected")

        print(f"\nCreating {args.count} accounts...")
        for i in range(1, args.count + 1):
            alias = dot_alias(args.email, i)
            username = f"usr{random.randint(10000, 99999)}{random.choice(string.ascii_lowercase)}"
            print(f"  [{i}/{args.count}] {alias}", end="", flush=True)

            try:
                # Send verification via browser fetch
                r = page.evaluate("""
                    async (d) => {
                        const xsrf = document.cookie.match(/XSRF-TOKEN=([^;]+)/)?.[1] || '';
                        const h = {"Content-Type":"application/json","Accept":"application/json",
                                   "X-XSRF-TOKEN":decodeURIComponent(xsrf),
                                   "Authorization":"Bearer "+decodeURIComponent(xsrf),
                                   "x-app-platform":"web","Origin":"https://kick.com"};
                        const r = await fetch("https://kick.com/api/v1/signup/send/email",
                            {method:"POST",credentials:"include",headers:h,
                             body:JSON.stringify({email:d.email})});
                        return {status:r.status,body:await r.text()};
                    }""", {"email": alias})
                if r.get("status", 0) != 200:
                    print(f" send:{r.get('status')}")
                    continue

                # Wait for code via IMAP
                code = None
                deadline = time.time() + 90
                while time.time() < deadline:
                    imap.select("INBOX")
                    _, msgs = imap.search(None, '(UNSEEN FROM "kick.com")')
                    for mid in (msgs[0].split() if msgs[0] else []):
                        if mid.decode() in seen_msg_ids: continue
                        seen_msg_ids.add(mid.decode())
                        _, data = imap.fetch(mid, "(RFC822)")
                        msg = em.message_from_bytes(data[0][1])
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    try: body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                                    except: pass
                        else:
                            try: body = msg.get_payload(decode=True).decode("utf-8", errors="replace")
                            except: pass
                        codes = re.findall(r"\b(\d{4,8})\b", body)
                        if codes: code = codes[0]; break
                    if code: break
                    time.sleep(3)

                if not code:
                    print(" no_code")
                    continue
                print(f" code={code}", end="", flush=True)

                # Complete signup via browser fetch
                r = page.evaluate("""
                    async (d) => {
                        const xsrf = document.cookie.match(/XSRF-TOKEN=([^;]+)/)?.[1] || '';
                        const h = {"Content-Type":"application/json","Accept":"application/json",
                                   "X-XSRF-TOKEN":decodeURIComponent(xsrf),
                                   "Authorization":"Bearer "+decodeURIComponent(xsrf),
                                   "x-app-platform":"web","Origin":"https://kick.com"};
                        // Verify code
                        await fetch("https://kick.com/api/v1/signup/verify/code",
                            {method:"POST",credentials:"include",headers:h,
                             body:JSON.stringify({email:d.email,code:d.code})});
                        // Username
                        await fetch("https://kick.com/api/v1/signup/verify/username",
                            {method:"POST",credentials:"include",headers:h,
                             body:JSON.stringify({username:d.username})});
                        // Terms
                        await fetch("https://kick.com/api/v1/signup/agreed-terms",
                            {method:"POST",credentials:"include",headers:h,body:"{}"});
                        // Complete
                        const rr = await fetch("https://kick.com/api/v1/signup/complete",
                            {method:"POST",credentials:"include",headers:h,body:"{}"});
                        return {status:rr.status,body:await rr.text()};
                    }""", {"email": alias, "code": code, "username": username})

                result = r.get("body", "{}")
                try: body = json.loads(result)
                except: body = {}
                token = body.get("access_token") or body.get("token")

                if token:
                    tokens.append({"email": alias, "username": username, "token": token})
                    print(f" ✓ {token[:30]}...")
                else:
                    print(f" no_token:{r.get('status')}")

            except Exception as e:
                print(f" ERR:{e}")

        browser.close()

    if imap:
        try: imap.logout()
        except: pass

    with open(args.output, "w") as f:
        json.dump(tokens, f, indent=2)
    print(f"\nCreated {len(tokens)}/{args.count} accounts → {args.output}")


if __name__ == "__main__":
    main()
