import asyncio
import contextlib

from browser_use.browser.types import Page
from loguru import logger

from src.schemas.configs import Account
from src.schemas.enums.message_tag import MessageTag
from src.services.websocket_handler import WebsocketHandler
from src.utils.contants import EventConfig
from src.utils.types.callbacks import OnAddMessageCallback


class LoginHandler:
    def __init__(
        self,
        page: Page,
        event_config: EventConfig,
        account: Account,
        websocket_handler: WebsocketHandler,
        on_add_message: OnAddMessageCallback,
    ) -> None:
        self._page = page
        self._event_config = event_config
        self._account = account

        self._websocket_handler = websocket_handler
        self._on_add_message = on_add_message

    async def ensure_logged_in(self) -> None:
        self._on_add_message(tag=MessageTag.INFO, message="Checking login status")

        # Check if user is already authenticated
        if await self._detect_login_status():
            self._on_add_message(tag=MessageTag.SUCCESS, message="Already logged in")
            self._websocket_handler.is_logged_in = True
            return

        # Perform login if not already authenticated
        self._on_add_message(tag=MessageTag.WARNING, message="Not logged in → performing login")
        if not await self._perform_login():
            msg = "Login failed! Exiting..."
            raise Exception(msg)

        # Update websocket handler and ensure correct URL after login
        self._websocket_handler.is_logged_in = True
        await self._ensure_base_url()
        self._on_add_message(tag=MessageTag.SUCCESS, message="Login completed successfully")

    async def _detect_login_status(self) -> bool:
        # If logout button is visible, user is logged in
        if await self._is_visible(selector=self._event_config.logout_btn_selector):
            return True

        # If login button is visible, user is not logged in
        if await self._is_visible(selector=self._event_config.login_btn_selector):
            return False

        # If neither button is visible, something is wrong with the page
        msg = "Login failed! Exiting..."
        raise Exception(msg)

    async def _perform_login(self) -> bool:
        try:
            # Open login form
            if not await self._click_if_present(self._event_config.login_btn_selector):
                self._on_add_message(tag=MessageTag.ERROR, message="Login button not found")
                return False
            await self._page.wait_for_load_state("networkidle")

            # Fill username
            user_base_loc = self._page.locator(self._event_config.username_input_selector)
            if await user_base_loc.count() == 0:
                self._on_add_message(tag=MessageTag.ERROR, message="Username input field not found")
                return False
            user_loc = user_base_loc.first
            await user_loc.fill(self._account.username)

            # Fill password
            pass_base_loc = self._page.locator(self._event_config.password_input_selector)
            if await pass_base_loc.count() == 0:
                self._on_add_message(tag=MessageTag.ERROR, message="Password input field not found")
                return False
            pass_loc = pass_base_loc.first
            await pass_loc.fill(self._account.password)

            # Submit
            submit_base_loc = self._page.locator(self._event_config.submit_btn_selector)
            if await submit_base_loc.count() == 0:
                self._on_add_message(tag=MessageTag.ERROR, message="Submit button not found")
                return False
            submit_loc = submit_base_loc.first
            await submit_loc.click()

            base = self._event_config.base_url
            while True:
                if base in self._page.url:
                    return True

                if self._page.is_closed():
                    self._on_add_message(tag=MessageTag.ERROR, message="Page closed during login")
                    return False

                await asyncio.sleep(0.5)

        except Exception as error:
            self._on_add_message(tag=MessageTag.ERROR, message=f"Error performing login: {error}")
            return False

    async def _ensure_base_url(self) -> None:
        try:
            base = self._event_config.base_url
            if base not in self._page.url:
                logger.warning(f"Unexpected URL after login: {self._page.url}")
                logger.info(f"Redirecting to: {base}")
                await self._page.goto(base)
                await self._page.wait_for_load_state("networkidle")

        except Exception as error:
            logger.warning(f"Error redirecting to base URL: {error}")

    async def _is_visible(self, selector: str) -> bool:
        with contextlib.suppress(Exception):
            loc = self._page.locator(selector).first
            return await loc.is_visible()

        return False

    async def _click_if_present(self, selector: str) -> bool:
        with contextlib.suppress(Exception):
            base_loc = self._page.locator(selector)
            if await base_loc.count() > 0:
                loc = base_loc.first
                await loc.click()
                return True

        return False
