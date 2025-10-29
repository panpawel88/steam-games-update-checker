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

    def __init__(self, steamcmd_path: str = None, debug: bool = False):
        """
        Initialize SteamCMD tracker

        Args:
            steamcmd_path: Path to steamcmd executable. If None, assumes it's in PATH
            debug: If True, save raw SteamCMD output to debug files
        """
        self.debug = debug

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
                encoding='utf-8',
                errors='replace',  # Replace invalid characters instead of crashing
                timeout=timeout
            )

            if result.returncode != 0:
                print(f"  SteamCMD returned error code: {result.returncode}")
                if result.stderr:
                    print(f"  Error output: {result.stderr[:200]}")
                return None

            # Save debug output if enabled
            if self.debug and result.stdout:
                debug_filename = f"steamcmd_debug_{app_id}.txt"
                try:
                    with open(debug_filename, 'w', encoding='utf-8') as f:
                        f.write(result.stdout)
                    print(f"  Debug output saved to: {debug_filename}")
                except Exception as e:
                    print(f"  Warning: Could not save debug output: {e}")

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
                    "public"
                    {
                        "gid"    "7234567890123456789"
                    }
                }
            }
        }

        Args:
            vdf_output: Raw SteamCMD output

        Returns:
            List of manifest GID values found
        """
        manifest_ids = []

        # Pattern to match manifest GIDs in nested VDF format
        # Matches: "public" { ... "gid" "1234567890" ... }
        pattern = r'"public"\s*\{\s*"gid"\s+"(\d+)"'

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
        Parse VDF output to extract depot IDs and their manifest GIDs

        Returns:
            Dict mapping depot_id -> manifest_gid
        """
        depot_manifests = {}

        # Pattern to match depot -> manifests -> public -> gid
        # Matches: "441" { ... "manifests" { ... "public" { "gid" "123456" } } }
        depot_section_pattern = r'"(\d+)"\s*\{[^}]*?"manifests"\s*\{[^}]*?"public"\s*\{\s*"gid"\s+"(\d+)"'

        matches = re.findall(depot_section_pattern, vdf_output, re.DOTALL)

        for depot_id, manifest_id in matches:
            depot_manifests[depot_id] = manifest_id

        return depot_manifests

    def _parse_vdf_build_id(self, vdf_output: str) -> Optional[str]:
        """
        Parse VDF output to extract the public branch build ID

        This is simpler and more reliable than tracking individual depot manifests.

        VDF format example:
        "branches"
        {
            "public"
            {
                "buildid"       "20565005"
                "timeupdated"   "1761608349"
            }
        }

        Args:
            vdf_output: Raw SteamCMD output

        Returns:
            Build ID string or None if not found
        """
        # Pattern to match build ID in branches section
        # Matches: "branches" { ... "public" { "buildid" "12345" } }
        pattern = r'"branches"\s*\{[^}]*?"public"\s*\{[^}]*?"buildid"\s+"(\d+)"'

        match = re.search(pattern, vdf_output, re.DOTALL)

        if match:
            return match.group(1)

        return None

    def get_build_info(self, app_id: str) -> Optional[Dict]:
        """
        Get build information for a Steam app

        Args:
            app_id: Steam App ID

        Returns:
            Dict with build info or None if error:
            {
                'app_id': '440',
                'build_id': '20565005',  # Primary version identifier
                'manifest_ids': ['123456789', '987654321'],
                'depot_manifests': {'441': '123456789', '442': '987654321'},
                'primary_manifest': '123456789',  # First depot's manifest (fallback)
                'checked_at': '2025-10-29T12:00:00'
            }
        """
        output = self._execute_steamcmd(app_id)

        if not output:
            return None

        # Parse build ID (primary version identifier)
        build_id = self._parse_vdf_build_id(output)

        # Parse manifest IDs (fallback/additional info)
        manifest_ids = self._parse_vdf_manifest_ids(output)
        depot_manifests = self._parse_vdf_depot_info(output)

        # Check if we have any version information
        if not build_id and not manifest_ids:
            print(f"  No build ID or manifest IDs found for app {app_id}")
            print(f"  This may be a DLC, tool, or unavailable app")
            return None

        build_info = {
            'app_id': app_id,
            'build_id': build_id,
            'manifest_ids': manifest_ids,
            'depot_manifests': depot_manifests,
            'primary_manifest': manifest_ids[0] if manifest_ids else None,
            'checked_at': datetime.now().isoformat()
        }

        # Print what we found
        if build_id:
            print(f"  Found build ID: {build_id}")
        if manifest_ids:
            print(f"  Found {len(manifest_ids)} depot manifest(s)")

        return build_info

    def has_build_changed(self, app_id: str, last_version: str) -> tuple[bool, Optional[Dict]]:
        """
        Check if build has changed since last known version

        Args:
            app_id: Steam App ID
            last_version: Previously tracked build ID or manifest ID

        Returns:
            Tuple of (changed: bool, build_info: Dict or None)
        """
        build_info = self.get_build_info(app_id)

        if not build_info:
            return False, None

        # Prefer build_id, fallback to primary_manifest
        current_version = build_info.get('build_id') or build_info.get('primary_manifest')

        if not current_version:
            return False, None

        # Compare versions
        changed = current_version != last_version

        if changed:
            print(f"  Build changed!")
            print(f"    Old version: {last_version}")
            print(f"    New version: {current_version}")

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
        if build_info.get('build_id'):
            print(f"  Build ID: {build_info['build_id']}")
        if build_info.get('primary_manifest'):
            print(f"  Primary Manifest: {build_info['primary_manifest']}")
        if build_info.get('manifest_ids'):
            print(f"  Total Depots: {len(build_info['manifest_ids'])}")
        print(f"  Checked At: {build_info['checked_at']}")

        if build_info.get('depot_manifests'):
            print("\n  Depot Details:")
            for depot_id, manifest_id in build_info['depot_manifests'].items():
                print(f"    Depot {depot_id}: {manifest_id}")
    else:
        print("\nFailed to retrieve build info")
        print("Make sure SteamCMD is installed and accessible")


if __name__ == '__main__':
    test_tracker()
