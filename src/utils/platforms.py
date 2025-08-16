import os
import platform
import shutil
import subprocess
import tempfile
import time
from typing import Optional

import shortuuid
from loguru import logger


class PlatformManager:
    @classmethod
    def platform(cls) -> str:
        return platform.system().lower()

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
        return cls.platform() in ["linux", "darwin"]

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

        return next((p for p in chrome_paths if os.path.exists(p)), None)

    @classmethod
    def get_user_data_directory(cls) -> str:
        # Generate a unique directory name with timestamp and UUID
        timestamp, unique_id = int(time.time()), shortuuid.uuid()
        dir_name = f"fconline-automation-{timestamp}-{unique_id}"

        user_data_dir = os.path.join(tempfile.gettempdir(), dir_name)  # default: macos and linux

        if cls.is_windows():  # Windows
            # Use TEMP directory on Windows
            temp_dir = os.environ.get("TEMP", os.environ.get("TMP", tempfile.gettempdir()))
            user_data_dir = os.path.join(temp_dir, dir_name)

        # Create directory if it doesn't exist
        try:
            os.makedirs(user_data_dir, exist_ok=True)
            logger.info(f"📁 Created user data directory: {user_data_dir}")

        except Exception as e:
            logger.warning(f"⚠️ Failed to create user data directory: {e}")
            # Fallback to system temporary directory with different name
            fallback_dir = os.path.join(tempfile.gettempdir(), f"fconline-automation-fallback-{unique_id}")
            try:
                os.makedirs(fallback_dir, exist_ok=True)
                logger.info(f"📁 Fallback user data directory: {fallback_dir}")
                user_data_dir = fallback_dir

            except Exception as fallback_error:
                logger.error(f"❌ Failed to create fallback directory: {fallback_error}")
                # Last resort: use system temp directory directly
                user_data_dir = tempfile.gettempdir()

        return user_data_dir

    @classmethod
    def cleanup_user_data_directory(cls, user_data_dir: Optional[str] = None) -> None:
        if not user_data_dir or not os.path.exists(user_data_dir):
            return

        try:
            shutil.rmtree(user_data_dir, ignore_errors=True)
            logger.info(f"🧹 Cleaned up user data directory: {user_data_dir}")

        except Exception as e:
            logger.warning(f"⚠️ Failed to cleanup user data directory: {e}")

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
            logger.warning(f"🔍 Default browser not detected, falling back to {fallback_browser.title()}")
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

        if default_browser_path:
            logger.info(f"🌐 Using default browser: {default_browser_path}")

        return default_browser_path

    @classmethod
    def _detect_windows_default_browser(cls) -> Optional[str]:
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
            logger.warning("🔍 Failed to detect default browser on Windows")

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
            logger.warning("🔍 Failed to detect default browser on macOS")

        return None

    @classmethod
    def _detect_linux_default_browser(cls) -> Optional[str]:
        try:
            result = subprocess.run(["xdg-settings", "get", "default-web-browser"], capture_output=True, text=True)
            if result.returncode != 0:
                return None

            if "chrome" in result.stdout.strip().lower():
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

            if "firefox" in result.stdout.strip().lower():
                return shutil.which("firefox")

        except Exception:
            logger.warning("🔍 Failed to detect default browser on Linux")

        return None
