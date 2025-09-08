import asyncio
import concurrent.futures
import contextlib
import threading
from typing import Any, Awaitable, Callable, Coroutine, Mapping, Optional, Sequence, TypeVar

from loguru import logger

T = TypeVar("T")


def run_in_thread(
    coro_func: Callable[..., Coroutine[Any, Any, T]],
    *args: Any,
    daemon: bool = True,
    **kwargs: Any,
) -> threading.Thread:
    """
    Run an async coroutine function inside a separate thread.

    Args:
        coro_func: An async function (coroutine function) to run in the thread.
        *args: Positional arguments for the coroutine.
        daemon: Whether the thread should run as daemon (default: True).
        **kwargs: Keyword arguments for the coroutine.

    Returns:
        threading.Thread: The thread object that was started.
                         Use .join() if you want to wait for it.
    """

    def _runner() -> None:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(coro_func(*args, **kwargs))

        except Exception as error:
            logger.exception(f"Error in thread running {coro_func.__name__}: {error}")

        finally:
            asyncio.set_event_loop(None)

    thread = threading.Thread(target=_runner, daemon=daemon)
    thread.start()

    return thread


def run_async_in_new_loop(coro: Awaitable[T], timeout: Optional[float] = None) -> None:
    """
    Run a coroutine in a fresh event loop, optionally with a timeout.
    """
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(asyncio.wait_for(coro, timeout=timeout) if timeout else coro)

    except asyncio.TimeoutError:
        logger.warning("Async operation timed out")

    except Exception as error:
        logger.exception("Error running async operation: %s", error)

    finally:
        with contextlib.suppress(Exception):
            loop.close()


def run_many_in_threads(
    tasks: Sequence[tuple[Callable[..., Awaitable[Any]], Sequence[Any], Mapping[str, Any]]],
    timeout: Optional[float] = None,
) -> None:
    """
    Run multiple async callables concurrently in separate threads.

    Args:
        tasks: List of (async function, args, kwargs) tuples.
        timeout: Optional timeout for each task.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        futures = {
            executor.submit(
                run_async_in_new_loop,
                func(*args, **kwargs),
                timeout,
            )
            for func, args, kwargs in tasks
        }

        with contextlib.suppress(Exception):
            concurrent.futures.wait(fs=futures, timeout=timeout)

        _ = [f.cancel() for f in futures if not f.done()]
