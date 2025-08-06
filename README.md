# FC Online Automation Tool

<div align="center">
  <img src="assets/icon.ico" alt="FC Online Tool" width="64" height="64">

**An intelligent automation tool for FC Online jackpot management**

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GUI](https://img.shields.io/badge/Interface-GUI%20%7C%20CLI-orange.svg)](#usage)

</div>

## 📋 Overview

FC Online Automation Tool is a sophisticated Python application designed to automate jackpot monitoring and management for FC Online. The tool features both a modern GUI interface and CLI support, utilizing browser automation to interact with the FC Online platform intelligently.

### ✨ Key Features

-  🎯 **Smart Jackpot Monitoring** - Automated tracking of special jackpot targets
-  🖥️ **Dual Interface** - Modern GUI with dark/light theme support and CLI options
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

## 🚀 Usage

### GUI Mode (Recommended)

#### Using uv:

```bash
uv run python manage.py
```

#### Using pip:

```bash
python manage.py
# or
python src/main.py
```

#### GUI Features:

-  **Username/Password Fields** - Enter your FC Online credentials
-  **Target Special Jackpot** - Set your desired jackpot threshold
-  **Start/Stop Controls** - Begin or halt automation with one click
-  **Real-time Status** - Monitor current progress and system status
-  **Theme Support** - Automatic dark/light theme detection

### CLI Mode

For headless operation or server environments:

```bash
# Using uv
uv run python -c "
from src.tool import FCOnlineTool
import asyncio

async def main():
    tool = FCOnlineTool(
        username='your_username',
        password='your_password',
        target_special_jackpot=10000,
        headless=True
    )
    await tool.run()

asyncio.run(main())
"

# Using pip
python -c "
from src.tool import FCOnlineTool
import asyncio

async def main():
    tool = FCOnlineTool(
        username='your_username',
        password='your_password',
        target_special_jackpot=10000,
        headless=True
    )
    await tool.run()

asyncio.run(main())
"
```

## ⚙️ Configuration

### Environment Variables

You can configure the tool using environment variables:

```bash
export FC_USERNAME="your_username"
export FC_PASSWORD="your_password"
export FC_TARGET_JACKPOT="10000"
export FC_HEADLESS="true"  # For CLI mode
```

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
│   ├── gui.py               # GUI interface implementation
│   ├── tool.py              # Core automation logic
│   ├── client.py            # Browser client management
│   ├── types.py             # Data models and types
│   └── logger.py            # Logging configuration
├── manage.py                # Main application launcher
├── pyproject.toml           # Project configuration
└── README.md                # This file
```

## 🔧 Development

### Setting up development environment:

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

### Available development tools:

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

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.
