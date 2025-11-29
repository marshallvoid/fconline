#!/usr/bin/env python3
# ruff: noqa: T201
"""
Script to generate license keys for FC Online application.
"""

import json
import os
import secrets
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def generate_license_key() -> str:
    segments = []
    for _ in range(4):
        # Generate 4 random uppercase alphanumeric characters
        segment = "".join(secrets.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(4))
        segments.append(segment)

    return f"FCOL-{'-'.join(segments)}"


def generate_multiple_licenses(count: int) -> list[str]:
    licenses = set()
    while len(licenses) < count:
        licenses.add(generate_license_key())
    return sorted(licenses)


def save_licenses_to_file(licenses: list[str], filename: str = ".licenses") -> Path:
    filepath = Path(filename)

    # Create parent directory if it doesn't exist
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Append to file (create if doesn't exist)
    with filepath.open("a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for license_key in licenses:
            f.write(f"{timestamp} - {license_key}\n")

    return filepath


def upload_to_gist(licenses: list[str]) -> tuple[int, int]:
    # Return: Tuple: (added_count, skipped_count)

    github_token = os.getenv("GITHUB_TOKEN")
    gist_id = os.getenv("GIST_ID")
    gist_filename = os.getenv("GIST_FILENAME")

    if not github_token:
        print("❌ GITHUB_TOKEN not found in .env file")
        return 0, 0

    if not gist_id:
        print("❌ GIST_ID not found in .env file")
        return 0, 0

    if not gist_filename:
        print("❌ GIST_FILENAME not found in .env file")

    print(f"\n� Fetching current Gist data (ID: {gist_id})...")

    # Fetch current Gist content
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        response = requests.get(f"https://api.github.com/gists/{gist_id}", headers=headers, timeout=10)
        response.raise_for_status()

        gist_data = response.json()
        file_content = gist_data["files"][gist_filename]["content"]
        config = json.loads(file_content)

        # Get current valid licenses
        current_licenses = set(config.get("app_configs", {}).get("valid_licenses", []))
        print(f"📊 Current valid licenses: {len(current_licenses)}")

        # Check for duplicates and add new licenses
        added = []
        skipped = []

        for license_key in licenses:
            if license_key in current_licenses:
                skipped.append(license_key)
                print(f"⚠️  Skipped (already exists): {license_key}")
            else:
                current_licenses.add(license_key)
                added.append(license_key)
                print(f"✅ Added: {license_key}")

        if not added:
            print("\n⚠️  No new licenses to upload (all already exist)")
            return 0, len(skipped)

        # Update config with new licenses
        config["app_configs"]["valid_licenses"] = sorted(current_licenses)

        # Update Gist
        print(f"\n🔄 Uploading {len(added)} new license(s) to Gist...")

        update_payload = {"files": {gist_filename: {"content": json.dumps(config, indent=3, ensure_ascii=False)}}}

        response = requests.patch(
            f"https://api.github.com/gists/{gist_id}",
            headers=headers,
            json=update_payload,
            timeout=10,
        )
        response.raise_for_status()

        print("✅ Successfully uploaded to Gist!")
        print(f"📊 Total valid licenses: {len(current_licenses)}")

        return len(added), len(skipped)

    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to update Gist: {e}")
        return 0, 0
    except (KeyError, json.JSONDecodeError) as e:
        print(f"❌ Failed to parse Gist data: {e}")
        return 0, 0


def main():
    print("�🔑 FC Online License Generator")
    print("=" * 50)

    # Get number of licenses to generate
    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
        except ValueError:
            print("❌ Invalid number. Usage: python generate_license.py [count]")
            sys.exit(1)
    else:
        try:
            count = int(input("\nHow many licenses to generate? [1]: ") or "1")
        except ValueError:
            print("❌ Invalid number")
            sys.exit(1)

    if count < 1:
        print("❌ Count must be at least 1")
        sys.exit(1)

    if count > 1000:
        print("⚠️  Generating more than 1000 licenses. This may take a while...")

    # Generate licenses
    print(f"\n🔄 Generating {count} license(s)...")
    licenses = generate_multiple_licenses(count)

    # Display licenses
    print(f"\n✅ Generated {len(licenses)} license(s):\n")
    for i, license_key in enumerate(licenses, 1):
        print(f"  {i}. {license_key}")

    # Save to local file
    filepath = save_licenses_to_file(licenses)
    print(f"\n✅ Licenses saved to: {filepath}")

    # Ask to upload to Gist
    upload = input("\n📤 Upload to GitHub Gist? [y/N]: ").lower().strip()

    if upload == "y":
        added, skipped = upload_to_gist(licenses)
        if added > 0 or skipped > 0:
            print("\n📊 Summary:")
            print(f"  ✅ Added: {added}")
            print(f"  ⚠️  Skipped: {skipped}")

    print("=" * 50)


if __name__ == "__main__":
    main()
