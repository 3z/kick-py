#!/usr/bin/env python3
"""
Mass Kick account creator using xvfb + Playwright browser.
ONE browser session handles Cloudflare, Kasada, form submission, and signup.
IMAP reads verification codes from your Gmail inbox.
Dot trick generates ~2000 unique aliases from one Gmail.

Requires: xvfb-run (apt install xvfb)

Usage:
    xvfb-run python mass_signup.py --email you@gmail.com --app-pass "xxxx" --count 10
"""

import imaplib, email as em, re, time, json, random, string, argparse
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
    imap = None

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--disable-dev-shm-usage",
                  "--disable-blink-features=AutomationControlled"]
        )
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/148.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
        )
        page = ctx.new_page()

        # Connect IMAP
        imap = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        imap.login(args.email, args.app_pass)

        for i in range(1, args.count + 1):
            alias = dot_alias(args.email, i)
            username = f"sk{random.randint(1000, 9999)}{random.choice(string.ascii_lowercase)}"
            password = "KickTestPass123!"
            print(f"[{i}/{args.count}] {alias} -> {username}", end="", flush=True)

            try:
                # Load homepage + open signup modal
                page.goto("https://kick.com/", wait_until="domcontentloaded", timeout=30000)
                time.sleep(2)
                page.locator('[data-testid="sign-up"]').first.click()
                time.sleep(3)

                # Fill form
                page.locator('input[name="email"]').fill(alias)
                time.sleep(0.3)
                page.locator('input[name="birthdate"]').fill("2000-01-01")
                time.sleep(0.3)
                page.locator('input[name="username"]').fill(username)
                time.sleep(0.3)
                page.locator('input[name="password"]').fill(password)
                time.sleep(2)

                # Submit
                page.evaluate("""() => {
                    const btns = document.querySelectorAll('[role="dialog"] button');
                    let c = 0;
                    for (const b of btns) {
                        if (b.textContent.trim() === 'Sign Up' && !b.disabled) {
                            c++;
                            if (c === 2) { b.click(); return; }
                        }
                    }
                }""")
                time.sleep(4)

                # Check for verification
                body = page.locator("body").inner_text().lower()
                if "verification" not in body and "check your email" not in body:
                    # Try clicking Sign Up again or check for errors
                    if "already taken" in body:
                        print(" username-taken"); continue
                    print(f" no-verify"); continue

                # Wait for code via IMAP
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
                                    try: body_text = part.get_payload(decode=True).decode("utf-8", "replace")
                                    except: pass
                        else:
                            try: body_text = msg.get_payload(decode=True).decode("utf-8", "replace")
                            except: pass
                        m = re.search(r"\b(\d{4,8})\b", body_text)
                        if m: code = m.group(1); break
                    if code: break
                    time.sleep(4)
                
                if not code:
                    print(" no-code"); continue
                print(f" code={code}", end="", flush=True)

                # Enter code
                code_input = page.locator('input[placeholder*="code" i], input[name*="code" i]')
                if code_input.count() > 0:
                    code_input.first.fill(code)
                    time.sleep(0.5)
                    page.keyboard.press("Enter")
                    time.sleep(4)

                # Save token if we can extract it
                # The signup flow may redirect/login automatically
                page_url = page.url
                if "dashboard" in page_url or "account" in page_url:
                    print(" ✓ logged-in")
                else:
                    print(" ?")

            except Exception as e:
                print(f" ERR:{e}")

        browser.close()

    if imap:
        try: imap.logout()
        except: pass

    if tokens:
        with open(args.output, "w") as f:
            json.dump(tokens, f, indent=2)
    print(f"\nDone. {len(tokens)} accounts → {args.output}")


if __name__ == "__main__":
    main()
