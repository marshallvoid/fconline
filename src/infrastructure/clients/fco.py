from typing import Any, Callable, Dict, Optional

import aiohttp
from browser_use.browser.types import Page
from loguru import logger

from src.core.managers.request_manager import RequestManager
from src.schemas.enums.message_tag import MessageTag
from src.schemas.spin_response import SpinResponse
from src.schemas.user_response import UserDetail, UserReponse
from src.utils import helpers as hp
from src.utils.contants import EventConfig


class FCOnlineClient:
    def __init__(
        self,
        event_config: EventConfig,
        page: Page,
        cookies: Dict[str, str],
        headers: Dict[str, str],
        username: str,
        on_add_message: Optional[Callable[[MessageTag, str, bool], None]],
        on_update_user_info: Optional[Callable[[str, UserDetail], None]],
    ) -> None:
        self._page = page
        self._cookies = cookies
        self._headers = headers
        self._username = username

        self._on_add_message = on_add_message
        self._on_update_user_info = on_update_user_info

        self._user_info: Optional[UserReponse] = None
        self._user_api = f"{event_config.base_url}/{event_config.user_endpoint}"
        self._spin_api = f"{event_config.base_url}/{event_config.spin_endpoint}"

    async def lookup(self) -> Optional[UserReponse]:
        try:
            async with aiohttp.ClientSession(
                cookies=self._cookies,
                headers=self._headers,
                connector=await RequestManager.connector(),
            ) as session:
                async with session.get(self._user_api) as response:
                    if not response.ok:
                        message = f"User API request failed with status: {response.status}"
                        hp.ensure_execute(self._on_add_message, MessageTag.ERROR, message)

                        logger.error(f"{message} - {await response.text(encoding='utf-8')}")
                        return None

                    self._user_info = UserReponse.model_validate(await response.json())
                    if not self._user_info.is_successful or self._user_info.payload.error_code:
                        message = f"Lookup user info failed: {self._user_info.payload.error_code or 'Unknown error'}"
                        hp.ensure_execute(self._on_add_message, MessageTag.ERROR, message)
                        return None

                    hp.ensure_execute(self._on_add_message, MessageTag.SUCCESS, "Lookup user info successfully")
                    return self._user_info

        except Exception as error:
            logger.exception(f"Failed to lookup user info: {error}")
            return None

    async def spin(self, spin_type: int, payment_type: int = 1, params: Dict[str, Any] = {}) -> None:
        try:
            async with aiohttp.ClientSession(
                cookies=self._cookies,
                headers=self._headers,
                connector=await RequestManager.connector(),
            ) as session:
                payload = {"spin_type": spin_type, "payment_type": payment_type, **params}

                async with session.post(url=self._spin_api, json=payload) as response:
                    if not response.ok:
                        message = f"Spin API request failed with status: {response.status}"
                        hp.ensure_execute(self._on_add_message, MessageTag.ERROR, message)

                        logger.error(f"{message} - {await response.text(encoding='utf-8')}")
                        return

                    spin_response = SpinResponse.model_validate(await response.json())
                    if not spin_response.payload or not spin_response.is_successful or spin_response.error_code:
                        message = f"Spin failed: {spin_response.error_code or 'Unknown error'}"
                        hp.ensure_execute(self._on_add_message, MessageTag.ERROR, message)
                        return

                    message = hp.format_results_block(results=spin_response.payload.spin_results)
                    hp.ensure_execute(self._on_add_message, MessageTag.REWARD, message)

        except Exception as error:
            logger.exception(f"Failed to spin: {error}")
