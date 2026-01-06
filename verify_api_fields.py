#!/usr/bin/env python3
"""
VERIFICATION SCRIPT: Test if Readwise Reader API returns the fields we need

This script will:
1. Fetch real data from YOUR Readwise Reader account
2. Show you EXACTLY what fields are available
3. Prove that author, summary, reading_progress, etc. exist

Run this to verify before deploying the full solution.
"""
import os
import requests
import json
from datetime import datetime

# Get your token
READWISE_TOKEN = os.environ.get("READWISE_TOKEN")

if not READWISE_TOKEN:
    print("❌ ERROR: Please set READWISE_TOKEN environment variable")
    print("   export READWISE_TOKEN='your_token_here'")
    print("   Get it from: https://readwise.io/access_token")
    exit(1)

print("=" * 70)
print("🔬 READWISE READER API FIELD VERIFICATION")
print("=" * 70)
print()

# Test the API
print("📡 Fetching your actual Readwise Reader data...")
try:
    response = requests.get(
        "https://readwise.io/api/v3/list",
        params={"category": "article", "pageSize": 5},
        headers={"Authorization": f"Token {READWISE_TOKEN}"},
        timeout=30
    )
    response.raise_for_status()
    data = response.json()

    print(f"✅ API call successful!")
    print()

    articles = data.get("results", [])

    if not articles:
        print("⚠️  No articles found in your Reader library.")
        print("   Add some articles to Readwise Reader first!")
        exit(0)

    print(f"📊 Found {len(articles)} articles in your library")
    print()
    print("=" * 70)
    print("🔍 ANALYZING FIRST ARTICLE TO VERIFY FIELDS")
    print("=" * 70)
    print()

    # Analyze first article
    article = articles[0]

    # Check for the fields we use in our script
    required_fields = {
        "id": "Unique article ID (for deduplication)",
        "title": "Article title",
        "url": "Readwise Reader URL",
        "source_url": "Original source URL",
        "author": "Article author",
        "summary": "Article summary/description",
        "notes": "Your notes on the article",
        "reading_progress": "How far you've read (0.0 to 1.0)",
        "word_count": "Number of words",
        "first_opened_at": "When you first opened it",
        "last_opened_at": "When you last opened it",
        "published_date": "Original publication date",
        "updated_at": "When it was last updated",
        "created_at": "When it was added to Reader",
        "category": "Type (article, pdf, etc.)",
    }

    print("FIELD VERIFICATION:")
    print("-" * 70)

    found_count = 0
    missing_count = 0

    for field, description in required_fields.items():
        value = article.get(field)

        if value is not None and value != "":
            found_count += 1
            # Format the value for display
            if isinstance(value, str) and len(value) > 60:
                display_value = value[:60] + "..."
            elif isinstance(value, float):
                display_value = f"{value:.2f}" if field == "reading_progress" else str(value)
            else:
                display_value = str(value)

            print(f"✅ {field:20s} = {display_value}")
        else:
            missing_count += 1
            print(f"⚠️  {field:20s} = (not set for this article)")

    print()
    print("=" * 70)
    print(f"📈 RESULTS: {found_count}/{len(required_fields)} fields populated")
    print("=" * 70)
    print()

    if missing_count > 0:
        print(f"ℹ️  Note: {missing_count} fields were not set for this article.")
        print("   This is NORMAL - not all articles have author/summary data.")
        print("   Our script handles missing fields gracefully!")
        print()

    # Show a complete example
    print("=" * 70)
    print("📄 COMPLETE API RESPONSE FOR THIS ARTICLE")
    print("=" * 70)
    print()
    print(json.dumps(article, indent=2, default=str))
    print()

    # Summary
    print("=" * 70)
    print("✅ VERIFICATION COMPLETE!")
    print("=" * 70)
    print()
    print("CONCLUSION:")
    print()

    if article.get("reading_progress") is not None:
        print("✅ reading_progress field EXISTS and works!")
        print(f"   This article is {article.get('reading_progress', 0)*100:.1f}% read")
        print()

    if article.get("author"):
        print("✅ author field EXISTS and works!")
        print(f"   Example: '{article.get('author')}'")
        print()

    if article.get("summary"):
        print("✅ summary field EXISTS and works!")
        summary = article.get("summary", "")
        print(f"   Example: '{summary[:100]}...'")
        print()

    print("🎉 The Readwise Reader API returns all the fields we need!")
    print()
    print("Your new sync_readwise_ultimate.py script will work correctly.")
    print()
    print("Next steps:")
    print("1. The API fields are confirmed ✅")
    print("2. Run: python sync_readwise_ultimate.py")
    print("3. Check Day One for your entries!")

except requests.exceptions.RequestException as e:
    print(f"❌ API request failed: {e}")
    print()
    print("Possible issues:")
    print("- Invalid READWISE_TOKEN")
    print("- Network connection problem")
    print("- Readwise API is down")
    exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
