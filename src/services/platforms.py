import os
import platform
from typing import Optional


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
                # Common Chrome installation paths on Windows
                chrome_paths = [
                    os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
                    os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
                    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                    # Additional fallback paths for Windows
                    os.path.expandvars(r"%PROGRAMFILES%\Chromium\Application\chrome.exe"),
                    os.path.expandvars(r"%PROGRAMFILES(X86)%\Chromium\Application\chrome.exe"),
                    os.path.expandvars(r"%LOCALAPPDATA%\Chromium\Application\chrome.exe"),
                    # Microsoft Edge as fallback
                    os.path.expandvars(r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe"),
                    os.path.expandvars(r"%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe"),
                    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
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
