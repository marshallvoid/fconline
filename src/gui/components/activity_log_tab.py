import tkinter as tk
from datetime import datetime
from tkinter import ttk

from src.schemas.enums.message_tag import MessageTag


class ActivityLogTab:
    def __init__(self, parent: tk.Misc) -> None:
        self._frame = ttk.Frame(parent)

        self._build()

    @property
    def frame(self) -> ttk.Frame:
        return self._frame

    def add_message(self, tag: str, message: str) -> None:
        if not message.strip():
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        timestamped_message = f"[{timestamp}] {message.strip()}"

        self._messages_text_widget.config(state="normal")
        current_text = self._messages_text_widget.get("1.0", tk.END).strip()
        if current_text:
            self._messages_text_widget.insert(tk.END, "\n")

        start_pos = self._messages_text_widget.index(tk.END + "-1c linestart")
        self._messages_text_widget.insert(tk.END, timestamped_message)
        end_pos = self._messages_text_widget.index(tk.END + "-1c")

        self._messages_text_widget.tag_add(tag, start_pos, end_pos)
        self._messages_text_widget.see(tk.END)
        self._messages_text_widget.config(state="disabled")

    def clear_messages(self) -> None:
        self._messages_text_widget.config(state="normal")
        self._messages_text_widget.delete("1.0", tk.END)
        self._messages_text_widget.config(state="disabled")

    def update_special_jackpot(self, special_jackpot: int) -> None:
        jackpot_text = (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"SPECIAL JACKPOT: {special_jackpot:,}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        self._special_jackpot_label.config(text=jackpot_text)

    def update_target_special_jackpot(self, value: int) -> None:
        target_text = (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"TARGET JACKPOT: {value:,}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        self._target_special_jackpot_label.config(text=target_text)

    def _build(self) -> None:
        title_label = ttk.Label(self._frame, text="Activity Log", font=("Arial", 14, "bold"))
        title_label.pack(pady=(10, 20))

        container = ttk.Frame(self._frame)
        container.pack(fill="both", expand=True, padx=20, pady=10)

        # Special Jackpot Display
        jackpot_frame = ttk.LabelFrame(container, text="Jackpot Status", padding=10)
        jackpot_frame.pack(fill="x", pady=(0, 10))

        jackpot_container = ttk.Frame(jackpot_frame)
        jackpot_container.pack(fill="x")

        self._special_jackpot_label = ttk.Label(
            jackpot_container,
            text="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "SPECIAL JACKPOT: 0\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            foreground="#f97316",
            font=("Consolas", 12, "bold"),
        )
        self._special_jackpot_label.pack(anchor="w")

        # Target Jackpot Display
        self._target_special_jackpot_label = ttk.Label(
            jackpot_container,
            text="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "TARGET SPECIAL JACKPOT: 0\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            foreground="#22c55e",
            font=("Consolas", 12, "bold"),
        )
        self._target_special_jackpot_label.pack(anchor="w", pady=(10, 0))

        self._messages_frame = ttk.LabelFrame(container, text="Messages", padding=10)
        self._messages_frame.pack(fill="both", expand=True)
        self._messages_frame.configure(height=250)

        text_container = ttk.Frame(self._messages_frame)
        text_container.pack(fill="both", expand=True)

        self._messages_text_widget = tk.Text(
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

        for tag in MessageTag:
            font = ("Arial", 12, "bold") if tag != MessageTag.DEFAULT else ("Arial", 12)
            self._messages_text_widget.tag_configure(tag.name, foreground=tag.value, font=font)

        scrollbar = ttk.Scrollbar(text_container, orient="vertical", command=self._messages_text_widget.yview)
        self._messages_text_widget.configure(yscrollcommand=scrollbar.set)

        self._messages_text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
