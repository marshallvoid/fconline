import os
import platform
import shutil
import subprocess
from typing import Optional

from loguru import logger


class PlatformManager:
    @classmethod
    def platform(cls) -> str:
        return platform.system().casefold()

    @classmethod
    def is_windows(cls) -> bool:
        return cls.platform() == "windows"

    @classmethod
    def is_macos(cls) -> bool:
        return cls.platform() == "darwin"

    @classmethod
    def is_linux(cls) -> bool:
        return cls.platform() == "linux"

    @classmethod
    def is_unix(cls) -> bool:
        return cls.is_linux() or cls.is_macos()

    @classmethod
    def node(cls) -> str:
        return platform.node()

    @classmethod
    def machine(cls) -> str:
        return platform.machine()

    @classmethod
    def get_chrome_executable_path(cls) -> Optional[str]:
        match cls.platform():
            case "windows":
                # Common Chrome installation paths on Windows
                chrome_paths = [
                    os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
                    os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
                    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                ]

            case "darwin":  # macOS
                # Common Chrome installation paths on macOS
                chrome_paths = [
                    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                    "/Applications/Chromium.app/Contents/MacOS/Chromium",
                    os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
                ]

            case "linux":
                # Common Chrome installation paths on Linux
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

        # Return first existing Chrome path found
        return next((p for p in chrome_paths if os.path.exists(p)), None)

    @classmethod
    def get_default_browser_path(cls, fallback_browser: str = "chrome") -> Optional[str]:
        match cls.platform():
            case "darwin":
                default_browser_path = cls._detect_macos_default_browser()
            case "windows":
                default_browser_path = cls._detect_windows_default_browser()
            case "linux":
                default_browser_path = cls._detect_linux_default_browser()
            case _:
                default_browser_path = None

        # If default browser detection failed or browser not found, fallback to Chrome
        if not default_browser_path or not os.path.exists(default_browser_path):
            logger.warning(f"Default browser not detected, falling back to {fallback_browser.title()}")
            match fallback_browser:
                case "chrome":
                    default_browser_path = cls.get_chrome_executable_path()
                case "firefox":
                    default_browser_path = shutil.which("firefox")
                case "edge":
                    default_browser_path = shutil.which("msedge")
                case "brave":
                    default_browser_path = shutil.which("brave")
                case _:
                    default_browser_path = None

        return default_browser_path

    @classmethod
    def _detect_windows_default_browser(cls) -> Optional[str]:
        try:
            import winreg

            registry_path = r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_path) as key:  # type: ignore[attr-defined]
                prog_id = winreg.QueryValueEx(key, "Progid")[0]  # type: ignore[attr-defined]

                if "chrome" in prog_id.casefold():
                    chrome_paths = [
                        os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
                        os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
                        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
                    ]
                    for path in chrome_paths:
                        if os.path.exists(path):
                            return path

                if "firefox" in prog_id.casefold():
                    return shutil.which("firefox")

                if "edge" in prog_id.casefold():
                    return shutil.which("msedge")

        except (ImportError, Exception):
            logger.error("Failed to detect default browser on Windows")

        return None

    @classmethod
    def _detect_macos_default_browser(cls) -> Optional[str]:
        try:
            result = subprocess.run(
                ["defaults", "read", "com.apple.LaunchServices/com.apple.launchservices.secure", "LSHandlers"],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                return None

            if "com.google.chrome" in result.stdout.strip():
                return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

            if "com.apple.safari" in result.stdout.strip():
                return "/Applications/Safari.app/Contents/MacOS/Safari"

            if "org.mozilla.firefox" in result.stdout.strip():
                return "/Applications/Firefox.app/Contents/MacOS/firefox"

            if "com.microsoft.edgemac" in result.stdout.strip():
                return "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"

        except Exception:
            logger.error("Failed to detect default browser on macOS")

        return None

    @classmethod
    def _detect_linux_default_browser(cls) -> Optional[str]:
        try:
            result = subprocess.run(["xdg-settings", "get", "default-web-browser"], capture_output=True, text=True)
            if result.returncode != 0:
                return None

            if "chrome" in result.stdout.strip().casefold():
                return next(
                    (
                        path
                        for path in [
                            "/usr/bin/google-chrome",
                            "/usr/bin/google-chrome-stable",
                            "/usr/bin/chromium",
                            "/usr/bin/chromium-browser",
                            "/snap/bin/chromium",
                        ]
                        if os.path.exists(path)
                    ),
                    None,
                )

            if "firefox" in result.stdout.strip().casefold():
                return shutil.which("firefox")

        except Exception:
            logger.error("Failed to detect default browser on Linux")

        return None
