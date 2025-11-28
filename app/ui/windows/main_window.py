import contextlib
import threading
import tkinter as tk
from tkinter import ttk
from typing import Any, Awaitable, Callable, Dict, Mapping, Optional, Sequence

import darkdetect
import sv_ttk
from dishka import AsyncContainer
from loguru import logger

from app.core.managers.config import config_mgr
from app.core.managers.file import file_mgr
from app.core.managers.platform import platform_mgr
from app.core.settings import Settings
from app.services.main_service import MainService
from app.ui.components.dialogs.update_dialog import UpdateDialog
from app.ui.components.notification_icon import NotificationIcon
from app.ui.components.tabs.accounts_tab import AccountsTab
from app.ui.components.tabs.activity_log_tab import ActivityLogTab
from app.ui.handlers.account_handler import AccountHandler
from app.ui.handlers.update_handler import UpdateHandler
from app.ui.utils.ui_factory import UIFactory
from app.ui.utils.ui_helpers import UIHelpers
from app.utils.concurrency import run_many_in_threads
from app.utils.constants import EVENT_CONFIGS_MAP
from app.utils.helpers import get_window_position

TaskList = Sequence[tuple[Callable[..., Awaitable[Any]], Sequence[Any], Mapping[str, Any]]]


class MainWindow:
    def __init__(self, container: AsyncContainer, settings: Settings) -> None:
        self._container = container
        self._settings = settings

        # Initialize window
        self._root = tk.Tk()
        self._root.title(string=self._settings.program_name)
        self._root.resizable(width=True, height=True)
        self._root.minsize(width=900, height=600)

        # Widgets
        self._accounts_tab: Optional[AccountsTab] = None
        self._activity_log_tab: Optional[ActivityLogTab] = None

        # Configs
        self._configs = config_mgr.load_configs()
        self._selected_event = self._configs.event
        self._running_services: Dict[str, MainService] = {}

        # Handlers
        self._base_params_handler = {"settings": self._settings, "root": self._root, "configs": self._configs}
        self._update_handler = UpdateHandler(**self._base_params_handler)  # type: ignore[arg-type]
        self._account_handler = AccountHandler(running_services=self._running_services, **self._base_params_handler)

        # Setup UI
        self._initialize()

        # Check for updates silently after 2 seconds
        self._root.after(2000, self._update_handler.check)

    def _initialize(self) -> None:
        self._setup_window_icon()
        self._setup_menu_bar()
        self._setup_notification_icon()
        self._setup_event_selection()
        self._setup_control_buttons()
        self._setup_tabs()
        self._adjust_window_size()

        self._account_handler.update_widgets(
            run_all_accounts_btn=self._run_all_accounts_btn,
            stop_all_accounts_btn=self._stop_all_accounts_btn,
            refresh_all_pages_btn=self._refresh_all_pages_btn,
            notification_icon=self._notification_icon,
            accounts_tab=self._accounts_tab,  # type: ignore[arg-type]
            activity_log_tab=self._activity_log_tab,  # type: ignore[arg-type]
        )

    def _setup_window_icon(self) -> None:
        # Set window icon
        with contextlib.suppress(Exception):
            png_path = file_mgr.get_resource_path(relative_path="assets/icon.png")
            icon = tk.PhotoImage(file=png_path)
            self._root.iconphoto(True, icon)

        # Set window icon for Windows
        if platform_mgr.is_windows:
            with contextlib.suppress(Exception):
                ico_path = file_mgr.get_resource_path(relative_path="assets/icon.ico")
                self._root.iconbitmap(ico_path)

    def _setup_menu_bar(self) -> None:
        menubar = tk.Menu(self._root)
        self._root.config(menu=menubar)

        # Settings menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)

        settings_menu.add_command(label="Check for Updates", command=lambda: UpdateDialog(parent=self._root))
        settings_menu.add_command(label="Change License Key", command=self._update_handler.manual_change_license_key)
        settings_menu.add_separator()
        settings_menu.add_command(label="Exit", command=self._on_close)

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
        event_var = tk.StringVar(value=self._selected_event)
        event_combobox = UIFactory.create_combobox(
            parent=event_frame,
            textvariable=event_var,
            values=list(EVENT_CONFIGS_MAP.keys()),
            width=30,
        )

        def on_combobox_select_changed() -> None:
            self._selected_event = event_var.get()
            self._accounts_tab.selected_event = self._selected_event  # type: ignore[union-attr]

            self._configs.event = self._selected_event
            config_mgr.save_configs(configs=self._configs)

            event_combobox.selection_clear()

        event_combobox.bind(sequence="<<ComboboxSelected>>", func=lambda _: on_combobox_select_changed())
        event_combobox.pack(anchor="w", fill="x", pady=(0, 10))

        # Auto refresh checkbox
        def on_auto_refresh_changed() -> None:
            self._configs.auto_refresh = auto_refresh_var.get()
            config_mgr.save_configs(configs=self._configs)

        auto_refresh_var = tk.BooleanVar(value=self._configs.auto_refresh)
        auto_refresh_checkbox = ttk.Checkbutton(
            master=event_frame,
            text="Auto Refresh after 1 hour",
            variable=auto_refresh_var,
            command=on_auto_refresh_changed,
        )
        auto_refresh_checkbox.pack(anchor="w")

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
                    "command": self._account_handler.run_all_accounts,
                },
                {
                    "text": "Stop All",
                    "state": "disabled",
                    "command": self._account_handler.stop_all_accounts,
                },
                {
                    "text": "Refresh All",
                    "state": "disabled",
                    "command": self._account_handler.refresh_all_pages,
                },
            ],
            spacing=5,
        )
        button_frame.pack(fill="x")

        self._run_all_accounts_btn = buttons[0]
        self._stop_all_accounts_btn = buttons[1]
        self._refresh_all_pages_btn = buttons[2]

    def _setup_tabs(self) -> None:
        tabs_container = ttk.Frame(master=self._root)
        tabs_container.pack(fill="both", expand=True, padx=10, pady=5)

        notebook = ttk.Notebook(master=tabs_container, takefocus=False)
        notebook.pack(fill="both", expand=True)

        # Accounts tab
        self._accounts_tab = AccountsTab(
            parent=notebook,
            configs=self._configs,
            selected_event=self._selected_event,
            on_account_run=self._account_handler.run_account,
            on_account_stop=self._account_handler.stop_account,
            on_refresh_page=self._account_handler.refresh_page,
        )
        notebook.add(child=self._accounts_tab.frame, text="Accounts")

        # Activity log tab
        self._activity_log_tab = ActivityLogTab(parent=notebook)
        notebook.add(child=self._activity_log_tab.frame, text="Activity Log")

        # Setup focus management using helper
        UIHelpers.setup_focus_management(root_or_frame=self._root, notebook=notebook)

    def _adjust_window_size(self) -> None:
        self._root.update_idletasks()
        _, _, width, height, x, y = get_window_position(child_frame=self._root)
        self._root.geometry(f"{width}x{height}+{x}+{y}")

    def run(self) -> None:
        logger.info(f"Running {self._settings.program_name}")

        self._root.protocol(name="WM_DELETE_WINDOW", func=self._on_close)
        self._setup_theme()
        self._root.mainloop()

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
        if self._running_services:
            for service in self._running_services.values():
                service.is_running = False

            def close_tools_concurrently() -> None:
                tasks: TaskList = [(service.close, (), {}) for service in self._running_services.values()]
                run_many_in_threads(tasks=tasks, timeout=5.0)

            threading.Thread(target=close_tools_concurrently, daemon=True).start()

        self._root.destroy()
