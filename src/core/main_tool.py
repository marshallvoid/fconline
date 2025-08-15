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
        self.user_info: Optional[UserInfo] = None
        self._user_data_dir: str = PlatformManager.get_user_data_directory(username=username)

    async def _check_login(self, page: Page) -> bool:
        try:
            # Check for logout button first (indicates user is logged in)
            logout_btn = await page.query_selector(selector=self.event_config.logout_btn_selector)
            if logout_btn:
                logger.info("🔍 Login status: User is already logged in")
                return True

            # Check for login button (indicates user is not logged in)
            login_btn = await page.query_selector(selector=self.event_config.login_btn_selector)
            if login_btn:
                logger.info("🔍 Login status: User is not logged in")
                return False

            logger.warning("⚠️ Unable to determine login status")
            return False

        except Exception as e:
            logger.error(f"❌ Error checking login status: {e}")
            return False

    async def _perform_login(self, page: Page) -> bool:
        try:
            # First check if already logged in
            if await self._check_login(page):
                logger.info("🔐 User already logged in, skipping login process")
                return True

            logger.info("🔐 Starting login process...")

            # Find and click login button
            login_btn = await page.query_selector(selector=self.event_config.login_btn_selector)
            if not login_btn:
                logger.error("❌ Login button not found")
                return False

            logger.info("🔐 Clicking login button...")
            await login_btn.click()
            await page.wait_for_load_state(state="networkidle")

            # Fill username
            username_input = await page.query_selector(selector=self.event_config.username_input_selector)
            if username_input:
                await username_input.fill(value=self.username)
                logger.info(f"🔐 Filled username: {self.username}")
            else:
                logger.warning("⚠️ Username input field not found")

            # Fill password
            password_input = await page.query_selector(selector=self.event_config.password_input_selector)
            if password_input:
                await password_input.fill(value=self.password)
                logger.info("🔐 Filled password field")
            else:
                logger.warning("⚠️ Password input field not found")

            # Submit form
            submit_btn = await page.query_selector(selector=self.event_config.submit_btn_selector)
            if not submit_btn:
                logger.error("❌ Submit button not found")
                return False

            logger.info("🔐 Submitting login form...")
            await submit_btn.click()

            # Wait for login response
            try:
                logger.info("⏳ Waiting for login response...")
                await page.wait_for_function(
                    (
                        f"window.location.href.includes('{self.event_config.base_url}') || "
                        "document.querySelector('.captcha') || document.querySelector('.error')"
                    ),
                )

                current_url = page.url
                if self.event_config.base_url in current_url:
                    logger.success("🔐 Login completed successfully - redirected to main page")
                    return True
                else:
                    # Still on login page, might need captcha or have error
                    logger.info("🔐 Login requires additional steps (captcha/verification)")

                    # Wait for user to solve captcha and redirect (up to 5 minutes)
                    logger.info("⏳ Waiting for captcha resolution and redirect...")
                    await page.wait_for_function(f"window.location.href.includes('{self.event_config.base_url}')")

                logger.success("🔐 Login completed successfully after captcha resolution")
                return True

            except Exception as timeout_error:
                logger.error(f"❌ Login timeout or failed: {timeout_error}")
                return False

        except Exception as e:
            logger.error(f"❌ Error performing login: {e}")
            return False

    async def _fetch_user_info(self) -> None:
        if not self._cookies and self._page:
            try:
                logger.info("🍪 Extracting cookies from browser session...")
                for cookie in await self._page.context.cookies():
                    domain = cookie.get("domain", "")
                    if not domain:
                        continue

                    name, value = cookie.get("name", ""), cookie.get("value", "")
                    if not name or not value:
                        continue

                    self._cookies[name] = value

                logger.success(f"🍪 Successfully extracted {len(self._cookies)} cookies")

            except Exception as e:
                logger.error(f"❌ Failed to extract cookies: {e}")

        headers = {
            "x-csrftoken": self._cookies.get("csrftoken", ""),
            "Cookie": "; ".join([f"{name}={value}" for name, value in self._cookies.items()]),
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        }
        # Create SSL context that doesn't verify certificates
        import ssl

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(cookies=self._cookies, headers=headers, connector=connector) as session:
            try:
                logger.info("📡 Fetching user information from API...")

                async with session.get(self.event_config.api_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.user_info = UserInfo.model_validate(data)
                        logger.success("✅ User information fetched successfully")

                        if self.user_panel_callback:
                            self.user_panel_callback(self.user_info)

                        if self.message_callback:
                            self.message_callback(
                                "info",
                                (
                                    f"🔍 User information fetched successfully: "
                                    f"{self.user_info.payload.user.nickname if self.user_info.payload.user else 'Unknown'}"  # noqa: E501
                                ),
                            )
                    else:
                        logger.warning(f"⚠️ API request failed with status: {response.status}")

            except Exception as e:
                logger.error(f"❌ Failed to fetch user info: {e}")

    async def _auto_spin(self, page: Page, current_value: int, target_value: int) -> None:
        mapping = self.event_config.spin_action_selectors
        selector = mapping.get(self.spin_action, next(iter(mapping.values())))[0]
        display_label = mapping.get(self.spin_action, ("", "Unknown"))[1]

        spin_count = 0
        spin_element = await page.query_selector(selector=selector)
        while spin_element and current_value >= target_value and not self.stop_flag:
            try:
                await page.evaluate(f"document.querySelector('{selector}').click()")
                spin_count += 1

                if self.message_callback:
                    msg = f"🎰 Auto-spinning with action: {display_label}"
                    self.message_callback("info", msg)

                # Log every 10 spins to avoid spam
                if spin_count % 10 == 0:
                    logger.info(f"🎰 Auto-spin progress: {spin_count} spins completed")

            except Exception as e:
                logger.error(f"❌ Auto-spin error on spin #{spin_count}: {e}")
                # Continue spinning despite errors

            await asyncio.sleep(0.1)

    async def _setup_websocket(self, page: Page) -> None:  # noqa: C901
        logger.info("🔌 Setting up WebSocket monitoring...")

        def handle_websocket(websocket: WebSocket) -> None:  # noqa: C901
            logger.info(f"🔌 WebSocket connection established: {websocket.url}")

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
                            logger.success(f"🎰 Special Jackpot: {value:,}")
                            prev_jackpot = self.special_jackpot
                            self.special_jackpot = value

                            if self.user_panel_callback:
                                self.user_panel_callback(self.user_info)

                            if value >= self.target_special_jackpot:
                                if self.message_callback:
                                    self.message_callback(
                                        "target_reached",
                                        f"🎯 Special Jackpot has reached {self.target_special_jackpot:,}",
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
                            logger.success(f"🎯 Mini Jackpot: {value:,}")
                            prev_jackpot = self.mini_jackpot
                            self.mini_jackpot = value

                except json.JSONDecodeError:
                    logger.debug("🔌 WebSocket frame received but failed to parse JSON")

            websocket.on("framereceived", on_framereceived)
            websocket.on("framesent", lambda frame: logger.debug(f"🔌 WebSocket frame sent: {frame}"))
            websocket.on("close", lambda ws: logger.info(f"🔌 WebSocket connection closed: {ws.url}"))

        page.on("websocket", handle_websocket)
        logger.success("✅ WebSocket monitoring setup completed")

    async def _setup_context(self) -> Tuple[PatchedContext, Page]:
        logger.info("🌐 Setting up browser context...")

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

        system = platform.system().lower()
        logger.info(f"🖥️ Detected platform: {system}")

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
            logger.info("🪟 Applied Windows-specific browser arguments")

        logger.info(f"📁 Using user data directory: {self._user_data_dir}")

        browser = BrowserClient(
            config=BrowserConfig(
                extra_chromium_args=extra_chromium_args,
                chrome_instance_path=PlatformManager.get_chrome_executable_path(),
            )
        )

        context_config = BrowserContextConfig(browser_window_size={"width": 1920, "height": 1080})
        logger.info("🖥️ Creating browser context with 1920x1080 resolution...")

        browser_context = await browser.new_context(config=context_config)
        page = await browser_context.get_current_page()

        logger.success("✅ Browser context setup completed successfully")
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
        self.user_info = None

    async def close(self) -> None:
        if not self._context:
            return

        logger.info("🔒 Closing browser context and cleaning up resources...")
        try:
            await self._context.reset_context()
            await self._context.close()
            logger.success("✅ Browser resources cleaned up successfully")
        except Exception as e:
            logger.error(f"❌ Failed to clean up browser resource: {e}")
        finally:
            self._context = None
            self._page = None

    async def run(self) -> None:
        self._context, self._page = await self._setup_context()

        try:
            # Navigate to base URL
            logger.info(f"🌐 Navigating to: {self.event_config.base_url}")
            await self._page.goto(url=self.event_config.base_url)
            await self._page.wait_for_load_state(state="networkidle")

            # Check login status first
            logger.info("🔍 Checking login status...")
            if not await self._check_login(page=self._page):
                # Attempt to login
                logger.info("🔐 User not logged in, attempting login...")
                login_success = await self._perform_login(page=self._page)
                if not login_success:
                    logger.error("❌ Login failed! Exiting...")
                    return

            # Ensure we're on the correct page
            current_url = self._page.url
            if self.event_config.base_url not in current_url:
                logger.warning(f"⚠️ Redirected to unexpected URL: {current_url}")
                logger.info(f"🔄 Redirecting to: {self.event_config.base_url}")
                await self._page.goto(url=self.event_config.base_url)
                await self._page.wait_for_load_state(state="networkidle")

            # Fetch user info
            await self._fetch_user_info()

            # Main monitoring loop
            await self._setup_websocket(page=self._page)
            logger.success("🚀 Starting WebSocket monitoring...")
            while not self.stop_flag:
                await asyncio.sleep(delay=1)

        except Exception as e:
            logger.error(f"❌ Unexpected error during execution: {e}")
        finally:
            await self.close()
            logger.info("🏁 FC Online automation tool stopped")
