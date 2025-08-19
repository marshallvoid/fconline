from typing import Callable, Dict, Optional

import aiohttp
from browser_use.browser.types import Page
from loguru import logger

from src.schemas.enums.message_tag import MessageTag
from src.schemas.spin_response import SpinResponse
from src.schemas.user_response import UserReponse
from src.utils import methods as md
from src.utils.requests import RequestManager


class FCOnlineClient:
    def __init__(
        self,
        page: Page,
        base_url: str,
        user_endpoint: str,
        spin_endpoint: str,
        add_message: Optional[Callable[[str, str], None]],
    ) -> None:
        self._page = page
        self._base_url = base_url
        self._user_endpoint = user_endpoint
        self._spin_endpoint = spin_endpoint
        self._add_message = add_message

        self._cookies: Dict[str, str] = {}
        self._headers: Dict[str, str] = {}

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
                async with session.get(f"{self._base_url}/{self._user_endpoint}") as response:
                    if not response.ok:
                        md.should_execute_callback(
                            self._add_message,
                            MessageTag.ERROR,
                            f"User API request failed with status: {response.status} for user '{username}'",
                        )
                        return None

                    user_response = UserReponse.model_validate(await response.json())
                    if not user_response.is_successful:
                        md.should_execute_callback(
                            self._add_message,
                            MessageTag.ERROR,
                            f"User '{username}' not found",
                        )
                        return None

                    md.should_execute_callback(
                        self._add_message,
                        MessageTag.SUCCESS,
                        f"Get user info successfully for user '{username}'",
                    )

                    return user_response

        except Exception as e:
            md.should_execute_callback(
                self._add_message,
                MessageTag.ERROR,
                f"Failed to get user info for user '{username}': {e}",
            )
            return None

    async def spin(self, spin_type: int, payment_type: int = 1) -> Optional[SpinResponse]:
        try:
            async with aiohttp.ClientSession(
                cookies=self._cookies,
                headers=self._headers,
                connector=RequestManager.connector(),
            ) as session:
                url = f"{self._base_url}/{self._spin_endpoint}"
                payload = {"spin_type": spin_type, "payment_type": payment_type}

                async with session.post(url=url, json=payload) as response:
                    if not response.ok:
                        md.should_execute_callback(
                            self._add_message,
                            MessageTag.ERROR,
                            f"Spin API request failed with status: {response.status}",
                        )
                        return None

                    spin_response = SpinResponse.model_validate(await response.json())
                    if not spin_response.payload or not spin_response.is_successful or spin_response.error_code:
                        md.should_execute_callback(
                            self._add_message,
                            MessageTag.ERROR,
                            f"Spin failed: {spin_response.error_code or 'Unknown error'}",
                        )
                        return None

                    md.should_execute_callback(
                        self._add_message,
                        MessageTag.REWARD,
                        md.format_spin_block_compact(
                            spin_results=spin_response.payload.spin_results,
                            jackpot_value=spin_response.payload.jackpot_value,
                        ),
                    )

                    return spin_response

        except Exception as e:
            md.should_execute_callback(self._add_message, MessageTag.ERROR, f"Failed to spin: {e}")
            return None

    async def _build_cookies(self) -> Dict[str, str]:
        try:
            cookies = await self._page.context.cookies()
            return {c["name"]: c["value"] for c in cookies if c.get("name") and c.get("value")}

        except Exception as e:
            logger.error(f"❌ Failed to extract cookies: {e}")
            return {}

    def _build_headers(self) -> Dict[str, str]:
        return {
            "x-csrftoken": self._cookies.get("csrftoken", ""),
            "Cookie": "; ".join([f"{name}={value}" for name, value in self._cookies.items()]),
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": self._base_url,
            "Origin": self._base_url,
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
