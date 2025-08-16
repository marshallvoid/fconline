from typing import Self

from browser_use.browser.types import Page
from loguru import logger

from src.core.event_config import EventConfig
from src.core.websocket_handler import WebsocketHandler


class LoginHandler:
    page: Page
    event_config: EventConfig
    username: str
    password: str

    @classmethod
    def setup(cls, page: Page, event_config: EventConfig, username: str, password: str) -> type[Self]:
        cls.page = page
        cls.event_config = event_config
        cls.username = username
        cls.password = password

        return cls

    @classmethod
    async def run(cls) -> None:
        logger.info("🔍 Checking login status...")

        if await cls._is_logged_in():
            return

        logger.info("🔐 User not logged in, attempting login...")
        if await cls._perform_login():
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
                logger.info("🔍 User is already logged in")
                WebsocketHandler.is_logged_in = True
                return True

            login_btn = await cls.page.query_selector(selector=cls.event_config.login_btn_selector)
            if login_btn:
                logger.info("🔍 User is not logged in")
                return False

            logger.warning("⚠️ Unable to determine login status")
            return False

        except Exception as error:
            logger.warning(f"⚠️ Error checking login status: {error}")
            return False

    @classmethod
    async def _perform_login(cls) -> bool:
        try:
            logger.info("🔐 Starting login process...")

            login_btn = await cls.page.query_selector(selector=cls.event_config.login_btn_selector)
            if not login_btn:
                logger.warning("⚠️ Login button not found")
                return False

            logger.info("🔐 Clicking login button...")
            await login_btn.click()
            await cls.page.wait_for_load_state(state="networkidle")

            username_input = await cls.page.query_selector(selector=cls.event_config.username_input_selector)
            if not username_input:
                logger.warning("⚠️ Username input field not found")
                return False
            await username_input.fill(value=cls.username)
            logger.info(f"🔐 Filled username: {cls.username}")

            password_input = await cls.page.query_selector(selector=cls.event_config.password_input_selector)
            if not password_input:
                logger.warning("⚠️ Password input field not found")
                return False
            await password_input.fill(value=cls.password)
            logger.info(f"🔐 Filled password: {cls.password}")

            submit_btn = await cls.page.query_selector(selector=cls.event_config.submit_btn_selector)
            if not submit_btn:
                logger.warning("⚠️ Submit button not found")
                return False
            await submit_btn.click()

            try:
                logger.info("⏳ Waiting for login response...")
                await cls.page.wait_for_function(
                    (
                        f"window.location.href.includes('{cls.event_config.base_url}') || "
                        "document.querySelector('.captcha') || document.querySelector('.error')"
                    ),
                )

                if cls.event_config.base_url in cls.page.url:
                    logger.success("🔐 Login completed successfully - redirected to main page")
                    WebsocketHandler.is_logged_in = True
                    return True

                logger.info("⏳ Waiting for captcha resolution and redirect...")
                await cls.page.wait_for_function(f"window.location.href.includes('{cls.event_config.base_url}')")
                logger.success("🔐 Login completed successfully after captcha resolution")
                WebsocketHandler.is_logged_in = True
                return True

            except Exception as error:
                logger.warning(f"⚠️ Login timeout or failed: {error}")
                return False

        except Exception as error:
            logger.warning(f"⚠️ Error performing login: {error}")
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
