from dishka import AsyncContainer, make_async_container

from app.core.providers.configs import ConfigsProvider
from app.core.settings import Settings


def make_container(settings: Settings) -> AsyncContainer:
    container = make_async_container(ConfigsProvider(settings=settings))

    return container
