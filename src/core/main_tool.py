import asyncio
import ssl
from typing import Callable, Dict, Optional, Tuple

import aiohttp
from browser_use import BrowserProfile, BrowserSession
from browser_use.browser.types import Page
from loguru import logger

from src.core.event_config import EventConfig
from src.core.login_handler import LoginHandler
from src.core.websocket_handler import WebsocketHandler
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

        self.is_running: bool = False
        self.special_jackpot: int = 0
        self.mini_jackpot: int = 0

        self.user_panel_callback: Optional[Callable[[Optional[UserInfo]], None]] = None
        self.message_callback: Optional[Callable[[str, str], None]] = None
        self.special_jackpot_callback: Optional[Callable[[int], None]] = None

        self.session: Optional[BrowserSession] = None
        self.page: Optional[Page] = None
        self.user_data_dir: Optional[str] = None

        self.user_info: Optional[UserInfo] = None

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
            ).run()

            await self._fetch_user_info()

            while self.is_running:
                await asyncio.sleep(delay=1)

        except Exception as e:
            logger.error(f"❌ Unexpected error during execution: {e}")

        finally:
            await self.close()
            logger.info("🏁 FC Online automation tool stopped")

    async def close(self) -> None:
        if not self.session:
            return

        logger.info("🔒 Closing browser context and cleaning up resources...")
        try:
            await self.page.close()
            await self.session.close()
            logger.success("✅ Browser resources cleaned up successfully")

        except Exception as e:
            logger.error(f"❌ Failed to clean up browser resource: {e}")

        finally:
            self.session = None
            self.page = None

        # Clean up user data directory if it was created
        if self.user_data_dir:
            PlatformManager.cleanup_user_data_directory(self.user_data_dir)
            self.user_data_dir = None

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
        user_panel_callback: Optional[Callable[[Optional[UserInfo]], None]] = None,
        message_callback: Optional[Callable[[str, str], None]] = None,
        special_jackpot_callback: Optional[Callable[[int], None]] = None,
    ) -> None:
        self.is_running = is_running
        self.event_config = event_config or self.event_config
        self.special_jackpot = special_jackpot or self.special_jackpot
        self.mini_jackpot = mini_jackpot or self.mini_jackpot
        self.spin_action = spin_action or self.spin_action
        self.target_special_jackpot = target_special_jackpot or self.target_special_jackpot
        self.user_panel_callback = user_panel_callback or self.user_panel_callback
        self.message_callback = message_callback or self.message_callback
        self.special_jackpot_callback = special_jackpot_callback or self.special_jackpot_callback

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
        chrome_path = PlatformManager.get_chrome_executable_path()
        if not chrome_path:
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
                    timeout=30000,  # 30 second timeout
                    default_timeout=30000,  # 30 second default timeout
                    default_navigation_timeout=60000,  # 60 second navigation timeout
                    args=extra_chromium_args,
                    viewport={"width": 1920, "height": 1080},
                    user_data_dir=user_data_dir,
                    executable_path=chrome_path,
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                )

                browser_session = BrowserSession(browser_profile=browser_profile)
                await asyncio.wait_for(browser_session.start(), timeout=45.0)  # 45 second timeout for startup
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

    async def _fetch_user_info(self) -> None:
        cookies: Dict[str, str] = await self._extract_cookies()

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(
            cookies=cookies,
            headers={
                "x-csrftoken": cookies.get("csrftoken", ""),
                "Cookie": "; ".join([f"{name}={value}" for name, value in cookies.items()]),
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            },
            connector=connector,
        ) as session:
            try:
                logger.info("📡 Fetching user information from API...")

                async with session.get(self.event_config.api_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.user_info = UserInfo.model_validate(data)

                        if not self.user_info.payload.user:
                            msg = "❌ User information not found"
                            raise Exception(msg)

                        logger.success("✅ User information fetched successfully")

                        if self.user_panel_callback:
                            self.user_panel_callback(self.user_info)
                    else:
                        logger.warning(f"⚠️ API request failed with status: {response.status}")

            except Exception as e:
                logger.error(f"❌ Failed to fetch user info: {e}")

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
