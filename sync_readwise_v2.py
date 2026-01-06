#!/usr/bin/env python3
"""
Sync Readwise Reader articles to Day One - Individual Entries Version
Creates a separate Day One entry for each finished article with full metadata.

This version creates individual, rich entries for each article you've finished reading,
including author, summary, highlights, and more.
"""
from datetime import datetime, timezone, timedelta
import os, subprocess, requests, smtplib, ssl, email.utils, json
from email.message import EmailMessage
from typing import List, Dict, Any, Optional

# ── 0. Config ───────────────────────────────────────────────────────────────────
READWISE_TOKEN = os.environ["READWISE_TOKEN"]
TIMEZONE = timezone.utc

# Sink options
USE_CLI = os.getenv("USE_CLI", "false").lower() == "true"
DAYONE_EMAIL = os.getenv("DAYONE_EMAIL")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)

# Reading progress threshold (0.95 = 95%)
READING_PROGRESS_THRESHOLD = float(os.getenv("READING_PROGRESS_THRESHOLD", "0.95"))

# How many days back to check (default: 1 day)
DAYS_BACK = int(os.getenv("DAYS_BACK", "1"))


# ── 1. Fetch recently finished articles ────────────────────────────────────────
def get_recently_finished_articles() -> List[Dict[str, Any]]:
    """
    Fetch articles that were recently finished (reading_progress >= threshold).

    Strategy:
    1. Get all articles updated in the last N days
    2. Filter for those with reading_progress >= threshold
    3. Prefer articles in 'archive' location (typically moved there after reading)
    4. Return with full metadata
    """
    # Calculate the date range
    days_ago = datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)
    updated_after = days_ago.date().isoformat()

    print(f"📅 Fetching articles updated since: {updated_after}")

    all_articles = []
    next_page_cursor = None

    # Fetch all recent articles (may need pagination)
    while True:
        params = {
            "category": "article",
            "updatedAfter": updated_after,
            "pageSize": 100,  # Max page size
        }

        if next_page_cursor:
            params["pageCursor"] = next_page_cursor

        try:
            r = requests.get(
                "https://readwise.io/api/v3/list",
                params=params,
                headers={"Authorization": f"Token {READWISE_TOKEN}"},
                timeout=30,
            )

            # If date filtering fails, try without it
            if r.status_code == 400:
                print("⚠️  Date filtering failed, fetching all recent articles...")
                params = {"category": "article", "pageSize": 100}
                if next_page_cursor:
                    params["pageCursor"] = next_page_cursor

                r = requests.get(
                    "https://readwise.io/api/v3/list",
                    params=params,
                    headers={"Authorization": f"Token {READWISE_TOKEN}"},
                    timeout=30,
                )

            r.raise_for_status()
            data = r.json()

            results = data.get("results", [])
            all_articles.extend(results)

            print(f"📥 Fetched {len(results)} articles (total so far: {len(all_articles)})")

            # Check if there are more pages
            next_page_cursor = data.get("nextPageCursor")
            if not next_page_cursor:
                break

        except Exception as e:
            print(f"❌ Error fetching articles: {e}")
            break

    print(f"📊 Total articles fetched: {len(all_articles)}")

    # Filter for finished articles
    finished_articles = [
        article for article in all_articles
        if article.get("reading_progress", 0) >= READING_PROGRESS_THRESHOLD
    ]

    print(f"✅ Found {len(finished_articles)} finished articles (>={READING_PROGRESS_THRESHOLD*100}% progress)")

    # Sort by most recently updated
    finished_articles.sort(
        key=lambda x: x.get("updated_at", x.get("last_opened_at", "")),
        reverse=True
    )

    return finished_articles


def get_article_summary(article: Dict[str, Any]) -> Optional[str]:
    """
    Get the article summary from various possible fields.
    Readwise Reader can have summaries in different fields.
    """
    # Try different summary fields
    summary = (
        article.get("summary") or
        article.get("notes") or
        article.get("description")
    )

    # If we have a summary, clean it up
    if summary and isinstance(summary, str):
        summary = summary.strip()
        if len(summary) > 500:
            summary = summary[:500] + "..."
        return summary

    return None


