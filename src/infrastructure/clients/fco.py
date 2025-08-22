from typing import Any, Callable, Dict, Optional

import aiohttp
from browser_use.browser.types import Page
from loguru import logger

from src.schemas.enums.message_tag import MessageTag
from src.schemas.reload_response import ReloadResponse
from src.schemas.spin_response import SpinResponse
from src.schemas.user_response import UserDetail, UserReponse
from src.utils import helpers as hp
from src.utils.contants import EventConfig
from src.utils.requests import RequestManager


class FCOnlineClient:
    def __init__(
        self,
        page: Page,
        event_config: EventConfig,
        username: str,
        on_add_message: Optional[Callable[[MessageTag, str], None]],
        on_update_user_info: Optional[Callable[[str, UserDetail], None]],
    ) -> None:
        self._page = page
        self._event_config = event_config
        self._username = username

        self._on_add_message = on_add_message
        self._on_update_user_info = on_update_user_info

        # HTTP request configuration extracted from browser session
        self._cookies: Dict[str, str] = {}
        self._headers: Dict[str, str] = {}
        self._user_info: Optional[UserReponse] = None

        self._user_api = f"{self._event_config.base_url}/{self._event_config.user_endpoint}"
        self._spin_api = f"{self._event_config.base_url}/{self._event_config.spin_endpoint}"
        self._reload_api = f"{self._event_config.base_url}/{self._event_config.reload_endpoint}"

    @property
    def cookies(self) -> Dict[str, str]:
        return self._cookies

    @property
    def headers(self) -> Dict[str, str]:
        return self._headers

    async def prepare_resources(self) -> None:
        self._cookies = await self._build_cookies()
        self._headers = self._build_headers()

    async def lookup(self, username: str) -> Optional[UserReponse]:
        try:
            async with aiohttp.ClientSession(
                cookies=self._cookies,
                headers=self._headers,
                connector=RequestManager.connector(),
            ) as session:
                # Make API request to get user information
                async with session.get(self._user_api) as response:
                    if not response.ok:
                        hp.maybe_callback(
                            self._on_add_message,
                            MessageTag.ERROR,
                            f"User API request failed with status: {response.status} for user '{username}'",
                        )
                        return None

                    # Parse and validate API response
                    user_response = UserReponse.model_validate(await response.json())
                    if not user_response.is_successful or user_response.payload.error_code:
                        hp.maybe_callback(
                            self._on_add_message,
                            MessageTag.ERROR,
                            f"Get user info failed: {user_response.payload.error_code or 'Unknown error'}",
                        )
                        return None

                    self._user_info = user_response
                    hp.maybe_callback(
                        self._on_add_message,
                        MessageTag.SUCCESS,
                        f"Get user info successfully for user '{username}'",
                    )

                    return user_response

        except Exception as e:
            hp.maybe_callback(self._on_add_message, MessageTag.ERROR, f"Failed to get user info: {e}")
            return None

    async def reload_balance(self) -> None:
        try:
            async with aiohttp.ClientSession(
                cookies=self._cookies,
                headers=self._headers,
                connector=RequestManager.connector(),
            ) as session:
                async with session.post(url=self._reload_api) as response:
                    if not response.ok:
                        hp.maybe_callback(
                            self._on_add_message,
                            MessageTag.ERROR,
                            f"Reload balance API request failed with status: {response.status}",
                        )
                        return

                    reload_response = ReloadResponse.model_validate(await response.json())
                    if not reload_response.payload or not reload_response.is_successful or reload_response.error_code:
                        hp.maybe_callback(
                            self._on_add_message,
                            MessageTag.ERROR,
                            f"Reload balance failed: {reload_response.error_code or 'Unknown error'}",
                        )
                        return

                    hp.maybe_callback(
                        self._on_add_message,
                        MessageTag.SUCCESS,
                        f"Reload balance successfully for user '{self._username}'",
                    )

                    if self._user_info and (user_detail := self._user_info.payload.user):
                        user_detail.fc = reload_response.payload.fc
                        user_detail.mc = reload_response.payload.mc

                        hp.maybe_callback(self._on_update_user_info, self._username, user_detail)

        except Exception as e:
            hp.maybe_callback(self._on_add_message, MessageTag.ERROR, f"Failed to reload balance: {e}")

    async def spin(self, spin_type: int, payment_type: int = 1, params: Dict[str, Any] = {}) -> None:
        try:
            async with aiohttp.ClientSession(
                cookies=self._cookies,
                headers=self._headers,
                connector=RequestManager.connector(),
            ) as session:
                # Prepare spin request payload
                payload = {"spin_type": spin_type, "payment_type": payment_type, **params}

                # Execute spin API call
                async with session.post(url=self._spin_api, json=payload) as response:
                    if not response.ok:
                        hp.maybe_callback(
                            self._on_add_message,
                            MessageTag.ERROR,
                            f"Spin API request failed with status: {response.status}",
                        )
                        return

                    # Parse and validate spin response
                    spin_response = SpinResponse.model_validate(await response.json())
                    if not spin_response.payload or not spin_response.is_successful or spin_response.error_code:
                        hp.maybe_callback(
                            self._on_add_message,
                            MessageTag.ERROR,
                            f"Spin failed: {spin_response.error_code or 'Unknown error'}",
                        )
                        return

                    hp.maybe_callback(
                        self._on_add_message,
                        MessageTag.REWARD,
                        hp.format_spin_results_block(spin_results=spin_response.payload.spin_results),
                    )

        except Exception as e:
            hp.maybe_callback(self._on_add_message, MessageTag.ERROR, f"Failed to spin: {e}")

    async def _build_cookies(self) -> Dict[str, str]:
        try:
            cookies = await self._page.context.cookies()
            return {name: value for c in cookies if (name := c.get("name")) and (value := c.get("value"))}

        except Exception as e:
            logger.error(f"❌ Failed to extract cookies: {e}")
            return {}

    def _build_headers(self) -> Dict[str, str]:
        return {
            "x-csrftoken": self._cookies.get("csrftoken", ""),
            "Cookie": "; ".join([f"{name}={value}" for name, value in self._cookies.items()]),
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": self._event_config.base_url,
            "Origin": self._event_config.base_url,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "content-type": "application/json",
            "foo": "bar",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Priority": "u=0",
            "TE": "trailers",
        }
