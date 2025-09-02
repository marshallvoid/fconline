import asyncio
from typing import Callable, Optional, Tuple

from browser_use import BrowserProfile, BrowserSession
from browser_use.browser.types import Page
from loguru import logger

from src.infrastructure.clients.fco import FCOnlineClient
from src.schemas.enums.message_tag import MessageTag
from src.schemas.user_response import UserDetail, UserReponse
from src.services.fco.login_handler import LoginHandler
from src.services.fco.websocket_handler import WebsocketHandler
from src.services.files import FileManager
from src.services.platforms import PlatformManager
from src.services.requests import RequestManager
from src.utils import helpers as hp
from src.utils.contants import EVENT_CONFIGS_MAP, PROGRAM_NAME, EventConfig


class MainTool:
    def __init__(
        self,
        browser_index: int,
        screen_width: int,
        screen_height: int,
        req_width: int,
        req_height: int,
        event_config: EventConfig,
        username: str,
        password: str,
        spin_action: int = 1,
        target_special_jackpot: int = 19000,
    ) -> None:
        self._browser_index = browser_index
        self._screen_width = screen_width
        self._screen_height = screen_height
        self._req_width = req_width
        self._req_height = req_height
        self._event_config = event_config
        self._username = username
        self._password = password
        self._spin_action = spin_action
        self._target_special_jackpot = target_special_jackpot

        # Runtime state management
        self._is_running: bool = False
        self._current_jackpot: int = 0

        # Callback functions for UI updates and notifications
        self._on_account_won: Optional[Callable[[str], None]] = None
        self._on_add_message: Optional[Callable[[MessageTag, str, bool], None]] = None
        self._on_add_notification: Optional[Callable[[str, str], None]] = None
        self._on_update_current_jackpot: Optional[Callable[[int], None]] = None
        self._on_update_ultimate_prize_winner: Optional[Callable[[str, str], None]] = None
        self._on_update_mini_prize_winner: Optional[Callable[[str, str], None]] = None
        self._on_update_user_info: Optional[Callable[[str, UserDetail], None]] = None

        # Browser automation components
        self._session: Optional[BrowserSession] = None
        self._page: Optional[Page] = None
        self._user_agent: Optional[str] = None
        self._user_data_dir: Optional[str] = None

        # User authentication and profile data
        self._user_info: Optional[UserReponse] = None

        self._client: Optional[FCOnlineClient] = None
        self._websocket_handler: Optional[WebsocketHandler] = None

    @property
    def page(self) -> Optional[Page]:
        return self._page

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
                event_name=next(
                    (
                        event_name
                        for event_name, event_config in EVENT_CONFIGS_MAP.items()
                        if event_config.tab_attr_name == self._event_config.tab_attr_name
                    ),
                    "Unknown Event",
                ),
                event_config=self._event_config,
                username=self._username,
                spin_action=self._spin_action,
                target_special_jackpot=self._target_special_jackpot,
                current_jackpot=self._current_jackpot,
                on_account_won=self._on_account_won,
                on_add_message=self._on_add_message,
                on_add_notification=self._on_add_notification,
                on_update_current_jackpot=self._on_update_current_jackpot,
                on_update_ultimate_prize_winner=self._on_update_ultimate_prize_winner,
                on_update_mini_prize_winner=self._on_update_mini_prize_winner,
            )
            self._websocket_handler.setup_websocket()

            # Handle user authentication - check if already logged in or perform login
            login_handler = LoginHandler(
                page=self._page,
                event_config=self._event_config,
                username=self._username,
                password=self._password,
                on_add_message=self._on_add_message,
            )
            login_handler.websocket_handler = self._websocket_handler
            await login_handler.ensure_logged_in()

            await self._page.wait_for_load_state(state="networkidle")

            # Initialize API client and fetch user profile information
            self._client = FCOnlineClient(
                event_config=self._event_config,
                page=self._page,
                cookies=await RequestManager.get_cookies(page=self._page),
                headers=await RequestManager.get_headers(page=self._page, event_config=self._event_config),
                on_add_message=self._on_add_message,
                on_update_user_info=self._on_update_user_info,
            )
            self._user_info = await self._client.lookup()

            self._update_ui()

            # Connect websocket handler with API client and user info
            self._websocket_handler.fconline_client = self._client
            self._websocket_handler.user_info = self._user_info

            # Main monitoring loop - keep running until stopped
            while self._is_running:
                await asyncio.sleep(delay=0.1)

        except Exception as error:
            logger.error(f"Error during execution: {error}")
            raise error

        finally:
            await self.close()
            hp.maybe_execute(self._on_add_message, MessageTag.INFO, f"{PROGRAM_NAME} stopped", True)

    async def close(self) -> None:
        logger.info("Closing browser context and cleaning up resources...")
        try:
            if self._page:
                await self._page.close()

            if self._session:
                await self._session.kill()

            logger.success("Browser resources cleaned up successfully")

        except Exception as error:
            logger.error(f"Failed to clean up browser resource: {error}")

        finally:
            FileManager.cleanup_data_directory(data_dir=self._user_data_dir)
            self._user_data_dir = None
            self._session = None
            self._page = None

    def update_configs(
        self,
        is_running: Optional[bool] = None,
        current_jackpot: Optional[int] = None,
        event_config: Optional[EventConfig] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        spin_action: Optional[int] = None,
        target_special_jackpot: Optional[int] = None,
        on_account_won: Optional[Callable[[str], None]] = None,
        on_add_message: Optional[Callable[[MessageTag, str, bool], None]] = None,
        on_add_notification: Optional[Callable[[str, str], None]] = None,
        on_update_current_jackpot: Optional[Callable[[int], None]] = None,
        on_update_ultimate_prize_winner: Optional[Callable[[str, str], None]] = None,
        on_update_mini_prize_winner: Optional[Callable[[str, str], None]] = None,
        on_update_user_info: Optional[Callable[[str, UserDetail], None]] = None,
    ) -> None:
        self._is_running = is_running if is_running is not None else self._is_running
        self._current_jackpot = current_jackpot or self._current_jackpot

        self._event_config = event_config or self._event_config
        self._username = username or self._username
        self._password = password or self._password
        self._spin_action = spin_action or self._spin_action
        self._target_special_jackpot = target_special_jackpot or self._target_special_jackpot

        self._on_account_won = on_account_won or self._on_account_won
        self._on_add_message = on_add_message or self._on_add_message
        self._on_add_notification = on_add_notification or self._on_add_notification
        self._on_update_current_jackpot = on_update_current_jackpot or self._on_update_current_jackpot
        self._on_update_ultimate_prize_winner = on_update_ultimate_prize_winner or self._on_update_ultimate_prize_winner
        self._on_update_mini_prize_winner = on_update_mini_prize_winner or self._on_update_mini_prize_winner
        self._on_update_user_info = on_update_user_info or self._on_update_user_info

    def update_target_special_jackpot(self, new_target: int) -> None:
        self._target_special_jackpot = new_target
        if self._websocket_handler:
            self._websocket_handler.update_target_special_jackpot(new_target_special_jackpot=new_target)

    async def reload_balance(self) -> None:
        if not self._client:
            return

        await self._client.lookup(is_reload=True)

    def _update_ui(self) -> None:
        # Update ultimate prize winner display
        if self._user_info and (jackpot_billboard := self._user_info.payload.jackpot_billboard):
            nickname = jackpot_billboard.nickname
            value = jackpot_billboard.value
            hp.maybe_execute(self._on_update_ultimate_prize_winner, nickname, value)

        # Update mini prize winner display
        if self._user_info and (mini_jackpot_billboard := self._user_info.payload.mini_jackpot_billboard):
            nickname = mini_jackpot_billboard.nickname
            value = mini_jackpot_billboard.value
            hp.maybe_execute(self._on_update_mini_prize_winner, nickname, value)

        # Update UI with user info
        if self._user_info and (user := self._user_info.payload.user):
            hp.maybe_execute(self._on_update_user_info, self._username, user)

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

        # Ensure Chrome is available for consistent automation behavior
        if not (chrome_path := PlatformManager.get_chrome_executable_path()):
            msg = "Chrome/Chromium not found. Please install Chrome or Chromium."
            raise Exception(msg)

        # Retry mechanism with different profile strategies for reliability
        for attempt in range(3):
            try:
                # Use persistent profile on first attempt, temporary on retries
                user_data_dir = None if attempt > 0 else FileManager.get_data_directory()
                # Store for cleanup later
                if user_data_dir:
                    self._user_data_dir = user_data_dir

                # Configure browser profile with stealth settings and timeouts
                x, y, width, height = hp.get_browser_position(
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
                logger.error(f"Browser startup timeout on attempt {attempt + 1}/3: {error}")
                await asyncio.sleep(2)  # Wait before retry
                continue

            except Exception as error:
                logger.error(f"Browser setup failed on attempt {attempt + 1}/3: {error}")
                await asyncio.sleep(2)  # Wait before retry
                continue

        # This should never be reached due to the raise statements above
        msg = "Failed to setup browser context after all attempts"
        raise Exception(msg)
