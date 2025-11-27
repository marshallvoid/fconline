import contextlib
import threading
import tkinter as tk
from tkinter import ttk
from typing import Any, Awaitable, Callable, Dict, Mapping, Sequence

import darkdetect  # type: ignore
import sv_ttk
from dishka import AsyncContainer
from loguru import logger

from app.core.managers.config import config_mgr
from app.core.managers.file import file_mgr
from app.core.managers.platform import platform_mgr
from app.core.settings import Settings
from app.schemas.configs import Account
from app.schemas.enums.message_tag import MessageTag
from app.services.main_service import MainService
from app.ui.components.accounts_tab import AccountsTab
from app.ui.components.activity_log_tab import ActivityLogTab
from app.ui.components.notification_icon import NotificationIcon
from app.ui.components.update_dialog import UpdateDialog
from app.ui.utils.ui_factory import UIFactory
from app.ui.utils.ui_helpers import UIHelpers
from app.utils.concurrency import run_in_thread, run_many_in_threads
from app.utils.constants import EVENT_CONFIGS_MAP
from app.utils.helpers import get_window_position


class MainWindow:
    def __init__(self, container: AsyncContainer, settings: Settings) -> None:
        self._container = container
        self._settings = settings

        self._root = tk.Tk()
        self._root.title(string=self._settings.program_name)
        self._root.resizable(width=False, height=False)

        self._setup_window_icon()

        self._configs = config_mgr.load_configs()
        self._selected_event = self._configs.event

        self._running_tools: Dict[str, MainService] = {}

        self._setup_ui()

    def run(self) -> None:
        logger.info(f"Running {self._settings.program_name}")

        self._root.protocol(name="WM_DELETE_WINDOW", func=self._on_close)
        self._setup_theme()
        self._root.mainloop()

    def _setup_window_icon(self) -> None:
        with contextlib.suppress(Exception):
            png_path = file_mgr.get_resource_path(relative_path="assets/icon.png")
            icon = tk.PhotoImage(file=png_path)
            self._root.iconphoto(True, icon)

        if platform_mgr.is_windows():
            with contextlib.suppress(Exception):
                ico_path = file_mgr.get_resource_path(relative_path="assets/icon.ico")
                self._root.iconbitmap(ico_path)

    def _setup_theme(self) -> None:
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

    def _on_close(self) -> None:
        if self._running_tools:
            _ = [setattr(tool, "is_running", False) for tool in self._running_tools.values()]  # type: ignore

            def close_tools_concurrently() -> None:
                tasks: Sequence[tuple[Callable[..., Awaitable[Any]], Sequence[Any], Mapping[str, Any]]] = [
                    (tool.close, (), {}) for tool in self._running_tools.values()
                ]
                run_many_in_threads(tasks=tasks, timeout=5.0)

            threading.Thread(target=close_tools_concurrently, daemon=True).start()

        self._root.destroy()

    def _setup_ui(self) -> None:
        self._setup_notification_icon()
        self._setup_event_selection()
        self._setup_control_buttons()
        self._setup_tabs()
        self._adjust_window_size()

    def _setup_notification_icon(self) -> None:
        notification_frame = ttk.Frame(master=self._root)
        notification_frame.pack(side="top", fill="x", padx=10, pady=(10, 0))

        # Spacer to push icon to right
        spacer = ttk.Frame(master=notification_frame)
        spacer.pack(side="left", fill="x", expand=True)

        self._notification_icon = NotificationIcon(parent=notification_frame, configs=self._configs)
        self._notification_icon.frame.pack(side="right")

    def _setup_event_selection(self) -> None:
        event_frame = UIFactory.create_label_frame(parent=self._root, text="Select Event:")
        event_frame.pack(fill="x", padx=10, pady=(10, 5))

        # Event selection combobox
        self._event_var = tk.StringVar(value=self._selected_event)
        self._event_combobox = UIFactory.create_combobox(
            parent=event_frame,
            textvariable=self._event_var,
            values=list(EVENT_CONFIGS_MAP.keys()),
            width=30,
        )

        def on_combobox_select_changed() -> None:
            self._selected_event = self._event_var.get()
            self._accounts_tab.selected_event = self._selected_event

            self._configs.event = self._selected_event
            config_mgr.save_configs(configs=self._configs)

            self._event_combobox.selection_clear()

        self._event_combobox.bind(sequence="<<ComboboxSelected>>", func=lambda _: on_combobox_select_changed())
        self._event_combobox.pack(anchor="w", fill="x", pady=(0, 10))

        # Auto refresh checkbox
        def on_auto_refresh_changed() -> None:
            self._configs.auto_refresh = self._auto_refresh_var.get()
            config_mgr.save_configs(configs=self._configs)

        self._auto_refresh_var = tk.BooleanVar(value=self._configs.auto_refresh)
        self._auto_refresh_checkbox = ttk.Checkbutton(
            master=event_frame,
            text="Auto Refresh after 1 hour",
            variable=self._auto_refresh_var,
            command=on_auto_refresh_changed,
        )
        self._auto_refresh_checkbox.pack(anchor="w")

    def _setup_control_buttons(self) -> None:
        buttons_frame = UIFactory.create_label_frame(parent=self._root, text="Actions")
        buttons_frame.pack(fill="x", padx=10, pady=(0, 5))

        button_frame, buttons = UIFactory.create_button_group(
            parent=buttons_frame,
            buttons=[
                {
                    "text": "Run All",
                    "style": "Accent.TButton",
                    "state": "normal",
                    "command": self._run_all_accounts,
                },
                {
                    "text": "Stop All",
                    "state": "disabled",
                    "command": self._stop_all_accounts,
                },
                {
                    "text": "Refresh All",
                    "state": "disabled",
                    "command": self._refresh_all_pages,
                },
                {
                    "text": "Check for Updates",
                    "state": "normal",
                    "command": lambda: UpdateDialog(parent=self._root),
                },
            ],
            spacing=5,
        )
        button_frame.pack(fill="x")

        self._run_all_btn = buttons[0]
        self._stop_all_btn = buttons[1]
        self._refresh_all_page_btn = buttons[2]
        self._update_btn = buttons[3]

    def _setup_tabs(self) -> None:
        tabs_container = ttk.Frame(master=self._root)
        tabs_container.pack(fill="both", expand=True, padx=10, pady=5)

        self._notebook = ttk.Notebook(master=tabs_container, takefocus=False)
        self._notebook.pack(fill="both", expand=True)

        # Accounts tab
        self._accounts_tab = AccountsTab(
            parent=self._notebook,
            selected_event=self._selected_event,
            on_account_run=self._run_account,
            on_account_stop=self._stop_account,
            on_refresh_page=self._refresh_page,
            configs=self._configs,
        )
        self._notebook.add(child=self._accounts_tab.frame, text="Accounts")

        # Activity log tab
        self._activity_log_tab = ActivityLogTab(parent=self._notebook)
        self._notebook.add(child=self._activity_log_tab.frame, text="Activity Log")

        # Setup focus management using helper
        UIHelpers.setup_focus_management(root_or_frame=self._root, notebook=self._notebook)

    def _adjust_window_size(self) -> None:
        self._root.update_idletasks()
        _, _, width, height, x, y = get_window_position(child_frame=self._root)
        self._root.geometry(f"{width}x{height}+{x}+{y}")

    def _update_all_buttons_state(self) -> None:
        total_running_accounts = len(self._running_tools)
        is_all_accounts_running = total_running_accounts == len(self._accounts_tab.accounts)

        self._run_all_btn.config(state="normal" if not is_all_accounts_running else "disabled")
        self._stop_all_btn.config(state="normal" if bool(total_running_accounts) else "disabled")
        self._refresh_all_page_btn.config(state="normal" if bool(total_running_accounts) else "disabled")

    def _run_account(self, account: Account) -> None:
        if account.username in self._running_tools:
            message = f"Account '{account.username}' is already running"
            self._activity_log_tab.add_message(tag=MessageTag.WARNING, message=message)
            return

        # Log spin delay configuration
        if account.spin_delay_seconds > 0:
            delay_message = f"Spin delay: {account.spin_delay_seconds} seconds between spins"
        else:
            delay_message = "Spin delay: Disabled (spin on every websocket update)"
        self._activity_log_tab.add_message(tag=MessageTag.INFO, message=delay_message, compact=True)

        # Update browser position in accounts tab
        browser_index = len(self._running_tools)
        self._accounts_tab.update_browser_position(username=account.username, browser_index=browser_index)

        # Log running message
        message = account.running_message(selected_event=self._selected_event)
        self._activity_log_tab.add_message(tag=MessageTag.INFO, message=message)

        new_service = MainService(
            is_running=True,
            browser_index=browser_index,
            screen_width=self._root.winfo_screenwidth(),
            screen_height=self._root.winfo_screenheight(),
            account=account,
            auto_refresh=self._configs.auto_refresh,
            event_config=EVENT_CONFIGS_MAP[self._selected_event],
            **self._build_callbacks(account=account),
        )
        self._running_tools[account.username] = new_service

        run_in_thread(coro_func=new_service.run)
        self._update_all_buttons_state()

    def _stop_account(self, username: str) -> None:
        if username not in self._running_tools:
            message = f"Account '{username}' is not running"
            self._activity_log_tab.add_message(tag=MessageTag.WARNING, message=message)
            return

        running_tool = self._running_tools.pop(username)
        running_tool.is_running = False

        run_in_thread(coro_func=running_tool.close)

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

        run_in_thread(coro_func=running_tool.page.reload)

    def _run_all_accounts(self) -> None:
        self._accounts_tab.run_all_accounts()
        self._update_all_buttons_state()

    def _stop_all_accounts(self) -> None:
        self._accounts_tab.stop_all_accounts()
        self._update_all_buttons_state()

    def _refresh_all_pages(self) -> None:
        self._accounts_tab.refresh_all_pages()
        self._update_all_buttons_state()

    def _build_callbacks(self, account: Account) -> Dict[str, Callable[..., None]]:
        def on_account_won(username: str) -> None:
            def _cb() -> None:
                self._accounts_tab.mark_account_as_won(username=username)
                if account.close_on_jp_win:
                    self._stop_account(username=username)

            UIHelpers.schedule_ui_update(root=self._root, callback=_cb)

        def on_add_message(tag: MessageTag, message: str, compact: bool = False) -> None:
            def _cb() -> None:
                self._activity_log_tab.add_message(tag=tag, message=f"[{account.username}] {message}", compact=compact)

            UIHelpers.schedule_ui_update(root=self._root, callback=_cb)

        def on_add_notification(nickname: str, jackpot_value: str) -> None:
            def _cb() -> None:
                self._notification_icon.add_notification(nickname=nickname, jackpot_value=jackpot_value)

            UIHelpers.schedule_ui_update(root=self._root, callback=_cb)

        def on_update_current_jp(value: int) -> None:
            def _cb() -> None:
                self._activity_log_tab.update_current_jackpot(value=value)

            UIHelpers.schedule_ui_update(root=self._root, callback=_cb)

        def on_update_prize_winner(nickname: str, value: str, is_jackpot: bool = False) -> None:
            def _cb() -> None:
                self._activity_log_tab.update_prize_winner(nickname=nickname, value=value, is_jackpot=is_jackpot)

            UIHelpers.schedule_ui_update(root=self._root, callback=_cb)

        return {
            on_account_won.__name__: on_account_won,
            on_add_message.__name__: on_add_message,
            on_add_notification.__name__: on_add_notification,
            on_update_current_jp.__name__: on_update_current_jp,
            on_update_prize_winner.__name__: on_update_prize_winner,
        }
