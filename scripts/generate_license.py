#!/usr/bin/env python3
# ruff: noqa: T201
"""
Script to generate license keys for FC Online application.
"""

import secrets
import sys
from datetime import datetime
from pathlib import Path


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


def save_licenses_to_file(licenses: list[str], filename: str = "storage/licenses.txt") -> Path:
    filepath = Path(filename)

    # Create parent directory if it doesn't exist
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Append to file (create if doesn't exist)
    with filepath.open("a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for license_key in licenses:
            f.write(f"{timestamp} - {license_key}\n")

    return filepath


def main():
    print("🔑 FC Online License Generator")
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

    filepath = save_licenses_to_file(licenses)
    print(f"\n✅ Licenses saved to: {filepath}")

    print("=" * 50)


if __name__ == "__main__":
    main()
