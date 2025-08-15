import tkinter as tk
from datetime import datetime
from tkinter import ttk

from loguru import logger


class ActivityLogTab:
    def __init__(self, parent: tk.Misc) -> None:
        self._frame = ttk.Frame(parent)
        self._build()

    @property
    def frame(self) -> ttk.Frame:
        return self._frame

    def _build(self) -> None:
        logger.info("🔧 Initializing ActivityLogTab")

        title_label = ttk.Label(self._frame, text="Application Log", font=("Arial", 14, "bold"))
        title_label.pack(pady=(10, 20))

        container = ttk.Frame(self._frame)
        container.pack(fill="both", expand=True, padx=20, pady=10)

        self.messages_frame = ttk.LabelFrame(container, text="Messages", padding=10)
        self.messages_frame.pack(fill="both", expand=True)
        self.messages_frame.configure(height=250)

        text_container = ttk.Frame(self.messages_frame)
        text_container.pack(fill="both", expand=True)

        self.messages_text_widget = tk.Text(
            text_container,
            wrap=tk.WORD,
            height=12,
            font=("Arial", 12),
            bg="#2b2b2b",
            fg="#e0e0e0",
            relief="flat",
            borderwidth=0,
            state="disabled",
            insertbackground="#e0e0e0",
        )

        self.messages_text_widget.tag_configure("default", foreground="#e0e0e0", font=("Arial", 12))
        self.messages_text_widget.tag_configure("general", foreground="#4caf50", font=("Arial", 12, "bold"))
        self.messages_text_widget.tag_configure("info", foreground="#2196f3", font=("Arial", 12))
        self.messages_text_widget.tag_configure("error", foreground="#f44336", font=("Arial", 12, "bold"))
        self.messages_text_widget.tag_configure("target_reached", foreground="#ff9800", font=("Arial", 12, "bold"))

        scrollbar = ttk.Scrollbar(text_container, orient="vertical", command=self.messages_text_widget.yview)
        self.messages_text_widget.configure(yscrollcommand=scrollbar.set)

        self.messages_text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        logger.success("✅ ActivityLogTab initialized successfully")

    def add_message(self, tag: str, message: str) -> None:
        if not message or not message.strip():
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        timestamped_message = f"[{timestamp}] {message.strip()}"

        self.messages_text_widget.config(state="normal")
        current_text = self.messages_text_widget.get("1.0", tk.END).strip()
        if current_text:
            self.messages_text_widget.insert(tk.END, "\n")

        start_pos = self.messages_text_widget.index(tk.END + "-1c linestart")
        self.messages_text_widget.insert(tk.END, timestamped_message)
        end_pos = self.messages_text_widget.index(tk.END + "-1c")

        self.messages_text_widget.tag_add(tag, start_pos, end_pos)
        self.messages_text_widget.see(tk.END)
        self.messages_text_widget.config(state="disabled")
