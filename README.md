# FC Online Automation Tool

A Python-based automation tool for FC Online events featuring a modern GUI interface and intelligent browser automation with anti-detection capabilities.

## 🏗️ Architecture

### Core Components

```
├── src/
│   ├── main.py              # Main application entry point
│   ├── manage.py            # Alternative entry point (recommended)
│   ├── core/
│   │   ├── main_tool.py     # Core automation engine
│   │   ├── event_config.py  # Event configuration system
│   │   ├── login_handler.py # Login automation and form handling
│   │   └── websocket_handler.py # WebSocket monitoring and auto-spin logic
│   ├── gui/
│   │   ├── main_window.py   # Main GUI application
│   │   └── components/      # Modular GUI components
│   │       ├── event_tab.py # Event-specific configuration tabs
│   │       └── activity_log_tab.py # Real-time activity logging
│   ├── infrastructure/
│   │   ├── logger.py        # Logging configuration with Loguru
│   │   └── auto_reload.py   # Development auto-reload functionality
│   ├── utils/
│   │   ├── credentials.py   # Secure credential management
│   │   ├── contants.py      # Event configurations and constants
│   │   └── platforms.py     # Cross-platform browser detection
│   └── schemas.py           # Pydantic data models
├── build.spec              # PyInstaller build configuration
├── build.sh / build.bat    # Build scripts for different platforms
├── pyproject.toml          # Project configuration and dependencies
```

## 🚀 Quick Start

### Prerequisites

-  **Python 3.12+** (required)
-  **Chrome/Chromium browser** (for browser automation)
-  **uv** package manager (recommended) or pip

### Installation

#### Using uv (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd fc-online

# Install dependencies
uv sync

# Install development dependencies (optional)
uv sync --group dev

# Install Playwright browsers (required)
uv run playwright install chromium

# Setup pre-commit hooks (optional)
uv run pre-commit install
```

#### Using pip

```bash
# Clone the repository
git clone <repository-url>
cd fc-online

# Install dependencies
pip install -e .

# Install Playwright browsers (required)
playwright install chromium
```

### Running the Application

#### GUI Application (Primary Method)

```bash
# Recommended entry point
uv run python manage.py

# Alternative entry point
uv run python src/main.py

# Development with auto-reload
uv run python src/infrastructure/auto_reload.py
```

#### CLI Application

The CLI application provides a command-line interface for automated FC Online jackpot monitoring and spinning. It's ideal for headless servers, automation scripts, or when you prefer command-line tools over the GUI.

**CLI Options:**

| Option                     | Type    | Required | Default       | Description                                                      |
| -------------------------- | ------- | -------- | ------------- | ---------------------------------------------------------------- |
| `--base-url`               | string  | Yes      | -             | FC Online event URL (e.g., https://typhu.fconline.garena.vn)     |
| `--username, -u`           | string  | No       | -             | Account username (can be omitted to read from ENV FC_USERNAME)   |
| `--password, -p`           | string  | No       | -             | Account password (can be omitted to read from ENV FC_PASSWORD)   |
| `--spin-action`            | integer | No       | 1             | Spin type (default: 1)                                           |
| `--target-special-jackpot` | integer | No       | 10000         | Special Jackpot threshold to stop auto (default: 10000)          |
| `--user-endpoint`          | string  | No       | api/user/get  | User info endpoint (default: api/user/get)                       |
| `--spin-endpoint`          | string  | No       | api/user/spin | Spin endpoint (default: api/user/spin)                           |
| `--duration`               | integer | No       | -             | Run for N seconds then exit (default: run until Ctrl+C)          |
| `--log-level`              | string  | No       | INFO          | Log level: TRACE, DEBUG, INFO, SUCCESS, WARNING, ERROR, CRITICAL |

**Examples:**

1. **Basic monitoring with default settings:**

```bash
uv run fconline \
  --base-url https://typhu.fconline.garena.vn \
  --username player123 \
  --password mypass123 \
  --spin-action 1 \
  --target-special-jackpot 15000
```

2. **Custom endpoints with duration limit:**

```bash
uv run fconline \
  --base-url https://typhu.fconline.garena.vn \
  --username player123 \
  --password mypass123 \
  --spin-action 2 \
  --target-special-jackpot 8000 \
  --duration 3600 \
  --log-level DEBUG
```

3. **Environment variables with minimal logging:**

```bash
# Set environment variables
export FC_USERNAME=player123
export FC_PASSWORD=mypass123

# Run without username/password arguments
uv run fconline \
  --base-url https://typhu.fconline.garena.vn \
  --spin-action 1 \
  --target-special-jackpot 20000 \
  --log-level WARNING
```

4. **Interactive credential input:**

```bash
# Run without username/password arguments or environment variables
# The tool will prompt you to enter them interactively
uv run fconline \
  --base-url https://typhu.fconline.garena.vn \
  --spin-action 1 \
  --target-special-jackpot 15000

# You'll see prompts like:
# Username:
# Password: (hidden input)
```

## ⚙️ Configuration

### Event Configuration

All event configurations are defined in `src/utils/contants.py` and can be customized for different events or updated selectors.

## 🔧 Development

### Development Setup

```bash
# Install all development dependencies
uv sync --group dev

# Install pre-commit hooks
uv run pre-commit install

# Run with auto-reload during development
uv run python src/infrastructure/auto_reload.py
```

### Code Quality Tools

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
```

## 📦 Building

### Quick Build

```bash
# Linux/macOS
./build.sh

# Windows
build.bat
```

### Manual Build

```bash
# Install build dependencies
uv sync --group build

# Create executable
uv run pyinstaller build.spec

# Clean build artifacts (optional)
rm -rf build/ dist/ __pycache__/ src/__pycache__/ src/*/__pycache__/ src/*/*/__pycache__/
```

The build process creates a standalone executable with embedded Python runtime and all dependencies.

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**

   ```bash
   # Ensure all dependencies are installed
   uv sync
   uv run playwright install chromium
   ```

2. **Browser Not Found**

   -  Install Chrome or Chromium browser
   -  The tool automatically detects browser installation paths

3. **Login Issues**

   -  Verify your FC Online credentials
   -  Check if captcha verification is required (tool will wait automatically)
   -  Ensure stable internet connection

4. **Build Issues**
   ```bash
   # Clean and rebuild
   rm -rf build/ dist/
   uv run pyinstaller build.spec
   ```

### Logging

-  Application logs are managed by Loguru with rotating file handlers
-  Error logs are saved to `app_error.log` for debugging
-  Activity logs are displayed in real-time within the GUI

## 📄 License

This project is intended for educational and personal use only. Please ensure compliance with FC Online's terms of service and use responsibly.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Install development dependencies (`uv sync --group dev`)
4. Make your changes following the code standards
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📞 Support

For issues, questions, or contributions, please:

1. Check the troubleshooting section above
2. Review existing issues in the repository
3. Create a new issue with detailed information about your problem

---

**⚠️ Disclaimer**: This tool is for educational purposes only. Users are responsible for ensuring compliance with FC Online's terms of service and applicable laws.
