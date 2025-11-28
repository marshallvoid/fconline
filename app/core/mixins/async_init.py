from typing import Any, Generator, Self


class AsyncMixin:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Standard constructor used for arguments pass
        Do not override. Use __ainit__ instead
        """
        self.__storedargs = args, kwargs
        self.async_initialized = False

    async def __ainit__(self, *args: Any, **kwargs: Any) -> None:
        """Async constructor, you should implement this"""

    async def __initobj(self) -> Self:
        """Crutch used for __await__ after spawning"""
        assert not self.async_initialized
        self.async_initialized = True
        # pass the parameters to __ainit__ that passed to __init__
        await self.__ainit__(*self.__storedargs[0], **self.__storedargs[1])
        return self

    def __await__(self) -> Generator[Any, Any, Self]:
        return self.__initobj().__await__()
