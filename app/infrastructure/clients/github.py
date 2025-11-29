import json
from typing import Any, Dict, Optional

import aiohttp
from loguru import logger

from app.core.managers.request import request_mgr
from app.core.settings import settings
from app.schemas.app_config import AppConfigs, Configs


class GithubClient:
    def __init__(self) -> None:
        self._gist_endpoint = settings.gist_url
        self._release_endpoint = settings.release_url

    @property
    def client_params(self) -> Dict[str, Any]:
        return {
            "connector": request_mgr.secure_connector,
            "timeout": request_mgr.get_timeout(timeout=10),
        }

    async def load_app_configs(self) -> Configs:
        try:
            async with aiohttp.ClientSession(**self.client_params) as session:
                async with session.get(url=self._gist_endpoint) as response:
                    gist_text = await response.text()
                    gist_json = json.loads(gist_text)

                    configs = Configs.model_validate(gist_json)
                    return configs

        except Exception as error:
            logger.exception(f"Failed to load app configs: {error}")
            return Configs(app_configs=AppConfigs())

    async def check_release(self) -> Optional[Dict[str, Any]]:
        try:
            async with aiohttp.ClientSession(**self.client_params) as session:
                async with session.get(url=self._release_endpoint) as response:
                    return await response.json()

        except Exception as error:
            logger.exception(f"Failed to check release: {error}")
            return None
