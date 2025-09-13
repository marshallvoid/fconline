# Environment Variables Setup Guide

This guide explains how to configure environment variables for both local development and GitHub Actions CI/CD.

## 🔧 Local Development Setup

### 1. Create Environment File

Copy the template and fill in your values:

```bash
cp .env.template .env
```

### 2. Configure Required Variables

Edit `.env` file with your values:

```bash
# Required for application to work
SECRET_KEY="your_32_character_secret_key_here"
DISCORD_DEVELOPER_WEBHOOK_ID="your_webhook_id"
DISCORD_DEVELOPER_WEBHOOK_TOKEN="your_webhook_token"
# ... (see .env.template for all variables)
```

### 3. Validate Configuration

Run the validation script to check your setup:

```bash
python scripts/validate-secrets.py
```

## 🚀 GitHub Actions Setup

### 1. Set Repository Secrets

You need to add secrets to your GitHub repository for CI/CD builds to work properly.

#### Method 1: Using GitHub CLI (Recommended)

1. First validate your local `.env` file:

   ```bash
   python scripts/validate-secrets.py
   ```

2. Generate GitHub CLI commands:

   ```bash
   python scripts/validate-secrets.py --generate-gh-commands
   ```

3. Copy and run the generated `gh secret set` commands

#### Method 2: Manual Setup via GitHub Web Interface

1. Go to your repository on GitHub
2. Navigate to: **Settings** → **Secrets and variables** → **Actions**
3. Click **"New repository secret"**
4. Add each of these secrets with values from your `.env` file:

| Secret Name                       | Description                                            | Default Value                |
| --------------------------------- | ------------------------------------------------------ | ---------------------------- |
| `SECRET_KEY`                      | Encryption key for securing application data           | **Required**                 |
| `DISCORD_DEVELOPER_WEBHOOK_ID`    | Discord webhook ID for developer notifications         | **Required**                 |
| `DISCORD_DEVELOPER_WEBHOOK_TOKEN` | Discord webhook token for developer notifications      | **Required**                 |
| `DISCORD_DEVELOPER_ROLE_ID`       | Discord role ID to mention for developer notifications | **Required**                 |
| `DISCORD_FCO_WEBHOOK_ID`          | Discord webhook ID for FCO notifications               | **Required**                 |
| `DISCORD_FCO_WEBHOOK_TOKEN`       | Discord webhook token for FCO notifications            | **Required**                 |
| `DISCORD_FCO_WEBHOOK_ROLE_ID`     | Discord role ID to mention for FCO notifications       | **Required**                 |
| `OPENAI_API_KEY`                  | _(Optional)_ OpenAI API key for AI features            | None                         |
| `OPENAI_MODEL`                    | _(Optional)_ OpenAI model to use                       | `"03"`                       |
| `OPENAI_TEMPERATURE`              | _(Optional)_ OpenAI temperature setting                | `"0.8"`                      |
| `OPENAI_MAX_RETRIES`              | _(Optional)_ OpenAI maximum retries                    | `"2"`                        |
| `ANTHROPIC_API_KEY`               | _(Optional)_ Anthropic API key for AI features         | None                         |
| `ANTHROPIC_MODEL`                 | _(Optional)_ Anthropic model to use                    | `"claude-sonnet-4-20250514"` |
| `ANTHROPIC_TEMPERATURE`           | _(Optional)_ Anthropic temperature setting             | `"0.8"`                      |
| `ANTHROPIC_MAX_RETRIES`           | _(Optional)_ Anthropic maximum retries                 | `"2"`                        |

### 2. Default Values & Fallbacks

The system automatically uses **default values** when optional secrets are not defined in GitHub:

-  **Required secrets**: Must be set, build will fail if missing
-  **Optional secrets with defaults**: Uses fallback values if not set
   -  Model configurations (OpenAI/Anthropic models, temperature, retries)
   -  Application will work with sensible defaults
-  **Optional secrets without defaults**: Features disabled if not set
   -  API keys (OpenAI, Anthropic) - AI features won't work without them

**Example**: If you don't set `OPENAI_MODEL` secret, it automatically uses `"03"` as default.

### 3. How It Works in CI/CD

The GitHub Actions workflow automatically:

1. **Sets environment variables** from GitHub Secrets
2. **Uses fallback defaults** for any missing optional configuration
3. **Creates `.env` file** during build using `setup-env.py` script
4. **Includes environment in build** so the executable has access to configuration
5. **Keeps secrets secure** - they never appear in logs or build artifacts

## 🔍 Validation & Troubleshooting

### Check Local Setup

```bash
# Validate all environment variables are set correctly
python scripts/validate-secrets.py

# Check what's missing and get setup commands
python scripts/validate-secrets.py --generate-gh-commands
```

### Common Issues

**❌ "Missing required environment variables"**

-  Make sure you've copied `.env.template` to `.env`
-  Fill in all required values in your `.env` file
-  Run the validation script to see what's missing

**❌ "GitHub Actions build fails"**

-  Check that all required secrets are set in GitHub repository settings
-  Verify secret names match exactly (case-sensitive)
-  Look at the Actions logs for specific error messages

**❌ "Application can't find configuration"**

-  For local development: ensure `.env` file exists in project root
-  For built executable: environment variables are embedded during build

## 🔒 Security Best Practices

✅ **DO:**

-  Keep `.env` file in `.gitignore` (already configured)
-  Use strong, unique values for `SECRET_KEY`
-  Rotate webhook tokens periodically
-  Use GitHub Secrets for CI/CD (never commit secrets to code)

❌ **DON'T:**

-  Commit `.env` file to git
-  Share secrets in chat/email
-  Use the same `SECRET_KEY` across different environments
-  Put secrets directly in GitHub Actions YAML files

## 📚 Additional Resources

-  [GitHub Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
-  [GitHub CLI Secrets Commands](https://cli.github.com/manual/gh_secret)
-  [Discord Webhook Setup Guide](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks)
