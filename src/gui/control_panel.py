import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Optional

from .base_component import BaseComponent


class ControlPanel(BaseComponent):
    """Control panel component with start/stop buttons and status display."""

    def __init__(
        self,
        parent: tk.Widget,
        on_start: Optional[Callable] = None,
        on_stop: Optional[Callable] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the control panel.

        Args:
            parent: Parent widget
            on_start: Callback function for start button
            on_stop: Callback function for stop button
            **kwargs: Additional keyword arguments
        """
        self.on_start = on_start
        self.on_stop = on_stop

        self.start_btn: Optional[ttk.Button] = None
        self.stop_btn: Optional[ttk.Button] = None
        self.status_label: Optional[ttk.Label] = None

        super().__init__(parent, **kwargs)

    def _setup_ui(self) -> None:
        """Setup the control panel UI."""
        self.frame = ttk.Frame(self.parent)

        # Start button
        self.start_btn = ttk.Button(
            self.frame,
            text="Start",
            command=self.on_start,
            style="Accent.TButton",
        )
        self.start_btn.pack(side="left", padx=(0, 5))

        # Stop button
        self.stop_btn = ttk.Button(
            self.frame,
            text="Stop",
            command=self.on_stop,
            state="disabled",
        )
        self.stop_btn.pack(side="left", padx=5)

        # Status label
        self.status_label = ttk.Label(self.frame, text="✅ Status: Ready", style="Status.TLabel")
        self.status_label.pack(side="right")

    def set_running_state(self, is_running: bool) -> None:
        """Set the running state of the control panel."""
        start_btn_state = "disabled" if is_running else "normal"
        stop_btn_state = "normal" if is_running else "disabled"
        status_text = "🚀 Status: Running..." if is_running else "✅ Status: Ready"

        self.start_btn.config(state=start_btn_state)
        self.stop_btn.config(state=stop_btn_state)
        self.status_label.config(text=status_text)

    def set_status(self, status: str) -> None:
        """Set the status text."""
        if self.status_label:
            self.status_label.config(text=status)

    def set_starting_status(self) -> None:
        """Set starting status."""
        self.status_label.config(text="🚀 Status: Starting...")

    def set_stopping_status(self) -> None:
        """Set stopping status."""
        self.status_label.config(text="⏹️ Status: Stopping...")
