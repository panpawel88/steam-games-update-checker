#!/usr/bin/env python3
"""
Steam Build Tracker using SteamCMD
Tracks actual game builds by monitoring depot manifest IDs
"""

import subprocess
import re
import platform
from typing import Optional, Dict, List
from datetime import datetime


class SteamCMDTracker:
    """Track Steam game builds using SteamCMD"""

    def __init__(self, steamcmd_path: str = None):
        """
        Initialize SteamCMD tracker

        Args:
            steamcmd_path: Path to steamcmd executable. If None, assumes it's in PATH
        """
        if steamcmd_path:
            self.steamcmd_path = steamcmd_path
        else:
            # Default paths based on platform
            system = platform.system()
            if system == "Linux":
                self.steamcmd_path = "steamcmd"
            elif system == "Windows":
                self.steamcmd_path = "steamcmd.exe"
            elif system == "Darwin":  # macOS
                self.steamcmd_path = "steamcmd.sh"
            else:
                self.steamcmd_path = "steamcmd"

    def _execute_steamcmd(self, app_id: str, timeout: int = 60) -> Optional[str]:
        """
        Execute SteamCMD to get app info

        Args:
            app_id: Steam App ID
            timeout: Command timeout in seconds

        Returns:
            SteamCMD output or None if error
        """
        try:
            cmd = [
                self.steamcmd_path,
                '+login', 'anonymous',
                '+app_info_print', app_id,
                '+quit'
            ]

            print(f"  Executing SteamCMD for app {app_id}...")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode != 0:
                print(f"  SteamCMD returned error code: {result.returncode}")
                if result.stderr:
                    print(f"  Error output: {result.stderr[:200]}")
                return None

            return result.stdout

        except subprocess.TimeoutExpired:
            print(f"  SteamCMD timed out after {timeout} seconds")
            return None
        except FileNotFoundError:
            print(f"  SteamCMD not found at: {self.steamcmd_path}")
            print("  Please install SteamCMD first")
            return None
        except Exception as e:
            print(f"  Error executing SteamCMD: {e}")
            return None

    def _parse_vdf_manifest_ids(self, vdf_output: str) -> List[str]:
        """
        Parse VDF output to extract depot manifest IDs

        VDF format example:
        "depots"
        {
            "441"  // Windows depot
            {
                "manifests"
                {
                    "public"    "7234567890123456789"
                }
            }
        }

        Args:
            vdf_output: Raw SteamCMD output

        Returns:
            List of manifest IDs found
        """
        manifest_ids = []

        # Pattern to match manifest IDs in VDF format
        # Matches: "public"    "1234567890"
        pattern = r'"public"\s+"(\d+)"'

        matches = re.findall(pattern, vdf_output)

        if matches:
            # Remove duplicates while preserving order
            seen = set()
            for manifest_id in matches:
                if manifest_id not in seen:
                    manifest_ids.append(manifest_id)
                    seen.add(manifest_id)

        return manifest_ids

    def _parse_vdf_depot_info(self, vdf_output: str) -> Dict[str, str]:
        """
        Parse VDF output to extract depot IDs and their manifest IDs

        Returns:
            Dict mapping depot_id -> manifest_id
        """
        depot_manifests = {}

        # More sophisticated parsing to match depot -> manifest
        # Pattern: depot number followed by its public manifest
        depot_section_pattern = r'"(\d+)"\s*{[^}]*?"manifests"\s*{[^}]*?"public"\s+"(\d+)"'

        matches = re.findall(depot_section_pattern, vdf_output, re.DOTALL)

        for depot_id, manifest_id in matches:
            depot_manifests[depot_id] = manifest_id

        return depot_manifests

    def get_build_info(self, app_id: str) -> Optional[Dict]:
        """
        Get build information for a Steam app

        Args:
            app_id: Steam App ID

        Returns:
            Dict with build info or None if error:
            {
                'app_id': '440',
                'manifest_ids': ['123456789', '987654321'],
                'depot_manifests': {'441': '123456789', '442': '987654321'},
                'primary_manifest': '123456789',  # First depot's manifest
                'checked_at': '2025-10-29T12:00:00'
            }
        """
        output = self._execute_steamcmd(app_id)

        if not output:
            return None

        # Parse manifest IDs
        manifest_ids = self._parse_vdf_manifest_ids(output)
        depot_manifests = self._parse_vdf_depot_info(output)

        if not manifest_ids:
            print(f"  No manifest IDs found for app {app_id}")
            print(f"  This may be a DLC, tool, or unavailable app")
            return None

        build_info = {
            'app_id': app_id,
            'manifest_ids': manifest_ids,
            'depot_manifests': depot_manifests,
            'primary_manifest': manifest_ids[0],  # Use first manifest as primary
            'checked_at': datetime.now().isoformat()
        }

        print(f"  Found {len(manifest_ids)} depot manifest(s)")
        print(f"  Primary manifest ID: {build_info['primary_manifest']}")

        return build_info

    def has_build_changed(self, app_id: str, last_manifest: str) -> tuple[bool, Optional[Dict]]:
        """
        Check if build has changed since last known manifest

        Args:
            app_id: Steam App ID
            last_manifest: Previously tracked manifest ID

        Returns:
            Tuple of (changed: bool, build_info: Dict or None)
        """
        build_info = self.get_build_info(app_id)

        if not build_info:
            return False, None

        current_manifest = build_info['primary_manifest']

        # Compare primary manifest
        changed = current_manifest != last_manifest

        if changed:
            print(f"  Build changed!")
            print(f"    Old manifest: {last_manifest}")
            print(f"    New manifest: {current_manifest}")

        return changed, build_info


def test_tracker():
    """Test the tracker with a known game"""
    print("Testing SteamCMD Tracker...")
    print("-" * 60)

    tracker = SteamCMDTracker()

    # Test with Team Fortress 2 (App ID 440)
    test_app_id = "440"
    print(f"\nTesting with Team Fortress 2 (App ID: {test_app_id})")

    build_info = tracker.get_build_info(test_app_id)

    if build_info:
        print("\nSuccess! Build info retrieved:")
        print(f"  App ID: {build_info['app_id']}")
        print(f"  Primary Manifest: {build_info['primary_manifest']}")
        print(f"  Total Depots: {len(build_info['manifest_ids'])}")
        print(f"  Checked At: {build_info['checked_at']}")

        if build_info['depot_manifests']:
            print("\n  Depot Details:")
            for depot_id, manifest_id in build_info['depot_manifests'].items():
                print(f"    Depot {depot_id}: {manifest_id}")
    else:
        print("\nFailed to retrieve build info")
        print("Make sure SteamCMD is installed and accessible")


if __name__ == '__main__':
    test_tracker()
