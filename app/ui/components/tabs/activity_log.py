import tkinter as tk
from collections import deque
from datetime import datetime
from tkinter import ttk
from typing import Deque, Dict, Tuple

from pydantic import BaseModel, ConfigDict

from app.schemas.enums.message_tag import MessageTag
from app.ui.utils.ui_factory import UIFactory
from app.ui.utils.ui_helpers import UIHelpers
from app.utils.constants import DUPLICATE_WINDOW_SECONDS


class MessageTabInfo(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    frame: ttk.Frame
    text_widget: tk.Text
    scrollbar: ttk.Scrollbar


class ActivityLogTab:
    _TABS = ["All", "Game Events", "Rewards", "System", "WebSockets"]

    _CURRENT_JACKPOT_LABEL_TEXT = "Current Jackpot: {value:,}"
    _JACKPOT_WINNER_TEXT = "Ultimate Prize Winner: {nickname} ({value})"
    _MINI_JACKPOT_WINNER_TEXT = "Mini Prize Winner: {nickname} ({value})"

    # Cache size - keep last N messages for duplicate detection
    _MAX_RECENT_MESSAGES = 100

    def __init__(self, parent: tk.Misc) -> None:
        # Widgets
        self._frame = ttk.Frame(master=parent)

        # States
        self._message_tabs: Dict[str, MessageTabInfo] = {}  # Format: { tab_name: MessageTabInfo }

        # Cache for duplicate detection: deque of (message_content, timestamp_dt)
        self._recent_messages: Deque[Tuple[str, datetime]] = deque(maxlen=self._MAX_RECENT_MESSAGES)

        self._initialize()

    @property
    def frame(self) -> ttk.Frame:
        return self._frame

    # ==================== Public Methods ====================
    def update_current_jackpot(self, value: int) -> None:
        self._current_jackpot_label.config(text=self._CURRENT_JACKPOT_LABEL_TEXT.format(value=value))

    def update_prize_winner(self, nickname: str, value: str, is_jackpot: bool = False) -> None:
        if is_jackpot:
            self._ultimate_prize_label.config(text=self._JACKPOT_WINNER_TEXT.format(nickname=nickname, value=value))
            return

        self._mini_prize_label.config(text=self._MINI_JACKPOT_WINNER_TEXT.format(nickname=nickname, value=value))

    def add_message(self, tag: MessageTag, message: str, compact: bool = False) -> None:
        if not message.strip():
            return

        now = datetime.now()
        timestamp = now.strftime("%d/%m/%Y %H:%M:%S")

        if compact:
            message_content = self._extract_message_content(message=message)

            # Fast duplicate check using in-memory cache
            if self._is_duplicate_message(message_content=message_content, now=now):
                return

            # Add to cache for future duplicate checks
            self._recent_messages.append((message_content, now))

            timestamped_message = f"[{timestamp}] {message_content}"
        else:
            timestamped_message = f"[{timestamp}] {message.strip()}"

        if tag != MessageTag.WEBSOCKET:
            self._add_message_to_tab(tab_name="All", tag=tag.name, message=timestamped_message)
        self._add_message_to_tab(tab_name=tag.tab_name, tag=tag.name, message=timestamped_message)

    def clear_messages(self) -> None:
        # Clear text widgets
        for tab_info in self._message_tabs.values():
            text_widget = tab_info.text_widget
            text_widget.config(state="normal")
            text_widget.delete("1.0", tk.END)
            text_widget.config(state="disabled")

        # Clear duplicate detection cache
        self._recent_messages.clear()

        self.update_current_jackpot(value=0)
        self.update_prize_winner(nickname="Unknown", value="0", is_jackpot=True)
        self.update_prize_winner(nickname="Unknown", value="0")

    # ==================== Private Methods ====================
    def _initialize(self) -> None:
        container = ttk.Frame(master=self._frame)
        container.pack(fill="both", expand=True, padx=20, pady=10)

        # Create horizontal container for status and winners
        row_container = ttk.Frame(master=container)
        row_container.pack(fill="x", pady=(0, 10))

        self._setup_status_panel(parent=row_container)
        self._setup_winners_panel(parent=row_container)
        self._setup_messages_notebook(parent=container)

    def _setup_status_panel(self, parent: tk.Misc) -> None:
        status_frame = ttk.LabelFrame(master=parent, text="Status", padding=8)
        status_frame.pack(side="left", fill="both", expand=True)

        jackpot_container = ttk.Frame(master=status_frame)
        jackpot_container.pack(side="left", fill="both", expand=True)

        self._current_jackpot_label = ttk.Label(
            master=jackpot_container,
            font=("Consolas", 12, "bold"),
            foreground="#f97316",
            text=self._CURRENT_JACKPOT_LABEL_TEXT.format(value=0),
        )
        self._current_jackpot_label.pack(anchor="w")

    def _setup_winners_panel(self, parent: tk.Misc) -> None:
        winners_frame = ttk.LabelFrame(master=parent, text="Winners", padding=8)
        winners_frame.pack(side="right", fill="both", expand=True, padx=(8, 0))

        winners_container = ttk.Frame(master=winners_frame)
        winners_container.pack(fill="x")

        self._ultimate_prize_label = ttk.Label(
            master=winners_container,
            font=("Consolas", 11, "bold"),
            foreground="#fbbf24",
            text=self._JACKPOT_WINNER_TEXT.format(nickname="Unknown", value="0"),
        )
        self._ultimate_prize_label.pack(anchor="w")

        self._mini_prize_label = ttk.Label(
            master=winners_container,
            font=("Consolas", 11, "bold"),
            foreground="#34d399",
            text=self._MINI_JACKPOT_WINNER_TEXT.format(nickname="Unknown", value="0"),
        )
        self._mini_prize_label.pack(anchor="w", pady=(5, 0))

    def _setup_messages_notebook(self, parent: tk.Misc) -> None:
        messages_frame = ttk.LabelFrame(master=parent, text="Messages", padding=8)
        messages_frame.pack(fill="both", expand=True, pady=(5, 0))

        self._notebook = ttk.Notebook(master=messages_frame)
        self._notebook.pack(fill="both", expand=True)

        # Create tabs
        for tab_name in self._TABS:
            self._create_message_tab(tab_name=tab_name)

        # Setup focus management using helper
        UIHelpers.setup_focus_management(root_or_frame=self._frame, notebook=self._notebook)

    def _create_message_tab(self, tab_name: str) -> None:
        tab_frame = ttk.Frame(master=self._notebook)
        self._notebook.add(child=tab_frame, text=tab_name)

        text_container = ttk.Frame(master=tab_frame)
        text_container.pack(fill="both", expand=True)

        # Use factory to create text widget with scrollbar
        text_widget, scrollbar = UIFactory.create_text_widget(
            parent=text_container,
            height=18,
            state="disabled",
        )

        # Configure tags for this text widget
        for tag in MessageTag:
            font = ("Arial", 12, "bold") if tag != MessageTag.DEFAULT else ("Arial", 12)
            text_widget.tag_configure(tagName=tag.name, foreground=tag.value, font=font)

        # Prevent unwanted text selection using helper
        UIHelpers.prevent_text_selection(text_widget=text_widget)

        text_widget.pack(side="left", fill="both", expand=True)
        if scrollbar:
            scrollbar.pack(side="right", fill="y")

        # Store tab information
        self._message_tabs[tab_name] = MessageTabInfo(
            frame=tab_frame,
            text_widget=text_widget,
            scrollbar=scrollbar,
        )

    def _extract_message_content(self, message: str) -> str:
        if "]" in message and message.startswith("["):
            end_bracket = message.find("]")
            if end_bracket != -1:
                content = message[end_bracket + 1 :].strip()
                return content

        return message.strip()

    def _is_duplicate_message(self, message_content: str, now: datetime) -> bool:
        """Check if message is duplicate using in-memory cache.

        Performance: O(n) where n = min(100, total_messages)
        Much faster than parsing text widgets which is O(n*m*k)
        """
        for cached_content, cached_time in reversed(self._recent_messages):
            # Stop checking if we've gone past the duplicate window
            time_diff = abs((now - cached_time).total_seconds())
            if time_diff > DUPLICATE_WINDOW_SECONDS:
                break

            # Check if content matches
            if cached_content == message_content:
                return True

        return False

    def _add_message_to_tab(self, tab_name: str, tag: str, message: str) -> None:
        if tab_name not in self._message_tabs:
            return

        text_widget = self._message_tabs[tab_name].text_widget
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
