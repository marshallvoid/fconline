import asyncio
import json
import platform
import re
from typing import Callable, Optional, Tuple

import aiohttp
from browser_use import BrowserConfig, BrowserContextConfig
from loguru import logger
from playwright.async_api import Page, WebSocket

from src.core.event_config import EventConfig
from src.infrastructure.client import BrowserClient, PatchedContext
from src.schemas import UserInfo
from src.utils.platforms import PlatformManager


class MainTool:
    def __init__(
        self,
        event_config: EventConfig,
        username: str,
        password: str,
        spin_action: int = 1,
        target_special_jackpot: int = 10000,
    ) -> None:
        self.event_config: EventConfig = event_config
        self.username: str = username
        self.password: str = password
        self.spin_action: int = spin_action
        self.target_special_jackpot: int = target_special_jackpot

        self.stop_flag: bool = False
        self.special_jackpot: int = 0
        self.mini_jackpot: int = 0

        self.message_callback: Optional[Callable[[str, str], None]] = None
        self.user_panel_callback: Optional[Callable[[Optional[UserInfo]], None]] = None

        self._context: Optional[PatchedContext] = None
        self._page: Optional[Page] = None

        self._cookies: dict[str, str] = {}
        self._user_info: Optional[UserInfo] = None

    async def _check_login(self, page: Page) -> bool:
        try:
            # Check for logout button first (indicates user is logged in)
            logout_btn = await page.query_selector(selector=self.event_config.logout_btn_selector)
            if logout_btn:
                return True

            # Check for login button (indicates user is not logged in)
            login_btn = await page.query_selector(selector=self.event_config.login_btn_selector)
            if login_btn:
                return False

            # If neither button is found, check URL or other indicators
            current_url = page.url
            if self.event_config.base_url in current_url:
                # Check if we're on a logged-in page by looking for user-specific elements
                try:
                    # Wait a bit for page to fully load
                    await page.wait_for_timeout(1000)

                    # Try to find any user-specific content
                    user_content = await page.query_selector("body")
                    if user_content:
                        page_content = await page.content()
                        # Simple check for logged-in indicators
                        if "logout" in page_content.lower() or "user" in page_content.lower():
                            return True

                except Exception:
                    pass

            return False

        except Exception:
            # Silent fail - don't log errors in production builds
            return False

    async def _perform_login(self, page: Page) -> bool:
        try:
            # First check if already logged in
            if await self._check_login(page):
                return True

            # Find and click login button
            login_btn = await page.query_selector(selector=self.event_config.login_btn_selector)
            if not login_btn:
                return False

            await login_btn.click()
            await page.wait_for_load_state(state="networkidle")

            # Fill username
            username_input = await page.query_selector(selector=self.event_config.username_input_selector)
            if username_input:
                await username_input.fill(value=self.username)

            # Fill password
            password_input = await page.query_selector(selector=self.event_config.password_input_selector)
            if password_input:
                await password_input.fill(value=self.password)

            # Submit form
            submit_btn = await page.query_selector(selector=self.event_config.submit_btn_selector)
            if not submit_btn:
                return False

            await submit_btn.click()

            # Wait for login response
            try:
                await page.wait_for_function(
                    (
                        f"window.location.href.includes('{self.event_config.base_url}') || "
                        "document.querySelector('.captcha') || document.querySelector('.error')"
                    ),
                    timeout=30000,
                )

                current_url = page.url
                if self.event_config.base_url in current_url:
                    return True

                # Handle captcha or additional verification
                await page.wait_for_function(
                    f"window.location.href.includes('{self.event_config.base_url}')", timeout=60000
                )

                return True

            except Exception:
                return False

        except Exception:
            return False

    async def _fetch_user_info(self) -> None:
        if not self._cookies and self._page:
            try:
                for cookie in await self._page.context.cookies():
                    domain = cookie.get("domain", "")
                    if not domain:
                        continue

                    name, value = cookie.get("name", ""), cookie.get("value", "")
                    if not name or not value:
                        continue

                    self._cookies[name] = value

                logger.info(f"🍪 Extracted {len(self._cookies)} cookies")

            except Exception as e:
                logger.error(f"❌ Failed to extract cookies: {e}")

        async with aiohttp.ClientSession() as session:
            try:
                headers = {
                    "X-CSRFToken": self._cookies.get("csrftoken", ""),
                    "Cookie": "; ".join([f"{name}={value}" for name, value in self._cookies.items()]),
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                }

                async with session.get(self.event_config.api_url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        self._user_info = UserInfo.model_validate(data)

                if self.user_panel_callback:
                    self.user_panel_callback(self._user_info)

            except Exception as e:
                logger.error(f"❌ Failed to fetch user info: {e}")

    async def _auto_spin(self, page: Page, current_value: int, target_value: int) -> None:
        mapping = self.event_config.spin_action_selectors
        selector = mapping.get(self.spin_action, next(iter(mapping.values())))[0]
        display_label = mapping.get(self.spin_action, ("", "Unknown"))[1]

        while current_value >= target_value and not self.stop_flag:
            try:
                await page.evaluate(f"document.querySelector('{selector}').click()")

                if self.message_callback:
                    msg = f"🎰 Auto-spinning with action: {display_label}"
                    self.message_callback("info", msg)

            except Exception:
                # Silent fail in production builds
                pass

            await asyncio.sleep(0.1)

    async def _setup_websocket(self, page: Page) -> None:  # noqa: C901
        def handle_websocket(websocket: WebSocket) -> None:  # noqa: C901
            async def on_framereceived(frame: bytes | str) -> None:  # noqa: C901
                if not frame:
                    return

                if isinstance(frame, bytes):
                    frame = frame.decode("utf-8")

                json_match = re.search(r"42(\[.*\])", frame)
                if not json_match:
                    return

                json_str = json_match.group(1)
                try:
                    socket_data = json.loads(json_str)
                    if not isinstance(socket_data, list) or len(socket_data) < 2:
                        return

                    event_data = socket_data[1]
                    if not isinstance(event_data, dict):
                        return

                    content = event_data.get("content")
                    if not content or not isinstance(content, dict):
                        return

                    type, value = content.get("type"), content.get("value")
                    if type is None or not isinstance(type, str) or value is None or not isinstance(value, int):
                        return

                    match type:
                        case "jackpot_value":
                            logger.success(f"🎰 Special Jackpot: {value}")
                            prev_jackpot = self.special_jackpot
                            self.special_jackpot = value

                            if self.user_panel_callback:
                                self.user_panel_callback(self._user_info)

                            if value >= self.target_special_jackpot:
                                if self.message_callback:
                                    self.message_callback(
                                        "target_reached",
                                        f"🎯 Special Jackpot has reached {self.target_special_jackpot}",
                                    )

                                if prev_jackpot < self.target_special_jackpot and self._page:
                                    asyncio.create_task(
                                        self._auto_spin(
                                            page=self._page,
                                            current_value=self.special_jackpot,
                                            target_value=self.target_special_jackpot,
                                        )
                                    )

                        case "mini_jackpot":
                            logger.success(f"🎯 Mini Jackpot: {value}")
                            prev_jackpot = self.mini_jackpot
                            self.mini_jackpot = value

                except json.JSONDecodeError:
                    pass

            websocket.on("framereceived", on_framereceived)
            websocket.on("framesent", lambda frame: logger.info(f"🔗 WebSocket frame sent: {frame}"))
            websocket.on("close", lambda ws: logger.info(f"🔌 WebSocket[{ws.url}] connection closed"))

        page.on("websocket", handle_websocket)

    async def _setup_context(self) -> Tuple[PatchedContext, Page]:
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
        ]

        system = platform.system().lower()
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

        browser = BrowserClient(
            config=BrowserConfig(
                extra_chromium_args=extra_chromium_args,
                chrome_instance_path=PlatformManager.get_chrome_executable_path(),
            )
        )

        context_config = BrowserContextConfig(browser_window_size={"width": 1920, "height": 1080})
        browser_context = await browser.new_context(config=context_config)
        page = await browser_context.get_current_page()

        return browser_context, page

    def update_credentials(self, username: str, password: str) -> None:
        old_username = self.username
        old_password = self.password

        credentials_changed = (old_username != username) or (old_password != password)
        if not credentials_changed:
            return

        self.username = username
        self.password = password

        self._cookies = {}
        self._user_info = None

    async def close(self) -> None:
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

    async def run(self) -> None:
        self._context, self._page = await self._setup_context()

        try:
            await self._setup_websocket(page=self._page)

            # Navigate to base URL
            await self._page.goto(url=self.event_config.base_url)
            await self._page.wait_for_load_state(state="networkidle")

            # Check login status first
            if not await self._check_login(page=self._page):
                # Attempt to login
                login_success = await self._perform_login(page=self._page)
                if not login_success:
                    # Double check if login actually succeeded
                    await self._page.wait_for_timeout(2000)
                    if not await self._check_login(page=self._page):
                        return  # Login failed

            # Ensure we're on the correct page
            current_url = self._page.url
            if self.event_config.base_url not in current_url:
                await self._page.goto(url=self.event_config.base_url)
                await self._page.wait_for_load_state(state="networkidle")

            # Fetch user info
            await self._fetch_user_info()

            # Main monitoring loop
            while not self.stop_flag:
                await asyncio.sleep(delay=1)

        except Exception:
            # Silent fail in production builds
            pass

        finally:
            await self.close()
