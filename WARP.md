# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Common Commands

### Development Setup
```bash
# Install dependencies (recommended method)
uv sync

# Install development dependencies
uv sync --group dev

# Install Playwright browsers (required for automation)
uv run playwright install chromium

# Setup pre-commit hooks
uv run pre-commit install
```

### Running the Application
```bash
# Run GUI application (primary method)
uv run python manage.py

# Alternative entry point
uv run python src/main.py

# Run with development auto-reload
uv run python src/infrastructure/auto_reload.py
```

### Development Tools
```bash
# Code formatting
uv run black src/
uv run ruff format

# Linting
uv run ruff check src/
uv run flake8 src/

# Type checking
uv run mypy src/

# Import sorting
uv run isort src/

# Run all pre-commit hooks
uv run pre-commit run --all-files

# Run tests
uv run pytest
```

### Building
```bash
# Quick build (uses build scripts)
./build.sh        # Linux/macOS
build.bat         # Windows

# Manual build
uv sync
uv add pyinstaller
uv run pyinstaller build.spec

# Clean build artifacts
rm -rf build/ dist/ __pycache__/ src/__pycache__/ src/*/__pycache__/ src/*/*/__pycache__/
```

### Single Test Execution
```bash
# Run specific test file
uv run pytest tests/test_specific.py

# Run specific test function
uv run pytest tests/test_specific.py::test_function_name

# Run tests with coverage
uv run pytest --cov=src/
```

## Architecture Overview

### Core Components

**Main Application Flow:**
- `manage.py` / `src/main.py` → Entry points that initialize logging and launch GUI
- `src/gui/main_window.py` → Main Tkinter GUI with tabbed interface
- `src/core/main_tool.py` → Core automation engine using Playwright
- `src/infrastructure/client.py` → Custom browser client with anti-detection features

**Key Architecture Patterns:**

1. **Event-Driven Configuration**: The application supports multiple FC Online events ("Bi Lắc" and "Tỷ Phú") through a configurable system in `src/core/event_config.py` and `src/utils/contants.py`. Each event has different URLs, selectors, and spin actions.

2. **Browser Automation Stack**: Uses Playwright with a custom `PatchedContext` class that implements anti-detection measures, cookie management, and WebSocket monitoring for real-time jackpot tracking.

3. **Secure Credential Management**: `src/utils/credentials.py` implements Fernet encryption for storing user credentials, with platform-specific data directories and fallback mechanisms.

4. **GUI Architecture**: Modern Tkinter interface using `sv-ttk` theming with:
   - Tabbed interface for different events
   - Real-time status updates via callbacks
   - Activity logging component
   - Theme switching (Auto/Light/Dark)

### Data Flow

1. **User Authentication**: Credentials are encrypted and stored locally, then used for automated browser login
2. **WebSocket Monitoring**: Real-time jackpot values are tracked through WebSocket frame parsing in `_setup_websocket()`
3. **Auto-Spinning Logic**: Based on target thresholds, the tool automatically clicks spin buttons using configured CSS selectors
4. **Status Updates**: All activities flow through callback functions to update the GUI in real-time

### Project Structure Highlights

- **`src/core/`**: Core automation logic and event configuration
- **`src/gui/components/`**: Modular GUI components (event tabs, activity log)
- **`src/infrastructure/`**: Low-level browser client, logging setup, auto-reload for development
- **`src/utils/`**: Utilities for credentials, constants, and platform-specific operations
- **`src/schemas.py`**: Pydantic models for API data validation

### Development Considerations

**Browser Automation**: The tool uses a patched Playwright context with anti-detection scripts to avoid bot detection. The `PatchedContext` class handles proper cleanup of CDP connections and WebSocket listeners.

**Multi-Platform Support**: Platform detection in `src/utils/platforms.py` handles Chrome/Chromium discovery across Windows, macOS, and Linux with automatic browser path detection.

**Error Handling**: Comprehensive error handling with Loguru logging, fallback mechanisms for encryption failures, and graceful GUI error dialogs.

**Threading Model**: GUI runs on main thread while browser automation uses asyncio in separate threads, with callback-based communication for real-time updates.

## Code Quality Standards

- **Line Length**: 120 characters (configured in `.ruff.toml` and `pyproject.toml`)
- **Type Annotations**: Required for all functions and methods (enforced by mypy)
- **Import Style**: `isort` with multi-line mode 3, trailing commas
- **Code Style**: Black formatting with string normalization disabled
- **Linting**: Ruff with custom rule selection focusing on security and performance
- **Pre-commit**: Automated formatting, linting, and type checking on commits

## Environment Requirements

- **Python**: 3.12+ (specified in `pyproject.toml`)
- **Browser**: Chrome/Chromium required for Playwright automation
- **Platform**: Cross-platform support (Windows, macOS, Linux)
- **Dependencies**: Managed through `uv` with lock file (`uv.lock`)

## Build System

The project uses PyInstaller for creating standalone executables:
- **Spec File**: `build.spec` defines build configuration
- **Assets**: Icons and resources in `assets/` directory
- **Platform Scripts**: Separate build scripts for different platforms
- **Output**: Single executable with embedded Python runtime and dependencies
