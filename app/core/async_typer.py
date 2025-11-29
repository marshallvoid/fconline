import asyncio
import inspect
from functools import wraps
from typing import Any, Callable, Coroutine, cast

import nest_asyncio
from typer import Typer
from typer.models import CommandFunctionType

nest_asyncio.apply()


class AsyncTyper(Typer):
    @staticmethod
    def maybe_run_async(
        decorator: Callable[[CommandFunctionType], CommandFunctionType],
        f: CommandFunctionType,
    ) -> CommandFunctionType:
        if inspect.iscoroutinefunction(f):

            @wraps(f)
            def runner(*args: Any, **kwargs: Any) -> Any:
                return asyncio.run(cast(Callable[..., Coroutine[Any, Any, Any]], f)(*args, **kwargs))

            decorator(cast(CommandFunctionType, runner))
        else:
            decorator(f)
        return f

    def callback(self, *args: Any, **kwargs: Any) -> Callable[[CommandFunctionType], CommandFunctionType]:
        decorator = super().callback(*args, **kwargs)
        return lambda f: self.maybe_run_async(decorator, f)

    def command(self, *args: Any, **kwargs: Any) -> Callable[[CommandFunctionType], CommandFunctionType]:
        decorator = super().command(*args, **kwargs)
        return lambda f: self.maybe_run_async(decorator, f)
