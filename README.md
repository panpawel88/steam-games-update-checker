# Steam Games Update Checker

Automatically monitor Steam games for updates and receive notifications via Mattermost.

## Features

- Tracks Steam game updates using the Steam News API
- Runs automatically via GitHub Actions (daily schedule)
- Sends notifications to Mattermost when updates are detected
- Commits tracking data to repository for historical record
- No Steam API key required (uses public endpoints)

## How It Works

1. **Game Tracking**: Monitors games listed in `games.txt` using their Steam App IDs
2. **Update Detection**: Checks the latest news/update posts for each game via Steam's News API
3. **Notification**: Sends Mattermost message when new updates are detected
4. **Data Persistence**: Commits updated tracking data to `tracked_games.json`

## Setup Instructions

### 1. Fork/Clone This Repository

```bash
git clone https://github.com/yourusername/steam-games-update-checker.git
cd steam-games-update-checker
```

### 2. Configure Games to Track

Edit `games.txt` and add your games in the format:
```
Game Name,AppID
```

Example:
```
Team Fortress 2,440
Counter-Strike 2,730
Dota 2,570
```

**Finding Steam App IDs:**
- Visit the game's Steam Store page
- Look at the URL: `https://store.steampowered.com/app/[APP_ID]/`
- Or use: https://steamdb.info/

### 3. Set Up Mattermost Webhook (Optional)

1. In Mattermost, go to **Integrations** → **Incoming Webhooks**
2. Create a new webhook
3. Copy the webhook URL

### 4. Configure GitHub Repository

#### Add Mattermost Webhook Secret

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `MATTERMOST_WEBHOOK_URL`
5. Value: Your Mattermost webhook URL
6. Click **Add secret**

#### Enable GitHub Actions

1. Go to **Actions** tab
2. Enable workflows if prompted

### 5. Customize Schedule (Optional)

Edit `.github/workflows/check_updates.yml` and modify the cron schedule:

```yaml
schedule:
  - cron: '0 9 * * *'  # Daily at 9:00 AM UTC
```

Cron format: `minute hour day month weekday`

Examples:
- `0 */6 * * *` - Every 6 hours
- `0 0 * * *` - Daily at midnight
- `0 12 * * 1` - Every Monday at noon

### 6. Initial Run

**Option A: Manual Trigger**
1. Go to **Actions** tab
2. Select "Check Steam Games Updates" workflow
3. Click **Run workflow**

**Option B: Commit Changes**
```bash
git add .
git commit -m "Initial setup"
git push
```

## File Structure

```
steam-games-update-checker/
├── games.txt                   # List of games to track
├── tracked_games.json          # Tracking data (auto-updated)
├── check_updates.py            # Main Python script
├── requirements.txt            # Python dependencies
├── .github/
│   └── workflows/
│       └── check_updates.yml   # GitHub Actions workflow
└── README.md                   # This file
```

## Local Testing

Test the script locally before deploying:

```bash
# Install dependencies
pip install -r requirements.txt

# Run check (without Mattermost)
python check_updates.py

# Run check with Mattermost
export MATTERMOST_WEBHOOK_URL="your_webhook_url"
python check_updates.py
```

## Tracked Data Format

`tracked_games.json` stores:

```json
{
  "440": {
    "name": "Team Fortress 2",
    "last_news_date": 1698765432,
    "last_news_title": "Halloween Update 2024",
    "last_checked": "2024-10-29T12:00:00.000000"
  }
}
```

## Notification Format

Mattermost notifications include:

- Game name
- Steam App ID
- Update title
- Update date
- Link to Steam Store page

## Troubleshooting

### No notifications received

1. Verify `MATTERMOST_WEBHOOK_URL` secret is set correctly
2. Check GitHub Actions logs for errors
3. Test webhook manually:
   ```bash
   curl -X POST -H 'Content-Type: application/json' \
     -d '{"text":"Test message"}' \
     YOUR_WEBHOOK_URL
   ```

### GitHub Actions not running

1. Ensure Actions are enabled in repository settings
2. Check if workflow file has correct syntax
3. Verify cron schedule is valid

### Script errors

1. Check Python version (requires 3.7+)
2. Verify `games.txt` format is correct
3. Check Steam App IDs are valid
4. Review GitHub Actions logs

### False positives

The script tracks news updates, which may include:
- Game updates/patches
- Community announcements
- Event notifications

This is by design since Steam doesn't provide public version numbers.

## Advanced Configuration

### Filtering News Types

Modify `check_updates.py` to filter specific news types or sources.

### Custom Notification Format

Edit the `_send_mattermost_notification()` method to customize message format.

### Multiple Notification Channels

Add additional webhook URLs and modify the notification logic to support multiple channels.

## Limitations

- Uses Steam News API (detects news posts, not direct version changes)
- Requires public news updates for detection
- Rate limited to 1 request/second per game (built-in delay)
- Some games may not post news for all updates

## Contributing

Contributions welcome! Please open an issue or submit a pull request.

## License

MIT License - feel free to use and modify as needed.

## Credits

Built using:
- [Steam Web API](https://steamcommunity.com/dev)
- [GitHub Actions](https://github.com/features/actions)
- [Mattermost](https://mattermost.com/)
