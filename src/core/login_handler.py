from typing import Callable, Optional, Self

from browser_use.browser.types import Page
from loguru import logger

from src.core.event_config import EventConfig
from src.core.websocket_handler import WebsocketHandler
from src.utils.methods import should_execute_callback


class LoginHandler:
    page: Page
    event_config: EventConfig
    username: str
    password: str
    message_callback: Optional[Callable[[str, str], None]] = None

    @classmethod
    def setup(
        cls,
        page: Page,
        event_config: EventConfig,
        username: str,
        password: str,
        message_callback: Optional[Callable[[str, str], None]] = None,
    ) -> type[Self]:
        cls.page = page
        cls.event_config = event_config
        cls.username = username
        cls.password = password
        cls.message_callback = message_callback

        return cls

    @classmethod
    async def run(cls) -> None:
        logger.info("🔍 Checking login status...")

        if await cls._is_logged_in():
            logger.info("🔍 User is already logged in")
            WebsocketHandler.is_logged_in = True
            return

        if await cls._perform_login():
            should_execute_callback(cls.message_callback, "success", "Login completed successfully")
            WebsocketHandler.is_logged_in = True
            await cls.page.wait_for_load_state(state="networkidle")
            await cls._redirect_to_base_url()
            return

        msg = "Login failed! Exiting..."
        raise Exception(msg)

    @classmethod
    async def _is_logged_in(cls) -> bool:
        try:
            logout_btn = await cls.page.query_selector(selector=cls.event_config.logout_btn_selector)
            if logout_btn:
                return True

            login_btn = await cls.page.query_selector(selector=cls.event_config.login_btn_selector)
            if login_btn:
                return False

            should_execute_callback(cls.message_callback, "warning", "Unable to determine login status")
            return False

        except Exception as error:
            should_execute_callback(cls.message_callback, "error", f"Error checking login status: {error}")
            return False

    @classmethod
    async def _perform_login(cls) -> bool:
        logger.info("🔐 User not logged in, attempting login...")
        try:
            login_btn = await cls.page.query_selector(selector=cls.event_config.login_btn_selector)
            if not login_btn:
                should_execute_callback(cls.message_callback, "error", "Login button not found")
                return False

            await login_btn.click()
            await cls.page.wait_for_load_state(state="networkidle")

            username_input = await cls.page.query_selector(selector=cls.event_config.username_input_selector)
            if not username_input:
                should_execute_callback(cls.message_callback, "error", "Username input field not found")
                return False

            await username_input.fill(value=cls.username)

            password_input = await cls.page.query_selector(selector=cls.event_config.password_input_selector)
            if not password_input:
                should_execute_callback(cls.message_callback, "error", "Password input field not found")
                return False

            await password_input.fill(value=cls.password)

            submit_btn = await cls.page.query_selector(selector=cls.event_config.submit_btn_selector)
            if not submit_btn:
                should_execute_callback(cls.message_callback, "error", "Submit button not found")
                return False

            await submit_btn.click()

            try:
                await cls.page.wait_for_function(
                    (
                        f"window.location.href.includes('{cls.event_config.base_url}') || "
                        "document.querySelector('.captcha') || document.querySelector('.error')"
                    ),
                )

                if cls.event_config.base_url in cls.page.url:
                    return True

                await cls.page.wait_for_function(f"window.location.href.includes('{cls.event_config.base_url}')")
                return True

            except Exception as error:
                should_execute_callback(cls.message_callback, "error", f"Login failed: {error}")
                return False

        except Exception as error:
            should_execute_callback(cls.message_callback, "error", f"Error performing login: {error}")
            return False

    @classmethod
    async def _redirect_to_base_url(cls) -> None:
        try:
            if cls.event_config.base_url not in cls.page.url:
                logger.warning(f"⚠️ Redirected to unexpected URL: {cls.page.url}")
                logger.info(f"🔄 Redirecting to: {cls.event_config.base_url}")
                await cls.page.goto(url=cls.event_config.base_url)
                await cls.page.wait_for_load_state(state="networkidle")

        except Exception as error:
            logger.warning(f"⚠️ Error redirecting to base URL: {error}")
