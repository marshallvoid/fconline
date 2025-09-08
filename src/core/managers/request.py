import asyncio
import ssl
from typing import Dict, Optional

import aiohttp
from browser_use.browser.types import Page
from loguru import logger

from src.utils.contants import EventConfig


class RequestManager:
    # Shared connector for connection pooling across all requests
    _connector: Optional[aiohttp.TCPConnector] = None
    _lock = asyncio.Lock()

    @classmethod
    async def connector(cls) -> aiohttp.TCPConnector:
        if cls._connector is None or cls._connector.closed:
            async with cls._lock:
                # Double-check pattern to avoid race conditions
                if cls._connector is None or cls._connector.closed:
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE
                    cls._connector = aiohttp.TCPConnector(
                        ssl=ssl_context,
                        limit=100,  # Total pool size
                        limit_per_host=30,  # Connections per host
                        ttl_dns_cache=300,  # DNS cache TTL
                        use_dns_cache=True,
                        keepalive_timeout=30,  # Keep connections alive
                        enable_cleanup_closed=True,
                    )
        return cls._connector

    @classmethod
    async def cleanup_connector(cls) -> None:
        if cls._connector is not None and not cls._connector.closed:
            await cls._connector.close()

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
