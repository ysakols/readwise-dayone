#!/usr/bin/env python3
"""
Readwise Reader → Day One Sync

Syncs archived items from Readwise Reader to Day One journal entries.
Supports articles, RSS feeds, and newsletters.
"""
from datetime import datetime, timezone, timedelta
import os, subprocess, requests, smtplib, ssl, email.utils, json, time
from email.message import EmailMessage
from typing import List, Dict, Any, Optional

# ── 0. Config ───────────────────────────────────────────────────────────────────
READWISE_TOKEN = os.environ["READWISE_TOKEN"]
TIMEZONE = timezone.utc

# Output method
USE_CLI = os.getenv("USE_CLI", "false").lower() == "true"
DAYONE_EMAIL = os.getenv("DAYONE_EMAIL")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)

# Optional daily summary in addition to individual entries
CREATE_DAILY_SUMMARY = os.getenv("CREATE_DAILY_SUMMARY", "false").lower() == "true"

# How many days back to check (default: 1 day)
DAYS_BACK = int(os.getenv("DAYS_BACK", "1"))

# Delay between emails in seconds (to avoid rate limiting)
EMAIL_DELAY = float(os.getenv("EMAIL_DELAY", "2.0"))

# Categories to sync (article = saved, rss = feed, email = newsletters)
CATEGORIES = os.getenv("CATEGORIES", "article,rss,email").split(",")

# State file to track processed articles (prevents duplicates)
STATE_FILE = os.path.expanduser("~/.readwise_dayone_state.json")


# ── 1. State Management ────────────────────────────────────────────────────────
def load_processed_articles() -> set:
    """Load the set of article IDs we've already processed"""
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                data = json.load(f)
                return set(data.get("processed_article_ids", []))
    except Exception as e:
        print(f"⚠️  Could not load state file: {e}")

    return set()


