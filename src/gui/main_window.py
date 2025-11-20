import contextlib
import threading
import tkinter as tk
from tkinter import ttk
from typing import Any, Awaitable, Callable, Dict, Mapping, Optional, Sequence

import darkdetect  # type: ignore
import sv_ttk
from dishka import AsyncContainer
from loguru import logger

from src.core.configs import Settings
from src.core.managers.config import config_mgr
from src.core.managers.file import file_mgr
from src.core.managers.platform import platform_mgr
from src.gui.accounts_tab import AccountsTab
from src.gui.activity_log_tab import ActivityLogTab
from src.gui.notification_icon import NotificationIcon
from src.schemas.configs import Account
from src.schemas.enums.message_tag import MessageTag
from src.services.main_service import MainTool
from src.utils import conc, hlp
from src.utils.contants import EVENT_CONFIGS_MAP


class MainWindow:
    def __init__(self, container: AsyncContainer, settings: Settings) -> None:
        self._container = container
        self._settings = settings

        self._root = tk.Tk()
        self._root.title(string=self._settings.program_name)
        self._root.resizable(width=False, height=False)

        with contextlib.suppress(Exception):
            png_path = file_mgr.get_resource_path(relative_path="assets/icon.png")
            icon = tk.PhotoImage(file=png_path)
            self._root.iconphoto(True, icon)

        if platform_mgr.is_windows():
            with contextlib.suppress(Exception):
                ico_path = file_mgr.get_resource_path(relative_path="assets/icon.ico")
                self._root.iconbitmap(ico_path)

        self._configs = config_mgr.load_configs()
        self._selected_event = self._configs.event

        self._running_tools: Dict[str, MainTool] = {}

        self._setup_ui()

    def run(self) -> None:
        logger.info(f"Running {self._settings.program_name}")

        def on_close() -> None:
            if self._running_tools:
                _ = [setattr(tool, "is_running", False) for tool in self._running_tools.values()]  # type: ignore

                # Close tools in separate threads to avoid blocking the UI
                def close_tools_concurrently() -> None:
                    tasks: Sequence[tuple[Callable[..., Awaitable[Any]], Sequence[Any], Mapping[str, Any]]] = [
                        (tool.close, (), {}) for tool in self._running_tools.values()
                    ]
                    conc.run_many_in_threads(tasks=tasks, timeout=5.0)

                # Start closing process in background thread
                threading.Thread(target=close_tools_concurrently, daemon=True).start()

            # Destroy the root window immediately
            self._root.destroy()

        self._root.protocol(name="WM_DELETE_WINDOW", func=on_close)

        sv_ttk.set_theme(theme=darkdetect.theme() or "dark")

        with contextlib.suppress(Exception):
            style = ttk.Style(master=self._root)
            layout = style.layout(style="TNotebook.Tab")

            def strip_focus(elements: Any) -> Any:
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
                            opts["children"] = strip_focus(elements=opts.get("children", []))
                            cleaned.append((name, opts))
                            continue

                        cleaned.append(elem)
                        continue

                    cleaned.append(elem)

                return cleaned

            cleaned_layout = strip_focus(elements=layout)
            style.layout(style="TNotebook.Tab", layoutspec=cleaned_layout)

        self._root.mainloop()

    def _setup_ui(self) -> None:
        # ==================== Notification Icon ====================
        notification_frame = ttk.Frame(master=self._root)
        notification_frame.pack(side="top", fill="x", padx=10, pady=(10, 0))

        # Spacer to push icon to right
        spacer = ttk.Frame(master=notification_frame)
        spacer.pack(side="left", fill="x", expand=True)

        self._notification_icon = NotificationIcon(parent=notification_frame, configs=self._configs)
        self._notification_icon.frame.pack(side="right")

        # ==================== Event Selection ====================
        event_selection_frame = ttk.LabelFrame(master=self._root, padding=10, text="Select Event:")
        event_selection_frame.pack(fill="x", padx=10, pady=(10, 5))

        # Event selection combobox
        self._event_var = tk.StringVar(value=self._selected_event)
        self._event_combobox = ttk.Combobox(
            master=event_selection_frame,
            textvariable=self._event_var,
            values=list(EVENT_CONFIGS_MAP.keys()),
            state="readonly",
            width=30,
        )

        # Update selected event when changed
        def on_combobox_select_changed() -> None:
            # Get the selected event from combobox
            self._selected_event = self._event_var.get()

            # Update the accounts tab with new event configuration
            self._accounts_tab.selected_event = self._selected_event

            self._configs.event = self._selected_event
            config_mgr.save_configs(configs=self._configs)

            # Clear selection to prevent text highlighting
            self._event_combobox.selection_clear()

        self._event_combobox.bind(sequence="<<ComboboxSelected>>", func=lambda _: on_combobox_select_changed())
        self._event_combobox.pack(anchor="w", fill="x", pady=(0, 10))

        def on_auto_refresh_changed() -> None:
            self._configs.auto_refresh = self._auto_refresh_var.get()
            config_mgr.save_configs(configs=self._configs)

        # Auto refresh checkbox
        self._auto_refresh_var = tk.BooleanVar(value=self._configs.auto_refresh)
        self._auto_refresh_checkbox = ttk.Checkbutton(
            master=event_selection_frame,
            text="Auto Refresh after 1 hour",
            variable=self._auto_refresh_var,
            command=on_auto_refresh_changed,
        )
        self._auto_refresh_checkbox.pack(anchor="w")

        # Spin delay input
        spin_delay_frame = ttk.Frame(master=event_selection_frame)
        spin_delay_frame.pack(anchor="w", fill="x", pady=(10, 0))

        spin_delay_label = ttk.Label(master=spin_delay_frame, text="Spin Delay (seconds):")
        spin_delay_label.pack(side="left", padx=(0, 5))

        def validate_spin_delay(value: str) -> bool:
            if value == "":
                return True
            try:
                num = float(value)
                return num >= 0
            except ValueError:
                return False

        def on_spin_delay_changed(*args: Any) -> None:
            try:
                value = self._spin_delay_var.get()
                if value == "":
                    delay = 0.0
                else:
                    delay = float(value)
                    if delay < 0:
                        delay = 0.0
                        self._spin_delay_var.set(str(delay))

                self._configs.spin_delay_seconds = delay
                config_mgr.save_configs(configs=self._configs)
            except ValueError:
                self._spin_delay_var.set(str(self._configs.spin_delay_seconds))

        vcmd = (self._root.register(validate_spin_delay), "%P")
        self._spin_delay_var = tk.StringVar(value=str(self._configs.spin_delay_seconds))
        self._spin_delay_var.trace_add("write", on_spin_delay_changed)
        self._spin_delay_entry = ttk.Entry(
            master=spin_delay_frame,
            textvariable=self._spin_delay_var,
            validate="key",
            validatecommand=vcmd,
            width=15,
        )
        self._spin_delay_entry.pack(side="left")

        # ==================== All Control Buttons ====================
        all_control_buttons_frame = ttk.LabelFrame(master=self._root, padding=10, text="Actions")
        all_control_buttons_frame.pack(fill="x", padx=10, pady=(0, 5))

        # Run All button
        self._run_all_btn = ttk.Button(
            master=all_control_buttons_frame,
            text="Run All",
            style="Accent.TButton",
            state="normal",
            command=self._run_all_accounts,
        )
        self._run_all_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))

        # Stop All button
        self._stop_all_btn = ttk.Button(
            master=all_control_buttons_frame,
            text="Stop All",
            state="disabled",
            command=self._stop_all_accounts,
        )
        self._stop_all_btn.pack(side="left", fill="x", expand=True, padx=2.5)

        # Refresh All Page button
        self._refresh_all_page_btn = ttk.Button(
            master=all_control_buttons_frame,
            text="Refresh All",
            state="disabled",
            command=lambda: self._accounts_tab.refresh_all_pages(),
        )
        self._refresh_all_page_btn.pack(side="left", fill="x", expand=True, padx=(5, 0))

        # ==================== Tabs Content ====================
        tabs_container = ttk.Frame(master=self._root)
        tabs_container.pack(fill="both", expand=True, padx=10, pady=5)

        # Notebook for tabs
        self._notebook = ttk.Notebook(master=tabs_container, takefocus=False)
        self._notebook.pack(fill="both", expand=True)

        # Accounts tab
        self._accounts_tab = AccountsTab(
            parent=self._notebook,
            selected_event=self._selected_event,
            configs=self._configs,
            on_account_run=self._run_account,
            on_account_stop=self._stop_account,
            on_refresh_page=self._refresh_page,
        )
        self._notebook.add(child=self._accounts_tab.frame, text="Accounts")

        # Activity log tab
        self._activity_log_tab = ActivityLogTab(parent=self._notebook)
        self._notebook.add(child=self._activity_log_tab.frame, text="Activity Log")

        self._focus_after_id: Optional[str] = None

        def schedule_focus_current_tab() -> None:
            def _focus_current_tab() -> None:
                with contextlib.suppress(tk.TclError):
                    current = self._notebook.nametowidget(name=self._notebook.select())
                    if current and isinstance(current, (tk.Frame, ttk.Frame)):
                        current.focus_set()

            if self._focus_after_id:
                with contextlib.suppress(Exception):
                    self._root.after_cancel(id=self._focus_after_id)
                self._focus_after_id = None

            self._focus_after_id = self._root.after(ms=10, func=_focus_current_tab)

        def on_notebook_tab_changed() -> None:
            with contextlib.suppress(tk.TclError):
                current = self._notebook.nametowidget(name=self._notebook.select())
                if current and isinstance(current, (tk.Frame, ttk.Frame)):
                    current.focus_set()

            schedule_focus_current_tab()

        # Update selected event when changed
        self._notebook.bind(sequence="<<NotebookTabChanged>>", func=lambda _: on_notebook_tab_changed())
        self._notebook.bind(sequence="<ButtonRelease-1>", func=lambda _: schedule_focus_current_tab())
        self._root.after_idle(func=schedule_focus_current_tab)

        # ==================== Adjust Window Size ====================
        self._root.update_idletasks()
        _, _, width, height, x, y = hlp.get_window_position(child_frame=self._root)
        self._root.geometry(f"{width}x{height}+{x}+{y}")

    def _update_all_buttons_state(self) -> None:
        total_running_accounts = len(self._running_tools)
        is_all_accounts_running = total_running_accounts == len(self._accounts_tab.accounts)

        self._run_all_btn.config(state="normal" if not is_all_accounts_running else "disabled")
        self._stop_all_btn.config(state="normal" if bool(total_running_accounts) else "disabled")
        self._refresh_all_page_btn.config(state="normal" if bool(total_running_accounts) else "disabled")

    def _run_account(self, account: Account) -> None:
        # Avoid starting duplicate runner for same username
        if account.username in self._running_tools:
            message = f"Account '{account.username}' is already running"
            self._activity_log_tab.add_message(tag=MessageTag.WARNING, message=message)
            return

        # Log spin delay configuration
        if self._configs.spin_delay_seconds > 0:
            delay_message = f"Spin delay: {self._configs.spin_delay_seconds} seconds between spins"
        else:
            delay_message = "Spin delay: Disabled (spin on every websocket update)"
        self._activity_log_tab.add_message(tag=MessageTag.INFO, message=delay_message, compact=True)

        # Update browser position in accounts tab
        browser_index = len(self._running_tools)
        self._accounts_tab.update_browser_position(username=account.username, browser_index=browser_index)

        # Log running message
        message = account.running_message(selected_event=self._selected_event)
        self._activity_log_tab.add_message(tag=MessageTag.INFO, message=message)

        new_tool = MainTool(
            is_running=True,
            browser_index=browser_index,
            screen_width=self._root.winfo_screenwidth(),
            screen_height=self._root.winfo_screenheight(),
            req_width=self._root.winfo_reqwidth(),
            req_height=self._root.winfo_reqheight(),
            event_config=EVENT_CONFIGS_MAP[self._selected_event],
            account=account,
            auto_refresh=self._configs.auto_refresh,
            spin_delay_seconds=self._configs.spin_delay_seconds,
            **self._build_callbacks(account=account),
        )
        self._running_tools[account.username] = new_tool

        conc.run_in_thread(coro_func=new_tool.run)
        self._update_all_buttons_state()

    def _stop_account(self, username: str) -> None:
        if username not in self._running_tools:
            message = f"Account '{username}' is not running"
            self._activity_log_tab.add_message(tag=MessageTag.WARNING, message=message)
            return

        running_tool = self._running_tools.pop(username)
        running_tool.is_running = False

        conc.run_in_thread(coro_func=running_tool.close)

        self._update_all_buttons_state()

    def _refresh_page(self, username: str) -> None:
        if username not in self._running_tools:
            message = f"Account '{username}' is not running"
            self._activity_log_tab.add_message(tag=MessageTag.WARNING, message=message)
            return

        running_tool = self._running_tools[username]
        if not running_tool.page:
            message = f"Account '{username}' does not have an active page to refresh"
            self._activity_log_tab.add_message(tag=MessageTag.WARNING, message=message)
            return

        conc.run_in_thread(coro_func=running_tool.page.reload)

    def _run_all_accounts(self) -> None:
        self._accounts_tab.run_all_accounts()
        self._update_all_buttons_state()

    def _stop_all_accounts(self) -> None:
        self._accounts_tab.stop_all_accounts()
        self._update_all_buttons_state()

    def _build_callbacks(self, account: Account) -> Dict[str, Callable[..., None]]:
        def on_account_won(username: str) -> None:
            def _cb() -> None:
                self._accounts_tab.mark_account_as_won(username=username)
                if account.close_on_jp_win:
                    self._stop_account(username=username)

            self._root.after(ms=0, func=_cb)

        def on_add_message(tag: MessageTag, message: str, compact: bool = False) -> None:
            def _cb() -> None:
                self._activity_log_tab.add_message(tag=tag, message=f"[{account.username}] {message}", compact=compact)

            self._root.after(ms=0, func=_cb)

        def on_add_notification(nickname: str, jackpot_value: str) -> None:
            def _cb() -> None:
                self._notification_icon.add_notification(nickname=nickname, jackpot_value=jackpot_value)

            self._root.after(ms=0, func=_cb)

        def on_update_cur_jp(value: int) -> None:
            def _cb() -> None:
                self._activity_log_tab.update_cur_jp(value=value)

            self._root.after(ms=0, func=_cb)

        def on_update_prize_winner(nickname: str, value: str, is_jackpot: bool = False) -> None:
            def _cb() -> None:
                self._activity_log_tab.update_prize_winner(nickname=nickname, value=value, is_jackpot=is_jackpot)

            self._root.after(ms=0, func=_cb)

        def on_update_info_display(username: str) -> None:
            def _cb() -> None:
                self._accounts_tab.update_info_display(username=username)

            self._root.after(ms=0, func=_cb)

        return {
            on_account_won.__name__: on_account_won,
            on_add_message.__name__: on_add_message,
            on_add_notification.__name__: on_add_notification,
            on_update_cur_jp.__name__: on_update_cur_jp,
            on_update_prize_winner.__name__: on_update_prize_winner,
            on_update_info_display.__name__: on_update_info_display,
        }
