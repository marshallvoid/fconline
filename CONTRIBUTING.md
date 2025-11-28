# Conventional Commits Guide

This project uses [Conventional Commits](https://www.conventionalcommits.org/) for automatic changelog generation.

## Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

-  **feat**: A new feature (appears in changelog as ✨ Features)
-  **fix**: A bug fix (appears as 🐛 Bug Fixes)
-  **perf**: Performance improvement (appears as ⚡ Performance)
-  **refactor**: Code refactoring (appears as ♻️ Refactor)
-  **style**: Code style changes (appears as 💄 Styling)
-  **test**: Adding/updating tests (appears as 🧪 Testing)
-  **docs**: Documentation changes (appears as 📚 Documentation)
-  **build**: Build system changes (appears as 🏗️ Build)
-  **ci**: CI/CD changes (appears as 👷 CI/CD)
-  **chore**: Other changes (appears as 🔧 Miscellaneous)

### Examples

#### Feature

```
feat(auth): add Discord OAuth login

Implemented Discord OAuth2 authentication flow with role-based access control.
```

#### Bug Fix

```
fix(webhook): handle rate limiting properly

Added exponential backoff when Discord API returns 429 status code.
```

#### Breaking Change

```
feat(api)!: change settings structure to nested config

BREAKING CHANGE: Discord settings now use nested structure instead of flat fields.
Migration guide: Update discord_webhook_id to discord.webhooks.main.id
```

#### Performance

```
perf(cache): implement Redis caching for API responses

Reduced API response time by 60% through Redis caching layer.
```

## Scope (Optional)

Scope indicates which part of the codebase is affected:

-  `auth` - Authentication
-  `webhook` - Discord webhooks
-  `ui` - User interface
-  `api` - API client
-  `build` - Build process
-  `ci` - CI/CD pipeline

## Breaking Changes

For breaking changes, add `!` after the type or add `BREAKING CHANGE:` in the footer:

```
feat!: redesign settings API

BREAKING CHANGE: Settings API now requires authentication token
```

## Benefits

✅ **Auto-generated changelog** - Changelog is automatically created from commits
✅ **Semantic versioning** - Version bumps based on commit types
✅ **Better collaboration** - Clear commit history for team members
✅ **Release notes** - Professional release notes without manual work
