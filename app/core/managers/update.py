import os
import platform
import shutil
import ssl
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Callable, Optional, Tuple

import aiohttp
import certifi
from loguru import logger
from packaging import version

from app.core.managers.version import version_manager
from app.core.settings import settings


class UpdateManager:
    """Manages application updates from GitHub releases."""

    GITHUB_API_URL = settings.release_url
    DOWNLOAD_TIMEOUT = 300  # 5 minutes

    def __init__(self) -> None:
        # self._current_version = app.__version__

        self._current_version = version_manager.version
        self._latest_version: Optional[str] = None
        self._download_url: Optional[str] = None

        # Create SSL context with certifi certificates
        self._ssl_context = ssl.create_default_context(cafile=certifi.where())

    @property
    def current_version(self) -> str:
        """Get current application version."""
        return self._current_version

    @property
    def latest_version(self) -> Optional[str]:
        """Get latest available version."""
        return self._latest_version

    async def check_for_updates(self) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Check if a new version is available.

        Returns:
            Tuple of (has_update, latest_version, release_notes)
        """
        try:
            connector = aiohttp.TCPConnector(ssl=self._ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(self.GITHUB_API_URL, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if not response.ok:
                        logger.error(f"Failed to check for updates: {response.status}")
                        return False, None, None

                    data = await response.json()

                    # Extract version from tag (e.g., "v1.0.0" -> "1.0.0")
                    tag_name = data.get("tag_name", "").lstrip("v")
                    release_notes = data.get("body", "")

                    if not tag_name:
                        logger.warning("No tag name found in release data")
                        return False, None, None

                    self._latest_version = tag_name

                    # Compare versions
                    current = version.parse(self._current_version)
                    latest = version.parse(tag_name)

                    if latest > current:
                        # Find appropriate asset for current platform
                        self._download_url = self._get_download_url(data.get("assets", []))
                        if self._download_url:
                            logger.info(f"New version available: {tag_name} (current: {self._current_version})")
                            return True, tag_name, release_notes

                    logger.info(f"Already on latest version: {self._current_version}")
                    return False, tag_name, None

        except Exception as error:
            logger.exception(f"Error checking for updates: {error}")
            return False, None, None

    def _get_download_url(self, assets: list) -> Optional[str]:
        """Get download URL for current platform."""
        system = platform.system().lower()
        machine = platform.machine().lower()

        # Define platform-specific patterns
        patterns = {
            "windows": ["windows", "win", ".exe", ".zip"],
            "darwin": ["macos", "darwin", "osx", ".dmg", ".zip"],
            "linux": ["linux", ".tar.gz", ".zip"],
        }

        # Get patterns for current platform
        platform_patterns = patterns.get(system, [])

        # Find matching asset
        for asset in assets:
            asset_name = asset.get("name", "").lower()
            browser_download_url = asset.get("browser_download_url")

            if not browser_download_url:
                continue

            # Check if asset matches platform
            if any(pattern in asset_name for pattern in platform_patterns):
                # Additional architecture check for linux/macos
                if system in ["darwin", "linux"]:
                    # Check for arm64/aarch64 vs x86_64
                    if "arm64" in machine or "aarch64" in machine:
                        if "arm64" in asset_name or "aarch64" in asset_name:
                            return browser_download_url
                    elif "x86_64" in asset_name or "amd64" in asset_name:
                        return browser_download_url
                    elif "arm64" not in asset_name and "aarch64" not in asset_name:
                        # Generic asset without architecture specification
                        return browser_download_url
                else:
                    return browser_download_url

        logger.warning(f"No suitable asset found for {system} {machine}")
        return None

    async def download_update(self, progress_callback: Optional[Callable[[int, int], None]] = None) -> Optional[Path]:
        """
        Download the update file.

        Args:
            progress_callback: Optional callback for progress updates (current, total)

        Returns:
            Path to downloaded file or None if failed
        """
        if not self._download_url:
            logger.error("No download URL available")
            return None

        try:
            # Create temp directory for download
            temp_dir = Path.home() / ".fconline_updates"
            temp_dir.mkdir(exist_ok=True)

            # Extract filename from URL
            filename = self._download_url.split("/")[-1]
            download_path = temp_dir / filename

            logger.info(f"Downloading update from: {self._download_url}")

            connector = aiohttp.TCPConnector(ssl=self._ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(
                    self._download_url, timeout=aiohttp.ClientTimeout(total=self.DOWNLOAD_TIMEOUT)
                ) as response:
                    if not response.ok:
                        logger.error(f"Failed to download update: {response.status}")
                        return None

                    total_size = int(response.headers.get("content-length", 0))
                    downloaded_size = 0

                    with open(download_path, "wb") as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                            downloaded_size += len(chunk)

                            if progress_callback and total_size > 0:
                                progress_callback(downloaded_size, total_size)

            logger.success(f"Update downloaded to: {download_path}")
            return download_path

        except Exception as error:
            logger.exception(f"Error downloading update: {error}")
            return None

    def install_update(self, download_path: Path) -> bool:
        """
        Install the downloaded update and restart the application.

        Args:
            download_path: Path to downloaded update file

        Returns:
            True if installation initiated successfully
        """
        try:
            system = platform.system().lower()

            if system == "windows":
                return self._install_windows(download_path)
            elif system == "darwin":
                return self._install_macos(download_path)
            elif system == "linux":
                return self._install_linux(download_path)
            else:
                logger.error(f"Unsupported platform: {system}")
                return False

        except Exception as error:
            logger.exception(f"Error installing update: {error}")
            return False

    def _install_windows(self, download_path: Path) -> bool:
        """Install update on Windows."""
        try:
            if download_path.suffix == ".exe":
                # Run installer
                subprocess.Popen([str(download_path), "/SILENT"])
            elif download_path.suffix == ".zip":
                # Extract and replace
                extract_dir = download_path.parent / "extract"
                extract_dir.mkdir(exist_ok=True)

                with zipfile.ZipFile(download_path, "r") as zip_ref:
                    zip_ref.extractall(extract_dir)

                # Create batch script to replace files after exit
                batch_script = download_path.parent / "update.bat"
                current_exe = Path(sys.executable)

                with open(batch_script, "w") as f:
                    f.write("@echo off\n")
                    f.write("timeout /t 2 /nobreak > nul\n")
                    f.write(f'xcopy /s /y "{extract_dir}\\*" "{current_exe.parent}\\"\n')
                    f.write(f'start "" "{current_exe}"\n')
                    f.write('del "%~f0"\n')

                # Run batch script and exit
                subprocess.Popen([str(batch_script)], shell=True)

            sys.exit(0)
            return True

        except Exception as error:
            logger.exception(f"Error installing Windows update: {error}")
            return False

    def _install_macos(self, download_path: Path) -> bool:
        """Install update on macOS."""
        try:
            if download_path.suffix == ".dmg":
                # Mount DMG and copy app
                subprocess.run(["open", str(download_path)])
                logger.info("Please drag the app to Applications folder and restart")
            elif download_path.suffix == ".zip":
                # Extract and replace
                extract_dir = download_path.parent / "extract"
                extract_dir.mkdir(exist_ok=True)

                with zipfile.ZipFile(download_path, "r") as zip_ref:
                    zip_ref.extractall(extract_dir)

                # Find .app bundle
                app_bundle = next(extract_dir.glob("*.app"), None)
                if app_bundle:
                    # Get current app location
                    current_app = Path(sys.executable).parent.parent.parent

                    # Replace app (requires restart)
                    shutil.rmtree(current_app)
                    shutil.copytree(app_bundle, current_app)

                    # Restart
                    subprocess.Popen([str(current_app / "Contents" / "MacOS" / current_app.stem)])
                    sys.exit(0)

            return True

        except Exception as error:
            logger.exception(f"Error installing macOS update: {error}")
            return False

    def _install_linux(self, download_path: Path) -> bool:
        """Install update on Linux."""
        try:
            # Extract archive
            extract_dir = download_path.parent / "extract"
            extract_dir.mkdir(exist_ok=True)

            if download_path.suffix == ".zip":
                with zipfile.ZipFile(download_path, "r") as zip_ref:
                    zip_ref.extractall(extract_dir)
            else:
                # tar.gz
                import tarfile

                with tarfile.open(download_path, "r:gz") as tar:
                    tar.extractall(extract_dir)

            # Replace current executable
            current_exe = Path(sys.executable)
            new_exe = next(extract_dir.glob("**/fconline*"), None)

            if new_exe and new_exe.is_file():
                # Make backup
                backup = current_exe.with_suffix(".bak")
                shutil.copy2(current_exe, backup)

                # Replace
                shutil.copy2(new_exe, current_exe)
                os.chmod(current_exe, 0o755)

                # Restart
                subprocess.Popen([str(current_exe)])
                sys.exit(0)

            return True

        except Exception as error:
            logger.exception(f"Error installing Linux update: {error}")
            return False


# Singleton instance
update_mgr = UpdateManager()
