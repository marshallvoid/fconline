import time
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Dict, List, Optional, Set, Tuple

from app.core.managers.local_config import local_config_mgr
from app.schemas.app_config import EventConfigs
from app.schemas.enums.account_tag import AccountTag
from app.schemas.local_config import Account, LocalConfigs
from app.ui.components.dialogs.upsert_account import UpsertAccountDialog
from app.ui.utils.ui_factory import UIFactory
from app.utils.constants import BROWSER_POSITIONS
from app.utils.types.callback import OnAccountRunCallback, OnAccountStopCallback, OnRefreshPageCallback


class AccountsTab:
    _BROWSER_POS_LABEL_TEXT = "Browser Position: {position}"

    _ACCOUNT_COLUMN_CONFIGS = {
        "Username": {"width": 160, "anchor": "w"},
        "Target Special Jackpot": {"width": 140, "anchor": "center"},
        "Target Mini Jackpot": {"width": 140, "anchor": "center"},
        "Spin Action": {"width": 120, "anchor": "center"},
        "Close on JP Win": {"width": 140, "anchor": "center"},
    }

    def __init__(
        self,
        parent: tk.Misc,
        event_configs: Dict[str, EventConfigs],
        local_configs: LocalConfigs,
        selected_event: str,
        on_account_run: OnAccountRunCallback,
        on_account_stop: OnAccountStopCallback,
        on_refresh_page: OnRefreshPageCallback,
    ) -> None:
        # Widgets
        self._frame = ttk.Frame(master=parent)

        # Configs
        self._event_configs = event_configs
        self._local_configs = local_configs
        self._accounts = self._local_configs.accounts
        self._selected_event = selected_event

        # Callbacks
        self._on_account_run = on_account_run
        self._on_account_stop = on_account_stop
        self._on_refresh_page = on_refresh_page

        # States
        self._running_usernames: Set[str] = set()
        self._browser_pos_by_username: Dict[str, str] = {}

        self._initialize()

    @property
    def frame(self) -> ttk.Frame:
        return self._frame

    @property
    def accounts(self) -> List[Account]:
        return self._accounts

    @property
    def selected_event(self) -> str:
        return self._selected_event

    @selected_event.setter
    def selected_event(self, value: str) -> None:
        self._selected_event = value
        self._update_accounts_tree()

    # ==================== Public Methods ====================
    def toggle_all_mark_not_run(self, accounts: List[Account]) -> None:
        if any(a.username in self._running_usernames for a in accounts):
            messagebox.showwarning("Warning", "Cannot toggle accounts that are currently running.")
            return

        for account in accounts:
            account.marked_not_run = not account.marked_not_run
            time.sleep(1)

        self._save_accounts_to_config()
        self._update_accounts_tree()

    def delete_all_accounts(self, accounts: List[Account]) -> None:
        if any(a.username in self._running_usernames for a in accounts):
            messagebox.showwarning("Warning", "Cannot delete accounts that are currently running.")
            return

        if not messagebox.askyesno(
            title="Confirm Deletion",
            message=f"Are you sure you want to delete the selected {len(accounts)} account(s)? This action cannot be undone.",  # noqa: E501
            icon="warning",
        ):
            return

        accounts_to_delete_set = set(accounts)
        current_accounts_set = set(self._accounts)
        self._accounts = list(current_accounts_set - accounts_to_delete_set)

        self._save_accounts_to_config()
        self._update_accounts_tree()

    def run_all_accounts(self, not_running_accounts: Optional[List[Account]] = None) -> None:
        not_running_accounts = not_running_accounts or [
            account
            for account in self._accounts
            # Check not running, not won and not marked not run
            if account.username not in self._running_usernames and account.available
        ]

        if not not_running_accounts:
            message = "No accounts available to run. All accounts might be running, not configured, or completed."
            messagebox.showinfo("Info", message)
            return

        for account in not_running_accounts:
            self._on_account_run(account=account)
            time.sleep(1)

        self._running_usernames.update(a.username for a in not_running_accounts)
        self._update_accounts_tree()

    def stop_all_accounts(self, running_usernames: Optional[Set[str]] = None) -> None:
        running_usernames = running_usernames or self._running_usernames
        if not running_usernames:
            message = "No accounts to stop. All accounts might be stopped, not running, or not configured."
            messagebox.showinfo("Info", message)
            return

        for username in running_usernames:
            self._on_account_stop(username=username)
            time.sleep(1)

        self._running_usernames.clear()
        self._update_accounts_tree()

    def refresh_all_pages(self, running_usernames: Optional[Set[str]] = None) -> None:
        running_usernames = running_usernames or self._running_usernames
        if not running_usernames:
            message = "No accounts to refresh. All accounts might be stopped, not running, or not configured."
            messagebox.showinfo("Info", message)
            return

        for username in running_usernames:
            self._on_refresh_page(username=username)
            time.sleep(1)

    def update_browser_position(self, username: str, browser_index: int) -> None:
        account = next((a for a in self._accounts if a.username == username), None)
        if not account:
            return

        row, col = divmod(browser_index, 2)
        self._browser_pos_by_username[username] = BROWSER_POSITIONS.get((row, col), "Center")
        self._update_information_frame(account=account, is_running=username in self._running_usernames)

    def mark_account_as_won(self, username: str) -> None:
        account = next((a for a in self._accounts if a.username == username), None)
        if not account:
            return

        account.has_won = True
        self._save_accounts_to_config()
        self._update_accounts_tree()

    # ==================== Private Methods ====================
    def _initialize(self) -> None:
        container = ttk.Frame(master=self._frame)
        container.pack(fill="both", expand=True, padx=20, pady=(20, 10))

        main_frame = ttk.Frame(master=container)
        main_frame.pack(fill="both", expand=True)

        self._setup_accounts_tree(parent=main_frame)
        self._setup_action_buttons(parent=main_frame)

    def _setup_accounts_tree(self, parent: ttk.Frame) -> None:
        self._left_frame = ttk.LabelFrame(master=parent, text=f"Accounts ({len(self._accounts)})", padding=10)
        self._left_frame.pack(side="left", fill="both", expand=True)

        # Create a frame to constrain treeview width
        tree_container = ttk.Frame(master=self._left_frame, width=300)
        tree_container.pack_propagate(flag=False)

        self._accounts_tree = ttk.Treeview(
            master=tree_container,
            columns=list(self._ACCOUNT_COLUMN_CONFIGS.keys()),
            height=8,
            padding=8,
            show="headings",
        )

        # Scrollbars
        hsc = ttk.Scrollbar(master=tree_container, orient="horizontal", command=self._accounts_tree.xview)
        self._accounts_tree.configure(xscrollcommand=hsc.set)

        vsc = ttk.Scrollbar(master=tree_container, orient="vertical", command=self._accounts_tree.yview)
        self._accounts_tree.configure(yscrollcommand=vsc.set)

        # Pack treeview and scrollbar
        tree_container.pack(side="left", fill="both", expand=True)
        hsc.pack(side="bottom", fill="x")
        vsc.pack(side="right", fill="y")
        self._accounts_tree.pack(fill="both", expand=True)

        # Configure columns
        for column, config in self._ACCOUNT_COLUMN_CONFIGS.items():
            self._accounts_tree.heading(column=column, text=column)
            self._accounts_tree.column(column=column, **config)  # type: ignore[call-overload]

        # Configure tags for colors
        for tag in AccountTag:
            self._accounts_tree.tag_configure(tag.name, background=tag.value[0], foreground=tag.value[1])

        # Bind events
        self._accounts_tree.bind("<<TreeviewSelect>>", lambda _: self._on_tree_select())
        self._accounts_tree.bind("<Double-1>", lambda _: self._on_tree_double_click())
        self._accounts_tree.bind("<Control-a>", lambda _: self._on_select_all_accounts())
        self._accounts_tree.bind("<Control-A>", lambda _: self._on_select_all_accounts())

        self._accounts_tree.focus_set()
        self._update_accounts_tree()

    def _setup_action_buttons(self, parent: ttk.Frame) -> None:
        self._right_frame = ttk.LabelFrame(master=parent, text="Actions", padding=10)
        self._right_frame.pack(side="right", fill="y", padx=(10, 0))

        # Add Account button
        self._add_account_btn = UIFactory.create_button(
            parent=self._right_frame,
            text="Add Account",
            command=lambda: self._open_upsert_dialog(),
            style="Accent.TButton",
            width=15,
        )
        self._add_account_btn.pack(fill="x", pady=(0, 10))

        # Management buttons group
        management_container = ttk.Frame(master=self._right_frame)
        management_container.pack(fill="x", pady=(0, 10))

        self._mark_not_run_btn = UIFactory.create_button(
            parent=management_container,
            text="Mark Not Run",
            width=15,
            state="disabled",
        )
        self._mark_not_run_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self._edit_btn = UIFactory.create_button(
            parent=management_container,
            text="Edit",
            width=15,
            state="disabled",
        )
        self._edit_btn.pack(side="right", fill="x", expand=True)

        self._delete_btn = UIFactory.create_button(
            parent=self._right_frame,
            text="Delete",
            width=15,
            state="disabled",
        )
        self._delete_btn.pack(fill="x")

        # Separator
        separator_single = ttk.Separator(master=self._right_frame, orient="horizontal")
        separator_single.pack(fill="x", pady=15)

        # Control buttons group
        control_container = ttk.Frame(master=self._right_frame)
        control_container.pack(fill="x", pady=(0, 10))

        self._run_btn = UIFactory.create_button(
            parent=control_container,
            text="Run",
            style="Accent.TButton",
            width=15,
            state="disabled",
        )
        self._run_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self._stop_btn = UIFactory.create_button(
            parent=control_container,
            text="Stop",
            style="Accent.TButton",
            width=15,
            state="disabled",
        )
        self._stop_btn.pack(side="right", fill="x", expand=True)

        # Refresh Page button
        self._refresh_btn = UIFactory.create_button(
            parent=self._right_frame,
            text="Refresh Page",
            style="Accent.TButton",
            width=15,
            state="disabled",
        )
        self._refresh_btn.pack(fill="x")

        # Information frame
        info_frame = ttk.LabelFrame(master=self._right_frame, text="Information", padding=10)
        info_frame.pack(fill="x", pady=(15, 0))

        self._browser_pos_label = ttk.Label(
            master=info_frame,
            text=self._BROWSER_POS_LABEL_TEXT.format(position="-"),
            font=("Arial", 14),
            foreground="#6b7280",
        )
        self._browser_pos_label.pack(anchor="w", pady=(0, 5))

    def _on_tree_select(self) -> None:
        selected_accounts = self._get_selected_accounts()

        if not selected_accounts:
            self._mark_not_run_btn.config(state="disabled")
            self._edit_btn.config(state="disabled")
            self._delete_btn.config(state="disabled")
            self._run_btn.config(state="disabled")
            self._stop_btn.config(state="disabled")
            self._refresh_btn.config(state="disabled")
            self._browser_pos_label.config(text=self._BROWSER_POS_LABEL_TEXT.format(position="-"), foreground="#6b7280")
            return

        if len(selected_accounts) == 1:
            self._handle_single_selection(selected_accounts[0])
        else:
            self._handle_multiple_selection(selected_accounts)

    def _get_selected_accounts(self) -> List[Account]:
        selected_items = self._accounts_tree.selection()
        selected_accounts = []

        for item_id in selected_items:
            values = self._accounts_tree.item(item=item_id, option="values")
            if not values:
                continue

            account = next((a for a in self._accounts if a.username == values[0]), None)
            if not account:
                continue

            selected_accounts.append(account)

        return selected_accounts

    def _handle_single_selection(self, account: Account) -> None:
        is_running = account.username in self._running_usernames
        is_marked_not_run = account.marked_not_run
        is_winning = account.has_won

        self._mark_not_run_btn.config(
            command=lambda: self._toggle_mark_not_run(account=account),
            state="disabled" if is_running or is_winning else "normal",
            text="Mark Run" if is_marked_not_run else "Mark Not Run",
        )

        self._edit_btn.config(
            command=lambda: self._open_upsert_dialog(account=account),
            state="disabled" if is_winning else "normal",
        )

        self._delete_btn.config(
            command=lambda: self._delete_account(account=account),
            state="disabled" if is_running else "normal",
        )

        self._run_btn.config(
            command=lambda: self._run_account(account=account),
            state="disabled" if is_running or is_marked_not_run or is_winning else "normal",
            text="Run",
        )

        self._stop_btn.config(
            command=lambda: self._stop_account(username=account.username),
            state="normal" if is_running else "disabled",
            text="Stop",
        )

        self._refresh_btn.config(
            command=lambda: self._refresh_page(username=account.username),
            state="normal" if is_running else "disabled",
        )

        self._update_information_frame(account=account, is_running=is_running)

    def _toggle_mark_not_run(self, account: Account) -> None:
        account.marked_not_run = not account.marked_not_run
        self._save_accounts_to_config()
        self._update_accounts_tree()

    def _delete_account(self, account: Account) -> None:
        if not messagebox.askyesno(
            title="Confirm Delete",
            message=f"Are you sure you want to delete account '{account.username}'?",
            icon="warning",
        ):
            return

        self._accounts.remove(account)
        self._save_accounts_to_config()
        self._update_accounts_tree()

    def _run_account(self, account: Account) -> None:
        if account.username in self._running_usernames:
            messagebox.showinfo("Info", f"Account '{account.username}' is already running.")
            return

        if account.marked_not_run:
            messagebox.showinfo("Info", f"Cannot run account '{account.username}' marked as not run.")
            return

        if account.has_won:
            messagebox.showinfo("Info", f"Cannot run winning account '{account.username}'.")
            return

        self._on_account_run(account=account)
        self._running_usernames.add(account.username)
        self._update_accounts_tree()

    def _stop_account(self, username: str) -> None:
        if username not in self._running_usernames:
            messagebox.showinfo("Info", f"Account '{username}' is not running.")
            return

        self._on_account_stop(username=username)
        self._running_usernames.remove(username)
        self._update_accounts_tree()

    def _refresh_page(self, username: str) -> None:
        if username not in self._running_usernames:
            messagebox.showinfo("Info", f"Account '{username}' is not running.")
            return

        self._on_refresh_page(username=username)

    def _handle_multiple_selection(self, accounts: List[Account]) -> None:
        self._edit_btn.config(state="disabled")

        not_running_accounts = [a for a in accounts if a.username not in self._running_usernames and a.available]
        running_usernames = {a.username for a in accounts if a.username in self._running_usernames}

        self._mark_not_run_btn.config(
            command=lambda: self.toggle_all_mark_not_run(accounts=accounts),
            state="disabled" if len(running_usernames) > 0 else "normal",
            text="Toggle Selected",
        )

        self._delete_btn.config(
            command=lambda: self.delete_all_accounts(accounts=accounts),
            state="disabled" if len(running_usernames) > 0 else "normal",
            text="Delete Selected",
        )

        self._run_btn.config(
            command=lambda: self.run_all_accounts(not_running_accounts=not_running_accounts),
            state="normal" if len(not_running_accounts) > 0 else "disabled",
            text="Run Selected",
        )

        self._stop_btn.config(
            command=lambda: self.stop_all_accounts(running_usernames=running_usernames),
            state="normal" if len(running_usernames) > 0 else "disabled",
            text="Stop Selected",
        )

        self._refresh_btn.config(
            command=lambda: self.refresh_all_pages(running_usernames=running_usernames),
            state="normal" if len(running_usernames) > 0 else "disabled",
        )

    def _on_tree_double_click(self) -> None:
        selected_items = self._accounts_tree.selection()
        if not selected_items:
            messagebox.showwarning("Warning", "Please select an account to process.")
            return

        item_id = selected_items[0]
        values = self._accounts_tree.item(item=item_id, option="values")
        if not values:
            return

        account = next((a for a in self._accounts if a.username == values[0]), None)
        if not account:
            return

        self._open_upsert_dialog(account=account)

    def _on_select_all_accounts(self) -> None:
        all_items = self._accounts_tree.get_children()
        self._accounts_tree.selection_set(all_items)

    def _open_upsert_dialog(self, account: Optional[Account] = None) -> None:
        def on_save(account: Account, is_new: bool) -> None:
            if is_new:
                self._accounts.append(account)

            self._save_accounts_to_config()
            self._update_accounts_tree()

        UpsertAccountDialog(
            parent=self._frame,
            event_configs=self._event_configs,
            selected_event=self._selected_event,
            existing_accounts=self._accounts,
            account=account,
            on_save=on_save,
        )

    def _update_information_frame(self, account: Account, is_running: bool) -> None:
        if not is_running:
            browser_pos = "Not Running"
            browser_color = "#6b7280"
        else:
            browser_pos = self._browser_pos_by_username.get(account.username, "Unknown")
            browser_color = "#22c55e" if browser_pos != "Unknown" else "#6b7280"

        widgets_configs = {
            self._browser_pos_label: {
                "text": self._BROWSER_POS_LABEL_TEXT.format(position=browser_pos),
                "foreground": browser_color,
            },
        }

        for label_widget, cofnigs in widgets_configs.items():
            label_widget.config(**cofnigs)

    def _update_accounts_tree(self) -> None:
        self._accounts_tree.delete(*self._accounts_tree.get_children())

        for account in self._accounts:
            conditions: List[Tuple[bool, Tuple[str]]] = [
                (account.username in self._running_usernames, (AccountTag.RUNNING.name,)),
                (account.marked_not_run, (AccountTag.MARKED_NOT_RUN.name,)),
                (account.has_won, (AccountTag.WINNER.name,)),
            ]
            tags = next((tag for cond, tag in conditions if cond), (AccountTag.STOPPED.name,))

            self._accounts_tree.insert(
                parent="",
                index=0,
                tags=tags,
                values=(
                    account.username,
                    account.target_sjp,
                    account.target_mjp if account.target_mjp is not None else "-",
                    account.spin_type_name(event_configs=self._event_configs, selected_event=self._selected_event),
                    account.close_on_jp_win,
                ),
            )

        self._left_frame.config(text=f"Accounts ({len(self._accounts)})")

    def _save_accounts_to_config(self) -> None:
        self._local_configs.accounts = self._accounts
        local_config_mgr.save_local_configs(configs=self._local_configs)