def save_processed_articles(article_ids: set):
    """Save the set of processed article IDs"""
    try:
        data = {
            "processed_article_ids": list(article_ids),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        with open(STATE_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"⚠️  Could not save state file: {e}")


# ── 2. Fetch Articles from Readwise Reader ─────────────────────────────────────
def get_recently_finished_articles() -> List[Dict[str, Any]]:
    """
    Fetch items that were recently archived across all categories.

    Returns items that:
    1. Are in the archive location
    2. Were moved/archived in the last N days
    3. Haven't been processed before (deduplication)
    """
    # Calculate the date range
    days_ago = datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)
    cutoff_date = days_ago

    print(f"📅 Fetching items archived since: {days_ago.date().isoformat()}")
    print(f"📂 Categories: {', '.join(CATEGORIES)}")

    all_items = []

    # Fetch from each category
    for category in CATEGORIES:
        print(f"\n📚 Fetching {category}...")
        next_page_cursor = None
        category_count = 0

        while True:
            params = {
                "category": category.strip(),
                "pageSize": 100,
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

                r.raise_for_status()
                data = r.json()

                results = data.get("results", [])
                all_items.extend(results)
                category_count += len(results)

                # Check for next page
                next_page_cursor = data.get("nextPageCursor")
                if not next_page_cursor or len(results) == 0:
                    break

                # Safety limit per category
                if category_count >= 500:
                    print(f"  ⚠️  Reached 500 limit for {category}")
                    break

            except Exception as e:
                print(f"  ❌ Error fetching {category}: {e}")
                break

        print(f"  📥 Fetched {category_count} {category} items")

    print(f"\n📊 Total items fetched: {len(all_items)}")

    # Filter for archived items
    archived_items = [
        item for item in all_items
        if item.get("location") == "archive"
    ]

    print(f"📂 Found {len(archived_items)} archived items")

    # Client-side date filtering based on last_moved_at
    date_filtered = []
    for item in archived_items:
        last_moved = item.get("last_moved_at", "")
        if last_moved:
            try:
                dt = datetime.fromisoformat(last_moved.replace("Z", "+00:00"))
                if dt >= cutoff_date:
                    date_filtered.append(item)
            except:
                pass  # Skip items with unparseable dates

    finished_articles = date_filtered
    print(f"✅ Found {len(finished_articles)} items archived in the last {DAYS_BACK} day(s)")

    # Load processed articles to avoid duplicates
    processed_ids = load_processed_articles()
    new_articles = [
        article for article in finished_articles
        if article.get("id") not in processed_ids
    ]

    if len(new_articles) < len(finished_articles):
        skipped = len(finished_articles) - len(new_articles)
        print(f"⏭️  Skipped {skipped} already-processed articles")

    # Sort by most recently updated
    new_articles.sort(
        key=lambda x: x.get("updated_at", x.get("last_opened_at", "")),
        reverse=True
    )

    return new_articles


# ── 3. Format Article Data ──────────────────────────────────────────────────────
def get_article_summary(article: Dict[str, Any]) -> Optional[str]:
    """Extract summary from various possible fields"""
    summary = (
        article.get("summary") or
        article.get("notes") or
        article.get("description")
    )

    if summary and isinstance(summary, str):
        summary = summary.strip()
        # Truncate very long summaries
        if len(summary) > 1000:
            summary = summary[:1000] + "..."
        return summary

    return None


def format_article_entry(article: Dict[str, Any]) -> Dict[str, str]:
    """
    Format a single article into a rich Day One entry with comprehensive metadata.
    """
    # Extract all metadata fields
    title = article.get("title", "Untitled Article")
    url = article.get("url", "")
    source_url = article.get("source_url", "")
    author = article.get("author", "")
    summary = get_article_summary(article)
    reading_progress = article.get("reading_progress", 0)
    word_count = article.get("word_count", 0)

    # Date fields
    last_opened = article.get("last_opened_at", "")
    first_opened = article.get("first_opened_at", "")
    published_date = article.get("published_date", "")

    # Notes (separate from summary)
    notes = article.get("notes", "")

    # Format last opened date
    read_date = "recently"
    if last_opened:
        try:
            dt = datetime.fromisoformat(last_opened.replace("Z", "+00:00"))
            read_date = dt.strftime("%B %d, %Y at %I:%M %p")
        except:
            pass

    # Format first opened date
    first_read = None
    if first_opened:
        try:
            dt = datetime.fromisoformat(first_opened.replace("Z", "+00:00"))
            first_read = dt.strftime("%B %d, %Y")
        except:
            pass

    # Format published date
    published = None
    if published_date:
        try:
            # Handle various date formats
            if "T" in published_date:
                dt = datetime.fromisoformat(published_date.replace("Z", "+00:00"))
            else:
                dt = datetime.fromisoformat(published_date)
            published = dt.strftime("%B %d, %Y")
        except:
            published = published_date  # Use as-is if parsing fails

    # Build entry subject and body
    subject = f"📖 {title}"

    body_parts = [
        f"# {title}\n\n",
    ]

    # Metadata section
    if author:
        body_parts.append(f"**Author:** {author}\n\n")

    if published:
        body_parts.append(f"**Published:** {published}\n\n")

    if url:
        body_parts.append(f"**Reader Link:** [{url}]({url})\n\n")

    if source_url and source_url != url:
        body_parts.append(f"**Original Source:** [{source_url}]({source_url})\n\n")

    body_parts.append(f"**Last Read:** {read_date}\n\n")

    if first_read and first_read != read_date:
        body_parts.append(f"**First Opened:** {first_read}\n\n")

    if word_count:
        read_time = max(1, word_count // 200)  # Assume 200 words/min
        body_parts.append(f"**Length:** ~{word_count:,} words (~{read_time} min read)\n\n")

    if reading_progress is not None:
        body_parts.append(f"**Progress:** {reading_progress*100:.0f}% read\n\n")

    # Summary section
    if summary:
        body_parts.append(f"---\n\n## Summary\n\n{summary}\n\n")

    # Notes section (if different from summary)
    if notes and notes.strip() and notes != summary:
        body_parts.append(f"---\n\n## My Notes\n\n{notes.strip()}\n\n")

    # Footer
    body_parts.append(f"---\n\n*Synced from Readwise Reader*")

    body = "".join(body_parts)

    # Tags
    tags = ["readwise", "reading", "articles"]
    if article.get("category"):
        tags.append(article["category"])

    return {
        "subject": subject,
        "body": body,
        "tags": tags,
        "url": url,
        "article_id": article.get("id"),
    }


def format_daily_summary(articles: List[Dict[str, Any]]) -> Dict[str, str]:
    """Create a daily summary entry with all articles"""
    today = datetime.now(TIMEZONE).strftime("%B %d, %Y")

    subject = f"📚 Reading Summary - {today}"

    body_parts = [
        f"# 📚 Reading Summary\n\n",
        f"**Date:** {today}\n\n",
        f"**Articles Finished:** {len(articles)}\n\n",
        f"---\n\n",
    ]

    # Group articles and list them
    for i, article in enumerate(articles, 1):
        title = article.get("title", "Untitled")
        url = article.get("url", "")
        author = article.get("author", "")
        word_count = article.get("word_count", 0)

        body_parts.append(f"## {i}. {title}\n\n")

        if author:
            body_parts.append(f"*by {author}*\n\n")

        if url:
            body_parts.append(f"🔗 [Read article]({url})\n\n")

        if word_count:
            read_time = max(1, word_count // 200)
            body_parts.append(f"📝 ~{word_count:,} words (~{read_time} min)\n\n")

        # Brief summary if available
        summary = get_article_summary(article)
        if summary and len(summary) > 50:
            # Use first 200 chars for daily summary
            brief = summary[:200] + "..." if len(summary) > 200 else summary
            body_parts.append(f"> {brief}\n\n")

        body_parts.append("\n")

    body_parts.append(f"---\n\n*Synced from Readwise Reader*")

    return {
        "subject": subject,
        "body": "".join(body_parts),
        "tags": ["readwise", "reading-summary", "daily"],
    }


# ── 4. Write to Day One ─────────────────────────────────────────────────────────
def write_via_cli(entry_data: Dict[str, str]):
    """Write entry via Day One CLI"""
    tags = ",".join(entry_data.get("tags", ["readwise"]))

    subprocess.run(
        ["dayone2", "--journal", "Reading Log", "--tags", tags, "new"],
        input=entry_data["body"].encode(),
        check=True,
    )


def send_email(entry_data: Dict[str, str]):
    """Send entry via email to Day One"""
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


def write_entry(entry_data: Dict[str, str]) -> bool:
    """Write an entry using configured method"""
    try:
        if USE_CLI:
            write_via_cli(entry_data)
        else:
            send_email(entry_data)
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False


# ── 5. Main ─────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("📚 Readwise Reader → Day One Sync")
    print("=" * 60)

    try:
        articles = get_recently_finished_articles()

        if not articles:
            print(f"\n✨ No new archived items in the last {DAYS_BACK} day(s).")
            return

        print(f"\n📝 Creating {len(articles)} entries...\n")

        processed_ids = load_processed_articles()
        new_processed_ids = []
        success_count = 0

        for i, article in enumerate(articles, 1):
            title = article.get('title', 'Untitled')[:60]
            print(f"  [{i}/{len(articles)}] {title}...")

            try:
                entry_data = format_article_entry(article)
                if write_entry(entry_data):
                    success_count += 1
                    new_processed_ids.append(article.get("id"))
                    print(f"      ✅ Created")
                    if not USE_CLI and i < len(articles):
                        time.sleep(EMAIL_DELAY)
            except Exception as e:
                print(f"      ❌ Error: {e}")

        print(f"\n✅ Created {success_count}/{len(articles)} entries")

        # Create daily summary
        if CREATE_DAILY_SUMMARY:
            print("Creating daily summary entry...")
            try:
                summary_entry = format_daily_summary(articles)
                if write_entry(summary_entry):
                    print("✅ Daily summary created\n")
            except Exception as e:
                print(f"❌ Failed to create daily summary: {e}\n")

        # Update state file
        if new_processed_ids:
            processed_ids.update(new_processed_ids)
            save_processed_articles(processed_ids)
            print(f"💾 Saved state ({len(processed_ids)} total articles tracked)")

        print("\n" + "=" * 60)
        print("✅ Sync complete!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
