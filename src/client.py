import json
import os

from browser_use import Browser, BrowserContextConfig
from browser_use.browser.context import BrowserContext
from browser_use.utils import time_execution_async
from loguru import logger
from playwright.async_api import Browser as PlaywrightBrowser
from playwright.async_api import BrowserContext as PlaywrightBrowserContext


class PatchedContext(BrowserContext):
    @time_execution_async("--close")
    async def close(self):  # noqa: C901
        """Close the browser instance"""
        logger.debug("Closing browser context")

        try:
            if self.session is None:
                return

            # Then remove CDP protocol listeners
            if self._page_event_handler and self.session.context:
                try:
                    # This actually sends a CDP command to unsubscribe
                    self.session.context.remove_listener("page", self._page_event_handler)
                except Exception as e:
                    logger.debug(f"Failed to remove CDP listener: {e}")
                self._page_event_handler = None

            # await self.save_cookies()

            if self.config.trace_path:
                try:
                    await self.session.context.tracing.stop(
                        path=os.path.join(self.config.trace_path, f"{self.context_id}.zip")
                    )
                except Exception as e:
                    logger.debug(f"Failed to stop tracing: {e}")

            # This is crucial - it closes the CDP connection
            if not self.config._force_keep_context_alive:  # noqa: SLF001
                try:
                    await self.session.context.close()
                except Exception as e:
                    logger.debug(f"Failed to close context: {e}")

        finally:
            # Dereference everything
            self.session = None
            self._page_event_handler = None

    async def _create_context(self, browser: PlaywrightBrowser) -> PlaywrightBrowserContext:
        """Creates a new browser context with anti-detection measures and loads cookies if available."""
        if self.browser.config.cdp_url and len(browser.contexts) > 0:
            context = browser.contexts[0]

        elif self.browser.config.chrome_instance_path and len(browser.contexts) > 0:
            # Connect to existing Chrome instance instead of creating new one
            context = browser.contexts[0]

        else:
            # Original code for creating new context
            context = await browser.new_context(
                viewport=self.config.browser_window_size,
                no_viewport=False,
                user_agent=self.config.user_agent,
                java_script_enabled=True,
                bypass_csp=self.config.disable_security,
                ignore_https_errors=self.config.disable_security,
                record_video_dir=self.config.save_recording_path,
                record_video_size=self.config.browser_window_size,
                locale=self.config.locale,
            )

        if self.config.trace_path:
            await context.tracing.start(screenshots=True, snapshots=True, sources=True)

        # Load cookies if they exist
        if self.config.cookies_file and os.path.exists(self.config.cookies_file):
            with open(self.config.cookies_file, "r") as f:
                cookies = json.load(f)
                logger.info(f"Loaded {len(cookies)} cookies from {self.config.cookies_file}")  # noqa: G004
                await context.add_cookies(cookies)

        # Expose anti-detection scripts
        await context.add_init_script(
            """
         // Webdriver property
         Object.defineProperty(navigator, 'webdriver', {
            get: () => false
         });

         // Languages
         Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US']
         });

         // Plugins
         // Object.defineProperty(navigator, 'plugins', {
         //    get: () => [1, 2, 3, 4, 5]
         // });

         // Uncomment this if need to use chrome extensions
         // if (!window.chrome) { window.chrome = {} };
         // if (!window.chrome.runtime) { window.chrome.runtime = {} };

         // Chrome runtime
         window.chrome = { runtime: {} };

         // Permissions
         const originalQuery = window.navigator.permissions.query;
         window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
               Promise.resolve({ state: Notification.permission }) :
               originalQuery(parameters)
         );
         (function () {
            const originalAttachShadow = Element.prototype.attachShadow;
            Element.prototype.attachShadow = function attachShadow(options) {
               return originalAttachShadow.call(this, { ...options, mode: "open" });
            };
         })();
      """
        )

        context.set_default_timeout(timeout=10000)  # 10 seconds
        context.set_default_navigation_timeout(timeout=60 * 1000 * 5)  # 5 minutes

        return context


class BrowserClient(Browser):
    async def new_context(self, config: BrowserContextConfig = BrowserContextConfig()) -> PatchedContext:
        return PatchedContext(config=config, browser=self)
