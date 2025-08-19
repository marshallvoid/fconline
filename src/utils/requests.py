import ssl

import aiohttp


class RequestManager:
    @classmethod
    def connector(cls) -> aiohttp.TCPConnector:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return aiohttp.TCPConnector(ssl=ssl_context)
