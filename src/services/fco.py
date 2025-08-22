import asyncio
from typing import Callable, Optional, Tuple

from browser_use import BrowserProfile, BrowserSession
from browser_use.browser.types import Page
from loguru import logger

from src.infrastructure.clients.fco import FCOnlineClient
from src.schemas.enums.message_tag import MessageTag
from src.schemas.user_response import UserReponse
from src.services.login_handler import LoginHandler
from src.services.websocket_handler import WebsocketHandler
from src.utils import methods as md
from src.utils.contants import PROGRAM_NAME, EventConfig
from src.utils.platforms import PlatformManager


class MainTool:
    def __init__(
        self,
        event_config: EventConfig,
        username: str,
        password: str,
        spin_action: int = 1,
        target_special_jackpot: int = 19000,
    ) -> None:
        self._event_config = event_config
        self._username = username
        self._password = password
        self._spin_action = spin_action
        self._target_special_jackpot = target_special_jackpot

        # Runtime state management
        self._screen_width: int = 0
        self._screen_height: int = 0
        self._req_width: int = 0
        self._req_height: int = 0
        self._is_running: bool = False
        self._current_jackpot: int = 0

        # Callback functions for UI updates and notifications
        self._on_account_won: Optional[Callable[[str], None]] = None
        self._on_add_message: Optional[Callable[[MessageTag, str], None]] = None
        self._on_add_notification: Optional[Callable[[str, str], None]] = None
        self._on_update_current_jackpot: Optional[Callable[[int], None]] = None
        self._on_update_ultimate_prize_winner: Optional[Callable[[str, str], None]] = None
        self._on_update_mini_prize_winner: Optional[Callable[[str, str], None]] = None

        # Browser automation components
        self._session: Optional[BrowserSession] = None
        self._page: Optional[Page] = None
        self._user_data_dir: Optional[str] = None

        # User authentication and profile data
        self._user_info: Optional[UserReponse] = None

    async def run(self) -> None:
        try:
            # Initialize browser session and navigate to target URL
            self._session, self._page = await self._setup_browser()

            logger.info(f"🌐 Navigating to: {self._event_config.base_url}")
            await self._page.goto(url=self._event_config.base_url)
            await self._page.wait_for_load_state(state="networkidle")

            # Setup websocket handler for real-time jackpot monitoring
            websocket_handler = WebsocketHandler(
                page=self._page,
                event_config=self._event_config,
                username=self._username,
                spin_action=self._spin_action,
                current_jackpot=self._current_jackpot,
                target_special_jackpot=self._target_special_jackpot,
                on_account_won=self._on_account_won,
                on_add_message=self._on_add_message,
                on_add_notification=self._on_add_notification,
                on_update_current_jackpot=self._on_update_current_jackpot,
                on_update_ultimate_prize_winner=self._on_update_ultimate_prize_winner,
                on_update_mini_prize_winner=self._on_update_mini_prize_winner,
            )
            websocket_handler.setup_websocket()

            # Handle user authentication - check if already logged in or perform login
            login_handler = LoginHandler(
                page=self._page,
                event_config=self._event_config,
                username=self._username,
                password=self._password,
                on_add_message=self._on_add_message,
            )
            login_handler.websocket_handler = websocket_handler
            await login_handler.ensure_logged_in()

            await self._page.wait_for_load_state(state="networkidle")

            # Initialize API client and fetch user profile information
            fconline_client = FCOnlineClient(
                page=self._page,
                base_url=self._event_config.base_url,
                user_endpoint=self._event_config.user_endpoint,
                spin_endpoint=self._event_config.spin_endpoint,
                on_add_message=self._on_add_message,
                on_update_ultimate_prize_winner=self._on_update_ultimate_prize_winner,
                on_update_mini_prize_winner=self._on_update_mini_prize_winner,
            )
            await fconline_client.prepare_resources()
            self._user_info = await fconline_client.lookup(username=self._username)

            # Connect websocket handler with API client and user info
            websocket_handler.fconline_client = fconline_client
            websocket_handler.user_info = self._user_info

            # Main monitoring loop - keep running until stopped
            while self._is_running:
                await asyncio.sleep(delay=0.1)

        except Exception as e:
            logger.error(f"❌ Error during execution: {e}")
            raise e

        finally:
            await self.close()
            md.should_execute_callback(self._on_add_message, MessageTag.INFO, f"{PROGRAM_NAME} stopped")

    async def close(self) -> None:
        if not self._page or not self._session:
            return

        logger.info("🔒 Closing browser context and cleaning up resources...")
        try:
            await self._page.close()
            await self._session.kill()
            logger.success("✅ Browser resources cleaned up successfully")

        except Exception as e:
            logger.error(f"❌ Failed to clean up browser resource: {e}")

        finally:
            self._user_data_dir = PlatformManager.cleanup_user_data_directory(user_data_dir=self._user_data_dir)
            self._session = None
            self._page = None

    def update_configs(
        self,
        screen_width: Optional[int] = None,
        screen_height: Optional[int] = None,
        req_width: Optional[int] = None,
        req_height: Optional[int] = None,
        is_running: Optional[bool] = None,
        current_jackpot: Optional[int] = None,
        event_config: Optional[EventConfig] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        spin_action: Optional[int] = None,
        target_special_jackpot: Optional[int] = None,
        on_account_won: Optional[Callable[[str], None]] = None,
        on_add_message: Optional[Callable[[MessageTag, str], None]] = None,
        on_add_notification: Optional[Callable[[str, str], None]] = None,
        on_update_current_jackpot: Optional[Callable[[int], None]] = None,
        on_update_ultimate_prize_winner: Optional[Callable[[str, str], None]] = None,
        on_update_mini_prize_winner: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        self._screen_width = screen_width if screen_width is not None else self._screen_width
        self._screen_height = screen_height if screen_height is not None else self._screen_height
        self._req_width = req_width if req_width is not None else self._req_width
        self._req_height = req_height if req_height is not None else self._req_height

        self._is_running = is_running if is_running is not None else self._is_running
        self._current_jackpot = current_jackpot or self._current_jackpot

        self._event_config = event_config or self._event_config
        self._username = username or self._username
        self._password = password or self._password
        self._spin_action = spin_action or self._spin_action
        self._target_special_jackpot = target_special_jackpot or self._target_special_jackpot

        if on_account_won:
            self._on_account_won = on_account_won

        if on_add_message:
            self._on_add_message = on_add_message

        if on_add_notification:
            self._on_add_notification = on_add_notification

        if on_update_current_jackpot:
            self._on_update_current_jackpot = on_update_current_jackpot

        if on_update_ultimate_prize_winner:
            self._on_update_ultimate_prize_winner = on_update_ultimate_prize_winner

        if on_update_mini_prize_winner:
            self._on_update_mini_prize_winner = on_update_mini_prize_winner

    async def _setup_browser(self) -> Tuple[BrowserSession, Page]:
        logger.info("🌐 Setting up browser context...")

        # Chrome arguments to disable security features and optimize for automation
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
            "--ignore-certificate-errors",
            "--no-sandbox",
        ]

        # Add Windows-specific optimizations for better performance
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

        # Ensure Chrome is available for consistent automation behavior
        if not (chrome_path := PlatformManager.get_chrome_executable_path()):
            msg = "Chrome/Chromium not found. Please install Chrome or Chromium."
            raise Exception(msg)

        logger.info(f"🌐 Using Chrome browser: {chrome_path}")

        # Retry mechanism with different profile strategies for reliability
        for attempt in range(3):
            try:
                # Use persistent profile on first attempt, temporary on retries
                user_data_dir = None if attempt > 0 else PlatformManager.get_user_data_directory()
                # Store for cleanup later
                if user_data_dir:
                    self._user_data_dir = user_data_dir

                # Configure browser profile with stealth settings and timeouts
                browser_profile = BrowserProfile(
                    stealth=True,
                    ignore_https_errors=True,
                    timeout=60000 * 3,
                    default_timeout=60000 * 3,
                    default_navigation_timeout=60000 * 3,
                    args=extra_chromium_args,
                    user_data_dir=user_data_dir,
                    executable_path=chrome_path,
                    window_size={"width": self._screen_width - self._req_width, "height": self._req_height},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                )

                # Start browser session and get initial page
                browser_session = BrowserSession(browser_profile=browser_profile)
                await asyncio.wait_for(browser_session.start(), timeout=60000 * 3)
                page = await browser_session.get_current_page()

                logger.success("✅ Browser context setup completed successfully")
                return browser_session, page

            except asyncio.TimeoutError:
                logger.warning(f"⚠️ Browser startup timeout on attempt {attempt + 1}/3")
                await asyncio.sleep(2)  # Wait before retry
                continue

            except Exception as e:
                logger.warning(f"⚠️ Browser setup failed on attempt {attempt + 1}/3: {e}")
                await asyncio.sleep(2)  # Wait before retry
                continue

        # This should never be reached due to the raise statements above
        msg = "Failed to setup browser context after all attempts"
        raise Exception(msg)
