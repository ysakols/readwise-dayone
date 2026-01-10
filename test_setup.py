#!/usr/bin/env python3
"""
Test script to verify your Readwise → Day One setup is working correctly.
Run this before setting up the automation to ensure everything is configured properly.
"""
import os
import requests
from datetime import datetime, timezone

def test_readwise_connection():
    """Test Readwise API connection"""
    token = os.getenv("READWISE_TOKEN")
    if not token:
        print("❌ READWISE_TOKEN not found in environment variables")
        return False
    
    try:
        r = requests.get(
            "https://readwise.io/api/v3/list",
            params={"category": "article", "page_size": 1},
            headers={"Authorization": f"Token {token}"},
            timeout=30,
        )
        r.raise_for_status()
        print("✅ Readwise API connection successful")
        return True
    except Exception as e:
        print(f"❌ Readwise API connection failed: {e}")
        return False

def test_dayone_cli():
    """Test Day One CLI availability"""
    if os.getenv("USE_CLI", "false").lower() != "true":
        print("ℹ️  USE_CLI not set to true, skipping CLI test")
        return True
    
    try:
        import subprocess
        result = subprocess.run(["dayone2", "--version"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Day One CLI is available")
            return True
        else:
            print("❌ Day One CLI not working properly")
            return False
    except FileNotFoundError:
        print("❌ Day One CLI not found. Install it with:")
        print("   sudo bash /Applications/Day\\ One.app/Contents/Resources/install_cli.sh")
        return False
    except Exception as e:
        print(f"❌ Day One CLI test failed: {e}")
        return False

def test_email_config():
    """Test email configuration"""
    if os.getenv("USE_CLI", "false").lower() == "true":
        print("ℹ️  Using CLI method, skipping email config test")
        return True
    
    required_vars = ["DAYONE_EMAIL", "SMTP_USER", "SMTP_PASS"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing email configuration: {', '.join(missing_vars)}")
        return False
    
    print("✅ Email configuration variables found")
    return True

def test_sample_data():
    """Test fetching sample data from Readwise"""
    token = os.getenv("READWISE_TOKEN")
    if not token:
        return False
    
    try:
        r = requests.get(
            "https://readwise.io/api/v3/list",
            params={"category": "article", "page_size": 5},
            headers={"Authorization": f"Token {token}"},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        articles = data.get("results", [])
        
        if articles:
            print(f"✅ Found {len(articles)} articles in Readwise")
            print("   Sample articles:")
            for i, article in enumerate(articles[:3], 1):
                title = article.get('title', 'No title')[:50]
                progress = article.get('reading_progress', 0)
                print(f"   {i}. {title}... (progress: {progress:.1%})")
        else:
            print("ℹ️  No articles found in Readwise (this is normal if you haven't added any)")
        
        return True
    except Exception as e:
        print(f"❌ Failed to fetch sample data: {e}")
        return False

def main():
    print("🧪 Testing Readwise → Day One Setup")
    print("=" * 40)
    
    tests = [
        ("Readwise API Connection", test_readwise_connection),
        ("Day One CLI", test_dayone_cli),
        ("Email Configuration", test_email_config),
        ("Sample Data Fetch", test_sample_data),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Testing {test_name}...")
        if test_func():
            passed += 1
    
    print("\n" + "=" * 40)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your setup is ready.")
        print("\nNext steps:")
        print("1. Test the full sync: python sync.py")
        print("2. Set up GitHub Actions for daily automation")
    else:
        print("⚠️  Some tests failed. Please fix the issues above before proceeding.")
        print("\nCommon fixes:")
        print("- Get your Readwise token from: https://readwise.io/access_token")
        print("- For CLI: Install Day One CLI and sign into Day One")
        print("- For email: Set up email-to-journal in Day One settings")

if __name__ == "__main__":
    main() 