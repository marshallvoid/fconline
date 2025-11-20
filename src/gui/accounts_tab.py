import time
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Dict, List, Optional, Set, Tuple

from src.core.managers.config import config_mgr
from src.schemas.configs import Account, Config
from src.schemas.enums.account_tag import AccountTag
from src.utils import hlp
from src.utils.contants import BROWSER_POSITIONS, EVENT_CONFIGS_MAP
from src.utils.types import callback as cb


class AccountsTab:
    _BROWSER_POS_LABEL_TEXT = "Browser Position: {position}"
    _NICKNAME_LABEL_TEXT = "Nickname: {nickname}"
    _FC_LABEL_TEXT = "FC: {fc}"

    def __init__(
        self,
        parent: tk.Misc,
        selected_event: str,
        on_account_run: cb.OnAccountRunCallback,
        on_account_stop: cb.OnAccountStopCallback,
        on_refresh_page: cb.OnRefreshPageCallback,
        configs: Optional[Config] = None,
    ) -> None:
        self._frame = ttk.Frame(parent)
        self._selected_event = selected_event

        self._on_account_run = on_account_run
        self._on_account_stop = on_account_stop
        self._on_refresh_page = on_refresh_page

        self._configs = configs if configs is not None else config_mgr.load_configs()
        self._accounts: List[Account] = self._configs.accounts
        self._running_usernames: Set[str] = set()

        self._browser_pos_by_username: Dict[str, str] = {}

        self._setup_ui()

    @property
    def frame(self) -> ttk.Frame:
        return self._frame

    @property
    def selected_event(self) -> str:
        return self._selected_event

    @selected_event.setter
    def selected_event(self, value: str) -> None:
        self._selected_event = value
        self._refresh_accounts_list()

    @property
    def accounts(self) -> List[Account]:
        return self._accounts

    # ==================== Public Methods ====================
    def delete_all_accounts(self, accounts: List[Account]) -> None:
        if not accounts:
            messagebox.showinfo("Info", "No accounts to delete.")
            return

        if any(a.username in self._running_usernames for a in accounts):
            messagebox.showwarning("Warning", "Cannot delete accounts that are currently running.")
            return

        confirm = messagebox.askyesno(
            title="Confirm Deletion",
            message=f"Are you sure you want to delete the selected {len(accounts)} account(s)? This action cannot be undone.",  # noqa: E501
            icon="warning",
        )
        if not confirm:
            return

        usernames_to_delete = {a.username for a in accounts}
        self._accounts = [a for a in self._accounts if a.username not in usernames_to_delete]
        self._save_accounts_to_config()
        self._refresh_accounts_list()

    def run_all_accounts(self, pending_accounts: Optional[List[Account]] = None) -> None:
        pending_accounts = pending_accounts or [
            a for a in self._accounts if a.username not in self._running_usernames and a.available
        ]
        if not pending_accounts:
            messagebox.showinfo("Info", "No accounts to run.")
            return

        for account in pending_accounts:
            self._on_account_run(account=account)
            time.sleep(1)

        self._running_usernames.update(a.username for a in pending_accounts)
        self._refresh_accounts_list()

    def stop_all_accounts(self, running_usernames: Optional[Set[str]] = None) -> None:
        running_usernames = running_usernames or self._running_usernames
        if not running_usernames:
            messagebox.showinfo("Info", "No accounts to stop.")
            return

        for username in running_usernames:
            self._on_account_stop(username=username)

        self._running_usernames.clear()
        self._refresh_accounts_list()

    def refresh_all_pages(self, running_usernames: Optional[Set[str]] = None) -> None:
        running_usernames = running_usernames or self._running_usernames
        if not running_usernames:
            messagebox.showinfo("Info", "No accounts to refresh.")
            return

        for username in running_usernames:
            self._on_refresh_page(username=username)

    def mark_account_as_won(self, username: str) -> None:
        account = next((a for a in self._accounts if a.username == username), None)
        if not account:
            return

        account.has_won = True
        self._save_accounts_to_config()
        self._refresh_accounts_list()

    def update_browser_position(self, username: str, browser_index: int) -> None:
        account = next((a for a in self._accounts if a.username == username), None)
        if not account:
            return

        row, col = divmod(browser_index, 2)
        self._browser_pos_by_username[username] = BROWSER_POSITIONS.get((row, col), "Center")
        self._update_info_display(account=account, is_running=username in self._running_usernames)

    def update_info_display(self, username: str) -> None:
        account = next((a for a in self._accounts if a.username == username), None)
        if not account:
            return

        self._update_info_display(account=account, is_running=username in self._running_usernames)

    # ==================== Private Methods ====================
    def _setup_ui(self) -> None:
        container = ttk.Frame(master=self._frame)
        container.pack(fill="both", expand=True, padx=20, pady=(20, 10))

        # Main content area with treeview and action buttons side by side
        main_content_frame = ttk.Frame(master=container)
        main_content_frame.pack(fill="both", expand=True)

        # Left side: Accounts list frame
        self._left_frame = ttk.LabelFrame(
            master=main_content_frame,
            text=f"Accounts ({len(self._accounts)})",
            padding=10,
        )
        self._left_frame.pack(side="left", fill="both", expand=True)

        # Configure columns for Treeview
        columns: Dict[str, Dict[str, Any]] = {
            "Username": {"width": 160, "anchor": "w"},
            "Target": {"width": 120, "anchor": "center"},
            "Spin Action": {"width": 120, "anchor": "center"},
            "Auto Close": {"width": 120, "anchor": "center"},
        }

        # Create a frame to constrain treeview width
        tree_container = ttk.Frame(master=self._left_frame, width=300)
        tree_container.pack_propagate(flag=False)  # Prevent frame from expanding

        self._accounts_tree = ttk.Treeview(
            master=tree_container,
            columns=list(columns.keys()),
            show="headings",
            height=8,
            padding=8,
        )

        # Scrollbar
        hsc = ttk.Scrollbar(master=tree_container, orient="horizontal", command=self._accounts_tree.xview)
        self._accounts_tree.configure(xscrollcommand=hsc.set)

        vsc = ttk.Scrollbar(master=tree_container, orient="vertical", command=self._accounts_tree.yview)
        self._accounts_tree.configure(yscrollcommand=vsc.set)

        # Pack treeview and scrollbar
        tree_container.pack(side="left", fill="both", expand=True)
        hsc.pack(side="bottom", fill="x")
        vsc.pack(side="right", fill="y")
        self._accounts_tree.pack(fill="both", expand=True)

        for column, config in columns.items():
            self._accounts_tree.heading(column=column, text=column)
            self._accounts_tree.column(column=column, **config)

        # Configure tags for colors
        for tag in AccountTag:
            self._accounts_tree.tag_configure(tag.name, background=tag.value[0], foreground=tag.value[1])

        # Right side: Action buttons frame
        right_frame = ttk.LabelFrame(master=main_content_frame, text="Actions", padding=10)
        right_frame.pack(side="right", fill="y", padx=(10, 0))

        # Add Account button
        self._add_account_btn = ttk.Button(
            master=right_frame,
            text="Add Account",
            style="Accent.TButton",
            width=15,
            state="normal",
            command=lambda: self._open_upsert_dialog(),
        )
        self._add_account_btn.pack(fill="x", pady=(0, 10))

        # Duplicate Account button
        self._duplicate_account_btn = ttk.Button(
            master=right_frame,
            text="Duplicate Account",
            width=15,
            state="normal",
            command=self._duplicate_selected_account,
        )
        self._duplicate_account_btn.pack(fill="x", pady=(0, 10))

        # Management buttons group
        management_container = ttk.Frame(master=right_frame)
        management_container.pack(fill="x", pady=(0, 10))

        # Mark Not Run button
        self._mark_not_run_btn = ttk.Button(
            master=management_container,
            text="Mark Not Run",
            width=15,
            state="disabled",
        )
        self._mark_not_run_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))

        # Edit button
        self._edit_btn = ttk.Button(
            master=management_container,
            text="Edit",
            width=15,
            state="disabled",
        )
        self._edit_btn.pack(side="right", fill="x", expand=True)

        # Delete button
        self._delete_btn = ttk.Button(
            master=right_frame,
            text="Delete",
            width=15,
            state="disabled",
        )
        self._delete_btn.pack(fill="x")

        # Separator between management buttons and single buttons group
        separator_single = ttk.Separator(master=right_frame, orient="horizontal")
        separator_single.pack(fill="x", pady=15)

        # Single buttons group (Run/Stop/Refresh Page)
        control_container = ttk.Frame(master=right_frame)
        control_container.pack(fill="x", pady=(0, 10))

        # Run button
        self._run_btn = ttk.Button(
            master=control_container,
            text="Run",
            style="Accent.TButton",
            width=15,
            state="disabled",
        )
        self._run_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))

        # Stop button
        self._stop_btn = ttk.Button(
            master=control_container,
            text="Stop",
            style="Accent.TButton",
            width=15,
            state="disabled",
        )
        self._stop_btn.pack(side="right", fill="x", expand=True)

        # Refresh Page button
        self._refresh_btn = ttk.Button(
            master=right_frame,
            text="Refresh Page",
            style="Accent.TButton",
            width=15,
            state="disabled",
        )
        self._refresh_btn.pack(fill="x")

        # Information frame (Browser Position/Nickname/FC)
        info_frame = ttk.LabelFrame(master=right_frame, text="Information", padding=10)
        info_frame.pack(fill="x", pady=(15, 0))

        # Browser position label
        self._browser_pos_label = ttk.Label(
            master=info_frame,
            text=self._BROWSER_POS_LABEL_TEXT.format(position="-"),
            font=("Arial", 14),
            foreground="#6b7280",
        )
        self._browser_pos_label.pack(anchor="w", pady=(0, 5))

        def select_all_accounts() -> str:
            all_items = self._accounts_tree.get_children()
            self._accounts_tree.selection_set(all_items)
            return "break"

        # Bind events
        self._accounts_tree.bind("<<TreeviewSelect>>", lambda _: self._on_tree_select())
        self._accounts_tree.bind("<Double-1>", lambda _: self._on_tree_double_click())
        self._accounts_tree.bind("<Control-a>", lambda _: select_all_accounts())
        self._accounts_tree.bind("<Control-A>", lambda _: select_all_accounts())

        # Make sure the treeview can receive focus for keyboard shortcuts
        self._accounts_tree.focus_set()

        # Refresh the accounts list
        self._refresh_accounts_list()

    def _update_info_display(self, account: Account, is_running: bool) -> None:
        green, gray = "#22c55e", "#6b7280"

        if not is_running:
            browser_pos, browser_color = "Not Running", gray
        else:
            # Browser position
            browser_pos = self._browser_pos_by_username.get(account.username, "Unknown")
            browser_color = green if browser_pos != "Unknown" else gray

        labels = {self._browser_pos_label: (self._BROWSER_POS_LABEL_TEXT.format(position=browser_pos), browser_color)}

        for label, (text, color) in labels.items():
            label.config(text=text, foreground=color)

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

    def _on_tree_select(self) -> None:
        selected_accounts = self._get_selected_accounts()

        if not selected_accounts:
            # No selection
            self._mark_not_run_btn.config(state="disabled")
            self._edit_btn.config(state="disabled")
            self._delete_btn.config(state="disabled")
            self._run_btn.config(state="disabled")
            self._stop_btn.config(state="disabled")
            self._refresh_btn.config(state="disabled")

            # Reset info display
            self._browser_pos_label.config(text=self._BROWSER_POS_LABEL_TEXT.format(position="-"), foreground="#6b7280")
            return

        if len(selected_accounts) == 1:
            # Single selection
            selected_account = selected_accounts[0]
            is_winning = selected_account.has_won
            is_marked_not_run = selected_account.marked_not_run
            is_running = selected_account.username in self._running_usernames

            self._mark_not_run_btn.config(
                command=lambda: self._toggle_mark_not_run(account=selected_account),
                state="disabled" if is_running else "normal",
                text="Mark Run" if is_marked_not_run else "Mark Not Run",
            )

            self._edit_btn.config(
                command=lambda: self._open_upsert_dialog(account=selected_account),
                state="disabled" if is_running or is_winning else "normal",
            )

            self._delete_btn.config(
                command=lambda: self._delete_account(account=selected_account),
                state="disabled" if is_running else "normal",
            )

            self._run_btn.config(
                command=lambda: self._run_account(account=selected_account),
                state="disabled" if is_running or is_winning or is_marked_not_run else "normal",
                text="Run",
            )

            self._stop_btn.config(
                command=lambda: self._stop_account(username=selected_account.username),
                state="disabled" if not is_running else "normal",
                text="Stop",
            )

            self._refresh_btn.config(
                command=lambda: self._on_refresh_page(username=selected_account.username),
                state="normal" if is_running else "disabled",
            )

            self._update_info_display(account=selected_account, is_running=is_running)

        else:
            # Multiple selection
            self._mark_not_run_btn.config(state="disabled")
            self._edit_btn.config(state="disabled")

            available_accounts = [
                a for a in selected_accounts if a.username not in self._running_usernames and a.available
            ]
            running_usernames = {a.username for a in selected_accounts if a.username in self._running_usernames}

            self._delete_btn.config(
                command=lambda: self.delete_all_accounts(accounts=selected_accounts),
                state="disabled" if len(running_usernames) > 0 else "normal",
                text="Delete Selected",
            )

            # Repurpose Run/Stop buttons for multi-selection
            self._run_btn.config(
                command=lambda: self.run_all_accounts(pending_accounts=available_accounts),
                state="normal" if len(available_accounts) > 0 else "disabled",
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
            messagebox.showwarning("Warning", "Please select an account to duplicate.")
            return

        # Get the selected account
        item_id = selected_items[0]
        values = self._accounts_tree.item(item=item_id, option="values")
        if not values:
            return

        account = next((a for a in self._accounts if a.username == values[0]), None)
        if not account:
            return

        if account.username in self._running_usernames:
            self._stop_account(username=account.username)
            return

        self._open_upsert_dialog(account=account)

    def _duplicate_selected_account(self) -> None:
        selected_items = self._accounts_tree.selection()
        if not selected_items:
            messagebox.showwarning("Warning", "Please select an account to duplicate.")
            return

        # Get the selected account
        item_id = selected_items[0]
        values = self._accounts_tree.item(item=item_id, option="values")
        if not values:
            return

        account = next((a for a in self._accounts if a.username == values[0]), None)
        if not account:
            return

        # Create a copy of the account with modified username
        base_username = account.username
        counter = 1
        new_username = f"{base_username}_copy"

        # Find an available username
        existing_usernames = {a.username for a in self._accounts}
        while new_username in existing_usernames:
            counter += 1
            new_username = f"{base_username}_copy{counter}"

        # Create new account with duplicated data but new username
        duplicated_account = Account(
            username=new_username,
            password=account.password,
            spin_type=account.spin_type,
            payment_type=account.payment_type,
            target_sjp=account.target_sjp,
            close_on_jp_win=account.close_on_jp_win,
            has_won=False,  # Reset win status
            marked_not_run=False,  # Reset marked not run status
        )

        # Open the upsert dialog with the duplicated account for editing
        self._open_upsert_dialog(account=duplicated_account)

    def _refresh_accounts_list(self) -> None:
        self._accounts_tree.delete(*self._accounts_tree.get_children())  # Clear existing items

        # Add accounts to treeview
        for account in self._accounts:
            conditions: List[Tuple[bool, Tuple[str]]] = [
                (account.has_won, (AccountTag.WINNER.name,)),
                (account.marked_not_run, (AccountTag.MARKED_NOT_RUN.name,)),
                (account.username in self._running_usernames, (AccountTag.RUNNING.name,)),
            ]
            tags = next((tag for cond, tag in conditions if cond), (AccountTag.STOPPED.name,))

            self._accounts_tree.insert(
                parent="",
                index="end",
                tags=tags,
                values=(
                    account.username,
                    account.target_sjp,
                    account.spin_type_name(selected_event=self._selected_event),
                    account.close_on_jp_win,
                ),
            )

        self._left_frame.config(text=f"Accounts ({len(self._accounts)})")

    def _run_account(self, account: Account) -> None:
        if account.has_won:
            messagebox.showinfo("Info", f"Cannot run winning account '{account.username}'.")
            return

        if account.marked_not_run:
            messagebox.showinfo("Info", f"Cannot run account '{account.username}' marked as not run.")
            return

        self._on_account_run(account=account)

        self._running_usernames.add(account.username)
        self._refresh_accounts_list()

    def _stop_account(self, username: str) -> None:
        self._on_account_stop(username=username)

        self._running_usernames.remove(username)
        self._refresh_accounts_list()

    def _open_upsert_dialog(self, account: Optional[Account] = None) -> None:
        is_edit_mode = account is not None and account.username in {a.username for a in self._accounts}
        is_duplicate_mode = account is not None and not is_edit_mode

        if is_edit_mode:
            title = "Edit Account"
        elif is_duplicate_mode:
            title = "Duplicate Account"
        else:
            title = "Add New Account"

        dialog = tk.Toplevel(master=self._frame)
        dialog.title(string=title)
        dialog.transient(master=self._frame)  # type: ignore
        dialog.grab_set()

        main_frame = ttk.Frame(master=dialog, padding=20)
        main_frame.pack(fill="both", expand=True)

        # Title
        title_label = ttk.Label(master=main_frame, text=title, font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))

        # Username
        username_frame = ttk.Frame(master=main_frame)
        username_frame.pack(fill="x", pady=(0, 15))
        ttk.Label(master=username_frame, text="Username:", width=15, font=("Arial", 12)).pack(side="left")
        username_var = tk.StringVar(value=(account.username if account else ""))
        username_entry = ttk.Entry(master=username_frame, textvariable=username_var, width=25, font=("Arial", 12))
        username_entry.pack(side="left", padx=(10, 0), fill="x", expand=True)

        # Password
        pwd_frame = ttk.Frame(master=main_frame)
        pwd_frame.pack(fill="x", pady=(0, 15))
        ttk.Label(master=pwd_frame, text="Password:", width=15, font=("Arial", 12)).pack(side="left")
        pwd_var = tk.StringVar(value=(account.password if account else ""))
        pwd_entry = ttk.Entry(master=pwd_frame, textvariable=pwd_var, show="*", width=25, font=("Arial", 12))
        pwd_entry.pack(side="left", padx=(10, 0), fill="x", expand=True)

        # Target Special Jackpot
        target_sjp_frame = ttk.Frame(master=main_frame)
        target_sjp_frame.pack(fill="x", pady=(0, 15))
        ttk.Label(master=target_sjp_frame, text="Target Jackpot:", width=15, font=("Arial", 12)).pack(side="left")
        target_sjp_var = tk.IntVar(value=(account.target_sjp if account else 18000))
        target_sjp_entry = ttk.Entry(
            master=target_sjp_frame,
            textvariable=target_sjp_var,
            width=25,
            font=("Arial", 12),
        )
        target_sjp_entry.pack(side="left", padx=(10, 0), fill="x", expand=True)

        # Payment Type
        payment_type_frame = ttk.Frame(master=main_frame)
        payment_type_frame.pack(fill="x", pady=(0, 15))
        ttk.Label(master=payment_type_frame, text="Payment Type:", width=15, font=("Arial", 12)).pack(side="left")

        initial_payment_type = "FC" if (account.payment_type if account else 1) == 1 else "MC"
        payment_type_var = tk.StringVar(value=initial_payment_type)

        # Spin Action
        spin_type_frame = ttk.Frame(master=main_frame)
        spin_type_frame.pack(fill="x", pady=(0, 15))
        ttk.Label(master=spin_type_frame, text="Spin Action:", width=15, font=("Arial", 12)).pack(side="left")

        def get_spin_type_options(payment_type: str) -> List[str]:
            payment_prefix = payment_type
            return [
                f"{i}. {action_name.replace('Spin', f'{payment_prefix} Spin')}"
                for i, action_name in enumerate(EVENT_CONFIGS_MAP[self._selected_event].spin_types, start=1)
            ]

        spin_type_options = get_spin_type_options(payment_type_var.get())

        initial_spin_display = (
            (f"{account.spin_type}. {account.spin_type_name(selected_event=self._selected_event)}")
            if account
            else spin_type_options[0]
        )

        spin_type_var = tk.StringVar(value=initial_spin_display)
        spin_type_combobox = ttk.Combobox(
            master=spin_type_frame,
            textvariable=spin_type_var,
            values=spin_type_options,
            state="readonly",
            width=25,
            font=("Arial", 12),
        )
        spin_type_combobox.pack(side="left", padx=(10, 0), fill="x", expand=True)

        def on_payment_type_changed(*args: Any) -> None:
            current_spin_display = spin_type_var.get()
            try:
                spin_index = int(current_spin_display.split(".")[0])
            except (ValueError, IndexError):
                spin_index = 1

            new_options = get_spin_type_options(payment_type_var.get())
            spin_type_combobox.config(values=new_options)

            if 1 <= spin_index <= len(new_options):
                spin_type_var.set(new_options[spin_index - 1])

        payment_type_var.trace_add("write", on_payment_type_changed)

        payment_radio_frame = ttk.Frame(master=payment_type_frame)
        payment_radio_frame.pack(side="left", padx=(10, 0), fill="x", expand=True)

        payment_fc_radio = ttk.Radiobutton(
            master=payment_radio_frame,
            text="FC",
            variable=payment_type_var,
            value="FC",
        )
        payment_fc_radio.pack(side="left", padx=(0, 15))

        payment_mc_radio = ttk.Radiobutton(
            master=payment_radio_frame,
            text="MC",
            variable=payment_type_var,
            value="MC",
        )
        payment_mc_radio.pack(side="left")

        # Close on Jackpot Win
        close_on_jp_win_frame = ttk.Frame(master=main_frame)
        close_on_jp_win_frame.pack(fill="x", pady=(0, 25))
        close_on_jp_win_var = tk.BooleanVar(value=(account.close_on_jp_win if account else True))
        close_on_jp_win_checkbox = ttk.Checkbutton(
            master=close_on_jp_win_frame,
            text="Auto Close when won Ultimate Prize",
            variable=close_on_jp_win_var,
        )
        close_on_jp_win_checkbox.pack(anchor="w")

        def handle_save() -> None:
            spin_type_display = spin_type_var.get().strip()
            auto_close = close_on_jp_win_var.get()
            payment_type_val = 1 if payment_type_var.get() == "FC" else 2

            if not (username := username_var.get().strip()):
                messagebox.showerror("Error", "Username is required!")
                return

            if not (password := pwd_var.get().strip()):
                messagebox.showerror("Error", "Password is required!")
                return

            if (target_val := target_sjp_var.get()) <= 0:
                messagebox.showerror("Error", "Target Jackpot must be greater than 0!")
                return

            # Parse spin action
            try:
                spin_type_val = int(spin_type_display.split(".")[0])
            except (ValueError, IndexError):
                messagebox.showerror("Error", "Invalid spin action selected!")
                return

            if is_edit_mode:
                # Edit mode: duplicate username check (excluding current)
                assert account is not None  # Type narrowing for mypy
                if username != account.username and username in {a.username for a in self._accounts}:
                    messagebox.showerror("Error", f"Account with username '{username}' already exists!")
                    return

                # Update existing account
                account.username = username
                account.password = password
                account.spin_type = spin_type_val
                account.payment_type = payment_type_val
                account.target_sjp = target_val
                account.close_on_jp_win = auto_close

            elif is_duplicate_mode:
                # Duplicate mode: check username doesn't exist
                if username in {a.username for a in self._accounts}:
                    messagebox.showerror("Error", f"Account with username '{username}' already exists!")
                    return

                # Update the duplicated account details and add to list
                assert account is not None  # Type narrowing for mypy
                account.username = username
                account.password = password
                account.spin_type = spin_type_val
                account.payment_type = payment_type_val
                account.target_sjp = target_val
                account.close_on_jp_win = auto_close

                # Add the updated duplicated account to the list
                self._accounts.append(account)

            else:
                # Add mode: duplicate username check
                if username in {a.username for a in self._accounts}:
                    messagebox.showerror("Error", f"Account with username '{username}' already exists!")
                    return

                # Create new account
                self._accounts.append(
                    Account(
                        username=username,
                        password=password,
                        spin_type=spin_type_val,
                        payment_type=payment_type_val,
                        target_sjp=target_val,
                        close_on_jp_win=auto_close,
                    )
                )

            self._save_accounts_to_config()
            self._refresh_accounts_list()

            action_text = "updated" if is_edit_mode else "duplicated" if is_duplicate_mode else "created"
            messagebox.showinfo("Success", f"Account '{username}' {action_text} successfully!")
            dialog.destroy()

        # Buttons
        buttons_frame = ttk.Frame(master=main_frame)
        buttons_frame.pack(fill="x", pady=(0, 10))

        save_btn = ttk.Button(master=buttons_frame, text="Save", style="Accent.TButton", width=10, command=handle_save)
        save_btn.pack(side="right", padx=(5, 0))

        cancel_btn = ttk.Button(master=buttons_frame, text="Cancel", width=10, command=lambda: dialog.destroy())
        cancel_btn.pack(side="right")

        # Center and focus
        dialog.update_idletasks()
        _, _, dw, dh, x, y = hlp.get_window_position(child_frame=dialog, parent_frame=self._frame)
        dialog.geometry(f"{dw}x{dh}+{x}+{y}")
        dialog.resizable(False, False)

        username_entry.focus_set()
        username_entry.bind("<Return>", lambda _: handle_save())
        pwd_entry.bind("<Return>", lambda _: handle_save())
        target_sjp_entry.bind("<Return>", lambda _: handle_save())
        spin_type_combobox.bind("<Return>", lambda _: handle_save())
        close_on_jp_win_checkbox.bind("<Return>", lambda _: handle_save())

        dialog.wait_window()

    def _toggle_mark_not_run(self, account: Account) -> None:
        account.marked_not_run = not account.marked_not_run
        self._save_accounts_to_config()
        self._refresh_accounts_list()

    def _delete_account(self, account: Account) -> None:
        result = messagebox.askyesno(
            title="Confirm Delete",
            message=f"Are you sure you want to delete account '{account.username}'?",
            icon="warning",
        )

        if not result:
            return

        self._accounts.remove(account)
        self._save_accounts_to_config()
        self._refresh_accounts_list()

    def _save_accounts_to_config(self) -> None:
        self._configs.accounts = self._accounts
        config_mgr.save_configs(configs=self._configs)
