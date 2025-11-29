# pyright: reportArgumentType=false
from typing import TYPE_CHECKING, Any, Dict, Optional

import aiohttp
from loguru import logger

from app.core.managers.request import request_mgr
from app.core.mixins.async_init import AsyncMixin
from app.schemas.enums.message_tag import MessageTag
from app.schemas.enums.payment_type import PaymentType
from app.schemas.spin_response import SpinResponse
from app.schemas.user_response import UserReponse

if TYPE_CHECKING:
    from app.services.main import MainService


class MainClient(AsyncMixin):
    async def __ainit__(self, main_service: "MainService") -> None:
        # Browser configs
        self._cookies = await request_mgr.get_cookies(page=main_service._page)
        self._headers = await request_mgr.get_headers(page=main_service._page, event_config=main_service._event_config)

        # Callbacks
        self._on_add_message = main_service._on_add_message

        # API endpoints
        self._user_api = f"{main_service._event_config.base_url}/{main_service._event_config.user_endpoint}"
        self._spin_api = f"{main_service._event_config.base_url}/{main_service._event_config.spin_endpoint}"

    @property
    def client_params(self) -> Dict[str, Any]:
        return {
            "cookies": self._cookies,
            "headers": self._headers,
            "connector": request_mgr.insecure_connector,
        }

    async def lookup(self, silent: bool = False) -> Optional[UserReponse]:
        try:
            async with aiohttp.ClientSession(**self.client_params) as session:
                async with session.get(url=self._user_api) as response:
                    if not response.ok:
                        message = f"User API request failed with status: {response.status}"
                        logger.error(f"{message} - {await response.text(encoding='utf-8')}")

                        if not silent:
                            self._on_add_message(tag=MessageTag.ERROR, message=message)

                        return None

                    user_response = UserReponse.model_validate(await response.json())
                    if user_response.invalid_response:
                        if not silent:
                            self._on_add_message(tag=MessageTag.ERROR, message=user_response.invalid_message)

                        return None

                    if not silent:
                        self._on_add_message(tag=MessageTag.SUCCESS, message="Lookup user info successfully")

                    return user_response

        except Exception as error:
            logger.exception(f"Failed to lookup user info: {error}")
            return None

    async def spin(
        self,
        spin_type: int,
        payment_type: PaymentType,
        params: Dict[str, Any] = {},
    ) -> Optional[SpinResponse]:
        payload = {"spin_type": spin_type, "payment_type": payment_type.value, **params}

        try:
            spin_response = await self._perform_spin(payload=payload)
            if not spin_response:
                return None

            # If balance not enough, try free spin
            if spin_response.error_code == "balance_not_enough":
                spin_response = await self._perform_spin(payload=payload, is_free_spin=True)
                if not spin_response:
                    return None

                # Check if free spin was successful
                if spin_response.invalid_response:
                    self._on_add_message(tag=MessageTag.ERROR, message=spin_response.invalid_message)
                    return None

                return spin_response

            # Check if normal spin was successful
            if spin_response.invalid_response:
                self._on_add_message(tag=MessageTag.ERROR, message=spin_response.invalid_message)
                return None

            return spin_response

        except Exception as error:
            logger.exception(f"Failed to spin: {error}")
            return None

    async def _perform_spin(self, payload: Dict[str, Any], is_free_spin: bool = False) -> Optional[SpinResponse]:
        spin_type = payload["spin_type"]
        payment_type = payload["payment_type"]

        if is_free_spin:
            user_response = await self.lookup(silent=True)
            if not user_response or not user_response.payload.user:
                return None

            # Map spin_type to required free_spin amount
            free_spin = user_response.payload.user.free_spin or 0
            required_free_spin = {1: 1, 2: 10, 3: 50, 4: 100}.get(spin_type)

            if required_free_spin is None:
                message = f"Invalid spin type '{spin_type}' for free spin."
                self._on_add_message(tag=MessageTag.ERROR, message=message)
                return None

            if free_spin < required_free_spin:
                message = "Balance and free spins are not enough to perform the spin."
                self._on_add_message(tag=MessageTag.ERROR, message=message)
                return None

            message = f"Balance not enough, using {free_spin} free spins..."
            self._on_add_message(tag=MessageTag.INFO, message=message)

            payload = {"free_spin_amount": free_spin, "spin_type": 0, "payment_type": payment_type}

        async with aiohttp.ClientSession(**self.client_params) as session:
            async with session.post(url=self._spin_api, json=payload) as response:
                if not response.ok:
                    spin_type = "Free spin" if is_free_spin else "Spin"
                    message = f"{spin_type} API request failed with status: {response.status}"
                    logger.error(f"{message} - {await response.text(encoding='utf-8')}")
                    self._on_add_message(tag=MessageTag.ERROR, message=message)
                    return None

                # Return response even if it has error_code, let caller handle it
                spin_response = SpinResponse.model_validate(await response.json())
                return spin_response
