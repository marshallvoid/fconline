#!/usr/bin/env python3
# ruff: noqa: T201
"""
Script to create .env file from GitHub Actions environment variables.
This script is used during CI/CD to securely pass environment variables to the build process.
"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_TEMPLATE_FILE = ROOT / ".env.template"
ENV_FILE = ROOT / ".env"


def parse_example() -> dict[str, str]:
    """Read .env.template and return dict of keys -> default values."""
    env_vars: dict[str, str] = {}
    for line in ENV_TEMPLATE_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if "=" not in line:
            continue

        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        env_vars[key] = value

    return env_vars


def create_env_file() -> None:
    if not ENV_TEMPLATE_FILE.exists():
        msg = f"Missing {ENV_TEMPLATE_FILE}"
        raise FileNotFoundError(msg)

    example_vars = parse_example()

    final_vars: dict[str, str] = {}
    for key, default in example_vars.items():
        # Prefer GitHub Actions env, fallback to .env.example default
        value = os.getenv(key, default)
        final_vars[key] = value

    with ENV_FILE.open("w", encoding="utf-8") as f:
        for key, value in final_vars.items():
            if value:
                safe = value.replace('"', '\\"')
                f.write(f'{key}="{safe}"\n')
            else:
                f.write(f"# {key}=\n")

    print(f"✅ Created {ENV_FILE.absolute()}")
    print(f"📋 Environment variables configured: {sum(bool(v) for v in final_vars.values())}/{len(final_vars)}")


if __name__ == "__main__":
    create_env_file()
    exit(0)
