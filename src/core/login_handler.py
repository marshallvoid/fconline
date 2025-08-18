from typing import Callable, Optional, Self

from browser_use.browser.types import Page
from loguru import logger

from src.core.event_config import EventConfig
from src.core.websocket_handler import WebsocketHandler
from src.schemas.enums.message_tag import MessageTag
from src.utils import methods as md


class LoginHandler:
    _page: Page

    _event_config: EventConfig
    _username: str
    _password: str

    _message_callback: Optional[Callable[[str, str], None]] = None

    @classmethod
    def setup(
        cls,
        page: Page,
        event_config: EventConfig,
        username: str,
        password: str,
        message_callback: Optional[Callable[[str, str], None]] = None,
    ) -> type[Self]:
        cls._page = page
        cls._event_config = event_config
        cls._username = username
        cls._password = password
        cls._message_callback = message_callback

        return cls

    @classmethod
    async def run(cls) -> None:
        logger.info("🔍 Checking login status...")

        if await cls._is_logged_in():
            logger.info("🔍 User is already logged in")
            WebsocketHandler.is_logged_in = True
            return

        if await cls._perform_login():
            md.should_execute_callback(cls._message_callback, MessageTag.SUCCESS.name, "Login completed successfully")
            WebsocketHandler.is_logged_in = True
            await cls._page.wait_for_load_state(state="networkidle")
            await cls._redirect_to_base_url()
            return

        msg = "Login failed! Exiting..."
        raise Exception(msg)

    @classmethod
    async def _is_logged_in(cls) -> bool:
        try:
            logout_btn = await cls._page.query_selector(selector=cls._event_config.logout_btn_selector)
            if logout_btn:
                return True

            login_btn = await cls._page.query_selector(selector=cls._event_config.login_btn_selector)
            if login_btn:
                return False

            md.should_execute_callback(
                cls._message_callback,
                MessageTag.WARNING.name,
                "Unable to determine login status",
            )
            return False

        except Exception as error:
            md.should_execute_callback(
                cls._message_callback,
                MessageTag.ERROR.name,
                f"Error checking login status: {error}",
            )
            return False

    @classmethod
    async def _perform_login(cls) -> bool:
        logger.info("🔐 User not logged in, attempting login...")
        try:
            login_btn = await cls._page.query_selector(selector=cls._event_config.login_btn_selector)
            if not login_btn:
                md.should_execute_callback(cls._message_callback, MessageTag.ERROR.name, "Login button not found")
                return False

            await login_btn.click()
            await cls._page.wait_for_load_state(state="networkidle")

            username_input = await cls._page.query_selector(selector=cls._event_config.username_input_selector)
            if not username_input:
                md.should_execute_callback(
                    cls._message_callback,
                    MessageTag.ERROR.name,
                    "Username input field not found",
                )
                return False

            await username_input.fill(value=cls._username)

            password_input = await cls._page.query_selector(selector=cls._event_config.password_input_selector)
            if not password_input:
                md.should_execute_callback(
                    cls._message_callback,
                    MessageTag.ERROR.name,
                    "Password input field not found",
                )
                return False

            await password_input.fill(value=cls._password)

            submit_btn = await cls._page.query_selector(selector=cls._event_config.submit_btn_selector)
            if not submit_btn:
                md.should_execute_callback(cls._message_callback, MessageTag.ERROR.name, "Submit button not found")
                return False

            await submit_btn.click()

            try:
                await cls._page.wait_for_function(
                    (
                        f"window.location.href.includes('{cls._event_config.base_url}') || "
                        "document.querySelector('.captcha') || document.querySelector('.error')"
                    ),
                )

                if cls._event_config.base_url in cls._page.url:
                    return True

                await cls._page.wait_for_function(f"window.location.href.includes('{cls._event_config.base_url}')")
                return True

            except Exception as error:
                md.should_execute_callback(cls._message_callback, MessageTag.ERROR.name, f"Login failed: {error}")
                return False

        except Exception as error:
            md.should_execute_callback(cls._message_callback, MessageTag.ERROR.name, f"Error performing login: {error}")
            return False

    @classmethod
    async def _redirect_to_base_url(cls) -> None:
        try:
            if cls._event_config.base_url not in cls._page.url:
                logger.warning(f"⚠️ Redirected to unexpected URL: {cls._page.url}")
                logger.info(f"🔄 Redirecting to: {cls._event_config.base_url}")
                await cls._page.goto(url=cls._event_config.base_url)
                await cls._page.wait_for_load_state(state="networkidle")

        except Exception as error:
            logger.warning(f"⚠️ Error redirecting to base URL: {error}")