def format_article_entry(article: Dict[str, Any]) -> Dict[str, str]:
    """
    Format a single article into a rich Day One entry.
    Returns dict with 'subject' and 'body'.
    """
    title = article.get("title", "Untitled Article")
    url = article.get("url", "")
    author = article.get("author", "Unknown Author")
    summary = get_article_summary(article)

    # Get reading metadata
    reading_progress = article.get("reading_progress", 0)
    word_count = article.get("word_count", 0)
    last_opened = article.get("last_opened_at", "")
    created_at = article.get("created_at", "")

    # Format the date when you read it
    read_date = "recently"
    if last_opened:
        try:
            dt = datetime.fromisoformat(last_opened.replace("Z", "+00:00"))
            read_date = dt.strftime("%B %d, %Y")
        except:
            pass

    # Build the entry
    subject = f"📚 {title}"

    body_parts = [
        f"# {title}\n",
        f"**Author:** {author}\n" if author and author != "Unknown Author" else "",
        f"**Source:** [{url}]({url})\n" if url else "",
        f"**Read on:** {read_date}\n",
        f"**Reading progress:** {reading_progress*100:.1f}%\n" if reading_progress else "",
        f"**Length:** ~{word_count:,} words\n" if word_count else "",
        "\n---\n\n",
    ]

    # Add summary if available
    if summary:
        body_parts.append(f"## Summary\n\n{summary}\n\n")

    # Add tags/categories
    tags = []
    if article.get("category"):
        tags.append(article["category"])
    if reading_progress >= 0.95:
        tags.append("finished-reading")
    else:
        tags.append("in-progress")

    if tags:
        body_parts.append(f"\n---\n\n*Tags: {', '.join(tags)}*\n")

    # Add reading metadata as a footer
    body_parts.append(f"\n*Saved to Readwise Reader: {created_at[:10] if created_at else 'unknown'}*")

    body = "".join(filter(None, body_parts))

    return {
        "subject": subject,
        "body": body,
        "tags": tags,
        "url": url,
    }


# ── 3A. Write via Day One CLI ───────────────────────────────────────────────────
def write_via_cli(entry_data: Dict[str, str]):
    """Write a single entry via Day One CLI"""
    tags = ",".join(entry_data.get("tags", ["readwise", "reading"]))

    subprocess.run(
        ["dayone2", "--journal", "Reading Log", "--tags", tags, "new"],
        input=entry_data["body"].encode(),
        check=True,
    )
    print(f"  ✅ Created CLI entry: {entry_data['subject'][:50]}...")


# ── 3B. Write via Email-to-Journal ──────────────────────────────────────────────
def send_email(entry_data: Dict[str, str]):
    """Send a single entry via email to Day One"""
    msg = EmailMessage()
    msg["Subject"] = entry_data["subject"]
    msg["From"] = SMTP_FROM
    msg["To"] = DAYONE_EMAIL
    msg["Date"] = email.utils.format_datetime(datetime.now(TIMEZONE))
    msg.set_content(entry_data["body"])

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, 465, context=ctx) as s:
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)

    print(f"  ✅ Sent email entry: {entry_data['subject'][:50]}...")


def write_entry(entry_data: Dict[str, str]):
    """Write an entry using the configured method"""
    if USE_CLI:
        write_via_cli(entry_data)
    else:
        send_email(entry_data)


# ── 4. Main ─────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("📚 Readwise Reader → Day One Sync (Individual Entries)")
    print("=" * 60)

    try:
        # Fetch finished articles
        articles = get_recently_finished_articles()

        if not articles:
            print("\n✨ No finished articles found in the specified time range.")
            print(f"   (Checked articles updated in last {DAYS_BACK} day(s))")
            return

        print(f"\n📝 Creating {len(articles)} Day One entries...\n")

        # Create individual entries for each article
        success_count = 0
        for i, article in enumerate(articles, 1):
            try:
                print(f"{i}/{len(articles)}: Processing '{article.get('title', 'Untitled')[:50]}...'")
                entry_data = format_article_entry(article)
                write_entry(entry_data)
                success_count += 1

            except Exception as e:
                print(f"  ❌ Failed to create entry: {e}")
                continue

        print("\n" + "=" * 60)
        print(f"✅ Successfully created {success_count}/{len(articles)} Day One entries!")
        print("=" * 60)

    except Exception as e:
        print(f"❌ Error during sync: {e}")
        raise


if __name__ == "__main__":
    main()
