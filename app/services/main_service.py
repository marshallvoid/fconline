import asyncio
import time
from typing import Optional, Tuple

from browser_use import BrowserProfile, BrowserSession
from browser_use.browser.types import Page
from loguru import logger

from app.core.managers.file import file_mgr
from app.core.managers.platform import platform_mgr
from app.core.settings import settings
from app.infrastructure.clients.main_client import MainClient
from app.schemas.configs import Account
from app.schemas.enums.message_tag import MessageTag
from app.schemas.user_response import UserReponse
from app.services.handlers.login_handler import LoginHandler
from app.services.handlers.websocket_handler import WebsocketHandler
from app.utils.concurrency import run_in_thread
from app.utils.constants import EventConfig
from app.utils.helpers import get_browser_position
from app.utils.types.callback import (
    OnAccountWonCallback,
    OnAddMessageCallback,
    OnAddNotificationCallback,
    OnUpdateCurrentJackpotCallback,
    OnUpdateWinnerCallback,
)


class MainService:
    def __init__(
        self,
        # Browser configs
        is_running: bool,
        browser_index: int,
        screen_width: int,
        screen_height: int,
        # Account configs
        account: Account,
        auto_refresh: bool,
        event_config: EventConfig,
        # Callbacks
        on_add_message: OnAddMessageCallback,
        on_add_notification: OnAddNotificationCallback,
        on_update_current_jp: OnUpdateCurrentJackpotCallback,
        on_update_prize_winner: OnUpdateWinnerCallback,
        on_account_won: OnAccountWonCallback,
    ) -> None:
        # Browser configs
        self._is_running = is_running
        self._browser_index = browser_index
        self._screen_width = screen_width
        self._screen_height = screen_height

        # Account configs
        self._account = account
        self._auto_refresh = auto_refresh
        self._event_config = event_config

        # Callbacks
        self._on_add_message = on_add_message
        self._on_add_notification = on_add_notification
        self._on_update_current_jp = on_update_current_jp
        self._on_update_prize_winner = on_update_prize_winner
        self._on_account_won = on_account_won

        # Browser session and page
        self._session: Optional[BrowserSession] = None
        self._page: Optional[Page] = None

        # User data
        self._user_data_dir: Optional[str] = None
        self._user_info: Optional[UserReponse] = None

        # Auto refresh configuration
        self._refresh_interval = 60 * 60  # 60 minutes in seconds
        self._last_refresh_time: Optional[float] = None

    @property
    def page(self) -> Optional[Page]:
        return self._page

    @property
    def is_running(self) -> bool:
        return self._is_running

    @is_running.setter
    def is_running(self, value: bool) -> None:
        self._is_running = value

    async def run(self) -> None:
        try:
            # Initialize browser session and navigate to target URL
            self._session, self._page = await self._setup_browser()

            logger.info(f"Navigating to: {self._event_config.base_url}")
            await self._page.goto(url=self._event_config.base_url)
            await self._page.wait_for_load_state(state="networkidle")

            # Setup websocket handler
            logger.info("Setting up websocket handler...")
            self.websocket_handler = WebsocketHandler(main_service=self)
            self.websocket_handler.setup_websocket()

            # Setup login handler and ensure user is logged in
            logger.info("Setting up login handler and ensuring user is logged in...")
            login_handler = LoginHandler(main_service=self)
            await login_handler.ensure_logged_in()
            await self._page.wait_for_load_state(state="networkidle")

            # Setup API client and fetch user profile information
            logger.info("Setting up API client and fetching user profile information...")
            self.client = MainClient(main_service=self)
            self._user_info = await self.client.lookup()

            self._update_ui()

            # Connect websocket handler with API client and user info
            self.websocket_handler.user_info = self._user_info
            self.websocket_handler.main_client = self.client

            # Main monitoring loop - keep running until stopped
            self._last_refresh_time = time.time()
            while self._is_running:
                # Auto-refresh browser session periodically to avoid stale sessions (if enabled)
                if self._auto_refresh:
                    current_time = time.time()
                    if (current_time - self._last_refresh_time) >= self._refresh_interval:
                        message = "Refreshing browser session to maintain stability..."
                        self._on_add_message(tag=MessageTag.INFO, message=message)

                        run_in_thread(coro_func=self._page.reload)
                        self._last_refresh_time = current_time
                        await self._page.wait_for_load_state(state="networkidle")

                        # Ensure user is still logged in after refresh
                        await login_handler.ensure_logged_in()
                        await self._page.wait_for_load_state(state="networkidle")

                        # Re-fetch user info after refresh
                        self._user_info = await self.client.lookup()
                        self._update_ui()

                await asyncio.sleep(delay=0.1)

        except Exception as error:
            raise error

        finally:
            await self.close()
            self._on_add_message(tag=MessageTag.INFO, message=f"{settings.program_name} stopped", compact=True)

    async def close(self) -> None:
        logger.info("Closing browser context and cleaning up resources...")
        try:
            if self._page:
                await self._page.close()

            if self._session:
                await self._session.kill()

            logger.success("Browser resources cleaned up successfully")

        except Exception as error:
            logger.exception(f"Failed to clean up browser resource: {error}")

        finally:
            file_mgr.cleanup_data_directory(data_dir=self._user_data_dir)
            self._user_data_dir = None
            self._session = None
            self._page = None

    def _update_ui(self) -> None:
        # Update ultimate prize winner display
        if self._user_info and (jackpot_billboard := self._user_info.payload.sjp_billboard):
            nickname = jackpot_billboard.nickname
            value = jackpot_billboard.value
            self._on_update_prize_winner(nickname=nickname, value=value, is_jackpot=True)

        # Update mini prize winner display
        if self._user_info and (mini_jackpot_billboard := self._user_info.payload.mjp_billboard):
            nickname = mini_jackpot_billboard.nickname
            value = mini_jackpot_billboard.value
            self._on_update_prize_winner(nickname=nickname, value=value)

    async def _setup_browser(self) -> Tuple[BrowserSession, Page]:
        logger.info("Setting up browser context...")

        # Chrome arguments to disable security features and optimize for automation
        extra_chromium_args = [
            "--enable-logging --v=1",  # enable Chrome debug logs
            "--disable-blink-features=AutomationControlled",  # stealth mode (hide automation)
            "--no-first-run",  # skip first run dialog
            "--no-default-browser-check",  # skip default browser check
            "--mute-audio",  # mute all sounds
            "--ignore-certificate-errors",  # ignore SSL certificate errors
            "--disable-infobars",  # hide "Chrome is being controlled" bar
            "--disable-gpu",  # disable GPU (reduce resource usage)
            "--disable-software-rasterizer",  # disable software GPU fallback
            # Performance optimizations for multiple browsers:
            "--disable-background-timer-throttling",  # do not throttle JS timers in background
            "--disable-renderer-backgrounding",  # keep rendering active even when unfocused
            "--disable-backgrounding-occluded-windows",  # keep rendering for covered/hidden windows
            "--disable-extensions",  # disable all extensions (save memory)
            "--disable-sync",  # disable Chrome account sync
            "--disable-translate",  # disable built-in Google Translate
            "--password-store=basic",  # use basic password store (avoid conflicts)
        ]

        # Ensure Chrome is available for consistent automation behavior
        if not (chrome_path := platform_mgr.get_chrome_executable_path()):
            msg = "Chrome/Chromium not found. Please install Chrome or Chromium."
            raise Exception(msg)

        # Retry mechanism with different profile strategies for reliability
        for attempt in range(3):
            try:
                # Use persistent profile on first attempt, temporary on retries
                user_data_dir = None if attempt > 0 else file_mgr.get_data_directory()
                # Store for cleanup later
                if user_data_dir:
                    self._user_data_dir = user_data_dir

                # Configure browser profile with stealth settings and timeouts
                x, y, width, height = get_browser_position(
                    browser_index=self._browser_index,
                    screen_width=self._screen_width,
                    screen_height=self._screen_height,
                )
                browser_profile = BrowserProfile(
                    stealth=True,
                    keep_alive=True,
                    ignore_https_errors=True,
                    timeout=60000 * 3,
                    default_timeout=60000 * 3,
                    default_navigation_timeout=60000 * 3,
                    args=extra_chromium_args,
                    user_data_dir=user_data_dir,
                    executable_path=chrome_path,
                    window_position={"width": x, "height": y},
                    window_size={"width": width, "height": height},
                )

                # Start browser session and get initial page
                browser_session = BrowserSession(browser_profile=browser_profile)
                await asyncio.wait_for(browser_session.start(), timeout=60000 * 3)
                page = await browser_session.get_current_page()

                logger.success("Browser context setup completed successfully")
                return browser_session, page

            except asyncio.TimeoutError as error:
                logger.exception(f"Browser startup timeout on attempt {attempt + 1}/3: {error}")
                await asyncio.sleep(2)  # Wait before retry
                continue

            except Exception as error:
                logger.exception(f"Browser setup failed on attempt {attempt + 1}/3: {error}")
                await asyncio.sleep(2)  # Wait before retry
                continue

        # This should never be reached due to the raise statements above
        msg = "Failed to setup browser context after all attempts"
        raise Exception(msg)
