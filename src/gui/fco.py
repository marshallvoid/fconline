import asyncio
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Dict, Optional, TypedDict

import darkdetect
import sv_ttk
from loguru import logger

from src.gui.accounts_tab import AccountsTab
from src.gui.activity_log_tab import ActivityLogTab
from src.gui.notification_icon import NotificationIcon
from src.schemas.enums.message_tag import MessageTag
from src.services.fco import MainTool
from src.utils import files
from src.utils.contants import EVENT_CONFIGS_MAP, PROGRAM_NAME
from src.utils.platforms import PlatformManager
from src.utils.user_config import UserConfigManager


class RunningTool(TypedDict):
    tool: MainTool
    thread: threading.Thread


class MainWindow:
    def __init__(self) -> None:
        self._root = tk.Tk()
        self._root.title(string=PROGRAM_NAME)
        self._root.resizable(width=True, height=True)

        try:
            png_path = files.resource_path("assets/icon.png")
            icon = tk.PhotoImage(file=png_path)
            self._root.iconphoto(True, icon)

        except Exception:
            pass

        if PlatformManager.is_windows():
            try:
                ico_path = files.resource_path("assets/icon.ico")
                self._root.iconbitmap(ico_path)

            except Exception:
                pass

        # Track per-account running tool instances
        configs = UserConfigManager.load_configs()
        self._selected_event = configs.event or list(EVENT_CONFIGS_MAP.keys())[0]
        self._running_tools: Dict[str, RunningTool] = {}

        self._setup_ui()

    def run(self) -> None:
        logger.info(f"Running {PROGRAM_NAME}")

        def on_close() -> None:
            for tool in self._running_tools.values():
                tool["tool"].update_configs(is_running=False)

            self._root.destroy()

        self._root.protocol("WM_DELETE_WINDOW", on_close)

        sv_ttk.set_theme(darkdetect.theme() or "dark")

        try:
            style = ttk.Style(self._root)
            layout = style.layout("TNotebook.Tab")

            def _strip_focus(elements: Any) -> Any:
                if not isinstance(elements, (list, tuple)):
                    return elements

                cleaned = []
                for elem in elements:
                    if isinstance(elem, tuple) and elem:
                        name = elem[0]
                        opts = elem[1] if len(elem) > 1 else {}

                        if isinstance(name, str) and name.endswith(".focus"):
                            continue

                        if isinstance(opts, dict) and "children" in opts:
                            opts = dict(opts)
                            opts["children"] = _strip_focus(opts.get("children", []))
                            cleaned.append((name, opts))
                            continue

                        cleaned.append(elem)
                        continue

                    cleaned.append(elem)

                return cleaned

            cleaned_layout = _strip_focus(layout)
            style.layout("TNotebook.Tab", cleaned_layout)

        except Exception:
            pass

        self._root.mainloop()

    def _setup_ui(self) -> None:
        self._setup_notification_icon()
        self._setup_event_selection()
        self._setup_main_content()

        self._root.update_idletasks()
        width, height = self._root.winfo_reqwidth(), self._root.winfo_reqheight()
        x, y = self._root.winfo_screenwidth() - width, 0
        self._root.geometry(f"{width}x{height}+{x}+{y}")

    def _setup_notification_icon(self) -> None:
        notification_frame = ttk.Frame(self._root)
        notification_frame.pack(side="top", fill="x", padx=10, pady=(10, 0))

        # Spacer to push icon to right
        spacer = ttk.Frame(notification_frame)
        spacer.pack(side="left", fill="x", expand=True)

        # Notification icon
        self._notification_icon = NotificationIcon(notification_frame)
        self._notification_icon.frame.pack(side="right")

    def _setup_event_selection(self) -> None:
        event_selection_frame = ttk.LabelFrame(self._root, padding=10)
        event_selection_frame.pack(fill="x", padx=10, pady=(10, 5))

        event_var = tk.StringVar(value=self._selected_event)

        # Create dropdown menu for event selection
        event_label = ttk.Label(event_selection_frame, text="Select Event:")
        event_label.pack(anchor="w", pady=(0, 5))

        event_combobox = ttk.Combobox(
            event_selection_frame,
            textvariable=event_var,
            values=list(EVENT_CONFIGS_MAP.keys()),
            state="readonly",
            width=30,
        )
        event_combobox.pack(anchor="w", fill="x")

        def on_event_changed(_event: Optional[tk.Event] = None) -> None:
            # Get the selected event from combobox
            self._selected_event = event_var.get()

            # Update the accounts tab with new event configuration
            self._accounts_tab.selected_event = self._selected_event

            configs = UserConfigManager.load_configs()
            configs.event = self._selected_event
            UserConfigManager.save_configs(configs)

        event_combobox.bind("<<ComboboxSelected>>", on_event_changed)

    def _setup_main_content(self) -> None:
        main_container = ttk.Frame(self._root)
        main_container.pack(fill="both", expand=True, padx=10, pady=5)

        # Notebook for tabs
        self._notebook = ttk.Notebook(main_container, takefocus=False)
        self._notebook.pack(fill="both", expand=True)

        # Accounts tab
        self._accounts_tab = AccountsTab(
            parent=self._notebook,
            selected_event=self._selected_event,
            on_account_run=self._run_account,
            on_account_stop=self._stop_account,
        )
        self._notebook.add(self._accounts_tab.frame, text="Accounts")

        # Activity log tab
        self._activity_log_tab = ActivityLogTab(parent=self._notebook)
        self._notebook.add(self._activity_log_tab.frame, text="Activity Log")

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
                    self._root.after_cancel(self._focus_after_id)
                except Exception:
                    pass
                finally:
                    self._focus_after_id = None

            self._focus_after_id = self._root.after(10, _focus_current_tab)

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
        self._root.after_idle(_schedule_focus_current_tab)

    def _run_account(
        self,
        username: str,
        password: str,
        spin_action: int,
        target_special_jackpot: int,
        close_when_jackpot_won: bool,
    ) -> None:
        # Avoid starting duplicate runner for same username
        if username in self._running_tools:
            self._activity_log_tab.add_message(
                tag=MessageTag.WARNING,
                message=f"Account '{username}' is already running",
            )
            return

        # Build a dedicated tool instance for this account
        tool = MainTool(
            event_config=EVENT_CONFIGS_MAP[self._selected_event],
            username=username,
            password=password,
            spin_action=spin_action,
            target_special_jackpot=target_special_jackpot,
            close_when_jackpot_won=close_when_jackpot_won,
        )

        # Announce start in activity log
        spin_action_name = EVENT_CONFIGS_MAP[self._selected_event].spin_actions[spin_action - 1]
        message = (
            f"Running account '{username}' with action '{spin_action_name}'"
            f" until target '{target_special_jackpot:,}'"
        )
        self._activity_log_tab.add_message(tag=MessageTag.INFO, message=message)

        def on_close_browser() -> None:
            def _cb() -> None:
                self._stop_account(username)

            self._root.after(0, _cb)

        def on_add_message(tag: MessageTag, message: str) -> None:
            def _cb() -> None:
                self._activity_log_tab.add_message(tag=tag, message=f"[{username}] {message}")

            self._root.after(0, _cb)

        def on_add_notification(nickname: str, jackpot_value: str) -> None:
            def _cb() -> None:
                self._notification_icon.add_notification(nickname=nickname, jackpot_value=jackpot_value)

            self._root.after(0, _cb)

        def on_update_current_jackpot(value: int) -> None:
            def _cb() -> None:
                self._activity_log_tab.update_current_jackpot(value=value)

            self._root.after(0, _cb)

        def on_update_ultimate_prize_winner(nickname: str, value: str) -> None:
            def _cb() -> None:
                self._activity_log_tab.update_ultimate_prize_winner(nickname=nickname, value=value)

            self._root.after(0, _cb)

        def on_update_mini_prize_winner(nickname: str, value: str) -> None:
            def _cb() -> None:
                self._activity_log_tab.update_mini_prize_winner(nickname=nickname, value=value)

            self._root.after(0, _cb)

        tool.update_configs(
            screen_width=self._root.winfo_screenwidth(),
            screen_height=self._root.winfo_screenheight(),
            req_width=self._root.winfo_reqwidth(),
            req_height=self._root.winfo_reqheight(),
            is_running=True,
            event_config=EVENT_CONFIGS_MAP[self._selected_event],
            username=username,
            password=password,
            spin_action=spin_action,
            target_special_jackpot=target_special_jackpot,
            close_when_jackpot_won=close_when_jackpot_won,
            current_jackpot=0,
            close_browser=on_close_browser,
            add_message=on_add_message,
            add_notification=on_add_notification,
            update_current_jackpot=on_update_current_jackpot,
            update_ultimate_prize_winner=on_update_ultimate_prize_winner,
            update_mini_prize_winner=on_update_mini_prize_winner,
        )

        # Runner thread
        def handle_account_task() -> None:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(tool.run())

            except Exception as error:
                self._root.after(0, messagebox.showerror, "❌ Error", f"Account '{username}': {error}")

            finally:
                # Cleanup entry once finished
                self._running_tools.pop(username, None)

                # Reflect running state removal in UI
                def _cb() -> None:
                    self._accounts_tab.running_usernames = set(self._running_tools.keys())

                self._root.after(0, _cb)

        thread = threading.Thread(target=handle_account_task, daemon=True)
        self._running_tools[username] = {"tool": tool, "thread": thread}
        thread.start()

    def _stop_account(self, username: str) -> None:
        entry = self._running_tools.get(username)
        if not entry:
            return

        tool = entry.get("tool")
        if not tool:
            return

        # Signal stop; MainTool.run will close resources in finally
        tool.update_configs(is_running=False)
