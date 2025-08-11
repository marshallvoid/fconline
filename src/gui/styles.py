from __future__ import annotations

import platform
import tkinter as tk
from tkinter import ttk


def apply_styles(root: tk.Misc) -> None:
    """Apply modern, consistent styles across the app.

    Keeps things neutral to work with sv_ttk themes (dark/light).
    """
    style = ttk.Style(root)

    # Base font selection per platform with sensible fallbacks
    system = platform.system().lower()
    if system == "darwin":
        base_font = ("SF Pro Text", 12)
        mono_font = ("SF Mono", 12)
        title_font = ("SF Pro Display", 18, "bold")
        subtitle_font = ("SF Pro Text", 12)
    elif system == "windows":
        base_font = ("Segoe UI", 11)
        mono_font = ("Cascadia Mono", 11)
        title_font = ("Segoe UI Semibold", 18)
        subtitle_font = ("Segoe UI", 11)
    else:
        base_font = ("Inter", 11)
        mono_font = ("DejaVu Sans Mono", 11)
        title_font = ("Inter", 18, "bold")
        subtitle_font = ("Inter", 11)

    style.configure(".", font=base_font)

    # Headings
    style.configure("AppTitle.TLabel", font=title_font)
    style.configure("AppSubtitle.TLabel", font=subtitle_font)

    # Buttons
    style.configure("Accent.TButton", padding=(14, 8))
    style.configure("TButton", padding=(12, 8))
    style.map(
        "TButton",
        relief=[("pressed", "sunken"), ("active", "raised")],
    )

    # Notebook
    style.configure("TNotebook", padding=0)
    style.configure("TNotebook.Tab", padding=(16, 8))

    # LabelFrames
    style.configure("TLabelframe", padding=12)
    style.configure("TLabelframe.Label", padding=(6, 2))

    # Status Label style (pill-like)
    style.configure("Status.TLabel", padding=(8, 4))

    # Text widgets: apply monospace font where used (log panel)
    try:
        root.option_add("*Text.font", mono_font)
    except Exception:
        pass
