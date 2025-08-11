from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional


class Header(ttk.Frame):
    """Modern app header with title, subtitle and theme toggle."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        title: str,
        subtitle: Optional[str] = None,
        on_toggle_theme: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(parent)

        self._on_toggle_theme = on_toggle_theme

        left = ttk.Frame(self)
        left.pack(side="left", fill="x", expand=True)

        title_lbl = ttk.Label(left, text=title, style="AppTitle.TLabel")
        title_lbl.pack(anchor="w")

        if subtitle:
            subtitle_lbl = ttk.Label(left, text=subtitle, style="AppSubtitle.TLabel")
            subtitle_lbl.pack(anchor="w")

        right = ttk.Frame(self)
        right.pack(side="right")

        self._theme_var = tk.StringVar(value="Auto")
        self._theme_btn = ttk.Menubutton(right, textvariable=self._theme_var, style="TButton")
        self._menu = tk.Menu(self._theme_btn, tearoff=False)
        self._theme_btn["menu"] = self._menu
        for mode in ("Auto", "Light", "Dark"):
            self._menu.add_radiobutton(
                label=mode,
                value=mode,
                variable=self._theme_var,
                command=self._handle_toggle,
            )
        self._theme_btn.pack()

    def _handle_toggle(self) -> None:
        if self._on_toggle_theme:
            self._on_toggle_theme()

    @property
    def selected_mode(self) -> str:
        return self._theme_var.get()
