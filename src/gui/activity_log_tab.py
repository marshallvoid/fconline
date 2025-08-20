import tkinter as tk
from datetime import datetime
from tkinter import ttk
from typing import Dict, List, Optional

from src.schemas.enums.message_tag import MessageTag


class ActivityLogTab:
    # Available tab categories for organizing different types of messages
    TAB_NAMES = ["All", "Game Events", "Rewards", "System", "Websocket"]
    CURRENT_JACKPOT_LABEL_TEXT = "CURRENT JACKPOT: {value:,}"
    TARGET_SPECIAL_JACKPOT_LABEL_TEXT = "TARGET SPECIAL JACKPOT: {value:,}"

    def __init__(self, parent: tk.Misc) -> None:
        self._frame = ttk.Frame(parent)

        # Message storage and tab management
        self._message_tabs: Dict[str, Dict[str, tk.Text]] = {}
        self._current_tab: Optional[str] = None
        self._messages_by_tab: Dict[str, List[str]] = {tab_name: [] for tab_name in self.TAB_NAMES}

        self._build()

    @property
    def frame(self) -> ttk.Frame:
        return self._frame

    def add_message(self, tag: MessageTag, message: str) -> None:
        if not message.strip():
            return

        # Add timestamp to message for logging purposes
        timestamp = datetime.now().strftime("%H:%M:%S")
        timestamped_message = f"[{timestamp}] {message.strip()}"

        # Distribute message to relevant tabs based on message type
        self._add_message_to_tab(tab_name="All", tag=tag.name, message=timestamped_message)
        self._add_message_to_tab(tab_name=tag.tab_name, tag=tag.name, message=timestamped_message)

    def _add_message_to_tab(self, tab_name: str, tag: str, message: str) -> None:
        if tab_name not in self._message_tabs:
            return

        text_widget = self._message_tabs[tab_name]["text_widget"]
        text_widget.config(state="normal")

        current_text = text_widget.get("1.0", tk.END).strip()
        if current_text:
            text_widget.insert(tk.END, "\n")

        start_pos = text_widget.index(tk.END + "-1c linestart")
        text_widget.insert(tk.END, message)
        end_pos = text_widget.index(tk.END + "-1c")

        text_widget.tag_add(tag, start_pos, end_pos)
        text_widget.see(tk.END)
        text_widget.config(state="disabled")

    def clear_messages(self) -> None:
        for tab_info in self._message_tabs.values():
            text_widget = tab_info["text_widget"]
            text_widget.config(state="normal")
            text_widget.delete("1.0", tk.END)
            text_widget.config(state="disabled")

    def update_current_jackpot(self, value: int) -> None:
        self._current_jackpot_label.config(text=self.CURRENT_JACKPOT_LABEL_TEXT.format(value=value))

    def update_target_special_jackpot(self, value: int) -> None:
        self._target_special_jackpot_label.config(text=self.TARGET_SPECIAL_JACKPOT_LABEL_TEXT.format(value=value))

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

        self._current_jackpot_label = ttk.Label(
            jackpot_container,
            text=self.CURRENT_JACKPOT_LABEL_TEXT.format(value=0),
            foreground="#f97316",
            font=("Consolas", 12, "bold"),
        )
        self._current_jackpot_label.pack(anchor="w")

        # Target Jackpot Display
        self._target_special_jackpot_label = ttk.Label(
            jackpot_container,
            text=self.TARGET_SPECIAL_JACKPOT_LABEL_TEXT.format(value=0),
            foreground="#22c55e",
            font=("Consolas", 12, "bold"),
        )
        self._target_special_jackpot_label.pack(anchor="w", pady=(10, 0))

        # Messages Tab Control
        messages_frame = ttk.LabelFrame(container, text="Messages", padding=10)
        messages_frame.pack(fill="both", expand=True)
        messages_frame.configure(height=250)

        # Create notebook for tabs
        self._notebook = ttk.Notebook(messages_frame)
        self._notebook.pack(fill="both", expand=True)

        # Create tabs
        for tab_name in self.TAB_NAMES:
            self._create_message_tab(tab_name=tab_name, display_name=tab_name)

        # Set default tab
        self._notebook.select(0)

        # Setup focus handling to prevent text selection issues
        self._setup_focus_handling()

    def _setup_focus_handling(self) -> None:
        self._focus_after_id: Optional[str] = None

        def _schedule_focus_current_tab() -> None:
            def _focus_current_tab() -> None:
                try:
                    current = self._notebook.nametowidget(self._notebook.select())
                    if current and isinstance(current, (tk.Frame, ttk.Frame)):
                        current.focus_set()
                except Exception:
                    pass

            if self._focus_after_id:
                try:
                    self._frame.after_cancel(self._focus_after_id)
                except Exception:
                    pass
                finally:
                    self._focus_after_id = None

            self._focus_after_id = self._frame.after(10, _focus_current_tab)

        def _on_tab_changed(_: object) -> None:
            try:
                current = self._notebook.nametowidget(self._notebook.select())
                if current and isinstance(current, (tk.Frame, ttk.Frame)):
                    current.focus_set()
            except Exception:
                pass

            _schedule_focus_current_tab()

        self._notebook.bind("<<NotebookTabChanged>>", _on_tab_changed)
        self._notebook.bind("<ButtonRelease-1>", lambda e: _schedule_focus_current_tab())
        self._frame.after_idle(_schedule_focus_current_tab)

    def _create_message_tab(self, tab_name: str, display_name: str) -> None:
        tab_frame = ttk.Frame(self._notebook)
        self._notebook.add(tab_frame, text=display_name)

        text_container = ttk.Frame(tab_frame)
        text_container.pack(fill="both", expand=True)

        text_widget = tk.Text(
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
            selectbackground="#404040",
            selectforeground="#ffffff",
        )

        # Configure tags for this text widget
        for tag in MessageTag:
            font = ("Arial", 12, "bold") if tag != MessageTag.DEFAULT else ("Arial", 12)
            text_widget.tag_configure(tag.name, foreground=tag.value, font=font)

        # Bind events to prevent unwanted text selection
        text_widget.bind("<Button-1>", lambda e: text_widget.tag_remove("sel", "1.0", tk.END))
        text_widget.bind("<B1-Motion>", lambda e: text_widget.tag_remove("sel", "1.0", tk.END))
        text_widget.bind("<Double-Button-1>", lambda e: text_widget.tag_remove("sel", "1.0", tk.END))

        scrollbar = ttk.Scrollbar(text_container, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)

        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Store tab information
        self._message_tabs[tab_name] = {"frame": tab_frame, "text_widget": text_widget, "scrollbar": scrollbar}
