#!/usr/bin/env python3
"""
Diagnostic script to test Readwise API endpoints and find the actual issue
"""
import os
import requests
from datetime import datetime, timezone, timedelta

READWISE_TOKEN = os.environ.get("READWISE_TOKEN")

if not READWISE_TOKEN:
    print("❌ ERROR: READWISE_TOKEN environment variable not set")
    exit(1)

print("🔍 Readwise API Diagnostic Tool")
print("=" * 50)

# Test 1: Basic authentication
print("\n1️⃣ Testing authentication...")
try:
    r = requests.get(
        "https://readwise.io/api/v2/auth/",
        headers={"Authorization": f"Token {READWISE_TOKEN}"},
        timeout=10
    )
    print(f"   Status: {r.status_code}")
    if r.status_code == 204:
        print("   ✅ Authentication successful")
    else:
        print(f"   ❌ Authentication failed: {r.text}")
except Exception as e:
    print(f"   ❌ Request failed: {e}")

# Test 2: List endpoint without parameters
print("\n2️⃣ Testing /api/v3/list without parameters...")
try:
    r = requests.get(
        "https://readwise.io/api/v3/list",
        headers={"Authorization": f"Token {READWISE_TOKEN}"},
        timeout=10
    )
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"   ✅ Success! Found {data.get('count', 0)} total items")
        if data.get('results'):
            print(f"   First item category: {data['results'][0].get('category', 'unknown')}")
    else:
        print(f"   ❌ Failed: {r.text}")
except Exception as e:
    print(f"   ❌ Request failed: {e}")

# Test 3: List endpoint with category filter
print("\n3️⃣ Testing /api/v3/list with category=article...")
try:
    r = requests.get(
        "https://readwise.io/api/v3/list",
        params={"category": "article"},
        headers={"Authorization": f"Token {READWISE_TOKEN}"},
        timeout=10
    )
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"   ✅ Success! Found {len(data.get('results', []))} articles")
    else:
        print(f"   ❌ Failed: {r.text}")
except Exception as e:
    print(f"   ❌ Request failed: {e}")

# Test 4: Test different date formats
print("\n4️⃣ Testing updatedAfter parameter with different formats...")

date_formats = [
    ("ISO format (Z)", datetime.now(timezone.utc).isoformat()),
    ("ISO date only", datetime.now(timezone.utc).date().isoformat()),
    ("Yesterday ISO", (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()),
    ("7 days ago", (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()),
    ("30 days ago", (datetime.now(timezone.utc) - timedelta(days=30)).date().isoformat()),
    ("RFC 3339", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")),
]

for format_name, date_value in date_formats:
    print(f"\n   Testing {format_name}: {date_value}")
    try:
        r = requests.get(
            "https://readwise.io/api/v3/list",
            params={"category": "article", "updatedAfter": date_value},
            headers={"Authorization": f"Token {READWISE_TOKEN}"},
            timeout=10
        )
        print(f"   Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"   ✅ Success! Found {len(data.get('results', []))} articles")
            break  # Found working format
        else:
            print(f"   ❌ Failed: {r.text[:200]}...")
    except Exception as e:
        print(f"   ❌ Request failed: {e}")

# Test 5: Check v2 API for comparison
print("\n5️⃣ Testing v2 API /api/v2/books endpoint...")
try:
    r = requests.get(
        "https://readwise.io/api/v2/books",
        params={"page_size": 5},
        headers={"Authorization": f"Token {READWISE_TOKEN}"},
        timeout=10
    )
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"   ✅ Success! Found {data.get('count', 0)} total books")
        for book in data.get('results', [])[:3]:
            print(f"   - {book.get('title', 'Untitled')[:50]} ({book.get('category', 'unknown')})")
    else:
        print(f"   ❌ Failed: {r.text}")
except Exception as e:
    print(f"   ❌ Request failed: {e}")

# Test 6: Get user info
print("\n6️⃣ Getting user info to check timezone...")
try:
    r = requests.get(
        "https://readwise.io/api/v2/user/",
        headers={"Authorization": f"Token {READWISE_TOKEN}"},
        timeout=10
    )
    if r.status_code == 200:
        user = r.json()
        print(f"   ✅ User email: {user.get('email', 'unknown')}")
    else:
        print(f"   ❌ Failed to get user info")
except Exception as e:
    print(f"   ❌ Request failed: {e}")

print("\n" + "=" * 50)
print("Diagnostic complete. Check the results above to identify the issue.") 