import os
import platform
from typing import Optional

from app.utils.decorators.singleton import singleton


@singleton
class PlatformManager:
    @property
    def is_windows(self) -> bool:
        return self.platform == "windows"

    @property
    def is_macos(self) -> bool:
        return self.platform == "darwin"

    @property
    def is_linux(self) -> bool:
        return self.platform == "linux"

    @property
    def is_unix(self) -> bool:
        return self.platform in ["linux", "darwin"]

    @property
    def platform(self) -> str:
        return platform.system().casefold()

    @property
    def machine(self) -> str:
        return platform.machine().casefold()

    @property
    def node(self) -> str:
        return platform.node().casefold()

    def get_chrome_executable_path(self) -> Optional[str]:
        match self.platform:
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


platform_mgr = PlatformManager()
