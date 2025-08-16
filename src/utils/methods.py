from typing import Any, Callable, Optional


def should_execute_callback(callback: Optional[Callable], *args: Any, **kwargs: Any) -> None:
    if callback is None:
        return

    callback(*args, **kwargs)
