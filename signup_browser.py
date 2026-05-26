#!/usr/bin/env python3
"""
Run this on YOUR machine with YOUR real Chrome browser.
It automates the signup flow through the website, reads codes from your Gmail,
and saves access tokens.

Usage:
    python signup_browser.py --email you@gmail.com --app-pass "xxxx" --count 10
"""

import imaplib, email as em, re, time, json, random, string, argparse, sys
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
    args = p.parse_args()

    tokens = []
    imap = imaplib.IMAP4_SSL("imap.gmail.com", 993)

    with sync_playwright() as pw:
        # Use YOUR real Chrome - not headless, not automated-looking
        browser = pw.chromium.launch(
            headless=False,  # Visible browser - Cloudflare accepts this
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 720},
        )
        page = ctx.new_page()

        # Connect IMAP
        imap.login(args.email, args.app_pass)

        for i in range(1, args.count + 1):
            alias = dot_alias(args.email, i)
            username = f"k{random.randint(10000, 99999)}{random.choice(string.ascii_lowercase)}{random.choice(string.ascii_lowercase)}"
            password = f"Kick{random.randint(100, 999)}Test!"
            print(f"[{i}/{args.count}] {username}", end="", flush=True)

            try:
                # Load homepage
                page.goto("https://kick.com/", wait_until="load", timeout=60000)
                time.sleep(3)

                # Open signup modal
                page.locator('[data-testid="sign-up"]').first.click(force=True, timeout=10000)
                time.sleep(3)

                # Fill form
                page.locator('input[name="email"]').fill(alias)
                page.locator('input[name="birthdate"]').fill("2000-01-01")
                page.locator('input[name="username"]').fill(username)
                page.locator('input[name="password"]').fill(password)

                # Check TOS
                tos = page.locator('input[type="checkbox"]')
                if tos.count() > 0:
                    try: tos.first.check(force=True, timeout=2000)
                    except: pass

                # Wait for validation
                time.sleep(4)
                body = page.locator("body").inner_text()
                if "already taken" in body.lower():
                    print(" taken"); continue

                # Click submit
                page.evaluate("""() => {
                    const d = document.querySelector('[role="dialog"]');
                    if (!d) return;
                    const btns = d.querySelectorAll('button');
                    let c = 0;
                    for (const b of btns) {
                        if (b.textContent.trim() === 'Sign Up' && !b.disabled) {
                            c++;
                            if (c === 2) { b.click(); return; }
                        }
                    }
                }""")
                time.sleep(5)

                # Check verification
                body = page.locator("body").inner_text()
                if "verification" not in body.lower() and "check your email" not in body.lower():
                    print(" no-verify"); continue

                # Wait for email code
                code = None
                deadline = time.time() + 120
                while time.time() < deadline:
                    imap.select("INBOX")
                    _, msgs = imap.search(None, '(UNSEEN FROM "kick.com")')
                    for mid in (msgs[0].split() if msgs[0] else []):
                        _, data = imap.fetch(mid, "(RFC822)")
                        msg = em.message_from_bytes(data[0][1])
                        body_text = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    try: body_text = part.get_payload(decode=True).decode("utf-8","replace")
                                    except: pass
                        else:
                            try: body_text = msg.get_payload(decode=True).decode("utf-8","replace")
                            except: pass
                        m = re.search(r"\b(\d{4,8})\b", body_text)
                        if m: code = m.group(1); break
                    if code: break
                    time.sleep(5)

                if not code:
                    print(" no-code"); continue
                print(f" code={code}", end="", flush=True)

                # Enter code
                ci = page.locator('input[placeholder*="code" i], input[name*="code" i]')
                if ci.count() > 0:
                    ci.first.fill(code)
                    page.keyboard.press("Enter")
                    time.sleep(6)

                # The signup should be complete. Try to get token.
                page_url = page.url
                cookies = {c["name"]: c["value"] for c in ctx.cookies()}
                
                # Try accessing account info to verify
                try:
                    r = page.evaluate("""
                        async () => {
                            const r = await fetch("https://kick.com/api/v1/user", {
                                headers: {"Accept":"application/json"}
                            });
                            return r.ok ? await r.json() : null;
                        }
                    """)
                    if r and r.get("id"):
                        print(f" ✓ id={r['id']}")
                        tokens.append({"email": alias, "username": username, 
                                       "password": password, "user_id": r["id"]})
                        continue
                except: pass

                print(" ?")

            except Exception as e:
                print(f" ERR:{e}")

        browser.close()

    imap.logout()

    if tokens:
        with open(args.output, "w") as f:
            json.dump(tokens, f, indent=2)
    print(f"\nDone. {len(tokens)}/{args.count} accounts → {args.output}")


if __name__ == "__main__":
    main()
