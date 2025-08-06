import asyncio
import json
import os
import platform
import re
from typing import Callable, Optional

import aiohttp
from browser_use import BrowserConfig, BrowserContextConfig
from loguru import logger
from playwright.async_api import Page, WebSocket

from src.client import BrowserClient, PatchedContext
from src.logger import init_logger
from src.types import UserInfo


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
        1: SPIN_ACTION_1_SELECTOR,
        2: SPIN_ACTION_2_SELECTOR,
        3: SPIN_ACTION_3_SELECTOR,
        4: SPIN_ACTION_4_SELECTOR,
    }

    SPIN_ACTION_TEXT = {
        1: "Free Spin",
        2: "FC10 Spin",
        3: "...",
        4: "...",
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
        self.username = username
        self.password = password
        self.headless = headless
        self.spin_action = spin_action

        self.target_special_jackpot = target_special_jackpot
        self.special_jackpot: int = 0

        self.mini_jackpot: int = 0

        self._context: Optional[PatchedContext] = None
        self._page: Optional[Page] = None
        self._stop_flag = False

    @staticmethod
    def _get_chrome_executable_path() -> Optional[str]:
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
                return path

        logger.warning("🌐 Chrome not found, will use default Chrome channel")
        return None

    async def _get_user_info_api(self, session: aiohttp.ClientSession) -> Optional[UserInfo]:
        try:
            async with session.get(self.API_URL) as response:
                if response.status != 200:
                    logger.error(f"❌ API Error: Status {response.status}")
                    return None

                data = await response.json()
                return UserInfo.model_validate(data)

        except Exception as e:
            logger.error(f"❌ API call error: {e}")
            return None

    async def _check_login(self, page: Page) -> bool:
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

            # Wait for login completion and redirect
            await page.wait_for_load_state(state="networkidle")
            logger.success("🔐 Login completed successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Login error: {e}")
            return False

    async def _auto_spin(
        self,
        page: Page,
        current_value: int,
        target_value: int,
        message_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Continuously click the spin button while target is reached"""
        selector = self.SPIN_ACTION_SELECTORS.get(self.spin_action, self.SPIN_ACTION_1_SELECTOR)

        try:
            while current_value >= target_value and not self._stop_flag:
                # Check for and handle SweetAlert2 modal first
                await self._handle_swal_modal(page)

                spin_element = await page.query_selector(selector)
                if spin_element:
                    try:
                        # Use force click to bypass intercepting elements
                        await spin_element.click(force=True, timeout=5000)
                        if message_callback:
                            msg = f"🎰 Auto-spinning with action: {self.SPIN_ACTION_TEXT.get(self.spin_action, 'Unknown')}"  # noqa: E501
                            message_callback(msg)
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
        """Handle SweetAlert2 modal if present"""
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

    def _process_frame(self, frame: str, message_callback: Optional[Callable[[str], None]]) -> None:  # noqa: C901
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
                    prev_jackpot = self.special_jackpot
                    self.special_jackpot = value

                    if message_callback:
                        message_callback(f"🎰 Special Jackpot: {value}")
                        if value >= self.target_special_jackpot:
                            message_callback(f"🎯 Special Jackpot has reached {self.target_special_jackpot}")

                            # If target just reached (wasn't reached before), start auto-spinning
                            if prev_jackpot < self.target_special_jackpot and self._page:
                                asyncio.create_task(
                                    self._auto_spin(
                                        page=self._page,
                                        current_value=self.special_jackpot,
                                        target_value=self.target_special_jackpot,
                                        message_callback=message_callback,
                                    )
                                )

                case "mini_jackpot":
                    logger.success(f"🎯 Mini Jackpot: {value}")
                    self.mini_jackpot = value

                    if message_callback:
                        message_callback(f"🎯 Mini Jackpot: {value}")

        except json.JSONDecodeError:
            pass  # Ignore JSON decode errors

    async def _setup_websocket(self, page: Page, message_callback: Optional[Callable[[str], None]] = None) -> None:
        def handle_websocket(websocket: WebSocket) -> None:
            async def on_framereceived(frame: bytes | str) -> None:
                if not frame or not isinstance(frame, str):
                    return
                self._process_frame(frame=frame, message_callback=message_callback)

            websocket.on("framereceived", on_framereceived)
            websocket.on("framesent", lambda frame: logger.info(f"🔗 WebSocket frame sent: {frame}"))
            websocket.on("close", lambda ws: logger.info(f"🔌 WebSocket[{ws.url}] connection closed"))

        page.on("websocket", handle_websocket)

    async def _setup_context(self) -> tuple[PatchedContext, Page]:
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
            "--user-data-dir=/tmp/chrome-automation",
        ]

        if self.headless:
            extra_chromium_args.append("--headless")

        browser = BrowserClient(
            config=BrowserConfig(
                headless=self.headless,
                extra_chromium_args=extra_chromium_args,
                chrome_instance_path=self._get_chrome_executable_path(),
            )
        )

        context_config = BrowserContextConfig(browser_window_size={"width": 1920, "height": 1080})
        browser_context = await browser.new_context(config=context_config)
        page = await browser_context.get_current_page()

        return browser_context, page

    async def close_browser(self) -> None:
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

    def stop(self) -> None:
        self._stop_flag = True

    def start(self) -> None:
        self._stop_flag = False

    async def run(self, message_callback: Optional[Callable[[str], None]] = None) -> None:
        self._context, self._page = await self._setup_context()

        try:
            async with self._context:
                # Setup WebSocket interception before loading the page
                await self._setup_websocket(page=self._page, message_callback=message_callback)

                await self._page.goto(url=self.BASE_URL)
                await self._page.wait_for_load_state(state="networkidle")

                # Check login status
                if not await self._check_login(page=self._page) and not await self._perform_login(page=self._page):
                    logger.error("❌ Login failed!")
                    return

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
    init_logger()
    asyncio.run(main_tool())
