import asyncio
import json
import os
import platform as sys_platform
import re
import shutil
from typing import Callable, Optional

import aiohttp
from browser_use import BrowserConfig, BrowserContextConfig
from loguru import logger
from playwright.async_api import Page, WebSocket

from src.client import BrowserClient, PatchedContext
from src.types import UserInfo
from src.utils import platform


class FCOnlineTool:
    # Selector constants
    LOGIN_BTN_SELECTOR = "a.btn-header.btn-header--login"
    LOGOUT_BTN_SELECTOR = "a.btn-header.btn-header--logout"
    USERNAME_INPUT_SELECTOR = "form input[type='text']"
    PASSWORD_INPUT_SELECTOR = "form input[type='password']"
    SUBMIT_BTN_SELECTOR = "form button[type='submit']"

    SPIN_ACTION_1_SELECTOR = "div.spin__actions a.spin__actions--1"
    SPIN_ACTION_2_SELECTOR = "div.spin__actions a.spin__actions--2"
    SPIN_ACTION_3_SELECTOR = "div.spin__actions a.spin__actions--3"
    SPIN_ACTION_4_SELECTOR = "div.spin__actions a.spin__actions--4"

    SPIN_ACTION_SELECTORS = {
        1: (SPIN_ACTION_1_SELECTOR, "Free Spin"),
        2: (SPIN_ACTION_2_SELECTOR, "FC10 Spin"),
        3: (SPIN_ACTION_3_SELECTOR, "..."),
        4: (SPIN_ACTION_4_SELECTOR, "..."),
    }

    # URL constants
    BASE_URL = "https://bilac.fconline.garena.vn/"
    API_URL = "https://bilac.fconline.garena.vn/api/user/get"

    def __init__(
        self,
        username: str,
        password: str,
        headless: bool = False,
        target_special_jackpot: int = 10000,
        spin_action: int = 1,
    ) -> None:
        """Initialize FC Online automation tool.

        Args:
            username: User login username
            password: User login password
            headless: Run browser in headless mode
            target_special_jackpot: Jackpot value to trigger auto-spin
            spin_action: Spin action type (1-4)
        """
        self.username = username
        self.password = password
        self.headless = headless
        self.spin_action = spin_action

        self.target_special_jackpot = target_special_jackpot
        self._special_jackpot: int = 0

        self._mini_jackpot: int = 0

        self._context: Optional[PatchedContext] = None
        self._page: Optional[Page] = None
        self._stop_flag = False
        self._needs_cookie_clear = False

        # User info
        self.user_info: Optional[UserInfo] = None
        self._cookies: dict[str, str] = {}

        # User data directory path - use platform-specific directory
        self._user_data_dir = platform.get_user_data_directory(username)

        # Callbacks for GUI updates
        self.message_callback: Optional[Callable[[str], None]] = None
        self.user_info_callback: Optional[Callable[[], None]] = None

    async def _check_login(self, page: Page) -> bool:
        """Check if user is logged in by looking for login/logout buttons.

        Args:
            page: Playwright page instance

        Returns:
            True if logged in, False otherwise

        Raises:
            Exception: For page interaction errors
        """
        try:
            # Check for login button (not logged in)
            login_btn = await page.query_selector(selector=self.LOGIN_BTN_SELECTOR)
            if login_btn:
                return False

            # Check for logout button (logged in)
            logout_btn = await page.query_selector(selector=self.LOGOUT_BTN_SELECTOR)
            if logout_btn:
                return True

            logger.warning("⚠️ Unable to determine login status")
            return False
        except Exception as e:
            logger.error(f"❌ Error checking login status: {e}")
            return False

    async def _perform_login(self, page: Page) -> bool:
        """Perform login by filling credentials and submitting form.

        Args:
            page: Playwright page instance

        Returns:
            True if login successful, False otherwise

        Raises:
            Exception: For page interaction or login errors
        """
        try:
            # Click login button
            login_btn = await page.query_selector(selector=self.LOGIN_BTN_SELECTOR)
            if not login_btn:
                logger.error("❌ Login button not found")
                return False

            await login_btn.click()

            # Wait for login page to load
            await page.wait_for_load_state(state="networkidle")

            # Fill username
            username_input = await page.query_selector(selector=self.USERNAME_INPUT_SELECTOR)
            if username_input:
                await username_input.fill(value=self.username)

            # Fill password
            password_input = await page.query_selector(selector=self.PASSWORD_INPUT_SELECTOR)
            if password_input:
                await password_input.fill(value=self.password)

            # Click submit button
            submit_btn = await page.query_selector(selector=self.SUBMIT_BTN_SELECTOR)
            if not submit_btn:
                logger.error("❌ Submit button not found")
                return False

            await submit_btn.click()

            # Wait for login completion - either redirect to BASE_URL or stay on login page for captcha
            logger.info("🔐 Login form submitted, waiting for response...")

            # Wait for either successful redirect to BASE_URL or captcha/error handling
            try:
                # Wait for navigation or URL change (up to 30 seconds for captcha solving)
                wait_condition = (
                    f"window.location.href.includes('{self.BASE_URL}') || "
                    "document.querySelector('.captcha') || document.querySelector('.error')"
                )
                await page.wait_for_function(wait_condition, timeout=30000)

                # Check current URL to determine login result
                current_url = page.url
                if self.BASE_URL in current_url:
                    logger.success("🔐 Login completed successfully - redirected to main page")
                    return True
                else:
                    # Still on login page, might need captcha or have error
                    logger.info("🔐 Login requires additional steps (captcha/verification)")

                    # Wait for user to solve captcha and redirect (up to 5 minutes)
                    logger.info("⏳ Waiting for captcha resolution and redirect...")
                    await page.wait_for_function(
                        f"window.location.href.includes('{self.BASE_URL}')",
                        timeout=300000,  # 5 minutes
                    )

                    logger.success("🔐 Login completed successfully after captcha resolution")
                    return True

            except Exception as timeout_error:
                logger.error(f"❌ Login timeout or failed: {timeout_error}")
                return False

        except Exception as e:
            logger.error(f"❌ Login error: {e}")
            return False

    async def _extract_cookies(self, page: Page) -> dict[str, str]:
        """Extract cookies from browser for API authentication.

        Args:
            page: Playwright page instance

        Returns:
            Dictionary of cookie name-value pairs

        Raises:
            Exception: For cookie extraction errors
        """
        try:
            cookies = await page.context.cookies()
            cookie_dict = {}

            for cookie in cookies:
                domain = cookie.get("domain", "")
                if domain in ["bilac.fconline.garena.vn", ".fconline.garena.vn"]:
                    name = cookie.get("name", "")
                    value = cookie.get("value", "")
                    if name and value:
                        cookie_dict[name] = value

            logger.info(f"🍪 Extracted {len(cookie_dict)} cookies")
            return cookie_dict

        except Exception as e:
            logger.error(f"❌ Failed to extract cookies: {e}")
            return {}

    async def _fetch_user_info(self) -> None:
        """Fetch user info from API using extracted cookies.

        Raises:
            Exception: For API request or parsing errors
        """
        if not self._cookies and self._page:
            self._cookies = await self._extract_cookies(self._page)

        async with aiohttp.ClientSession() as session:
            try:
                cookie_header = "; ".join([f"{name}={value}" for name, value in self._cookies.items()])

                headers = {
                    "Cookie": cookie_header,
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                }

                # Add CSRF token if available
                if "csrftoken" in self._cookies:
                    headers["X-CSRFToken"] = self._cookies["csrftoken"]

                    async with session.get(self.API_URL, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            self.user_info = UserInfo.model_validate(data)

                    # Notify GUI about user info update
                    if self.user_info_callback:
                        self.user_info_callback()

            except Exception as e:
                logger.error(f"❌ Failed to fetch user info: {e}")

    async def _auto_spin(self, page: Page, current_value: int, target_value: int) -> None:
        """Continuously click the spin button while target is reached.

        Args:
            page: Playwright page instance
            current_value: Current jackpot value
            target_value: Target jackpot threshold

        Raises:
            Exception: For page interaction errors
        """
        selector = self.SPIN_ACTION_SELECTORS.get(self.spin_action, self.SPIN_ACTION_1_SELECTOR)[0]

        try:
            while current_value >= target_value and not self._stop_flag:
                # Check for and handle SweetAlert2 modal first
                await self._handle_swal_modal(page)

                spin_element = await page.query_selector(selector)
                if spin_element:
                    try:
                        # Use force click to bypass intercepting elements
                        await spin_element.click(force=True, timeout=5000)
                        if self.message_callback:
                            msg = f"🎰 Auto-spinning with action: {self.SPIN_ACTION_SELECTORS.get(self.spin_action, 'Unknown')[1]}"  # noqa: E501
                            self.message_callback(msg)
                    except Exception as click_error:
                        logger.warning(f"⚠️ Click failed, trying alternative method: {click_error}")
                        # Try JavaScript click as fallback
                        await page.evaluate(f"document.querySelector('{selector}').click()")
                else:
                    logger.warning(f"⚠️ Spin element not found: {selector}")
                    break

                # Small delay to prevent overwhelming the browser
                await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"❌ Auto-spin error: {e}")

    async def _handle_swal_modal(self, page: Page) -> None:
        """Handle SweetAlert2 modal if present.

        Args:
            page: Playwright page instance

        Raises:
            Exception: For modal handling errors (non-critical)
        """
        try:
            # Check if SweetAlert2 modal is present
            swal_container = await page.query_selector(".swal2-container")
            if swal_container:
                # Try to find and click OK/Confirm button
                confirm_btn = await page.query_selector(".swal2-confirm")
                if confirm_btn:
                    await confirm_btn.click(force=True)
                    await asyncio.sleep(0.2)  # Wait for modal to close
                else:
                    # Try other common button selectors
                    for btn_selector in [".swal2-styled", ".swal2-close", ".swal2-cancel"]:
                        btn = await page.query_selector(btn_selector)
                        if btn:
                            await btn.click(force=True)
                            await asyncio.sleep(0.2)
                            break
        except Exception as e:
            logger.debug(f"Modal handling error (non-critical): {e}")

    def _process_frame(self, frame: str) -> None:  # noqa: C901
        """Process WebSocket frame data for jackpot updates.

        Args:
            frame: Raw WebSocket frame string
        """
        # Handle Socket.IO format: 42["message",{"content":{...}}]
        if not frame.startswith("42["):
            return

        # Extract JSON part after "42"
        json_match = re.search(r"42(\[.*\])", frame)
        if not json_match:
            return

        json_str = json_match.group(1)
        try:
            # Socket.IO format is usually ["event_name", event_data (dict)]
            socket_data = json.loads(json_str)
            if not isinstance(socket_data, list) or len(socket_data) < 2:
                return

            event_data = socket_data[1]
            if not isinstance(event_data, dict):
                return

            # Check nested content
            content = event_data.get("content")
            if not content or not isinstance(content, dict):
                return

            type = content.get("type")
            value = content.get("value")
            if not isinstance(type, str) or not type or not isinstance(value, int) or value is None:
                return

            match type:
                case "jackpot_value":
                    logger.success(f"🎰 Special Jackpot: {value}")
                    prev_jackpot = self._special_jackpot
                    self._special_jackpot = value

                    if self.message_callback:
                        self.message_callback(f"🎰 Special Jackpot: {value}")
                        if value >= self.target_special_jackpot:
                            self.message_callback(f"🎯 Special Jackpot has reached {self.target_special_jackpot}")

                            # If target just reached (wasn't reached before), start auto-spinning
                            if prev_jackpot < self.target_special_jackpot and self._page:
                                asyncio.create_task(
                                    self._auto_spin(
                                        page=self._page,
                                        current_value=self._special_jackpot,
                                        target_value=self.target_special_jackpot,
                                    )
                                )

                case "mini_jackpot":
                    logger.success(f"🎯 Mini Jackpot: {value}")
                    self._mini_jackpot = value

                    if self.message_callback:
                        self.message_callback(f"🎯 Mini Jackpot: {value}")

        except json.JSONDecodeError:
            pass  # Ignore JSON decode errors

    async def _setup_websocket(self, page: Page) -> None:
        """Setup WebSocket listeners for real-time jackpot updates.

        Args:
            page: Playwright page instance
        """

        def handle_websocket(websocket: WebSocket) -> None:
            async def on_framereceived(frame: bytes | str) -> None:
                if not frame or not isinstance(frame, str):
                    return
                self._process_frame(frame=frame)

            websocket.on("framereceived", on_framereceived)
            websocket.on("framesent", lambda frame: logger.info(f"🔗 WebSocket frame sent: {frame}"))
            websocket.on("close", lambda ws: logger.info(f"🔌 WebSocket[{ws.url}] connection closed"))

        page.on("websocket", handle_websocket)

    async def _setup_context(self) -> tuple[PatchedContext, Page]:
        """Setup browser context and page with Chrome configuration.

        Returns:
            Tuple of (browser_context, page)

        Raises:
            Exception: For browser setup errors
        """
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
            f"--user-data-dir={self._user_data_dir}",
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

        # Choose browser based on user preference
        browser_path = platform.get_default_browser_executable_path() or platform.get_chrome_executable_path()

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

        return browser_context, page

    def stop(self) -> None:
        """Stop the automation tool."""
        self._stop_flag = True

    def start(self) -> None:
        """Start the automation tool."""
        self._stop_flag = False

    def update_credentials(self, username: str, password: str) -> None:
        """Update login credentials and clean old user data if username changed.

        Args:
            username: New username
            password: New password

        Raises:
            Exception: For file system cleanup errors
        """
        old_username = self.username
        old_password = self.password

        # Only clean up if credentials actually changed
        credentials_changed = (old_username != username) or (old_password != password)

        if not credentials_changed:
            # No changes, nothing to do
            return

        if old_username != username:
            # Username changed, clean old user data directory
            old_user_data_dir = platform.get_user_data_directory(old_username)
            try:
                if os.path.exists(old_user_data_dir):
                    shutil.rmtree(old_user_data_dir)
                #   logger.info(f"🧹 Cleaned old user data directory: {old_user_data_dir}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to clean old user data directory: {e}")

        # Update credentials and user data directory
        self.username = username
        self.password = password
        self._user_data_dir = platform.get_user_data_directory(username)

        # Clear cached data only when credentials changed
        self.user_info = None
        self._cookies = {}

        # Clear browser cookies if browser is running and credentials changed
        if self._page:
            self._clear_cookies()
        else:
            # Mark that cookies need to be cleared when browser starts
            self._needs_cookie_clear = True
            # logger.info("🍪 Cookies will be cleared when browser starts")

        # Notify GUI to update user info display
        if self.user_info_callback:
            self.user_info_callback()

    def _clear_cookies(self) -> None:
        """Safely clear browser cookies, handling event loop issues."""
        if not self._page:
            return

        try:
            # Check if we're already in an event loop
            loop = asyncio.get_running_loop()
            # Schedule the cookie clearing in the existing loop
            loop.create_task(self._page.context.clear_cookies())
        except RuntimeError:
            # No running loop, safe to use asyncio.run()
            try:
                asyncio.run(self._page.context.clear_cookies())
            except Exception as e:
                logger.warning(f"⚠️ Failed to clear cookies: {e}")

    async def close_browser(self) -> None:
        """Close browser context and cleanup resources.

        Raises:
            Exception: For browser cleanup errors
        """
        if not self._context:
            return

        try:
            await self._context.reset_context()
            await self._context.close()
        except Exception as e:
            logger.error(f"❌ Failed to clean up browser resource: {e}")
        finally:
            self._context = None
            self._page = None
            self._needs_cookie_clear = False

    async def run(self) -> None:
        """Main automation loop - setup browser, login, and monitor WebSocket.

        Raises:
            Exception: For various automation errors
        """
        self._context, self._page = await self._setup_context()

        try:
            async with self._context:
                # Clear cookies if needed (when credentials were updated before browser started)
                if self._needs_cookie_clear:
                    try:
                        await self._page.context.clear_cookies()
                        # logger.info("🍪 Cleared cookies after browser startup")
                        self._needs_cookie_clear = False
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to clear cookies at startup: {e}")

                # Setup WebSocket interception before loading the page
                await self._setup_websocket(page=self._page)

                await self._page.goto(url=self.BASE_URL)
                await self._page.wait_for_load_state(state="networkidle")

                # Check login status and perform login if needed
                login_needed = not await self._check_login(page=self._page)
                if login_needed:
                    login_success = await self._perform_login(page=self._page)
                    if not login_success:
                        logger.error("❌ Login failed!")
                        return

                    # After successful login, ensure we're back to BASE_URL
                    current_url = self._page.url
                    if self.BASE_URL not in current_url:
                        # logger.info("🔄 Navigating back to main page after login...")
                        await self._page.goto(url=self.BASE_URL)
                        await self._page.wait_for_load_state(state="networkidle")

                # Always fetch user info when starting automation (whether logged in or just logged in)
                await self._fetch_user_info()

                logger.info("🚀 Starting WebSocket monitoring...")
                # Keep the browser open and monitor WebSocket
                while not self._stop_flag:
                    await asyncio.sleep(delay=1)

        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")

        finally:
            await self.close_browser()


async def main_tool() -> None:
    automation = FCOnlineTool(
        username="dummy_username",
        password="dummy_password",
        headless=False,
        target_special_jackpot=10000,
        spin_action=1,
    )
    await automation.run()


if __name__ == "__main__":
    import src.logger  # noqa: F401

    asyncio.run(main_tool())
