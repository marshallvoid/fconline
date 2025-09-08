import ssl
from typing import Dict

import aiohttp
from browser_use.browser.types import Page
from loguru import logger

from src.utils.contants import EventConfig


class RequestManager:
    @classmethod
    def connector(cls) -> aiohttp.TCPConnector:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return aiohttp.TCPConnector(ssl=ssl_context)

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
            logger.exception(f"Failed to extract cookies: {error}")
            return {}

    @classmethod
    async def get_headers(cls, page: Page, event_config: EventConfig) -> Dict[str, str]:
        cookies = await cls.get_cookies(page=page)

        return {
            "Cookie": "; ".join([f"{name}={value}" for name, value in cookies.items()]),
            "x-csrftoken": cookies.get("csrftoken", ""),
            "Referer": event_config.base_url,
            "Origin": event_config.base_url,
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
