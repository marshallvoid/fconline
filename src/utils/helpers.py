import tkinter as tk
from typing import Any, Callable, Counter, List, Optional, Tuple

from src.schemas.spin_response import SpinResult


def maybe_execute(func: Optional[Callable], *args: Any, **kwargs: Any) -> None:
    if func is None:
        return

    func(*args, **kwargs)


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


BROWSER_POSITIONS = {
    (0, 0): "Top-Left",
    (0, 1): "Top-Right",
    (1, 0): "Bottom-Left",
    (1, 1): "Bottom-Right",
}


def get_browser_position(
    browser_index: int,
    screen_width: int,
    screen_height: int,
    margin: float = 2.5,
) -> Tuple[int, int, int, int]:
    if screen_width <= 0 or screen_height <= 0:
        screen_width = 1920
        screen_height = 1080

    if browser_index < 4:
        # Divide the screen into 4 equal regions (2x2 grid)
        grid_width = float(screen_width // 2)
        grid_height = float(screen_height // 2)

        # Calculate position based on index
        row, col = divmod(browser_index, 2)

        # Browser position
        x = col * grid_width
        y = row * grid_height

        # Browser size
        width = grid_width
        height = grid_height

        if row == 0 and col == 0:  # Top-left
            width -= margin
            height -= margin

        elif row == 0 and col == 1:  # Top-right
            x += margin
            width -= margin
            height -= margin

        elif row == 1 and col == 0:  # Bottom-left
            y += margin
            width -= margin
            height -= margin

        elif row == 1 and col == 1:  # Bottom-right
            x += margin
            y += margin
            width -= margin
            height -= margin

        return int(x), int(y), int(width), int(height)

    # Browser 5+: center on the screen, fixed size for center browser
    width = min(800, screen_width // 2)
    height = min(600, screen_height // 2)

    # Calculate center position
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2

    return int(x), int(y), int(width), int(height)
