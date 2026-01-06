#!/usr/bin/env python3
"""
Test script to see exactly what data the Readwise Reader API returns
"""
import os
import requests
import json
from datetime import datetime, timezone, timedelta

READWISE_TOKEN = os.environ.get("READWISE_TOKEN")

if not READWISE_TOKEN:
    print("❌ ERROR: READWISE_TOKEN environment variable not set")
    print("Please set it with: export READWISE_TOKEN='your_token_here'")
    exit(1)

print("🔍 Testing Readwise Reader API Response Structure")
print("=" * 60)

# Test 1: Get recent articles without any date filter
print("\n1️⃣ Fetching recent articles (no date filter)...")
try:
    r = requests.get(
        "https://readwise.io/api/v3/list",
        params={"category": "article", "page_size": 3},
        headers={"Authorization": f"Token {READWISE_TOKEN}"},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()

    print(f"✅ Success! Found {len(data.get('results', []))} articles")
    print(f"Total count: {data.get('count', 0)}")

    if data.get('results'):
        print("\n📄 First article full structure:")
        article = data['results'][0]
        print(json.dumps(article, indent=2, default=str))

        print("\n📋 Available fields in this article:")
        for key in sorted(article.keys()):
            value = article[key]
            if isinstance(value, str) and len(value) > 100:
                print(f"  - {key}: (long string, {len(value)} chars)")
            else:
                print(f"  - {key}: {value}")
    else:
        print("ℹ️  No articles found in your Readwise Reader")

except Exception as e:
    print(f"❌ Request failed: {e}")

# Test 2: Check what fields are typically populated
print("\n\n2️⃣ Checking which metadata fields are populated...")
try:
    r = requests.get(
        "https://readwise.io/api/v3/list",
        params={"category": "article", "page_size": 10},
        headers={"Authorization": f"Token {READWISE_TOKEN}"},
        timeout=30,
    )
    r.raise_for_status()
    articles = r.json().get("results", [])

    if articles:
        # Check which fields have values
        field_stats = {}
        for article in articles:
            for key, value in article.items():
                if key not in field_stats:
                    field_stats[key] = {"count": 0, "sample": None}
                if value:
                    field_stats[key]["count"] += 1
                    if field_stats[key]["sample"] is None:
                        field_stats[key]["sample"] = value

        print(f"\n📊 Field population across {len(articles)} articles:")
        for field in sorted(field_stats.keys()):
            stats = field_stats[field]
            percentage = (stats["count"] / len(articles)) * 100
            sample = stats["sample"]
            if isinstance(sample, str) and len(sample) > 50:
                sample = sample[:50] + "..."
            print(f"  - {field}: {stats['count']}/{len(articles)} ({percentage:.0f}%) - Example: {sample}")

except Exception as e:
    print(f"❌ Request failed: {e}")

# Test 3: Test different location filters
print("\n\n3️⃣ Testing different location filters...")
locations = ["new", "later", "archive"]
for location in locations:
    try:
        r = requests.get(
            "https://readwise.io/api/v3/list",
            params={"category": "article", "location": location, "page_size": 1},
            headers={"Authorization": f"Token {READWISE_TOKEN}"},
            timeout=30,
        )
        r.raise_for_status()
        count = len(r.json().get("results", []))
        print(f"  - location='{location}': {count} article(s)")
    except Exception as e:
        print(f"  - location='{location}': Error - {e}")

# Test 4: Test date filtering with different formats
print("\n\n4️⃣ Testing date filtering (last 30 days)...")
try:
    # Try ISO format
    thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).date().isoformat()
    print(f"  Using date: {thirty_days_ago}")

    r = requests.get(
        "https://readwise.io/api/v3/list",
        params={"category": "article", "updatedAfter": thirty_days_ago, "page_size": 5},
        headers={"Authorization": f"Token {READWISE_TOKEN}"},
        timeout=30,
    )

    if r.status_code == 200:
        articles = r.json().get("results", [])
        print(f"  ✅ Found {len(articles)} articles updated in last 30 days")

        if articles:
            print("\n  Recent articles:")
            for i, article in enumerate(articles[:3], 1):
                title = article.get('title', 'No title')[:50]
                updated = article.get('updated_at', article.get('last_opened_at', 'unknown'))
                progress = article.get('reading_progress', 0)
                author = article.get('author', 'Unknown')
                print(f"  {i}. {title}")
                print(f"     Author: {author}")
                print(f"     Progress: {progress * 100:.1f}%")
                print(f"     Updated: {updated}")
    else:
        print(f"  ❌ Failed with status {r.status_code}: {r.text[:200]}")

except Exception as e:
    print(f"  ❌ Request failed: {e}")

print("\n" + "=" * 60)
print("✅ API structure test complete!")
