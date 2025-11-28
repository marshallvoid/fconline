#!/usr/bin/env python3
# ruff: noqa: T201
"""
Script to validate GitHub Actions secrets are properly configured.
Run this locally to check if all required secrets are set up.
"""

import sys
from pathlib import Path
from typing import Any, Dict

from app.core.settings import Settings

# Add project root to python path to allow importing app
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))


ENV_FILE = ROOT / ".env"


def get_settings_fields() -> Dict[str, Any]:
    """Get all fields from Settings model."""
    return Settings.model_fields


def validate_local_env() -> bool:
    """Validate local .env file has required variables."""
    if not ENV_FILE.exists():
        print("❌ No .env file found. Please copy .env.template to .env and configure it.")
        return False

    # Load .env file
    env_vars = {}
    with ENV_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                # Remove quotes if present
                value = value.strip("\"'")
                env_vars[key] = value

    print("🔍 Validating local .env file...")

    fields = get_settings_fields()
    missing_required = []

    # Track nested configs to handle them specially
    nested_configs = ["discord"]

    for name, field in fields.items():
        # Skip nested configs for now
        if name in nested_configs:
            continue

        env_key = name.upper()
        is_required = field.is_required()

        if env_key not in env_vars or not env_vars[env_key]:
            if is_required:
                missing_required.append(f"  {env_key}")
        else:
            print(f"✅ {env_key}")

    if missing_required:
        print("\n❌ Missing required environment variables:")
        print("\n".join(missing_required))
        return False

    print("\n🎉 All required environment variables are configured!")
    return True


def generate_github_secrets_json() -> None:
    """Generate JSON template for GitHub CLI to set secrets."""
    if not ENV_FILE.exists():
        print("❌ No .env file found. Please copy .env.template to .env and configure it.")
        return

    # Load .env file
    secrets = {}
    with ENV_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                # Remove quotes if present
                value = value.strip("\"'")
                if value:  # Only include non-empty values
                    secrets[key] = value

    # Generate GitHub CLI commands
    print("\n🔧 GitHub CLI commands to set secrets:")
    print("Run these commands to set up GitHub Actions secrets:\n")

    fields = get_settings_fields()
    known_keys = set()
    for name in fields:
        known_keys.add(name.upper())

    for key, value in secrets.items():
        # Only suggest setting secrets that are known settings or start with DISCORD (nested)
        if key in known_keys or key.startswith("DISCORD__"):
            print(f'gh secret set {key} --body "{value}"')

    print("\nOr set them manually in GitHub:")
    print("1. Go to your repository on GitHub")
    print("2. Settings → Secrets and variables → Actions")
    print("3. Click 'New repository secret'")
    print("4. Add each secret with the values from your .env file")


def main():
    """Main function to run validation and provide setup instructions."""
    print("🔐 GitHub Actions Environment Variables Setup")
    print("=" * 50)

    if len(sys.argv) > 1 and sys.argv[1] == "--generate-gh-commands":
        generate_github_secrets_json()
        return

    success = validate_local_env()

    if success:
        print("\n📚 Next steps:")
        print("1. Set up GitHub Actions secrets with:")
        print("   python scripts/validate-secrets.py --generate-gh-commands")
        print("2. Push your changes to trigger the build")
        print("3. Check the Actions tab for build status")
    else:
        print("\n📚 Next steps:")
        print("1. Set the missing environment variables in your .env file")
        print("2. Run this script again to validate")


if __name__ == "__main__":
    main()
