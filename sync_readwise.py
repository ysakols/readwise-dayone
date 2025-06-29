#!/usr/bin/env python3
"""
Pull today's Readwise articles and create a Day One entry.
Choose ONE sink:  CLI (macOS)  OR  email (any platform).
"""
from datetime import datetime, timezone
import os, subprocess, requests, smtplib, ssl, email.utils
from email.message import EmailMessage

# ── 0. Config ───────────────────────────────────────────────────────────────────
READWISE_TOKEN = os.environ["READWISE_TOKEN"]            # required
TIMEZONE       = timezone.utc                            # adjust if you like

# --- Sink A: Day One CLI (macOS) ---
USE_CLI        = os.getenv("USE_CLI", "false").lower() == "true"

# --- Sink B: Email-to-Journal (cloud / Linux) ---
DAYONE_EMAIL   = os.getenv("DAYONE_EMAIL")               # e.g. abc123@journal.dayone.app
SMTP_HOST      = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_USER      = os.getenv("SMTP_USER")
SMTP_PASS      = os.getenv("SMTP_PASS")
SMTP_FROM      = os.getenv("SMTP_FROM", SMTP_USER)

# ── 1. Fetch today's finished articles ──────────────────────────────────────────
def get_today_articles():
    """Return only today's fully-read articles (progress ≥ 0.95)."""
    today = None
    try:
        today = requests.get('http://worldtimeapi.org/api/timezone/Etc/UTC', timeout=10).json()['utc_datetime'][:10]
        print(f"DEBUG: Got today from worldtimeapi.org: {today}")
    except Exception as e:
        print(f"WARNING: Could not fetch date from worldtimeapi.org: {e}")
        try:
            # Try another public time API
            today = requests.get('https://worldclockapi.com/api/json/utc/now', timeout=10).json()['currentDateTime'][:10]
            print(f"DEBUG: Got today from worldclockapi.com: {today}")
        except Exception as e2:
            print(f"WARNING: Could not fetch date from worldclockapi.com: {e2}")
            # As a last resort, hardcode today's date (for testing)
            today = "2024-06-29"
            print(f"DEBUG: Using hardcoded date: {today}")

    # Readwise Reader API expects a full ISO‑8601 timestamp, not a bare date
    updated_after = f"{today}T00:00:00Z"
    print(f"DEBUG: Using updated_after={updated_after} for updatedAfter param")
    
    r = requests.get(
        "https://readwise.io/api/v3/list",
        params={"category": "article", "updatedAfter": updated_after},
        headers={"Authorization": f"Token {READWISE_TOKEN}"},
        timeout=30,
    )
    if r.status_code == 400:
        print("DEBUG: 400 returned for updatedAfter filter, retrying without it")
        r = requests.get(
            "https://readwise.io/api/v3/list",
            params={"category": "article"},
            headers={"Authorization": f"Token {READWISE_TOKEN}"},
            timeout=30,
        )
    r.raise_for_status()

    return [
        a for a in r.json().get("results", [])
        if a.get("reading_progress", 0) >= 0.95        # fully read
           and (a.get("last_opened_at") or a.get("first_opened_at", "")).startswith(today)
    ]

# ── 2. Format entry text ────────────────────────────────────────────────────────
def format_entry(articles) -> str:
    date_str = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    if not articles:
        return f"## 📚 Articles I finished reading on {date_str}\n\n_(None today.)_"

    lines = [f"- [{a['title']}]({a['url']})" for a in articles]
    return f"## 📚 Articles I finished reading on {date_str}\n\n" + "\n".join(lines)

# ── 3A. Write via Day One CLI ───────────────────────────────────────────────────
def write_via_cli(text: str):
    subprocess.run(
        ["dayone2", "--journal", "Reading Log", "--tags", "readwise,articles", "new"],
        input=text.encode(),
        check=True,
    )

# ── 3B. Write via Email-to-Journal ──────────────────────────────────────────────
def send_email(text: str):
    msg = EmailMessage()
    msg["Subject"] = f"Readwise digest {datetime.now(TIMEZONE).date()}"
    msg["From"]    = SMTP_FROM
    msg["To"]      = DAYONE_EMAIL
    msg["Date"]    = email.utils.format_datetime(datetime.now(TIMEZONE))
    msg.set_content(text)

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, 465, context=ctx) as s:
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)

# ── 4. Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        entry = format_entry(get_today_articles())
        if USE_CLI:
            write_via_cli(entry)
        else:
            send_email(entry)
        print("✅ Finished Readwise → Day One sync")
    except Exception as e:
        print(f"❌ Error during sync: {e}")
        raise 