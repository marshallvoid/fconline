# FC Online Automation Tool

A Python-based automation tool for FC Online events featuring a modern GUI interface and intelligent browser automation with anti-detection capabilities.

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
cd fconline

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

#### GUI Application

```bash
# Recommended entry point
uv run python manage.py

# Alternative entry point
uv run python src/main.py
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
