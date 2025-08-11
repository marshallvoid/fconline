import tkinter as tk
from datetime import datetime
from tkinter import ttk
from typing import Any, Dict, Optional

import darkdetect

from .base_component import BaseComponent


class LogPanel(BaseComponent):
    """Log panel component with category tabs for messages."""

    def __init__(self, parent: tk.Widget, **kwargs: Any) -> None:
        """
        Initialize the log panel.

        Args:
            parent: Parent widget
            **kwargs: Additional keyword arguments
        """
        self.notebook: Optional[ttk.Notebook] = None
        self.text_widgets: Dict[str, tk.Text] = {}

        super().__init__(parent, **kwargs)

    def _setup_ui(self) -> None:
        """Setup the log panel UI."""
        self.frame = ttk.LabelFrame(self.parent, text="Messages", padding=10)

        # Notebook with per-category tabs
        self.notebook = ttk.Notebook(self.frame)
        self.notebook.pack(fill="both", expand=True)
        # Avoid focus outline on tab label when clicked/selected
        try:
            self.notebook.configure(takefocus=0)
        except Exception:
            pass

        for code, title in (
            ("all", "All"),
            ("info", "Info"),
            ("event", "Events"),
            ("target", "Targets"),
            ("error", "Errors"),
        ):
            tab = ttk.Frame(self.notebook)
            self.notebook.add(tab, text=title)

            text_container = ttk.Frame(tab)
            text_container.pack(fill="both", expand=True)

            text_widget = tk.Text(
                text_container,
                wrap=tk.WORD,
                height=12,
                relief="flat",
                borderwidth=0,
                state="disabled",
            )
            scrollbar = ttk.Scrollbar(text_container, orient="vertical", command=text_widget.yview)
            text_widget.configure(yscrollcommand=scrollbar.set)
            text_widget.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            self.text_widgets[code] = text_widget

        # Configure text tags with theme-aware colors
        self._apply_colors(darkdetect.theme() or "dark")

        # Redirect focus to tab content to hide tab-label focus ring
        self.notebook.bind(
            "<<NotebookTabChanged>>",
            lambda e: self.frame.after(0, self._focus_current_tab_content),
            add=True,
        )
        self.notebook.bind(
            "<ButtonPress-1>",
            lambda e: self.frame.after(0, self._focus_current_tab_content),
            add=True,
        )

    def _apply_colors(self, theme: str) -> None:
        """Apply theme-aware colors to text widget and tags."""
        is_dark = theme.lower() == "dark"

        bg = "#1e1e1e" if is_dark else "#ffffff"
        fg = "#e6e6e6" if is_dark else "#1f1f1f"
        insert = fg

        general = "#4caf50" if is_dark else "#2e7d32"
        target = "#ff9800" if is_dark else "#ef6c00"
        error = "#ff5252" if is_dark else "#c62828"
        info = "#64b5f6" if is_dark else "#1565c0"

        for widget in self.text_widgets.values():
            widget.config(bg=bg, fg=fg, insertbackground=insert)
            for tag in ("general", "target", "error", "info", "default"):
                try:
                    widget.tag_delete(tag)
                except Exception:
                    pass
            widget.tag_configure("general", foreground=general)
            widget.tag_configure("target", foreground=target)
            widget.tag_configure("error", foreground=error)
            widget.tag_configure("info", foreground=info)
            widget.tag_configure("default", foreground=fg)

    def apply_theme(self, theme: str) -> None:
        """Public API for updating theme from outside."""
        self._apply_colors(theme)

    def add_message(self, message: str, code: str = "general") -> None:
        """Add a message to the All tab and the specific category tab.

        code accepted: 'info' | 'event' | 'target' | 'error' | 'general'
        """
        if not message or not message.strip():
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        timestamped_message = f"[{timestamp}] {message.strip()}"

        self._write_to_widget(self.text_widgets.get("all"), timestamped_message, code)
        if code in self.text_widgets:
            self._write_to_widget(self.text_widgets.get(code), timestamped_message, code)
        else:
            self._write_to_widget(self.text_widgets.get("info"), timestamped_message, code)

    def clear_messages(self) -> None:
        """Clear all messages from all tabs."""
        for widget in self.text_widgets.values():
            widget.config(state="normal")
            widget.delete("1.0", tk.END)
            widget.config(state="disabled")

    def _write_to_widget(self, widget: Optional[tk.Text], text: str, code: str) -> None:
        if not widget:
            return
        widget.config(state="normal")
        if widget.get("1.0", tk.END).strip():
            widget.insert(tk.END, "\n")
        start_pos = widget.index(tk.END + "-1c linestart")
        widget.insert(tk.END, text)
        end_pos = widget.index(tk.END + "-1c")
        tag = code if code in ("info", "event", "target", "error", "general") else "general"
        widget.tag_add(tag, start_pos, end_pos)
        widget.see(tk.END)
        widget.config(state="disabled")

    def _focus_current_tab_content(self) -> None:
        """Move focus to the current tab's content to remove tab label focus outline."""
        try:
            current = self.notebook.nametowidget(self.notebook.select())
            current.focus_set()
        except Exception:
            # Fallback: focus on frame to clear outline
            try:
                self.frame.focus_set()
            except Exception:
                pass
