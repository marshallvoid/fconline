import ssl
from typing import Dict

import aiohttp


class RequestManager:
    @classmethod
    def headers(cls, cookies: Dict[str, str], base_url: str) -> Dict[str, str]:
        return {
            "x-csrftoken": cookies.get("csrftoken", ""),
            "Cookie": "; ".join([f"{name}={value}" for name, value in cookies.items()]),
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": base_url,
            "Origin": base_url,
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

    @classmethod
    def connector(cls) -> aiohttp.TCPConnector:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return aiohttp.TCPConnector(ssl=ssl_context)
