import tkinter as tk
from typing import Counter, List, Optional, Tuple

from app.schemas.spin_response import SpinResult

# window_width, window_height, child_frame_width, child_frame_height, x, y
WP_TYPE = Tuple[int, int, int, int, int, int]

# x, y, width, height
BP_TYPE = Tuple[int, int, int, int]


def format_results_block(results: List[SpinResult]) -> str:
    counter = Counter(r.reward_name for r in results)
    lines: List[str] = ["Auto-spin Results"]

    for name, cnt in counter.items():
        suffix = f" × {cnt}" if cnt > 1 else ""
        lines.append(f"  • {name}{suffix}")

    return "\n".join(lines)


def get_window_position(child_frame: tk.Misc, parent_frame: Optional[tk.Misc] = None) -> WP_TYPE:
    """Calculate positioning coordinates for centering a child window.

    This function calculates the position to center a child frame either relative
    to a parent window or relative to the screen. It returns both the dimensions
    of the reference area and the calculated position coordinates.

    Args:
        child_frame (tk.Misc): The tkinter widget/frame to be positioned. Used to
            get the child frame's dimensions and screen information.
        parent_frame (Optional[tk.Misc], optional): The parent window to center
            relative to. If provided, the child will be centered within the parent
            window's bounds. If None, the child will be centered on the screen.
            Defaults to None.

    Returns:
        Tuple[int, int, int, int, int, int]: A tuple containing positioning information:
            - window_width (int): Width of the reference area (parent window or screen)
            - window_height (int): Height of the reference area (parent window or screen)
            - child_frame_width (int): Width of the child frame to be positioned
            - child_frame_height (int): Height of the child frame to be positioned
            - x (int): Calculated x-coordinate for centering the child frame
            - y (int): Calculated y-coordinate for centering the child frame
    """
    if parent_frame is not None:  # Center relative to root window
        root_window = parent_frame.winfo_toplevel()  # Find the root window (main application window)
        window_width = root_window.winfo_width()
        window_height = root_window.winfo_height()
        parent_x = root_window.winfo_rootx()
        parent_y = root_window.winfo_rooty()

    else:  # Center relative to screen
        window_width = child_frame.winfo_screenwidth()
        window_height = child_frame.winfo_screenheight()
        parent_x = 0
        parent_y = 0

    child_frame_width = child_frame.winfo_width()
    child_frame_height = child_frame.winfo_height()

    x = parent_x + (window_width // 2) - (child_frame_width // 2)
    y = parent_y + (window_height // 2) - (child_frame_height // 2)

    return window_width, window_height, child_frame_width, child_frame_height, x, y


def get_browser_position(browser_index: int, screen_width: int, screen_height: int, margin: float = 2.5) -> BP_TYPE:
    """Calculate browser window position and size based on index and screen dimensions.

    This function positions browser windows in a grid layout for the first 4 browsers
    (2x2 grid with margins), and centers additional browsers (index 4+) on the screen
    with a fixed size. It handles invalid screen dimensions by using defaults.

    Args:
        browser_index (int): Zero-based index of the browser window. Browsers 0-3
            are positioned in a 2x2 grid (0: top-left, 1: top-right, 2: bottom-left,
            3: bottom-right). Browsers 4+ are centered on screen.
        screen_width (int): Width of the screen in pixels. If <= 0, defaults to 1920.
        screen_height (int): Height of the screen in pixels. If <= 0, defaults to 1080.
        margin (float, optional): Margin in pixels between browser windows in the grid
            layout. Only applied to browsers 0-3. Defaults to 2.5.

    Returns:
        Tuple[int, int, int, int]: Browser window positioning information:
            - x (int): X-coordinate of the browser window's top-left corner
            - y (int): Y-coordinate of the browser window's top-left corner
            - width (int): Width of the browser window
            - height (int): Height of the browser window
    """
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
