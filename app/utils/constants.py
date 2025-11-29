from typing import Dict, Tuple

DUPLICATE_WINDOW_SECONDS: int = 60

BROWSER_POSITIONS: Dict[Tuple[int, int], str] = {
    (0, 0): "Top-Left",
    (0, 1): "Top-Right",
    (1, 0): "Bottom-Left",
    (1, 1): "Bottom-Right",
}
