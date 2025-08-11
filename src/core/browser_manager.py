import platform as sys_platform
from typing import Optional, Tuple

from browser_use import BrowserConfig, BrowserContextConfig
from playwright.async_api import Page

from src.infrastructure import BrowserClient, PatchedContext
from src.utils.platforms import PlatformManager


class BrowserManager:
    """Manages browser setup, context, and page creation."""

    def __init__(self, headless: bool = False, user_data_dir: str = "") -> None:
        """
        Initialize the browser manager.

        Args:
            headless: Run browser in headless mode
            user_data_dir: User data directory path
        """
        self.headless = headless
        self.user_data_dir = user_data_dir
        self._context: Optional[PatchedContext] = None
        self._page: Optional[Page] = None

    async def setup_browser(self) -> Tuple[PatchedContext, Page]:
        """
        Setup browser context and page with Chrome configuration.

        Returns:
            Tuple of (browser_context, page)

        Raises:
            Exception: For browser setup errors
        """
        extra_chromium_args = self._get_chromium_args()

        # Choose browser based on user preference
        browser_path = PlatformManager.get_chrome_executable_path()

        browser = BrowserClient(
            config=BrowserConfig(
                headless=self.headless,
                extra_chromium_args=extra_chromium_args,
                chrome_instance_path=browser_path,
            )
        )

        context_config = BrowserContextConfig(browser_window_size={"width": 1920, "height": 1080})
        browser_context = await browser.new_context(config=context_config)
        page = await browser_context.get_current_page()

        self._context = browser_context
        self._page = page

        return browser_context, page

    def _get_chromium_args(self) -> list[str]:
        """Get platform-specific Chromium arguments."""
        extra_chromium_args = [
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--disable-background-timer-throttling",
            "--disable-popup-blocking",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-window-activation",
            "--disable-focus-on-load",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-dev-shm-usage",
            "--hide-scrollbars",
            "--mute-audio",
            "--start-maximized",
            f"--user-data-dir={self.user_data_dir}",
        ]

        # Add Windows-specific arguments
        system = sys_platform.platform().lower()
        if "windows" in system:
            extra_chromium_args.extend(
                [
                    "--disable-gpu-sandbox",
                    "--disable-software-rasterizer",
                    "--disable-background-networking",
                    "--disable-default-apps",
                    "--disable-extensions",
                    "--disable-sync",
                    "--disable-translate",
                    "--hide-crash-restore-bubble",
                    "--no-service-autorun",
                    "--password-store=basic",
                    "--use-mock-keychain",
                ]
            )

        if self.headless:
            extra_chromium_args.append("--headless")

        return extra_chromium_args

    async def close_browser(self) -> None:
        """
        Close browser context and cleanup resources.

        Raises:
            Exception: For browser cleanup errors
        """
        if not self._context:
            return

        try:
            await self._context.reset_context()
            await self._context.close()
        except Exception as e:
            msg = f"Failed to clean up browser resource: {e}"
            raise Exception(msg)
        finally:
            self._context = None
            self._page = None

    @property
    def context(self) -> Optional[PatchedContext]:
        """Get current browser context."""
        return self._context

    @property
    def page(self) -> Optional[Page]:
        """Get current browser page."""
        return self._page
