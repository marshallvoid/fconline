import asyncio
from typing import Callable, Optional

from browser_use.browser.types import Page
from loguru import logger

from src.schemas.enums.message_tag import MessageTag
from src.services.websocket_handler import WebsocketHandler
from src.utils import helpers as hp
from src.utils.contants import EventConfig


class LoginHandler:
    def __init__(
        self,
        page: Page,
        event_config: EventConfig,
        username: str,
        password: str,
        on_add_message: Optional[Callable[[MessageTag, str, bool], None]] = None,
    ) -> None:
        self._page = page

        self._event_config = event_config
        self._username = username
        self._password = password

        self._on_add_message = on_add_message

        # Reference to websocket handler to update login status
        self._websocket_handler: Optional[WebsocketHandler] = None

    @property
    def websocket_handler(self) -> Optional[WebsocketHandler]:
        return self._websocket_handler

    @websocket_handler.setter
    def websocket_handler(self, new_websocket_handler: WebsocketHandler) -> None:
        self._websocket_handler = new_websocket_handler

    async def ensure_logged_in(self) -> None:
        hp.maybe_execute(self._on_add_message, MessageTag.INFO, "Checking login status")

        # Check if user is already authenticated
        if await self._detect_login_status():
            hp.maybe_execute(self._on_add_message, MessageTag.SUCCESS, "Already logged in")

            if self._websocket_handler:
                self._websocket_handler.is_logged_in = True
            return

        # Perform login if not already authenticated
        hp.maybe_execute(self._on_add_message, MessageTag.WARNING, "Not logged in → performing login")
        if not await self._perform_login():
            msg = "Login failed! Exiting..."
            raise Exception(msg)

        # Update websocket handler and ensure correct URL after login
        if self._websocket_handler:
            self._websocket_handler.is_logged_in = True
        await self._ensure_base_url()
        hp.maybe_execute(self._on_add_message, MessageTag.SUCCESS, "Login completed successfully")

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
                hp.maybe_execute(self._on_add_message, MessageTag.ERROR, "Login button not found")
                return False
            await self._page.wait_for_load_state("networkidle")

            # Fill username
            user_loc = self._page.locator(self._event_config.username_input_selector).first
            if await user_loc.count() == 0:
                hp.maybe_execute(self._on_add_message, MessageTag.ERROR, "Username input field not found")
                return False
            await user_loc.fill(self._username)

            # Fill password
            pass_loc = self._page.locator(self._event_config.password_input_selector).first
            if await pass_loc.count() == 0:
                hp.maybe_execute(self._on_add_message, MessageTag.ERROR, "Password input field not found")
                return False
            await pass_loc.fill(self._password)

            # Submit
            submit_loc = self._page.locator(self._event_config.submit_btn_selector).first
            if await submit_loc.count() == 0:
                hp.maybe_execute(self._on_add_message, MessageTag.ERROR, "Submit button not found")
                return False
            await submit_loc.click()

            base = self._event_config.base_url
            while True:
                if base in self._page.url:
                    return True

                if self._page.is_closed():
                    hp.maybe_execute(self._on_add_message, MessageTag.ERROR, "Page closed during login")
                    return False

                await asyncio.sleep(0.5)

        except Exception as error:
            hp.maybe_execute(self._on_add_message, MessageTag.ERROR, f"Error performing login: {error}")
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
        try:
            loc = self._page.locator(selector).first
            return await loc.is_visible()

        except Exception:
            pass

        return False

    async def _click_if_present(self, selector: str) -> bool:
        try:
            loc = self._page.locator(selector).first
            if await loc.count() > 0:
                await loc.click()
                return True

        except Exception:
            pass

        return False
