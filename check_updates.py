#!/usr/bin/env python3
"""
Steam Games Update Checker
Monitors Steam games for updates using the Steam News API
"""

import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Tuple
import requests


class SteamUpdateChecker:
    """Checks Steam games for updates and sends notifications"""

    STEAM_NEWS_API = "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/"

    def __init__(self, games_file: str = "games.txt",
                 tracked_file: str = "tracked_games.json",
                 mattermost_webhook: str = None):
        self.games_file = games_file
        self.tracked_file = tracked_file
        self.mattermost_webhook = mattermost_webhook
        self.tracked_data = self._load_tracked_data()

    def _load_tracked_data(self) -> Dict:
        """Load previously tracked game data"""
        if os.path.exists(self.tracked_file):
            with open(self.tracked_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_tracked_data(self):
        """Save tracked game data"""
        with open(self.tracked_file, 'w') as f:
            json.dump(self.tracked_data, f, indent=2)

    def _parse_games_file(self) -> List[Tuple[str, str]]:
        """Parse games.txt and return list of (name, app_id) tuples"""
        games = []
        with open(self.games_file, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue

                parts = line.split(',')
                if len(parts) == 2:
                    name, app_id = parts[0].strip(), parts[1].strip()
                    games.append((name, app_id))
                else:
                    print(f"Warning: Invalid line format: {line}")

        return games

    def _get_latest_news(self, app_id: str) -> Dict:
        """Get the latest news item for a Steam game"""
        try:
            params = {
                'appid': app_id,
                'count': 1,  # Only get the latest news item
                'maxlength': 300,
                'format': 'json'
            }

            response = requests.get(self.STEAM_NEWS_API, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if 'appnews' in data and 'newsitems' in data['appnews']:
                newsitems = data['appnews']['newsitems']
                if newsitems:
                    return newsitems[0]

            return None

        except requests.exceptions.RequestException as e:
            print(f"Error fetching news for app {app_id}: {e}")
            return None

    def _send_mattermost_notification(self, game_name: str, app_id: str,
                                     news_title: str, news_date: str):
        """Send update notification to Mattermost"""
        if not self.mattermost_webhook:
            return

        try:
            message = {
                "text": f"### Steam Game Update Detected!\n\n"
                       f"**Game:** {game_name}\n"
                       f"**App ID:** {app_id}\n"
                       f"**Update:** {news_title}\n"
                       f"**Date:** {news_date}\n"
                       f"**Steam Store:** https://store.steampowered.com/app/{app_id}/"
            }

            response = requests.post(self.mattermost_webhook, json=message, timeout=10)
            response.raise_for_status()
            print(f"Mattermost notification sent for {game_name}")

        except requests.exceptions.RequestException as e:
            print(f"Error sending Mattermost notification: {e}")

    def check_updates(self) -> bool:
        """Check all games for updates. Returns True if any updates found."""
        games = self._parse_games_file()
        updates_found = False

        print(f"Checking {len(games)} games for updates...")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print("-" * 60)

        for game_name, app_id in games:
            print(f"\nChecking: {game_name} (App ID: {app_id})")

            # Get latest news
            latest_news = self._get_latest_news(app_id)

            if not latest_news:
                print(f"  No news data available")
                continue

            news_timestamp = latest_news.get('date', 0)
            news_title = latest_news.get('title', 'No title')
            news_date = datetime.fromtimestamp(news_timestamp).strftime('%Y-%m-%d %H:%M:%S')

            # Check if this is a new update
            if app_id in self.tracked_data:
                last_timestamp = self.tracked_data[app_id].get('last_news_date', 0)

                if news_timestamp > last_timestamp:
                    print(f"  UPDATE DETECTED!")
                    print(f"  Latest news: {news_title}")
                    print(f"  News date: {news_date}")
                    updates_found = True

                    # Send notification
                    self._send_mattermost_notification(game_name, app_id, news_title, news_date)
                else:
                    print(f"  No updates (last check: {self.tracked_data[app_id].get('last_checked', 'N/A')})")
            else:
                print(f"  First time tracking this game")
                print(f"  Latest news: {news_title}")
                print(f"  News date: {news_date}")

            # Update tracked data
            self.tracked_data[app_id] = {
                'name': game_name,
                'last_news_date': news_timestamp,
                'last_news_title': news_title,
                'last_checked': datetime.now().isoformat()
            }

            # Be nice to Steam's API - add a small delay between requests
            time.sleep(1)

        # Save updated tracking data
        self._save_tracked_data()
        print("\n" + "=" * 60)
        print(f"Check complete. Updates found: {updates_found}")

        return updates_found


def main():
    """Main entry point"""
    # Get Mattermost webhook from environment variable
    mattermost_webhook = os.environ.get('MATTERMOST_WEBHOOK_URL')

    if not mattermost_webhook:
        print("Warning: MATTERMOST_WEBHOOK_URL environment variable not set")
        print("Notifications will not be sent\n")

    # Create checker and run
    checker = SteamUpdateChecker(
        games_file='games.txt',
        tracked_file='tracked_games.json',
        mattermost_webhook=mattermost_webhook
    )

    updates_found = checker.check_updates()

    # Exit with code 1 if updates found (signals GitHub Actions to commit)
    sys.exit(1 if updates_found else 0)


if __name__ == '__main__':
    main()
