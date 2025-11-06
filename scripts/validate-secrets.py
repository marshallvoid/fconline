#!/usr/bin/env python3
# ruff: noqa: T201
"""
Script to validate GitHub Actions secrets are properly configured.
Run this locally to check if all required secrets are set up.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"

# Required secrets for the application
REQUIRED_SECRETS = {
    "SECRET_KEY": "Encryption key for securing application data",
    "DISCORD_WEBHOOK_ID": "Discord webhook ID for notifications",
    "DISCORD_WEBHOOK_TOKEN": "Discord webhook token for notifications",
    "DISCORD_ROLE_ID": "Discord role ID to mention for notifications",
}

# Optional secrets (application will work without these but with limited features)
OPTIONAL_SECRETS = {
    "OPENAI_API_KEY": "OpenAI API key for AI features",
    "OPENAI_MODEL": "OpenAI model to use (default: 03)",
    "OPENAI_TEMPERATURE": "OpenAI temperature setting (default: 0.8)",
    "OPENAI_MAX_RETRIES": "OpenAI maximum retries (default: 2)",
    "ANTHROPIC_API_KEY": "Anthropic API key for AI features",
    "ANTHROPIC_MODEL": "Anthropic model to use (default: claude-sonnet-4-20250514)",
    "ANTHROPIC_TEMPERATURE": "Anthropic temperature setting (default: 0.8)",
    "ANTHROPIC_MAX_RETRIES": "Anthropic maximum retries (default: 2)",
}


def validate_local_env() -> bool:
    """Validate local .env file has required variables."""
    if not ENV_FILE.exists():
        print("❌ No .env file found. Use scripts/setup-env.py to create one.")
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

    # Check required secrets
    missing_required = []
    for secret, description in REQUIRED_SECRETS.items():
        if secret not in env_vars or not env_vars[secret]:
            missing_required.append(f"  {secret}: {description}")
        else:
            print(f"✅ {secret}")

    # Check optional secrets
    missing_optional = []
    for secret, description in OPTIONAL_SECRETS.items():
        if secret not in env_vars or not env_vars[secret]:
            missing_optional.append(f"  {secret}: {description}")
        else:
            print(f"✅ {secret}")

    if missing_required:
        print("\n❌ Missing required environment variables:")
        print("\n".join(missing_required))

    if missing_optional:
        print("\n⚠️  Missing optional environment variables (features will be limited):")
        print("\n".join(missing_optional))

    if not missing_required:
        print("\n🎉 All required environment variables are configured!")
        return True

    return False


def generate_github_secrets_json() -> None:
    """Generate JSON template for GitHub CLI to set secrets."""
    if not ENV_FILE.exists():
        print("❌ No .env file found. Use scripts/setup-env.py to create one.")
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

    for key, value in secrets.items():
        if key in {**REQUIRED_SECRETS, **OPTIONAL_SECRETS}:
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
        print("   python scripts/setup-env.py")
        print("2. Run this script again to validate")


if __name__ == "__main__":
    main()
