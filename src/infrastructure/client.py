from typing import Any, Dict, Optional

import aiohttp
from browser_use.browser.types import Page
from loguru import logger

from src.core.managers.request import RequestManager
from src.schemas.enums.message_tag import MessageTag
from src.schemas.spin_response import SpinResponse
from src.schemas.user_response import UserReponse
from src.utils.contants import EventConfig
from src.utils.types.callbacks import OnAddMessageCallback


class FCOnlineClient:
    def __init__(
        self,
        event_config: EventConfig,
        page: Page,
        cookies: Dict[str, str],
        headers: Dict[str, str],
        on_add_message: OnAddMessageCallback,
    ) -> None:
        self._page = page
        self._cookies = cookies
        self._headers = headers

        self._on_add_message = on_add_message

        self._user_api = f"{event_config.base_url}/{event_config.user_endpoint}"
        self._spin_api = f"{event_config.base_url}/{event_config.spin_endpoint}"

    async def lookup(self) -> Optional[UserReponse]:
        try:
            async with aiohttp.ClientSession(
                cookies=self._cookies,
                headers=self._headers,
                connector=RequestManager.connector(),
            ) as session:
                async with session.get(self._user_api) as response:
                    if not response.ok:
                        message = f"User API request failed with status: {response.status}"
                        logger.error(f"{message} - {await response.text(encoding='utf-8')}")
                        self._on_add_message(tag=MessageTag.ERROR, message=message)
                        return None

                    user_response = UserReponse.model_validate(await response.json())
                    if not user_response.is_successful or user_response.payload.error_code:
                        message = f"Lookup user info failed: {user_response.payload.error_code or 'Unknown error'}"
                        self._on_add_message(tag=MessageTag.ERROR, message=message)
                        return None

                    self._on_add_message(tag=MessageTag.SUCCESS, message="Lookup user info successfully")
                    return user_response

        except Exception as error:
            logger.exception(f"Failed to lookup user info: {error}")
            return None

    async def spin(
        self,
        spin_type: int,
        payment_type: int = 1,
        extra_params: Dict[str, Any] = {},
    ) -> Optional[SpinResponse]:
        try:
            async with aiohttp.ClientSession(
                cookies=self._cookies,
                headers=self._headers,
                connector=RequestManager.connector(),
            ) as session:
                payload = {"spin_type": spin_type, "payment_type": payment_type, **extra_params}

                async with session.post(url=self._spin_api, json=payload) as response:
                    if not response.ok:
                        message = f"Spin API request failed with status: {response.status}"
                        logger.error(f"{message} - {await response.text(encoding='utf-8')}")
                        self._on_add_message(tag=MessageTag.ERROR, message=message)
                        return None

                    spin_response = SpinResponse.model_validate(await response.json())
                    if not spin_response.payload or not spin_response.is_successful or spin_response.error_code:
                        message = f"Spin failed: {spin_response.error_code or 'Unknown error'}"
                        self._on_add_message(tag=MessageTag.ERROR, message=message)
                        return None

                    return spin_response

        except Exception as error:
            logger.exception(f"Failed to spin: {error}")
            return None
