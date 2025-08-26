import ssl
from typing import Dict

import aiohttp
from browser_use.browser.types import Page
from loguru import logger
from random_user_agent.params import HardwareType, OperatingSystem, SoftwareName
from random_user_agent.user_agent import UserAgent

from src.utils.contants import EventConfig


class RequestManager:
    @classmethod
    async def get_cookies(cls, page: Page) -> Dict[str, str]:
        try:
            cookies = await page.context.cookies()
            return {
                name: value
                for c in cookies
                if (name := c.get("name")) is not None and (value := c.get("value")) is not None
            }

        except Exception as error:
            logger.error(f"Failed to extract cookies: {error}")
            return {}

    @classmethod
    async def get_headers(cls, page: Page, event_config: EventConfig, user_agent: str) -> Dict[str, str]:
        cookies = await cls.get_cookies(page=page)

        return {
            "Cookie": "; ".join([f"{name}={value}" for name, value in cookies.items()]),
            "x-csrftoken": cookies.get("csrftoken", ""),
            "Referer": event_config.base_url,
            "Origin": event_config.base_url,
            "User-Agent": user_agent,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "TE": "trailers",
            "Priority": "u=0",
        }

    @classmethod
    def connector(cls) -> aiohttp.TCPConnector:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return aiohttp.TCPConnector(ssl=ssl_context)

    @classmethod
    def get_random_user_agent(cls) -> str:
        user_agent_rotator = UserAgent(
            hardware_types=[HardwareType.COMPUTER.value],
            software_names=[
                SoftwareName.CHROME.value,
                SoftwareName.FIREFOX.value,
                SoftwareName.EDGE.value,
                SoftwareName.SAFARI.value,
            ],
            operating_systems=[
                OperatingSystem.WINDOWS.value,
                OperatingSystem.MACOS.value,
                OperatingSystem.LINUX.value,
            ],
            limit=100,
        )

        return user_agent_rotator.get_random_user_agent()
