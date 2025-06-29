# ☕ Daily Readwise → Day One Automation

Automatically sync your daily Readwise reading activity to Day One journal entries. This system runs daily and creates a formatted entry with all the articles you **finished reading** that day.

## 🚀 Quick Start

### 1. What You'll Need

| Item                     | Where to get it                                                                                                                                              | Notes                                     |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------- |
| **Readwise API token**   | [https://readwise.io/access\_token](https://readwise.io/access_token)                                                                                        | Copy the long string shown under *Token*. |
| **Day One write method** | Pick **one**:<br>**A. Day One CLI** (macOS only) – uses your logged-in Day One account.<br>**B. Email-to-Journal** – works from any server; Premium feature. | Decide before continuing.                 |
| **Python 3.8+**          | Already installed on macOS / most Linux images.                                                                                                              |                                           |
| **Hosting choice**       | • **GitHub Actions** (no server)<br>• **cron/Launchd on a Mac** (always-on machine)<br>• **cron on Linux/VPS** (email route)                                 | Detailed setup below.                     |

### 2. Environment Variables Required

| Variable                                           | Needed for                  | Example                             |
| -------------------------------------------------- | --------------------------- | ----------------------------------- |
| `READWISE_TOKEN`                                   | Always                      | `RW_abc123…`                        |
| `USE_CLI=true`                                     | **Only** if using macOS CLI | `true`                              |
| `DAYONE_EMAIL`                                     | Email route                 | `abc123+reading@journal.dayone.app` |
| `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`, `SMTP_HOST` | Email route                 | Gmail or any SMTP                   |

## 📋 Setup Instructions

### Option A: GitHub Actions (Recommended - No Server Required)

1. **Fork this repository** or create a new private repository
2. **Add your secrets** in GitHub:
   - Go to your repo → Settings → Secrets and variables → Actions
   - Add the following secrets:
     - `READWISE_TOKEN`: Your Readwise API token
     - `DAYONE_EMAIL`: Your Day One email-to-journal address
     - `SMTP_USER`: Your email username
     - `SMTP_PASS`: Your email password/app password
     - `SMTP_FROM`: Your from email address (usually same as SMTP_USER)
3. **The workflow will run automatically** every day at 2:15 UTC (7:15 PM PT)

### Option B: Local macOS Setup (Day One CLI)

1. **Set up Python environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Install Day One CLI**:
   ```bash
   sudo bash /Applications/Day\ One.app/Contents/Resources/install_cli.sh
   ```

3. **Make the script executable**:
   ```bash
   chmod +x sync_readwise.py
   ```

4. **Set up environment variables** in your shell profile (`~/.zshrc` or `~/.bash_profile`):
   ```bash
   export READWISE_TOKEN="your_readwise_token_here"
   export USE_CLI="true"
   ```

5. **Test your setup**:
   ```bash
   source venv/bin/activate
   python test_setup.py
   ```

6. **Set up cron** to run daily:
   ```bash
   crontab -e
   ```
   Add this line:
   ```
   0 20 * * * cd /path/to/readwise-dayone && source venv/bin/activate && READWISE_TOKEN=your_token USE_CLI=true python sync_readwise.py >> ~/Library/Logs/readwise_dayone.log 2>&1
   ```

### Option C: Linux/VPS Setup (Email Method)

1. **Set up Python environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Set up environment variables**:
   ```bash
   export READWISE_TOKEN="your_readwise_token_here"
   export DAYONE_EMAIL="your_dayone_email@journal.dayone.app"
   export SMTP_USER="your_email@gmail.com"
   export SMTP_PASS="your_app_password"
   export SMTP_FROM="your_email@gmail.com"
   ```

3. **Test your setup**:
   ```bash
   source venv/bin/activate
   python test_setup.py
   ```

4. **Set up cron**:
   ```bash
   crontab -e
   ```
   Add this line:
   ```
   15 2 * * * cd /path/to/readwise-dayone && source venv/bin/activate && READWISE_TOKEN=your_token DAYONE_EMAIL=your_email SMTP_USER=your_user SMTP_PASS=your_pass SMTP_FROM=your_from python sync_readwise.py >> /var/log/readwise_dayone.log 2>&1
   ```

## 🔧 Day One Setup

### For Day One CLI (macOS)
1. Open Day One and sign in
2. (Optional) Create a "Reading Log" journal in the app
3. Install the CLI as shown above

### For Email-to-Journal
1. In Day One iOS or macOS → **Settings → Email-to-Journal**
2. Copy the unique email address (one per journal)
3. Keep it secret - anyone who knows it can add entries

## 🧪 Testing Your Setup

Before setting up automation, test your configuration:

```bash
# Set up virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set your environment variables
export READWISE_TOKEN="your_token_here"
export USE_CLI="true"  # or set email variables

# Run the test
python test_setup.py
```

The test script will check:
- ✅ Readwise API connection
- ✅ Day One CLI availability (if using CLI)
- ✅ Email configuration (if using email)
- ✅ Sample data fetching

## 📝 What the Script Does

1. **Fetches today's finished articles** from Readwise API (reading progress ≥ 95%)
2. **Formats them nicely** with Markdown links
3. **Creates a Day One entry** with the format:
   ```
   ## 📚 Articles I finished reading on 2024-01-15

   - [Article Title](https://article-url.com)
   - [Another Article](https://another-url.com)
   ```

## 🎯 Smart Filtering

The script uses intelligent filtering to ensure you only log articles you actually **finished reading**:

- **Reading Progress ≥ 95%**: Only includes articles where you reached at least 95% completion
- **Today's Activity**: Only includes articles that were opened/read today
- **No Partial Reads**: Excludes articles you just archived without reading
- **No Duplicates**: Multiple runs won't create duplicate entries

## 🛡️ Safety Features

- **Idempotent**: Running multiple times won't create duplicates
- **Error handling**: Script will fail gracefully and report errors
- **Smart filtering**: Only includes articles with ≥95% reading progress from today
- **Timeout protection**: API calls timeout after 30 seconds

## 🔍 Troubleshooting

### Common Issues

1. **"No articles today"** - This is normal if you didn't finish reading anything in Readwise today
2. **Authentication errors** - Check your `READWISE_TOKEN` is correct
3. **SMTP errors** - Verify your email credentials and enable "Less secure app access" or use app passwords
4. **Day One CLI not found** - Make sure you've installed the CLI and are signed into Day One

### Testing

You can test the script manually by running:
```bash
source venv/bin/activate
python sync_readwise.py
```

### Monitoring

- **GitHub Actions**: Check the Actions tab in your repository
- **Local cron**: Check the log files specified in your cron job
- **Manual testing**: Run the script directly to see output

## 🎯 Customization

### Change the Schedule
- **GitHub Actions**: Edit the cron in `.github/workflows/daily.yml`
- **Local cron**: Modify the cron schedule in your crontab

### Custom Formatting
Edit the `format_entry()` function in `sync_readwise.py` to change how entries look.

### Adjust Reading Threshold
To change what constitutes "finished reading", modify the `reading_progress >= 0.95` line in `get_today_articles()`.

### Multiple Runs Per Day
Change the cron schedule to run more frequently (e.g., `0 */6 * * *` for every 6 hours).

## 📄 License

This project is open source. Feel free to modify and distribute as needed.

## 🤝 Contributing

Found a bug or have an improvement? Open an issue or submit a pull request! 