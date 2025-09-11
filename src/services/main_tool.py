import asyncio
from typing import Optional, Tuple

from browser_use import BrowserProfile, BrowserSession
from browser_use.browser.types import Page
from loguru import logger

from src.core.configs import settings
from src.core.managers.file import file_mgr
from src.core.managers.platform import platform_mgr
from src.core.managers.request import request_mgr
from src.infrastructure.client import FCOnlineClient
from src.schemas.configs import Account
from src.schemas.enums.message_tag import MessageTag
from src.schemas.user_response import UserReponse
from src.services.login_handler import LoginHandler
from src.services.websocket_handler import WebsocketHandler
from src.utils import conc, hlp
from src.utils.contants import EventConfig
from src.utils.types import callback as cb


class MainTool:
    def __init__(
        self,
        is_running: bool,
        browser_index: int,
        screen_width: int,
        screen_height: int,
        req_width: int,
        req_height: int,
        event_config: EventConfig,
        account: Account,
        on_account_won: cb.OnAccountWonCallback,
        on_add_message: cb.OnAddMessageCallback,
        on_add_notification: cb.OnAddNotificationCallback,
        on_update_cur_jp: cb.OnUpdateCurrentJackpotCallback,
        on_update_prize_winner: cb.OnUpdateWinnerCallback,
        on_update_info_display: cb.OnUpdateUserInfoCallback,
    ) -> None:
        self._is_running = is_running
        self._browser_index = browser_index
        self._screen_width = screen_width
        self._screen_height = screen_height
        self._req_width = req_width
        self._req_height = req_height
        self._event_config = event_config
        self._account = account

        self._on_account_won = on_account_won
        self._on_add_message = on_add_message
        self._on_add_notification = on_add_notification
        self._on_update_cur_jp = on_update_cur_jp
        self._on_update_prize_winner = on_update_prize_winner
        self._on_update_info_display = on_update_info_display

        self._session: Optional[BrowserSession] = None
        self._page: Optional[Page] = None

        self._user_data_dir: Optional[str] = None
        self._user_info: Optional[UserReponse] = None

        self._client: Optional[FCOnlineClient] = None
        self._websocket_handler: Optional[WebsocketHandler] = None

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

            # Setup websocket handler for real-time jackpot monitoring
            self._websocket_handler = WebsocketHandler(
                page=self._page,
                event_config=self._event_config,
                account=self._account,
                on_account_won=self._on_account_won,
                on_add_message=self._on_add_message,
                on_add_notification=self._on_add_notification,
                on_update_cur_jp=self._on_update_cur_jp,
                on_update_prize_winner=self._on_update_prize_winner,
            )
            self._websocket_handler.setup_websocket()

            # Handle user authentication - check if already logged in or perform login
            login_handler = LoginHandler(
                page=self._page,
                event_config=self._event_config,
                account=self._account,
                websocket_handler=self._websocket_handler,
                on_add_message=self._on_add_message,
            )
            await login_handler.ensure_logged_in()

            await self._page.wait_for_load_state(state="networkidle")

            # Initialize API client and fetch user profile information
            self._client = FCOnlineClient(
                event_config=self._event_config,
                page=self._page,
                cookies=await request_mgr.get_cookies(page=self._page),
                headers=await request_mgr.get_headers(page=self._page, event_config=self._event_config),
                on_add_message=self._on_add_message,
            )
            self._user_info = await self._client.lookup()

            await self._check_first_spin(page=self._page)
            self._update_ui()

            # Connect websocket handler with API client and user info
            self._websocket_handler.fconline_client = self._client
            self._websocket_handler.user_info = self._user_info

            # Main monitoring loop - keep running until stopped
            while self._is_running:
                await asyncio.sleep(delay=0.1)

        except Exception as error:
            logger.exception(f"Error during execution: {error}")
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

    async def _check_first_spin(self, page: Page) -> None:
        if (
            not self._client
            or not self._user_info
            or not self._user_info.payload.user
            or self._user_info.payload.user.accumulation is None
            or self._user_info.payload.user.accumulation > 0
        ):
            return

        self._on_add_message(
            tag=MessageTag.INFO,
            message="First spin detected, performing initial spin to accumulate points...",
        )
        await self._client.spin(spin_type=1, extra_params=self._event_config.params)

        conc.run_in_thread(coro_func=page.reload)

    def _update_ui(self) -> None:
        # Update ultimate prize winner display
        if self._user_info and (jackpot_billboard := self._user_info.payload.jackpot_billboard):
            nickname = jackpot_billboard.nickname
            value = jackpot_billboard.value
            self._on_update_prize_winner(nickname=nickname, value=value, is_jackpot=True)

        # Update mini prize winner display
        if self._user_info and (mini_jackpot_billboard := self._user_info.payload.mini_jackpot_billboard):
            nickname = mini_jackpot_billboard.nickname
            value = mini_jackpot_billboard.value
            self._on_update_prize_winner(nickname=nickname, value=value)

        # Update UI with user info
        if self._user_info and (user := self._user_info.payload.user):
            self._on_update_info_display(username=self._account.username, user=user)

    async def _setup_browser(self) -> Tuple[BrowserSession, Page]:
        logger.info("Setting up browser context...")

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
        if platform_mgr.platform() == "windows":
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
                x, y, width, height = hlp.get_browser_position(
                    browser_index=self._browser_index,
                    screen_width=self._screen_width,
                    screen_height=self._screen_height,
                )
                browser_profile = BrowserProfile(
                    stealth=True,
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
