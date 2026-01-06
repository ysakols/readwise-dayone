# 🚀 Migration Guide: Switching to the New Version

## Quick Migration (5 minutes)

### Step 1: Understand What Changed

The old version (`sync_readwise.py`) has been **replaced** with:
- ✅ `sync_readwise_ultimate.py` - **RECOMMENDED** - Full-featured with deduplication
- ✅ `sync_readwise_v2.py` - Simpler version for individual entries only

**Why migrate?**
- ❌ Old version: Creates 1 daily summary with just title + URL
- ✅ New version: Creates individual entries with author, summary, metadata

### Step 2: Test Locally First

Before changing your automation, test the new version:

```bash
# Set your credentials
export READWISE_TOKEN="your_token_here"
export DAYONE_EMAIL="your_email@journal.dayone.app"
export SMTP_USER="your_email@gmail.com"
export SMTP_PASS="your_app_password"
export SMTP_FROM="your_email@gmail.com"

# Configure what you want (individual entries)
export CREATE_INDIVIDUAL_ENTRIES=true
export CREATE_DAILY_SUMMARY=false

# Test it!
python sync_readwise_ultimate.py
```

Check your Day One to see if the entries look good!

### Step 3: Update GitHub Actions

**The workflow is already updated!** I've changed:
- `.github/workflows/daily.yml` to use `sync_readwise_ultimate.py`

Your GitHub Actions will now:
1. ✅ Create individual entries per article
2. ✅ Include author, summary, word count, etc.
3. ✅ Track processed articles (no duplicates)
4. ✅ Handle pagination for large libraries

### Step 4: Customize (Optional)

Want to customize the behavior? Edit the workflow:

```yaml
# .github/workflows/daily.yml
env:
  # Choose your mode
  CREATE_INDIVIDUAL_ENTRIES: true   # Individual detailed entries
  CREATE_DAILY_SUMMARY: false       # Daily rollup

  # Adjust thresholds
  READING_PROGRESS_THRESHOLD: 0.95  # 95% = finished
  DAYS_BACK: 1                      # Check last day
```

**Common configurations:**

| Use Case | Individual | Summary | Threshold | Days Back |
|----------|-----------|---------|-----------|-----------|
| Your use case (individual entries) | `true` | `false` | `0.95` | `1` |
| Both individual + summary | `true` | `true` | `0.95` | `1` |
| Just daily summary (old behavior) | `false` | `true` | `0.95` | `1` |
| Catch-up mode (last week) | `true` | `false` | `0.90` | `7` |
| Aggressive (include partially read) | `true` | `false` | `0.80` | `1` |

---

## What's Different?

### Old Entry Format
```markdown
## 📚 Articles I finished reading on 2026-01-06

- [The Future of AI](https://example.com/ai)
- [Better Habits](https://example.com/habits)
```

### New Entry Format
```markdown
# The Future of AI in Healthcare

**Author:** Dr. Sarah Chen
**Link:** [https://example.com/ai-healthcare](https://example.com/ai-healthcare)
**Read:** January 6, 2026 at 10:30 AM
**Length:** ~2,500 words (~12 min read)

---

## Summary

This comprehensive article explores how artificial intelligence is
revolutionizing healthcare delivery...

---

*Synced from Readwise Reader*
```

---

## Common Questions

### Q: Will I get duplicate entries?

**A:** No! The ultimate version tracks processed articles in `~/.readwise_dayone_state.json`.

### Q: What if I want both individual + daily summary?

**A:** Set both to true:
```bash
export CREATE_INDIVIDUAL_ENTRIES=true
export CREATE_DAILY_SUMMARY=true
```

### Q: Can I run a one-time catch-up for old articles?

**A:** Yes! Set `DAYS_BACK=30` to process the last 30 days, then change it back to `1`.

```bash
# One-time catch-up
export DAYS_BACK=30
python sync_readwise_ultimate.py

# Then set back to daily
export DAYS_BACK=1
```

### Q: What if some articles are missing author/summary?

**A:** Not all articles have complete metadata. The script gracefully handles missing data:
- No author? Shows "by" without name
- No summary? Skips summary section
- No word count? Skips length info

### Q: Can I change the reading threshold?

**A:** Yes! `READING_PROGRESS_THRESHOLD`:
- `1.0` = Only 100% read (strictest)
- `0.95` = 95% read (default, recommended)
- `0.80` = 80% read (includes partially-read)

### Q: Will the old script still work?

**A:** Yes, but it's not recommended. The old `sync_readwise.py` is preserved but has the issues documented in FIXES_AND_IMPROVEMENTS.md.

---

## Troubleshooting

### "No articles found"

Try:
```bash
# Lower threshold
export READING_PROGRESS_THRESHOLD=0.80

# Look back further
export DAYS_BACK=7
```

### "Getting duplicate entries"

You might be using the old script or v2. Switch to `sync_readwise_ultimate.py` which has built-in deduplication.

### "Missing metadata (author/summary)"

This is normal - not all articles have complete metadata. The script shows what's available.

---

## Rollback (if needed)

If you need to rollback to the old version:

```yaml
# .github/workflows/daily.yml
- run: python sync_readwise.py  # Old version
```

But we recommend using the new version! 🎉

---

## Need Help?

1. Check `FIXES_AND_IMPROVEMENTS.md` for detailed explanations
2. Read the main `README.md` for setup instructions
3. Test locally before deploying to GitHub Actions

**Happy reading journaling!** 📚
