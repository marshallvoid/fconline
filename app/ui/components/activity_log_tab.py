import tkinter as tk
from datetime import datetime
from tkinter import ttk
from typing import Dict

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

    def __init__(self, parent: tk.Misc) -> None:
        self._frame = ttk.Frame(master=parent)

        self._message_tabs: Dict[str, MessageTabInfo] = {}

        self._setup_ui()

    @property
    def frame(self) -> ttk.Frame:
        return self._frame

    # ==================== Public Methods ====================
    def add_message(self, tag: MessageTag, message: str, compact: bool = False) -> None:
        if not message.strip():
            return

        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        if compact:
            message_content = self._extract_message_content(message=message)
            if self._is_message_duplicate(message_content=message_content, now_timestamp=timestamp):
                return

            timestamped_message = f"[{timestamp}] {message_content}"
        else:
            timestamped_message = f"[{timestamp}] {message.strip()}"

        if tag != MessageTag.WEBSOCKET:
            self._add_message_to_tab(tab_name="All", tag=tag.name, message=timestamped_message)
        self._add_message_to_tab(tab_name=tag.tab_name, tag=tag.name, message=timestamped_message)

    def clear_messages(self) -> None:
        for tab_info in self._message_tabs.values():
            text_widget = tab_info.text_widget
            text_widget.config(state="normal")
            text_widget.delete("1.0", tk.END)
            text_widget.config(state="disabled")

        self.update_current_jackpot(value=0)
        self.update_prize_winner(nickname="Unknown", value="0", is_jackpot=True)
        self.update_prize_winner(nickname="Unknown", value="0")

    def update_current_jackpot(self, value: int) -> None:
        self._current_jackpot_label.config(text=self._CURRENT_JACKPOT_LABEL_TEXT.format(value=value))

    def update_prize_winner(self, nickname: str, value: str, is_jackpot: bool = False) -> None:
        if is_jackpot:
            self._ultimate_prize_label.config(text=self._JACKPOT_WINNER_TEXT.format(nickname=nickname, value=value))
        else:
            self._mini_prize_label.config(text=self._MINI_JACKPOT_WINNER_TEXT.format(nickname=nickname, value=value))

    # ==================== Private Methods ====================
    def _setup_ui(self) -> None:
        container = ttk.Frame(master=self._frame)
        container.pack(fill="both", expand=True, padx=20, pady=10)

        # Create horizontal container for status and winners
        row_container = ttk.Frame(master=container)
        row_container.pack(fill="x", pady=(0, 10))

        self._setup_status_panel(parent=row_container)
        self._setup_winners_panel(parent=row_container)
        self._setup_messages_notebook(parent=container)

    def _setup_status_panel(self, parent: tk.Misc) -> None:
        status_frame = UIFactory.create_label_frame(parent=parent, text="Status", padding=8)
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
        winners_frame = UIFactory.create_label_frame(parent=parent, text="Winners", padding=8)
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
        messages_frame = UIFactory.create_label_frame(parent=parent, text="Messages", padding=8)
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
            scrollbar=scrollbar,  # type: ignore
        )

    def _extract_message_content(self, message: str) -> str:
        if "]" in message and message.startswith("["):
            end_bracket = message.find("]")
            if end_bracket != -1:
                content = message[end_bracket + 1 :].strip()
                return content

        return message.strip()

    def _is_message_duplicate(self, message_content: str, now_timestamp: str) -> bool:
        now_dt = datetime.strptime(now_timestamp, "%d/%m/%Y %H:%M:%S")
        for tab_info in self._message_tabs.values():
            text_widget = tab_info.text_widget
            current_text = text_widget.get("1.0", tk.END)

            lines = current_text.split("\n")
            for line in reversed(lines):
                line = line.strip()
                if not line:
                    continue

                content, timestamp_str = self._extract_line_content(line=line)
                if content != message_content or not timestamp_str:
                    continue

                past_dt = datetime.strptime(timestamp_str, "%d/%m/%Y %H:%M:%S")
                if abs((now_dt - past_dt).total_seconds()) <= DUPLICATE_WINDOW_SECONDS:
                    return True

        return False

    def _extract_line_content(self, line: str) -> tuple[str, str]:
        if not line.startswith("["):
            return line.strip(), ""

        try:
            ts_end = line.index("]")
            timestamp = line[1:ts_end]
        except ValueError:
            return line.strip(), ""

        rest = line[ts_end + 1 :]

        # Strip optional "[username]"
        if rest.startswith("[") and "]" in rest:
            rest = rest[rest.index("]") + 1 :]

        return rest.strip(), timestamp.strip()

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
