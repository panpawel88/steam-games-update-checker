#!/usr/bin/env python3
"""
Steam Games Update Checker
Monitors Steam games for updates by tracking depot manifest IDs using SteamCMD
"""

import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import requests

from steam_build_tracker import SteamCMDTracker


class SteamUpdateChecker:
    """Checks Steam games for updates and sends notifications"""

    def __init__(self, games_file: str = "games.txt",
                 tracked_file: str = "tracked_games.json",
                 mattermost_webhook: str = None,
                 steamcmd_path: str = None):
        self.games_file = games_file
        self.tracked_file = tracked_file
        self.mattermost_webhook = mattermost_webhook
        self.tracked_data = self._load_tracked_data()
        self.build_tracker = SteamCMDTracker(steamcmd_path)

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

    def _send_mattermost_notification(self, game_name: str, app_id: str,
                                     old_version: str, new_version: str,
                                     update_time: str):
        """Send update notification to Mattermost"""
        if not self.mattermost_webhook:
            return

        try:
            message = {
                "text": f"### Steam Game Build Update Detected!\n\n"
                       f"**Game:** {game_name}\n"
                       f"**App ID:** {app_id}\n"
                       f"**Old Version:** `{old_version}`\n"
                       f"**New Version:** `{new_version}`\n"
                       f"**Detected:** {update_time}\n"
                       f"**Steam Store:** https://store.steampowered.com/app/{app_id}/\n"
                       f"**SteamDB:** https://steamdb.info/app/{app_id}/patchnotes/"
            }

            response = requests.post(self.mattermost_webhook, json=message, timeout=10)
            response.raise_for_status()
            print(f"  Mattermost notification sent for {game_name}")

        except requests.exceptions.RequestException as e:
            print(f"  Error sending Mattermost notification: {e}")

    def check_updates(self) -> bool:
        """Check all games for updates. Returns True if any updates found."""
        games = self._parse_games_file()
        updates_found = False

        print(f"Checking {len(games)} games for updates using SteamCMD...")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Note: This may take a while (~30 seconds per game)")
        print("-" * 60)

        for game_name, app_id in games:
            print(f"\nChecking: {game_name} (App ID: {app_id})")

            # Get current build info from SteamCMD
            build_info = self.build_tracker.get_build_info(app_id)

            if not build_info:
                print(f"  Unable to retrieve build info")
                print(f"  (This may be a DLC, unavailable app, or SteamCMD error)")
                continue

            # Prefer build_id, fallback to primary_manifest
            current_version = build_info.get('build_id') or build_info.get('primary_manifest')
            update_time = build_info['checked_at']

            if not current_version:
                print(f"  No version information available")
                continue

            # Check if this is a new update
            if app_id in self.tracked_data:
                # Support both old 'manifest_id' and new 'version' field names
                last_version = self.tracked_data[app_id].get('version') or self.tracked_data[app_id].get('manifest_id', '')

                if current_version != last_version and last_version:
                    print(f"  BUILD UPDATE DETECTED!")
                    print(f"    Old version: {last_version}")
                    print(f"    New version: {current_version}")
                    updates_found = True

                    # Send notification
                    self._send_mattermost_notification(
                        game_name, app_id, last_version, current_version, update_time
                    )
                elif current_version == last_version:
                    print(f"  No updates")
                    print(f"    Current version: {current_version}")
                    print(f"    Last checked: {self.tracked_data[app_id].get('last_checked', 'N/A')}")
                else:
                    # First time tracking (last_version is empty)
                    print(f"  First time tracking this game")
                    print(f"    Current version: {current_version}")
            else:
                print(f"  First time tracking this game")
                print(f"    Current version: {current_version}")
                if build_info.get('manifest_ids'):
                    print(f"    Total depots: {len(build_info['manifest_ids'])}")

            # Update tracked data
            self.tracked_data[app_id] = {
                'name': game_name,
                'version': current_version,  # Renamed from manifest_id to version
                'build_id': build_info.get('build_id'),
                'primary_manifest': build_info.get('primary_manifest'),
                'all_manifests': build_info.get('manifest_ids', []),
                'depot_count': len(build_info.get('manifest_ids', [])),
                'last_checked': datetime.now().isoformat()
            }

            # Small delay between games to avoid overwhelming Steam
            time.sleep(2)

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
