# mypy: disable-error-code="union-attr"

from tkinter import ttk
from typing import Any, Callable, Dict, Optional

from app.schemas.enums.message_tag import MessageTag
from app.schemas.local_config import Account
from app.schemas.user_response import UserDetail
from app.services.main import MainService
from app.ui.components.notification_icon import NotificationIcon
from app.ui.components.tabs.accounts import AccountsTab
from app.ui.components.tabs.activity_log import ActivityLogTab
from app.ui.handlers.base import BaseHandler
from app.utils.concurrency import run_in_thread


class AccountHandler(BaseHandler):
    def __init__(
        self,
        *args: Any,
        running_services: Dict[str, MainService],  # Format: { username: MainService }
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]

        # States
        self._running_services = running_services

        # Widgets
        self._event_combobox: Optional[ttk.Combobox] = None
        self._auto_refresh_checkbox: Optional[ttk.Checkbutton] = None
        self._headless_checkbox: Optional[ttk.Checkbutton] = None
        self._run_all_accounts_btn: Optional[ttk.Button] = None
        self._stop_all_accounts_btn: Optional[ttk.Button] = None
        self._refresh_all_pages_btn: Optional[ttk.Button] = None
        self._notification_icon: Optional[NotificationIcon] = None
        self._notebook: Optional[ttk.Notebook] = None
        self._accounts_tab: Optional[AccountsTab] = None
        self._activity_log_tab: Optional[ActivityLogTab] = None

    # ==================== Public Methods ====================
    def update_widgets(
        self,
        notification_icon: NotificationIcon,
        event_combobox: ttk.Combobox,
        auto_refresh_checkbox: ttk.Checkbutton,
        headless_checkbox: ttk.Checkbutton,
        run_all_accounts_btn: ttk.Button,
        stop_all_accounts_btn: ttk.Button,
        refresh_all_pages_btn: ttk.Button,
        notebook: ttk.Notebook,
        accounts_tab: AccountsTab,
        activity_log_tab: ActivityLogTab,
    ) -> None:
        self._notification_icon = notification_icon
        self._event_combobox = event_combobox
        self._auto_refresh_checkbox = auto_refresh_checkbox
        self._headless_checkbox = headless_checkbox
        self._run_all_accounts_btn = run_all_accounts_btn
        self._stop_all_accounts_btn = stop_all_accounts_btn
        self._refresh_all_pages_btn = refresh_all_pages_btn
        self._notebook = notebook
        self._accounts_tab = accounts_tab
        self._activity_log_tab = activity_log_tab

    def run_all_accounts(self) -> None:
        # Select activity tab when run
        self._notebook.select(tab_id=self._activity_log_tab.frame)
        self._accounts_tab.run_all_accounts()

    def stop_all_accounts(self) -> None:
        self._accounts_tab.stop_all_accounts()

    def refresh_all_pages(self) -> None:
        self._accounts_tab.refresh_all_pages()

    def run_account(self, account: Account) -> None:
        # Select activity tab when run
        self._notebook.select(tab_id=self._activity_log_tab.frame)

        # Update browser position in accounts tab
        browser_index = len(self._running_services)
        self._accounts_tab.update_browser_position(username=account.username, browser_index=browser_index)

        # Get current selected event from accounts_tab
        selected_event = self._local_configs.event

        # Log running message
        message = account.running_message(event_configs=self._event_configs, selected_event=selected_event)
        self._activity_log_tab.add_message(tag=MessageTag.INFO, message=message)

        new_service = MainService(
            is_running=True,
            browser_index=browser_index,
            screen_width=self._root.winfo_screenwidth(),
            screen_height=self._root.winfo_screenheight(),
            account=account,
            auto_refresh=self._local_configs.auto_refresh,
            headless=self._local_configs.headless,
            event_config=self._event_configs[selected_event],
            **self._build_callbacks(account=account),
        )
        self._running_services[account.username] = new_service

        run_in_thread(coro_func=new_service.run)
        self._update_all_buttons_state()

    def stop_account(self, username: str) -> None:
        running_service = self._running_services.pop(username)
        running_service.is_running = False

        run_in_thread(coro_func=running_service.close)
        self._update_all_buttons_state()

    def refresh_page(self, username: str) -> None:
        running_service = self._running_services[username]
        if not running_service.page:
            message = f"Account '{username}' does not have an active page to refresh"
            self._activity_log_tab.add_message(tag=MessageTag.WARNING, message=message)
            return

        run_in_thread(coro_func=running_service.page.reload)
        self._update_all_buttons_state()

    # ==================== Private Methods ====================
    def _update_all_buttons_state(self) -> None:
        total_running_services = len(self._running_services)
        is_all_services_running = total_running_services == len(self._accounts_tab.accounts)

        self._event_combobox.config(state="disabled" if bool(total_running_services) else "normal")
        self._auto_refresh_checkbox.config(state="disabled" if bool(total_running_services) else "normal")
        self._headless_checkbox.config(state="disabled" if bool(total_running_services) else "normal")
        self._run_all_accounts_btn.config(state="disabled" if is_all_services_running else "normal")
        self._stop_all_accounts_btn.config(state="normal" if bool(total_running_services) else "disabled")
        self._refresh_all_pages_btn.config(state="normal" if bool(total_running_services) else "disabled")

    def _build_callbacks(self, account: Account) -> Dict[str, Callable[..., None]]:
        def on_account_won(username: str) -> None:
            def _cb() -> None:
                self._accounts_tab.mark_account_as_won(username=username)
                if account.close_on_jp_win:
                    self.stop_account(username=username)

            self._root.after(ms=0, func=_cb)

        def on_update_account_info(username: str, user_detail: UserDetail) -> None:
            def _cb() -> None:
                self._accounts_tab.update_account_info(username=username, user_detail=user_detail)

            self._root.after(ms=0, func=_cb)

        def on_update_current_jackpot(value: int) -> None:
            def _cb() -> None:
                self._activity_log_tab.update_current_jackpot(value=value)

            self._root.after(ms=0, func=_cb)

        def on_update_prize_winner(nickname: str, value: str, is_jackpot: bool = False) -> None:
            def _cb() -> None:
                self._activity_log_tab.update_prize_winner(nickname=nickname, value=value, is_jackpot=is_jackpot)

            self._root.after(ms=0, func=_cb)

        def on_add_message(tag: MessageTag, message: str, compact: bool = False) -> None:
            def _cb() -> None:
                self._activity_log_tab.add_message(tag=tag, message=f"[{account.username}] {message}", compact=compact)

            self._root.after(ms=0, func=_cb)

        def on_add_notification(nickname: str, jackpot_value: str) -> None:
            def _cb() -> None:
                self._notification_icon.add_notification(nickname=nickname, jackpot_value=jackpot_value)

            self._root.after(ms=0, func=_cb)

        # Auto-collect inner functions
        callbacks = {name: fn for name, fn in locals().items() if callable(fn) and name.startswith("on_")}
        return callbacks
