import contextlib
import tkinter as tk
from datetime import datetime
from tkinter import ttk
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.enums.message_tag import MessageTag
from app.utils.contants import DUPLICATE_WINDOW_SECONDS


class MessageTabInfo(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    frame: ttk.Frame
    text_widget: tk.Text
    scrollbar: ttk.Scrollbar


class ActivityLogTab:
    _TABS = ["All", "Game Events", "Rewards", "System", "WebSockets"]

    _CUR_JP_LABEL_TEXT = "Current Jackpot: {value:,}"
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

        # Add timestamp to message for logging purposes
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        # If compact mode is enabled, remove username prefix and check for duplicates
        if compact:
            message_content = self._extract_message_content(message=message)
            if self._is_message_duplicate(message_content=message_content, now_timestamp=timestamp):
                return  # Skip duplicate message within time window

            # Use message content without username prefix for compact mode
            timestamped_message = f"[{timestamp}] {message_content}"
        else:
            # Keep original message with username prefix for non-compact mode
            timestamped_message = f"[{timestamp}] {message.strip()}"

        # Distribute message to relevant tabs based on message type
        if tag != MessageTag.WEBSOCKET:
            self._add_message_to_tab(tab_name="All", tag=tag.name, message=timestamped_message)
        self._add_message_to_tab(tab_name=tag.tab_name, tag=tag.name, message=timestamped_message)

    def clear_messages(self) -> None:
        for tab_info in self._message_tabs.values():
            text_widget = tab_info.text_widget
            text_widget.config(state="normal")
            text_widget.delete("1.0", tk.END)
            text_widget.config(state="disabled")

        self.update_cur_jp(value=0)
        self.update_prize_winner(nickname="Unknown", value="0", is_jackpot=True)
        self.update_prize_winner(nickname="Unknown", value="0")

    def update_cur_jp(self, value: int) -> None:
        self._current_jackpot_label.config(text=self._CUR_JP_LABEL_TEXT.format(value=value))

    def update_prize_winner(self, nickname: str, value: str, is_jackpot: bool = False) -> None:
        if is_jackpot:
            self._ultimate_prize_label.config(text=self._JACKPOT_WINNER_TEXT.format(nickname=nickname, value=value))
        else:
            self._mini_prize_label.config(text=self._MINI_JACKPOT_WINNER_TEXT.format(nickname=nickname, value=value))

    # ==================== Private Methods ====================
    def _setup_ui(self) -> None:
        container = ttk.Frame(master=self._frame)
        container.pack(fill="both", expand=True, padx=20, pady=10)

        # Create a horizontal container for jackpot status and last winners
        row_container = ttk.Frame(master=container)
        row_container.pack(fill="x", pady=(0, 10))

        # Jackpot Status
        jackpot_status_frame = ttk.LabelFrame(master=row_container, text="Status", padding=8)
        jackpot_status_frame.pack(side="left", fill="both", expand=True)

        jackpot_container = ttk.Frame(master=jackpot_status_frame)
        jackpot_container.pack(side="left", fill="both", expand=True)

        self._current_jackpot_label = ttk.Label(
            master=jackpot_container,
            font=("Consolas", 12, "bold"),
            foreground="#f97316",
            text=self._CUR_JP_LABEL_TEXT.format(value=0),
        )
        self._current_jackpot_label.pack(anchor="w")

        # Winners Display
        winners_frame = ttk.LabelFrame(master=row_container, text="Winners", padding=8)
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

        # Messages Tab Control
        messages_frame = ttk.LabelFrame(master=container, text="Messages", padding=8)
        messages_frame.pack(fill="both", expand=True, pady=(5, 0))

        # Create notebook for tabs
        self._notebook = ttk.Notebook(master=messages_frame)
        self._notebook.pack(fill="both", expand=True)

        # Create tabs
        for tab_name in self._TABS:
            self._create_message_tab(tab_name=tab_name)

        # Setup focus handling to prevent text selection issues
        self._focus_after_id: Optional[str] = None

        def schedule_focus_current_tab() -> None:
            def _focus_current_tab() -> None:
                with contextlib.suppress(tk.TclError):
                    current = self._notebook.nametowidget(name=self._notebook.select())
                    if current and isinstance(current, (tk.Frame, ttk.Frame)):
                        current.focus_set()

            if self._focus_after_id:
                with contextlib.suppress(Exception):
                    self._frame.after_cancel(id=self._focus_after_id)
                self._focus_after_id = None

            self._focus_after_id = self._frame.after(ms=10, func=_focus_current_tab)

        def on_notebook_tab_changed() -> None:
            with contextlib.suppress(tk.TclError):
                current = self._notebook.nametowidget(name=self._notebook.select())
                if current and isinstance(current, (tk.Frame, ttk.Frame)):
                    current.focus_set()

            schedule_focus_current_tab()

        self._notebook.bind(sequence="<<NotebookTabChanged>>", func=lambda _: on_notebook_tab_changed())
        self._notebook.bind(sequence="<ButtonRelease-1>", func=lambda _: schedule_focus_current_tab())
        self._frame.after_idle(func=schedule_focus_current_tab)

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

    def _create_message_tab(self, tab_name: str) -> None:
        tab_frame = ttk.Frame(master=self._notebook)
        self._notebook.add(child=tab_frame, text=tab_name)

        text_container = ttk.Frame(master=tab_frame)
        text_container.pack(fill="both", expand=True)

        text_widget = tk.Text(
            master=text_container,
            wrap=tk.WORD,
            height=18,
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
            text_widget.tag_configure(tagName=tag.name, foreground=tag.value, font=font)

        # Bind events to prevent unwanted text selection
        text_widget.bind(sequence="<Button-1>", func=lambda _: text_widget.tag_remove("sel", "1.0", tk.END))
        text_widget.bind(sequence="<B1-Motion>", func=lambda _: text_widget.tag_remove("sel", "1.0", tk.END))
        text_widget.bind(sequence="<Double-Button-1>", func=lambda _: text_widget.tag_remove("sel", "1.0", tk.END))

        scrollbar = ttk.Scrollbar(master=text_container, orient="vertical")
        text_widget.configure(yscrollcommand=scrollbar.set)
        scrollbar.configure(command=text_widget.yview)

        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Store tab information
        self._message_tabs[tab_name] = MessageTabInfo(frame=tab_frame, text_widget=text_widget, scrollbar=scrollbar)

    def _extract_message_content(self, message: str) -> str:
        # Remove username prefix if present (e.g., "[username] message" -> "message")
        if "]" in message and message.startswith("["):
            # Find the first "]" and extract content after it
            end_bracket = message.find("]")
            if end_bracket != -1:
                content = message[end_bracket + 1 :].strip()
                return content

        # If no username prefix, return the message as is
        return message.strip()

    def _is_message_duplicate(self, message_content: str, now_timestamp: str) -> bool:
        now_dt = datetime.strptime(now_timestamp, "%d/%m/%Y %H:%M:%S")
        for tab_info in self._message_tabs.values():
            text_widget = tab_info.text_widget
            current_text = text_widget.get("1.0", tk.END)

            # Check if message content exists in current tab within the time window
            lines = current_text.split("\n")
            for line in reversed(lines):
                line = line.strip()
                if not line:
                    continue

                # Extract content and timestamp
                content, timestamp_str = self._extract_line_content(line=line)
                if content != message_content or not timestamp_str:
                    continue

                past_dt = datetime.strptime(timestamp_str, "%d/%m/%Y %H:%M:%S")
                if abs((now_dt - past_dt).total_seconds()) <= DUPLICATE_WINDOW_SECONDS:
                    return True

        return False

    def _extract_line_content(self, line: str) -> tuple[str, str]:
        # Expect format "[dd/mm/yyyy HH:MM:SS][username] message..."
        if not line.startswith("["):
            return line.strip(), ""

        try:
            ts_end = line.index("]")
            timestamp = line[1:ts_end]
        except ValueError:  # no closing bracket
            return line.strip(), ""

        rest = line[ts_end + 1 :]

        # Strip optional "[username]"
        if rest.startswith("[") and "]" in rest:
            rest = rest[rest.index("]") + 1 :]

        return rest.strip(), timestamp.strip()
