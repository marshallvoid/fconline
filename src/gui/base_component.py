import tkinter as tk
from typing import Any, Optional


class BaseComponent:
    """Base class for all GUI components."""

    def __init__(self, parent: tk.Widget, **kwargs: Any) -> None:
        """
        Initialize the base component.

        Args:
            parent: Parent widget
            **kwargs: Additional keyword arguments
        """
        self.parent = parent

        self.frame: Optional[tk.Widget] = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the UI for this component. Override in subclasses."""
        msg = "Subclasses must implement _setup_ui"
        raise NotImplementedError(msg)

    def pack(self, **kwargs: Any) -> None:
        """Pack the component frame."""
        if self.frame:
            self.frame.pack(**kwargs)

    def grid(self, **kwargs: Any) -> None:
        """Grid the component frame."""
        if self.frame:
            self.frame.grid(**kwargs)

    def place(self, **kwargs: Any) -> None:
        """Place the component frame."""
        if self.frame:
            self.frame.place(**kwargs)
