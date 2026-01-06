#!/usr/bin/env python3
"""
Readwise Reader → Day One Sync - Ultimate Edition

Features:
- ✅ Fetches articles you've actually READ (high reading progress)
- ✅ Individual entries per article with rich metadata (author, summary, etc.)
- ✅ Optional daily summary rollup
- ✅ Configurable via environment variables
- ✅ Handles pagination for large libraries
- ✅ Smart deduplication to avoid creating duplicate entries
"""
from datetime import datetime, timezone, timedelta
import os, subprocess, requests, smtplib, ssl, email.utils, json, hashlib
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

# Entry creation mode
CREATE_INDIVIDUAL_ENTRIES = os.getenv("CREATE_INDIVIDUAL_ENTRIES", "true").lower() == "true"
CREATE_DAILY_SUMMARY = os.getenv("CREATE_DAILY_SUMMARY", "false").lower() == "true"

# Reading progress threshold (0.95 = 95%)
READING_PROGRESS_THRESHOLD = float(os.getenv("READING_PROGRESS_THRESHOLD", "0.95"))

# How many days back to check (default: 1 day)
DAYS_BACK = int(os.getenv("DAYS_BACK", "1"))

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
    Fetch articles that were recently finished reading.

    Returns articles that:
    1. Have reading_progress >= threshold (e.g., 95%)
    2. Were updated in the last N days
    3. Haven't been processed before (deduplication)
    """
    # Calculate the date range
    days_ago = datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)
    updated_after = days_ago.date().isoformat()

    print(f"📅 Fetching articles updated since: {updated_after}")
    print(f"📊 Reading progress threshold: {READING_PROGRESS_THRESHOLD*100}%")

    all_articles = []
    next_page_cursor = None

    # Fetch all recent articles (with pagination)
    while True:
        params = {
            "category": "article",
            "updatedAfter": updated_after,
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

            # If date filtering fails, try without it (fallback)
            if r.status_code == 400:
                print("⚠️  Date filtering not supported, fetching without date filter...")
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

            print(f"  📥 Fetched {len(results)} articles (total: {len(all_articles)})")

            # Check for next page
            next_page_cursor = data.get("nextPageCursor")
            if not next_page_cursor or len(results) == 0:
                break

            # Safety limit: don't fetch more than 1000 articles
            if len(all_articles) >= 1000:
                print("⚠️  Reached 1000 article limit, stopping pagination")
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

    print(f"✅ Found {len(finished_articles)} finished articles")

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

    if reading_progress and reading_progress < 1.0:
        body_parts.append(f"**Progress:** {reading_progress*100:.1f}% complete\n\n")

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
    print("=" * 70)
    print("📚 Readwise Reader → Day One Sync - Ultimate Edition")
    print("=" * 70)
    print(f"Mode: {'CLI' if USE_CLI else 'Email'}")
    print(f"Individual entries: {CREATE_INDIVIDUAL_ENTRIES}")
    print(f"Daily summary: {CREATE_DAILY_SUMMARY}")
    print("=" * 70)

    try:
        # Fetch finished articles
        articles = get_recently_finished_articles()

        if not articles:
            print("\n✨ No new finished articles found.")
            print(f"   (Checked last {DAYS_BACK} day(s), threshold: {READING_PROGRESS_THRESHOLD*100}%)")
            return

        print(f"\n📝 Processing {len(articles)} articles...\n")

        # Track successful entries
        processed_ids = load_processed_articles()
        new_processed_ids = []

        # Create individual entries
        if CREATE_INDIVIDUAL_ENTRIES:
            print(f"Creating individual entries:\n")
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
                except Exception as e:
                    print(f"      ❌ Error: {e}")

            print(f"\n✅ Created {success_count}/{len(articles)} individual entries\n")

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

        print("\n" + "=" * 70)
        print("✅ Sync complete!")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error during sync: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
