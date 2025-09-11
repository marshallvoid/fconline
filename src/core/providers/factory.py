from dishka import AsyncContainer, make_async_container

from src.core.configs import Settings
from src.core.providers.configs import ConfigsProvider


def make_container(settings: Settings) -> AsyncContainer:
    container = make_async_container(
        ConfigsProvider(settings=settings),
        #   ManagersProvider(),
        #   ServicesProvider(),
    )

    return container
