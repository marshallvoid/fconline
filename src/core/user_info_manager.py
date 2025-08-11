from typing import Callable, Dict, Optional

import aiohttp
from fake_useragent import UserAgent
from loguru import logger
from playwright.async_api import Page

from src.models import UserInfo


class UserInfoManager:
    """Manages user information and cookie extraction for API authentication."""

    # API constants
    API_URL = "https://bilac.fconline.garena.vn/api/user/get"

    def __init__(self) -> None:
        """Initialize the user info manager."""
        self.user_info: Optional[UserInfo] = None
        self._cookies: Dict[str, str] = {}

        # Callbacks for GUI updates
        self.user_info_callback: Optional[Callable[[], None]] = None

    async def extract_cookies(self, page: Page) -> Dict[str, str]:
        """
        Extract cookies from browser for API authentication.

        Args:
            page: Playwright page instance

        Returns:
            Dictionary of cookie name-value pairs

        Raises:
            Exception: For cookie extraction errors
        """
        try:
            cookies = await page.context.cookies()
            cookie_dict = {}

            for cookie in cookies:
                domain = cookie.get("domain", "")
                if domain in ["bilac.fconline.garena.vn", ".fconline.garena.vn"]:
                    name = cookie.get("name", "")
                    value = cookie.get("value", "")
                    if name and value:
                        cookie_dict[name] = value

            logger.info(f"🍪 Extracted {len(cookie_dict)} cookies")
            self._cookies = cookie_dict
            return cookie_dict

        except Exception as e:
            logger.error(f"❌ Failed to extract cookies: {e}")
            return {}

    async def fetch_user_info(self, page: Optional[Page] = None) -> None:
        """
        Fetch user info from API using extracted cookies.

        Args:
            page: Optional page instance to extract cookies from

        Raises:
            Exception: For API request or parsing errors
        """
        if not self._cookies and page:
            await self.extract_cookies(page)

        if not self._cookies:
            logger.warning("⚠️ No cookies available for API request")
            return

        # Prefer a random desktop-like user agent to reduce detection
        user_agent = self._get_random_user_agent()

        async with aiohttp.ClientSession() as session:
            try:
                cookie_header = "; ".join([f"{name}={value}" for name, value in self._cookies.items()])

                headers = {
                    "Cookie": cookie_header,
                    "User-Agent": user_agent,
                }

                # Add CSRF token if available
                if "csrftoken" in self._cookies:
                    headers["X-CSRFToken"] = self._cookies["csrftoken"]

                async with session.get(self.API_URL, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.user_info = UserInfo.model_validate(data)

                        # Notify GUI about user info update
                        if self.user_info_callback:
                            self.user_info_callback()
                    else:
                        logger.error(f"❌ API request failed with status: {response.status}")

            except Exception as e:
                logger.error(f"❌ Failed to fetch user info: {e}")

    def _get_random_user_agent(self) -> str:
        """Return a random desktop User-Agent string with fallbacks."""
        fallback = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
        if UserAgent is None:
            return fallback

        try:
            ua = UserAgent()
            candidate = ua.random
            return candidate if isinstance(candidate, str) and candidate else fallback

        except Exception:
            return fallback

    def clear_cookies(self) -> None:
        """Clear stored cookies."""
        self._cookies = {}

    def set_user_info_callback(self, callback: Callable[[], None]) -> None:
        """
        Set callback for user info updates.

        Args:
            callback: Function to call when user info is updated
        """
        self.user_info_callback = callback

    @property
    def cookies(self) -> Dict[str, str]:
        """Get current cookies."""
        return self._cookies.copy()
