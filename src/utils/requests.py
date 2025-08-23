import ssl

import aiohttp
from random_user_agent.params import HardwareType, OperatingSystem, SoftwareName
from random_user_agent.user_agent import UserAgent


class RequestManager:
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
