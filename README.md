# FC Online Automation Tool

<div align="center">
  <img src="assets/icon.ico" alt="FC Online Tool" width="64" height="64">

**An intelligent automation tool for FC Online jackpot management**

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](LICENSE)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GUI](https://img.shields.io/badge/Interface-GUI-orange.svg)](#usage)

</div>

## 📋 Overview

FC Online Automation Tool is a Python application that automates jackpot monitoring and management for FC Online via a modern desktop GUI. It uses browser automation to interact with the platform and provides real‑time insights.

### ✨ Key Features

-  🎯 **Smart Jackpot Monitoring** - Automated tracking of special jackpot targets
-  🖥️ **Modern GUI** - Dark/Light theme, header with theme toggle, improved spacing
-  🤖 **Browser Automation** - Powered by Playwright and browser-use for reliable web interactions
-  🔐 **Secure Authentication** - Safe login management with credential protection
-  📊 **Real-time Status Updates** - Live monitoring of spin activities and jackpot progress
-  🎨 **Modern UI** - Clean, professional interface with sv-ttk theming
-  🔄 **Auto-detection** - Smart Chrome/Chromium browser detection across platforms

## 🛠️ Technology Stack

-  **Python 3.12+** - Core application framework
-  **Tkinter + sv-ttk** - Modern GUI with theme support
-  **Playwright** - Browser automation engine
-  **browser-use** - Enhanced browser interaction library

## 📦 Installation

### Prerequisites

-  Python 3.12 or higher
-  Google Chrome or Chromium browser
-  Internet connection

### Method 1: Using uv (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd fc-online

# Install dependencies using uv
uv sync

# Install Playwright browsers
uv run playwright install chromium
```

### Method 2: Using pip

```bash
# Clone the repository
git clone <repository-url>
cd fc-online

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Install Playwright browsers
playwright install chromium
```

## 🚀 Usage (GUI)

### Using uv

```bash
uv run python manage.py
```

### Using pip

```bash
python manage.py
# or
python src/main.py
```

### GUI Highlights

-  Username/Password fields
-  Target Special Jackpot and Spin Action
-  Start/Stop controls
-  Live user info with current special jackpot
-  Activity Log with tabs (All/Info/Events/Targets/Errors)
-  Theme toggle: Auto/Light/Dark

## 🔨 Building

### Quick Build

```bash
./build.sh
```

### Manual Build

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies
uv sync

# Add PyInstaller
uv add pyinstaller

# Build executable
uv run pyinstaller build.spec

# Output will be in: dist/FC_Online_Tool.exe
```

## ⚙️ Configuration

### Browser Configuration

The tool automatically detects Chrome/Chromium installations across platforms:

-  **Windows**: Program Files, Local AppData
-  **macOS**: Applications folder
-  **Linux**: Standard system paths

## 📁 Project Structure

```
fc-online/
├── src/
│   ├── __init__.py          # Package initialization
│   ├── main.py              # Application entry point
│   ├── gui/                 # GUI components package
│   │   ├── __init__.py      # Package initialization
│   │   ├── main_window.py   # Main window application
│   │   ├── base_component.py # Base component class
│   │   ├── control_panel.py # Control panel component
│   │   ├── user_settings_panel.py # User settings component
│   │   ├── user_info_panel.py # User info display component
│   │   ├── log_panel.py     # Log display component
│   ├── core/                 # Core automation components
│   │   ├── __init__.py      # Package initialization
│   │   ├── fc_automation.py # Main FC automation tool
│   │   ├── browser_manager.py # Browser management
│   │   ├── login_handler.py # Login handling
│   │   ├── websocket_monitor.py # WebSocket monitoring
│   │   ├── auto_spin.py     # Auto-spin handling
│   │   └── user_info_manager.py # User info management
│   ├── models.py            # Data models and types
│   └── infrastructure/      # Logging, browser client, utilities
├── manage.py                # Main application launcher
├── pyproject.toml           # Project configuration
└── README.md                # This file
```

## 🔧 Development

### Setting up development environment

```bash
# Clone and setup
git clone <repository-url>
cd fc-online
uv sync --group dev

# Install pre-commit hooks
uv run pre-commit install

# Run tests
uv run pytest

# Code formatting
uv run black src/
uv run isort src/

# Type checking
uv run mypy src/
```

### Available development tools

-  **Black** - Code formatting
-  **isort** - Import sorting
-  **Flake8** - Linting
-  **MyPy** - Type checking
-  **Pytest** - Testing framework
-  **Pre-commit** - Git hooks

## 🐛 Troubleshooting

### Common Issues

1. **Browser not found**

   ```bash
   # Install Playwright browsers
   uv run playwright install chromium
   ```

2. **Import errors**

   ```bash
   # Ensure all dependencies are installed
   uv sync
   ```

3. **GUI theme issues**

   -  The application automatically detects system theme
   -  Ensure `darkdetect` package is properly installed

4. **Login failures**
   -  Verify credentials are correct
   -  Check internet connection
   -  Ensure FC Online website is accessible

### Logs

Application logs are automatically generated with detailed information:

-  Error tracking and debugging
-  Performance monitoring
-  User action logging
