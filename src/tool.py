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

from src.client import BrowserClient, PatchedBrowserContext
from src.logger import init_logger
from src.types import UserInfo


class FCOnlineAutomation:
    # Selector constants
    LOGIN_BTN_SELECTOR = "a.btn-header.btn-header--login"
    LOGOUT_BTN_SELECTOR = "a.btn-header.btn-header--logout"
    USERNAME_INPUT_SELECTOR = "form input[type='text']"
    PASSWORD_INPUT_SELECTOR = "form input[type='password']"
    SUBMIT_BTN_SELECTOR = "form button[type='submit']"

    # URL constants
    BASE_URL = "https://bilac.fconline.garena.vn/"
    API_URL = "https://bilac.fconline.garena.vn/api/user/get"

    def __init__(
        self,
        username: str,
        password: str,
        headless: bool = False,
        target_jackpot: int = 10000,
    ) -> None:
        self.username = username
        self.password = password
        self.headless = headless
        self.target_jackpot = target_jackpot

        self.current_special_jackpot: int | float = 0  # Giải đặc biệt

        self._context: Optional[PatchedBrowserContext] = None
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

    def _check_target_reached(self, current_value, message_callback: Optional[Callable[[str], None]]) -> None:
        if not message_callback:
            return

        try:
            if isinstance(current_value, (int, float)) and current_value >= self.target_jackpot:
                message_callback(f"🎯 Jackpot has reached {self.target_jackpot}")
            elif isinstance(current_value, str):
                # Try to extract number from string
                numbers = re.findall(r"\d+", str(current_value).replace(",", ""))
                if numbers and int(numbers[0]) >= self.target_jackpot:
                    message_callback(f"🎯 Jackpot has reached {self.target_jackpot}")
        except (ValueError, TypeError):
            pass  # Ignore conversion errors

    def _process_jackpot_value(self, current_value, message_callback: Optional[Callable[[str], None]]) -> None:
        """Process and store jackpot value, then notify callbacks"""
        # Store the current special jackpot value
        try:
            if isinstance(current_value, (int, float)):
                self.current_special_jackpot = current_value
            elif isinstance(current_value, str):
                numbers = re.findall(r"\d+", str(current_value).replace(",", ""))
                if numbers:
                    self.current_special_jackpot = int(numbers[0])
        except (ValueError, TypeError):
            pass

        logger.success(f"🎰 Current Jackpot: {current_value}")
        if message_callback:
            message_callback(f"🎰 Current Jackpot: {current_value}")
            self._check_target_reached(current_value=current_value, message_callback=message_callback)

    def _check_jackpot_present(self, data: dict, message_callback: Optional[Callable[[str], None]]) -> bool:
        jackpot_keys = ["jackpot_value", "jackpot", "prize", "amount", "value"]

        # Check top level
        for key in jackpot_keys:
            if key in data:
                current_value = data[key]
                self._process_jackpot_value(current_value=current_value, message_callback=message_callback)
                return True

        # Check nested payload
        if "payload" in data and isinstance(data["payload"], dict):
            for key in jackpot_keys:
                if key in data["payload"]:
                    current_value = data["payload"][key]
                    self._process_jackpot_value(current_value=current_value, message_callback=message_callback)
                    return True

        return False

    def _parse_socketio_message(  # noqa: C901
        self,
        frame: str,
        message_callback: Optional[Callable[[str], None]],
    ) -> bool:
        # Handle Socket.IO format: 42["message",{"content":{...}}]
        if not frame.startswith("42["):
            return False

        # Extract JSON part after "42"
        json_match = re.search(r"42(\[.*\])", frame)
        if not json_match:
            return False

        json_str = json_match.group(1)
        try:
            # Socket.IO format is usually ["event_name", data]
            socket_data = json.loads(json_str)
            if not isinstance(socket_data, list) or len(socket_data) < 2:
                return False

            event_data = socket_data[1]
            if not isinstance(event_data, dict):
                return False

            # Check if this is jackpot data directly
            if self._check_jackpot_present(data=event_data, message_callback=message_callback):
                return True

            # Check nested content
            if "content" not in event_data or not isinstance(event_data["content"], dict):
                return False

            content = event_data["content"]

            # Check for jackpot_value in content
            if content.get("type") == "jackpot_value":
                value = content.get("value")
                if value is not None:
                    self._process_jackpot_value(current_value=value, message_callback=message_callback)
                    return True

            # Check other jackpot patterns in content
            return self._check_jackpot_present(data=content, message_callback=message_callback)

        except json.JSONDecodeError:
            return False

    async def _setup_websocket(self, page: Page, message_callback: Optional[Callable[[str], None]] = None) -> None:
        def handle_websocket(websocket: WebSocket) -> None:
            async def on_framereceived(frame: bytes | str) -> None:
                if not frame:
                    return

                logger.warning(f"🔗 WebSocket frame received: {frame}")

                try:
                    # Try Socket.IO format first
                    if isinstance(frame, str) and self._parse_socketio_message(
                        frame=frame, message_callback=message_callback
                    ):
                        return

                    # Try parsing as regular JSON
                    try:
                        data = json.loads(frame)
                        if isinstance(data, dict):
                            # Check for jackpot data
                            self._check_jackpot_present(data=data, message_callback=message_callback)

                    except json.JSONDecodeError:
                        # Not standard JSON, might be binary or other format
                        pass

                except Exception as e:
                    logger.error(f"❌ Error processing WebSocket message: {e}")

            websocket.on("framereceived", on_framereceived)
            websocket.on("framesent", lambda frame: logger.debug(f"🔗 WebSocket frame sent: {frame}"))
            websocket.on("close", lambda ws: logger.info("🔌 WebSocket connection closed"))

        page.on("websocket", handle_websocket)

    async def _setup_context(self) -> tuple[PatchedBrowserContext, Page]:
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

    def get_current_special_jackpot(self) -> int | float:
        """Get the current special jackpot value (Giải đặc biệt)"""
        return self.current_special_jackpot

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
    automation = FCOnlineAutomation(
        username="dummy_username",
        password="dummy_password",
        headless=False,
    )
    await automation.run()


if __name__ == "__main__":
    init_logger()
    asyncio.run(main_tool())
