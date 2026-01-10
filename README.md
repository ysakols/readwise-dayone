# Readwise Reader → Day One

Automatically sync archived items from Readwise Reader to Day One journal entries.

## How It Works

When you archive an article, RSS item, or newsletter in Readwise Reader, this script creates a rich Day One entry with:

- Title and author
- Original link and Reader link
- Reading progress
- Word count and estimated read time
- AI-generated summary (when available)
- Your notes/highlights

## Quick Start

### 1. Get Your Credentials

| Item | Where to get it |
|------|-----------------|
| Readwise API token | [readwise.io/access_token](https://readwise.io/access_token) |
| Day One email | Day One → Settings → Email-to-Journal |
| Gmail app password | [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) |

### 2. Set Up Locally

```bash
# Clone and set up
git clone https://github.com/ysakols/readwise-dayone.git
cd readwise-dayone
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set environment variables
export READWISE_TOKEN="your_token"
export DAYONE_EMAIL="your@journal.dayone.app"
export SMTP_HOST="smtp.gmail.com"
export SMTP_USER="your@gmail.com"
export SMTP_PASS="your_app_password"
export SMTP_FROM="your@gmail.com"

# Test your setup
python test_setup.py

# Run the sync
python sync.py
```

### 3. Set Up GitHub Actions (Recommended)

1. Fork this repository
2. Go to Settings → Secrets and variables → Actions
3. Add these secrets:
   - `READWISE_TOKEN`
   - `DAYONE_EMAIL`
   - `SMTP_USER`
   - `SMTP_PASS`
   - `SMTP_FROM`
4. The workflow runs daily at midnight PT (7:00 UTC)

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `READWISE_TOKEN` | required | Your Readwise API token |
| `DAYONE_EMAIL` | required | Day One email-to-journal address |
| `SMTP_*` | required | Email credentials for sending |
| `CATEGORIES` | `article,rss,email` | Content types to sync |
| `DAYS_BACK` | `1` | How many days back to check |
| `EMAIL_DELAY` | `2.0` | Seconds between emails (rate limiting) |
| `USE_CLI` | `false` | Use Day One CLI instead of email (macOS) |

## What Gets Synced

The script syncs items that are:
1. **Archived** in Readwise Reader (articles, RSS, newsletters)
2. **Recently moved** to archive (within `DAYS_BACK` days)
3. **Not already synced** (tracks state to avoid duplicates)

## Files

```
sync.py          # Main sync script
test_setup.py    # Verify your configuration
env.example      # Example environment variables
requirements.txt # Python dependencies (just requests)
```

## License

MIT
