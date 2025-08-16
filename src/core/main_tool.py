import asyncio
from typing import Callable, Dict, Optional, Tuple

import aiohttp
from browser_use import BrowserProfile, BrowserSession
from browser_use.browser.types import Page
from loguru import logger

from src.core.event_config import EventConfig
from src.core.login_handler import LoginHandler
from src.core.websocket_handler import WebsocketHandler
from src.schemas.user_response import UserReponse
from src.utils.methods import should_execute_callback
from src.utils.platforms import PlatformManager
from src.utils.requests import RequestManager


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

        self.is_running: bool = False
        self.special_jackpot: int = 0
        self.mini_jackpot: int = 0

        self.user_panel_callback: Optional[Callable[[Optional[UserReponse]], None]] = None
        self.message_callback: Optional[Callable[[str, str], None]] = None
        self.special_jackpot_callback: Optional[Callable[[int], None]] = None

        self.session: Optional[BrowserSession] = None
        self.page: Optional[Page] = None
        self.user_data_dir: Optional[str] = None

        self.cookies: Dict[str, str] = {}
        self.headers: Dict[str, str] = {}
        self.user_info: Optional[UserReponse] = None

    async def run(self) -> None:
        self.session, self.page = await self._setup_browser()

        try:
            logger.info(f"🌐 Navigating to: {self.event_config.base_url}")
            await self.page.goto(url=self.event_config.base_url)
            await self.page.wait_for_load_state(state="networkidle")

            WebsocketHandler.setup(
                page=self.page,
                event_config=self.event_config,
                spin_action=self.spin_action,
                special_jackpot=self.special_jackpot,
                mini_jackpot=self.mini_jackpot,
                target_special_jackpot=self.target_special_jackpot,
                message_callback=self.message_callback,
                jackpot_callback=self.special_jackpot_callback,
            ).run()

            await LoginHandler.setup(
                page=self.page,
                event_config=self.event_config,
                username=self.username,
                password=self.password,
                message_callback=self.message_callback,
            ).run()

            await self._get_user_info()

            WebsocketHandler.cookies = self.cookies
            WebsocketHandler.headers = self.headers

            while self.is_running:
                await asyncio.sleep(delay=1)

        except Exception as e:
            logger.error(f"❌ Unexpected error during execution: {e}")

        finally:
            await self.close()
            should_execute_callback(self.message_callback, "info", "FC Online automation tool stopped")

    async def close(self) -> None:
        if not self.page or not self.session:
            return

        logger.info("🔒 Closing browser context and cleaning up resources...")
        try:
            await self.page.close()
            await self.session.close()
            logger.success("✅ Browser resources cleaned up successfully")
        except Exception as e:
            logger.error(f"❌ Failed to clean up browser resource: {e}")
        finally:
            self.user_data_dir = PlatformManager.cleanup_user_data_directory(user_data_dir=self.user_data_dir)
            self.session = None
            self.page = None

    def update_credentials(self, username: str, password: str) -> None:
        old_username = self.username
        old_password = self.password

        credentials_changed = (old_username != username) or (old_password != password)
        if not credentials_changed:
            return

        self.user_info = None
        self.username = username
        self.password = password

    def update_configs(
        self,
        is_running: Optional[bool] = None,
        event_config: Optional[EventConfig] = None,
        special_jackpot: Optional[int] = None,
        mini_jackpot: Optional[int] = None,
        spin_action: Optional[int] = None,
        target_special_jackpot: Optional[int] = None,
        user_panel_callback: Optional[Callable[[Optional[UserReponse]], None]] = None,
        message_callback: Optional[Callable[[str, str], None]] = None,
        special_jackpot_callback: Optional[Callable[[int], None]] = None,
    ) -> None:
        self.is_running = is_running or self.is_running
        self.event_config = event_config or self.event_config
        self.special_jackpot = special_jackpot or self.special_jackpot
        self.mini_jackpot = mini_jackpot or self.mini_jackpot
        self.spin_action = spin_action or self.spin_action
        self.target_special_jackpot = target_special_jackpot or self.target_special_jackpot
        self.user_panel_callback = user_panel_callback or self.user_panel_callback
        self.message_callback = message_callback or self.message_callback

        if special_jackpot_callback:
            self.special_jackpot_callback = special_jackpot_callback

    async def _setup_browser(self) -> Tuple[BrowserSession, Page]:
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
            "--ignore-certificate-errors",
            "--no-sandbox",
        ]

        if PlatformManager.platform() == "windows":
            extra_chromium_args.extend(
                [
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

        # Force Chrome usage for better compatibility with browser automation
        if not (chrome_path := PlatformManager.get_chrome_executable_path()):
            msg = "❌ Chrome/Chromium not found. Please install Chrome or Chromium."
            logger.error(msg)
            raise Exception(msg)

        logger.info(f"🌐 Using Chrome browser: {chrome_path}")

        # Try multiple attempts with different profile strategies
        for attempt in range(3):
            try:
                user_data_dir = None if attempt > 0 else PlatformManager.get_user_data_directory()
                # Store for cleanup later
                if user_data_dir:
                    self.user_data_dir = user_data_dir

                browser_profile = BrowserProfile(
                    stealth=True,
                    ignore_https_errors=True,
                    timeout=60000 * 3,
                    default_timeout=60000 * 3,
                    default_navigation_timeout=60000 * 3,
                    args=extra_chromium_args,
                    viewport={"width": 1920, "height": 1080},
                    user_data_dir=user_data_dir,
                    executable_path=chrome_path,
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                )

                browser_session = BrowserSession(browser_profile=browser_profile)
                await asyncio.wait_for(browser_session.start(), timeout=60000 * 3)
                page = await browser_session.get_current_page()

                logger.success("✅ Browser context setup completed successfully")
                return browser_session, page

            except asyncio.TimeoutError:
                logger.warning(f"⚠️ Browser startup timeout on attempt {attempt + 1}/3")
                if attempt > 1:
                    logger.error("❌ Browser startup failed after 3 attempts")
                    raise

                await asyncio.sleep(2)  # Wait before retry
                continue

            except Exception as e:
                logger.warning(f"⚠️ Browser setup failed on attempt {attempt + 1}/3: {e}")
                if attempt > 1:
                    logger.error("❌ Browser setup failed after 3 attempts")
                    raise

                await asyncio.sleep(2)  # Wait before retry
                continue

        # This should never be reached due to the raise statements above
        msg = "Failed to setup browser context after all attempts"
        raise Exception(msg)

    async def _get_user_info(self) -> None:
        self.cookies = await self._extract_cookies()
        self.headers = RequestManager.headers(cookies=self.cookies, base_url=self.event_config.base_url)

        async with aiohttp.ClientSession(
            cookies=self.cookies,
            headers=self.headers,
            connector=RequestManager.connector(),
        ) as session:
            logger.info("📡 Fetching user information from API...")
            try:
                async with session.get(f"{self.event_config.base_url}/{self.event_config.user_endpoint}") as response:
                    if not response.ok:
                        msg = f"API request failed with status: {response.status}"
                        should_execute_callback(self.message_callback, "error", msg)
                        return

                    self.user_info = UserReponse.model_validate(await response.json())
                    if not self.user_info.payload.user:
                        msg = "User information not found"
                        should_execute_callback(self.message_callback, "error", msg)
                        return

                    should_execute_callback(self.message_callback, "success", "Get user info successfully")
                    should_execute_callback(self.user_panel_callback, self.user_info)

            except Exception as e:
                should_execute_callback(self.message_callback, "error", f"Failed to get user info: {e}")

    async def _extract_cookies(self) -> Dict[str, str]:
        cookies: Dict[str, str] = {}
        if self.page:
            try:
                logger.info("🍪 Extracting cookies from browser session...")
                for cookie in await self.page.context.cookies():
                    domain = cookie.get("domain", "")
                    if not domain:
                        continue

                    name, value = cookie.get("name", ""), cookie.get("value", "")
                    if not name or not value:
                        continue

                    cookies[name] = value

                logger.success(f"🍪 Successfully extracted {len(cookies)} cookies")

            except Exception as e:
                logger.error(f"❌ Failed to extract cookies: {e}")

        return cookies
