import os
import platform
import shutil
import subprocess
from typing import Optional

from loguru import logger


def detect_macos_default_browser() -> Optional[str]:
    """Detect default browser on macOS"""
    try:
        result = subprocess.run(
            ["defaults", "read", "com.apple.LaunchServices/com.apple.launchservices.secure", "LSHandlers"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return None

        output = result.stdout
        if "com.google.chrome" in output:
            return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

        if "com.apple.safari" in output:
            return "/Applications/Safari.app/Contents/MacOS/Safari"

        if "org.mozilla.firefox" in output:
            return "/Applications/Firefox.app/Contents/MacOS/firefox"

        if "com.microsoft.edgemac" in output:
            return "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"

    except Exception:
        pass

    return None


def detect_windows_default_browser() -> Optional[str]:
    """Detect default browser on Windows"""
    try:
        import winreg

        registry_path = r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_path) as key:  # type: ignore[attr-defined]
            prog_id = winreg.QueryValueEx(key, "Progid")[0]  # type: ignore[attr-defined]

            if "chrome" in prog_id.lower():
                chrome_paths = [
                    os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
                    os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
                    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
                ]
                for path in chrome_paths:
                    if os.path.exists(path):
                        return path

            if "firefox" in prog_id.lower():
                return shutil.which("firefox")

            if "edge" in prog_id.lower():
                return shutil.which("msedge")

    except (ImportError, Exception):
        pass

    return None


def detect_linux_default_browser() -> Optional[str]:
    """Detect default browser on Linux"""
    try:
        result = subprocess.run(["xdg-settings", "get", "default-web-browser"], capture_output=True, text=True)
        if result.returncode != 0:
            return None

        browser_desktop = result.stdout.strip()

        if "chrome" in browser_desktop.lower():
            chrome_paths = [
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
                "/usr/bin/chromium",
                "/usr/bin/chromium-browser",
                "/snap/bin/chromium",
            ]
            for path in chrome_paths:
                if os.path.exists(path):
                    return path

        if "firefox" in browser_desktop.lower():
            return shutil.which("firefox")

    except Exception:
        pass

    return None


def get_default_browser_executable_path() -> Optional[str]:
    """Automatically detect default browser path across different operating systems"""
    system = platform.system().lower()

    logger.info(f"🌐 Detecting default browser for {system}")

    default_browser_path = None

    match system:
        case "darwin":
            default_browser_path = detect_macos_default_browser()
        case "windows":
            default_browser_path = detect_windows_default_browser()
        case "linux":
            default_browser_path = detect_linux_default_browser()

    # If default browser detection failed or browser not found, fallback to Chrome
    if not default_browser_path or not os.path.exists(default_browser_path):
        logger.info("🔍 Default browser not detected or not supported, falling back to Chrome")
        return get_chrome_executable_path()

    logger.info(f"🌐 Using default browser: {default_browser_path}")
    return default_browser_path


def get_chrome_executable_path() -> Optional[str]:
    """Automatically detect Chrome path across different operating systems"""
    system = platform.system().lower()

    match system:
        case "windows":
            chrome_paths = [
                os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            ]
        case "darwin":  # macOS
            chrome_paths = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
                os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            ]
        case "linux":
            chrome_paths = [
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
                "/usr/bin/chromium",
                "/usr/bin/chromium-browser",
                "/snap/bin/chromium",
                "/usr/local/bin/chrome",
                "/opt/google/chrome/chrome",
            ]
        case _:
            chrome_paths = []

    # Check each path
    for path in chrome_paths:
        if os.path.exists(path):
            logger.info(f"🌐 Found Chrome at: {path}")
            return path

    logger.warning("🌐 Chrome not found, will use default Chrome channel")
    return None
