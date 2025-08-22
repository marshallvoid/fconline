import tkinter as tk
from inspect import isawaitable
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Counter, List, Optional, Tuple, TypeVar, Union

from loguru import logger

if TYPE_CHECKING:
    from src.schemas.spin_response import SpinResult


T = TypeVar("T")


async def maybe_awaitable(func: Union[T, Awaitable[T]]) -> T:
    if isawaitable(func):
        return await func
    return func


def maybe_callback(callback: Optional[Callable], *args: Any, **kwargs: Any) -> None:
    if callback is None:
        return

    callback(*args, **kwargs)


def format_spin_results_block(spin_results: List["SpinResult"]) -> str:
    counter = Counter(r.reward_name for r in spin_results)
    lines: List[str] = ["Auto-spin Results"]

    for name, cnt in counter.items():
        suffix = f" × {cnt}" if cnt > 1 else ""
        lines.append(f"  • {name}{suffix}")

    return "\n".join(lines)


def get_window_position(
    child_frame: tk.Misc,
    parent_frame: Optional[tk.Misc] = None,
) -> Tuple[int, int, int, int, int, int]:
    if parent_frame is not None:
        # Find the root window (main application window)
        root_window = parent_frame.winfo_toplevel()
        # Center relative to root window
        window_width = root_window.winfo_width()
        window_height = root_window.winfo_height()
        parent_x = root_window.winfo_rootx()
        parent_y = root_window.winfo_rooty()
    else:
        # Center relative to screen
        window_width = child_frame.winfo_screenwidth()
        window_height = child_frame.winfo_screenheight()
        parent_x = 0
        parent_y = 0

    child_frame_width = child_frame.winfo_width()
    child_frame_height = child_frame.winfo_height()

    x = parent_x + (window_width // 2) - (child_frame_width // 2)
    y = parent_y + (window_height // 2) - (child_frame_height // 2)

    return window_width, window_height, child_frame_width, child_frame_height, x, y


def get_browser_position(
    browser_index: int,
    screen_width: int,
    screen_height: int,
) -> Tuple[int, int, int, int]:
    if screen_width <= 0 or screen_height <= 0:
        logger.warning("⚠️ Invalid screen dimensions, using default values")
        screen_width = 1920
        screen_height = 1080

    if browser_index < 4:
        # Divide the screen into 4 equal regions (2x2 grid)
        grid_width = screen_width // 2
        grid_height = screen_height // 2

        # Calculate position based on index
        row = browser_index // 2  # 0: top, 1: bottom
        col = browser_index % 2  # 0: left, 1: right

        x = col * grid_width
        y = row * grid_height

        # Browser size
        width = grid_width
        height = grid_height

        logger.info(f"📍 Browser {browser_index}: Grid position ({row}, {col}) -> ({x}, {y}) {width}x{height}")
        return x, y, width, height

    else:
        # Browser 5+: center on the screen
        # Fixed size for center browser
        width = min(800, screen_width // 2)
        height = min(600, screen_height // 2)

        # Calculate center position
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

        logger.info(f"📍 Browser {browser_index}: Center position ({x}, {y}) {width}x{height}")
        return x, y, width, height
