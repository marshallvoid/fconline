from typing import Any, Dict, Optional

import aiohttp
from browser_use.browser.types import Page
from loguru import logger

from src.core.managers.request import request_mgr
from src.schemas.enums.message_tag import MessageTag
from src.schemas.spin_response import SpinResponse
from src.schemas.user_response import UserReponse
from src.utils.contants import EventConfig
from src.utils.types import callback as cb


class FCOnlineClient:
    def __init__(
        self,
        event_config: EventConfig,
        page: Page,
        cookies: Dict[str, str],
        headers: Dict[str, str],
        on_add_message: cb.OnAddMessageCallback,
    ) -> None:
        self._page = page
        self._cookies = cookies
        self._headers = headers

        self._on_add_message = on_add_message

        self._user_api = f"{event_config.base_url}/{event_config.user_endpoint}"
        self._spin_api = f"{event_config.base_url}/{event_config.spin_endpoint}"

    async def lookup(self, silent: bool = False) -> Optional[UserReponse]:
        try:
            async with aiohttp.ClientSession(
                cookies=self._cookies,
                headers=self._headers,
                connector=request_mgr.connector(),
            ) as session:
                async with session.get(self._user_api) as response:
                    if not response.ok:
                        message = f"User API request failed with status: {response.status}"
                        logger.error(f"{message} - {await response.text(encoding='utf-8')}")
                        if not silent:
                            self._on_add_message(tag=MessageTag.ERROR, message=message)
                        return None

                    user_response = UserReponse.model_validate(await response.json())
                    if not user_response.is_successful or user_response.payload.error_code:
                        message = f"Lookup user info failed: {user_response.payload.error_code or 'Unknown error'}"
                        if not silent:
                            self._on_add_message(tag=MessageTag.ERROR, message=message)
                        return None

                    if not silent:
                        self._on_add_message(tag=MessageTag.SUCCESS, message="Lookup user info successfully")
                    return user_response

        except Exception as error:
            logger.exception(f"Failed to lookup user info: {error}")
            return None

    async def _perform_spin_request(
        self,
        session: aiohttp.ClientSession,
        payload: Dict[str, Any],
        is_free_spin: bool = False,
    ) -> Optional[SpinResponse]:
        """Perform a single spin request and return the response."""
        async with session.post(url=self._spin_api, json=payload) as response:
            if not response.ok:
                spin_type = "Free spin" if is_free_spin else "Spin"
                message = f"{spin_type} API request failed with status: {response.status}"
                logger.error(f"{message} - {await response.text(encoding='utf-8')}")
                self._on_add_message(tag=MessageTag.ERROR, message=message)
                return None

            spin_response = SpinResponse.model_validate(await response.json())

            # Return response even if it has error_code, let caller handle it
            return spin_response

    async def _try_free_spin(self, session: aiohttp.ClientSession, spin_type: int) -> Optional[SpinResponse]:
        """Try to use free spin if available and balance is not enough."""
        user_response = await self.lookup(silent=True)
        if not user_response or not user_response.payload.user:
            return None

        free_spin = user_response.payload.user.free_spin or 0
        # Map spin_type to required free_spin amount
        required_free_spin = {1: 1, 2: 10, 3: 50, 4: 100}.get(spin_type, 0)

        if free_spin < required_free_spin:
            message = "Balance and free spins are not enough to perform the spin."
            self._on_add_message(tag=MessageTag.ERROR, message=message)
            return None

        message = f"Balance not enough, using {free_spin} free spins..."
        self._on_add_message(tag=MessageTag.INFO, message=message)

        payload = {"spin_type": 0, "payment_type": spin_type, "free_spin_amount": free_spin}
        return await self._perform_spin_request(session=session, payload=payload, is_free_spin=True)

    async def spin(
        self,
        spin_type: int,
        payment_type: int = 1,
        extra_params: Dict[str, Any] = {},
    ) -> Optional[SpinResponse]:
        message = f"Spinning with type {spin_type} and payment type {payment_type}..."
        self._on_add_message(tag=MessageTag.INFO, message=message)

        try:
            async with aiohttp.ClientSession(
                cookies=self._cookies,
                headers=self._headers,
                connector=request_mgr.connector(),
            ) as session:
                payload = {"spin_type": spin_type, "payment_type": payment_type, **extra_params}

                spin_response = await self._perform_spin_request(session=session, payload=payload)
                if not spin_response:
                    return None

                # If balance not enough, try free spin
                if spin_response.error_code == "balance_not_enough":
                    free_spin_response = await self._try_free_spin(session=session, spin_type=spin_type)
                    if not free_spin_response:
                        return None

                    # Check if free spin was successful
                    if (
                        not free_spin_response.payload
                        or not free_spin_response.is_successful
                        or free_spin_response.error_code
                    ):
                        message = f"Free spin failed: {free_spin_response.error_code or 'Unknown error'}"
                        self._on_add_message(tag=MessageTag.ERROR, message=message)
                        return None

                    return free_spin_response

                # Check if normal spin was successful
                if not spin_response.payload or not spin_response.is_successful or spin_response.error_code:
                    message = f"Spin failed: {spin_response.error_code or 'Unknown error'}"
                    self._on_add_message(tag=MessageTag.ERROR, message=message)
                    return None

                return spin_response

        except Exception as error:
            logger.exception(f"Failed to spin: {error}")
            return None
