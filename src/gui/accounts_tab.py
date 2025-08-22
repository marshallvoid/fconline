import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable, Dict, List, Optional, Set

from src.schemas.configs import Account
from src.schemas.enums.account_tag import AccountTag
from src.schemas.user_response import UserDetail
from src.utils import helpers as hp
from src.utils.contants import EVENT_CONFIGS_MAP
from src.utils.user_config import UserConfigManager


class AccountsTab:
    def __init__(
        self,
        parent: tk.Misc,
        selected_event: str,
        on_account_run: Callable[[str, str, int, int, bool], None],
        on_account_stop: Callable[[str], None],
    ) -> None:
        self._frame = ttk.Frame(parent)

        self._selected_event = selected_event
        self._on_account_run = on_account_run
        self._on_account_stop = on_account_stop

        self._accounts: List[Account] = self._load_accounts_from_config()
        self._running_usernames: Set[str] = set()
        self._users_info: Dict[str, UserDetail] = {}

        self._build()

    @property
    def frame(self) -> ttk.Frame:
        return self._frame

    @property
    def selected_event(self) -> str:
        return self._selected_event

    @selected_event.setter
    def selected_event(self, new_event: str) -> None:
        self._selected_event = new_event

    def mark_account_as_won(self, username: str) -> None:
        account = next((a for a in self._accounts if a.username == username), None)
        if not account:
            return

        account.has_won = True
        self._save_accounts_to_config()
        self._refresh_accounts_list()

    def update_user_info(self, username: str, user: UserDetail) -> None:
        account = next((a for a in self._accounts if a.username == username), None)
        if not account:
            return

        self._users_info[username] = user
        self._update_info_display(account=account, is_running=username in self._running_usernames)

    def _build(self) -> None:
        container = ttk.Frame(self._frame)
        container.pack(fill="both", expand=True, padx=20, pady=(20, 10))

        # No accounts message
        self._no_accounts_label = ttk.Label(
            container,
            font=("Arial", 14),
            foreground="#6b7280",
            justify="center",
            text="No accounts saved yet.\nAdd some accounts and select an event.",
        )

        # Main content area with treeview and action buttons side by side
        main_content_frame = ttk.Frame(container)
        main_content_frame.pack(fill="both", expand=True)

        # Left side: Accounts list frame
        left_frame = ttk.LabelFrame(main_content_frame, text="Saved Accounts", padding=10)
        left_frame.pack(side="left", fill="both", expand=True)

        # Configure columns for Treeview
        columns: Dict[str, Dict[str, Any]] = {
            "Username": {"width": 160, "anchor": "w"},
            "Target": {"width": 120, "anchor": "center"},
            "Spin Action": {"width": 120, "anchor": "center"},
            "Auto Close": {"width": 120, "anchor": "center"},
        }

        # Create a frame to constrain treeview width
        tree_container = ttk.Frame(left_frame, width=300)
        tree_container.pack_propagate(False)  # Prevent frame from expanding

        self._accounts_tree = ttk.Treeview(
            tree_container,
            columns=list(columns.keys()),
            show="headings",
            height=8,
            padding=8,
        )

        # Scrollbar
        hsc = ttk.Scrollbar(tree_container, orient="horizontal", command=self._accounts_tree.xview)
        self._accounts_tree.configure(xscrollcommand=hsc.set)

        vsc = ttk.Scrollbar(tree_container, orient="vertical", command=self._accounts_tree.yview)
        self._accounts_tree.configure(yscrollcommand=vsc.set)

        # Pack treeview and scrollbar
        tree_container.pack(side="left", fill="both", expand=True)
        hsc.pack(side="bottom", fill="x")
        vsc.pack(side="right", fill="y")
        self._accounts_tree.pack(fill="both", expand=True)

        for column, config in columns.items():
            self._accounts_tree.heading(column, text=column)
            self._accounts_tree.column(column, **config)

        # Right side: Action buttons frame
        right_frame = ttk.LabelFrame(main_content_frame, text="Actions", padding=10)
        right_frame.pack(side="right", fill="y", padx=(10, 0))

        self._add_account_btn = ttk.Button(
            right_frame,
            text="Add Account",
            style="Accent.TButton",
            width=15,
            command=self._add_account,
        )
        self._add_account_btn.pack(fill="x", pady=(0, 20))

        # Run All and Stop All buttons on the same row
        control_all_container = ttk.Frame(right_frame)
        control_all_container.pack(fill="x", pady=(0, 20))

        self._run_all_btn = ttk.Button(
            control_all_container,
            text="Run All",
            style="Accent.TButton",
            width=15,
            state="normal",
            command=self._run_all_account,
        )
        self._run_all_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self._stop_all_btn = ttk.Button(
            control_all_container,
            text="Stop All",
            style="Accent.TButton",
            width=15,
            state="disabled",
            command=self._stop_all_account,
        )
        self._stop_all_btn.pack(side="right", fill="x", expand=True)

        # Reset Winners button
        self._reset_winners_btn = ttk.Button(
            right_frame,
            text="Reset Winners",
            width=15,
            command=self._reset_winners,
        )
        self._reset_winners_btn.pack(fill="x", pady=(0, 20))

        # Frame for hidden buttons
        self._hidden_frame = ttk.Frame(right_frame)
        self._hidden_frame.pack(fill="x")

        # Bind selection event
        self._accounts_tree.bind("<<TreeviewSelect>>", self._on_account_selected)
        self._accounts_tree.bind("<Double-1>", self._on_tree_double_click)
        self._accounts_tree.bind("<Shift-Double-1>", self._on_tree_shift_double_click)

        # Refresh the accounts list
        self._refresh_accounts_list()

    def _on_account_selected(self, _event: tk.Event) -> None:
        selection = self._accounts_tree.selection()

        # Clear previous buttons
        for widget in self._hidden_frame.winfo_children():
            widget.destroy()

        if not selection:
            return

        # Get selected username
        item = self._accounts_tree.item(selection[0])
        username = item["values"][0]

        # Find the account
        selected_account = None
        for account in self._accounts:
            if account.username == username:
                selected_account = account
                break

        if not selected_account:
            return

        # Create buttons reflecting enabled state and running status
        is_running = selected_account.username in self._running_usernames
        is_winning = selected_account.has_won
        is_marked_not_run = selected_account.marked_not_run

        # Control buttons group (Run/Stop)
        control_container = ttk.Frame(self._hidden_frame)
        control_container.pack(fill="x", pady=(0, 10))

        run_btn = ttk.Button(
            control_container,
            text="Run",
            style="Accent.TButton",
            width=15,
            state="disabled" if is_running or is_winning or is_marked_not_run else "normal",
            command=lambda: self._run_account(selected_account),
        )
        run_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))

        stop_btn = ttk.Button(
            control_container,
            text="Stop",
            style="Accent.TButton",
            width=15,
            state="disabled" if not is_running else "normal",
            command=lambda: self._stop_account(selected_account.username),
        )
        stop_btn.pack(side="right", fill="x", expand=True)

        # Management buttons group (Mark/Edit)
        management_container = ttk.Frame(self._hidden_frame)
        management_container.pack(fill="x", pady=(0, 10))

        mark_not_run_btn = ttk.Button(
            management_container,
            text="Unmark Not Run" if is_marked_not_run else "Mark Not Run",
            width=15,
            state="disabled" if is_running or is_winning else "normal",
            command=lambda: self._toggle_mark_not_run(selected_account),
        )
        mark_not_run_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))

        edit_btn = ttk.Button(
            management_container,
            text="Edit",
            width=15,
            state="disabled" if is_running or is_winning or is_marked_not_run else "normal",
            command=lambda: self._edit_account(selected_account),
        )
        edit_btn.pack(side="right", fill="x", expand=True)

        # Delete button
        delete_btn = ttk.Button(
            self._hidden_frame,
            text="Delete",
            width=15,
            state="disabled" if is_running or is_winning or is_marked_not_run else "normal",
            command=lambda: self._delete_account(selected_account),
        )
        delete_btn.pack(fill="x")

        # Frame for browser and user information
        self._info_frame = ttk.LabelFrame(self._hidden_frame, text="Information", padding=10)
        self._info_frame.pack(fill="x", pady=(20, 0))

        # Browser position info
        self._browser_position_label = ttk.Label(
            self._info_frame,
            text="Browser Position: -",
            font=("Arial", 14),
            foreground="#6b7280",
        )
        self._browser_position_label.pack(anchor="w", pady=(0, 5))

        # User info
        self._user_info_label = ttk.Label(
            self._info_frame,
            text="User: -",
            font=("Arial", 14),
            foreground="#6b7280",
        )
        self._user_info_label.pack(anchor="w", pady=(0, 5))

        # FC info
        self._fc_info_label = ttk.Label(
            self._info_frame,
            text="FC: -",
            font=("Arial", 14),
            foreground="#6b7280",
        )
        self._fc_info_label.pack(anchor="w")

        # Update information display
        self._update_info_display(account=selected_account, is_running=is_running)

    def _get_account_at_event(self, event: tk.Event) -> Optional[Account]:
        iid = self._accounts_tree.identify_row(event.y)
        if not iid:
            return None

        values = self._accounts_tree.item(iid, "values")
        if not values:
            return None

        username = values[0]
        return next((a for a in self._accounts if a.username == username), None)

    def _on_tree_double_click(self, event: tk.Event) -> None:
        account = self._get_account_at_event(event=event)
        if not account:
            return

        if account.username in self._running_usernames:
            messagebox.showinfo("Info", f"Account '{account.username}' is running; stop it before editing.")
            return

        self._edit_account(account)

    def _on_tree_shift_double_click(self, event: tk.Event) -> object:
        account = self._get_account_at_event(event=event)
        if not account:
            return "break"

        if account.username in self._running_usernames:
            messagebox.showinfo("Info", f"Account '{account.username}' is already running.")
            return "break"

        if account.has_won:
            messagebox.showinfo("Info", f"Account '{account.username}' has already won; cannot run winning accounts.")
            return "break"

        if account.marked_not_run:
            messagebox.showinfo(
                "Info", f"Account '{account.username}' is marked as not run; cannot run marked accounts."
            )
            return "break"

        self._run_account(account=account)

        return "break"

    def _refresh_accounts_list(self) -> None:
        # Clear existing items
        for item in self._accounts_tree.get_children():
            self._accounts_tree.delete(item)

        # Clear Delete buttons
        for widget in self._hidden_frame.winfo_children():
            widget.destroy()

        if not self._accounts and self._accounts_tree.master.master:
            # Show no accounts message above the accounts frame
            self._no_accounts_label.pack(before=self._accounts_tree.master.master, pady=(0, 20))
            return

        # Hide no accounts message
        self._no_accounts_label.pack_forget()

        # Configure tags for colors
        for tag in AccountTag:
            self._accounts_tree.tag_configure(tag.name, background=tag.value[0], foreground=tag.value[1])

        # Add accounts to treeview
        for account in self._accounts:
            if account.has_won:
                tags = (AccountTag.WINNER.name,)
            elif account.username in self._running_usernames:
                tags = (AccountTag.RUNNING.name,)
            elif account.marked_not_run:
                tags = (AccountTag.MARKED_NOT_RUN.name,)
            else:
                tags = (AccountTag.STOPPED.name,)

            self._accounts_tree.insert(
                "",
                "end",
                values=(
                    account.username,
                    account.target_special_jackpot,
                    EVENT_CONFIGS_MAP[self._selected_event].spin_actions[account.spin_action - 1],
                    account.close_when_jackpot_won,
                ),
                tags=tags,
            )

        # Enable if there is at least one account not running
        # Check if there are any accounts that can be run (not running, not winning, and not marked not run)
        any_pending = any(
            a.username not in self._running_usernames and not a.has_won and not a.marked_not_run for a in self._accounts
        )
        self._run_all_btn.config(state="normal" if any_pending else "disabled")

        any_running = any(a.username in self._running_usernames for a in self._accounts)
        self._stop_all_btn.config(state="normal" if any_running else "disabled")

        # Enable Reset Winners button only if there are winning accounts
        any_winning = any(a.has_won for a in self._accounts)
        self._reset_winners_btn.config(state="normal" if any_winning else "disabled")

    def _open_account_dialog(
        self,
        title: str,
        initial: Optional[Account],
        on_submit: Callable[[str, str, int, int, bool], bool],
    ) -> None:
        dialog = tk.Toplevel(self._frame)
        dialog.title(title)
        dialog.transient(self._frame)  # type: ignore
        dialog.grab_set()

        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill="both", expand=True)

        # Title
        title_label = ttk.Label(main_frame, text=title, font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))

        # Username
        username_frame = ttk.Frame(main_frame)
        username_frame.pack(fill="x", pady=(0, 15))
        ttk.Label(username_frame, text="Username:", width=15, font=("Arial", 12)).pack(side="left")
        username_var = tk.StringVar(value=(initial.username if initial else ""))
        username_entry = ttk.Entry(username_frame, textvariable=username_var, width=25, font=("Arial", 12))
        username_entry.pack(side="left", padx=(10, 0), fill="x", expand=True)

        # Password
        password_frame = ttk.Frame(main_frame)
        password_frame.pack(fill="x", pady=(0, 15))
        ttk.Label(password_frame, text="Password:", width=15, font=("Arial", 12)).pack(side="left")
        password_var = tk.StringVar(value=(initial.password if initial else ""))
        password_entry = ttk.Entry(password_frame, textvariable=password_var, show="*", width=25, font=("Arial", 12))
        password_entry.pack(side="left", padx=(10, 0), fill="x", expand=True)

        # Target Special Jackpot
        target_frame = ttk.Frame(main_frame)
        target_frame.pack(fill="x", pady=(0, 15))
        ttk.Label(target_frame, text="Target Jackpot:", width=15, font=("Arial", 12)).pack(side="left")
        target_var = tk.IntVar(value=(initial.target_special_jackpot if initial else 19000))
        target_entry = ttk.Entry(target_frame, textvariable=target_var, width=25, font=("Arial", 12))
        target_entry.pack(side="left", padx=(10, 0), fill="x", expand=True)

        # Spin Action
        spin_action_frame = ttk.Frame(main_frame)
        spin_action_frame.pack(fill="x", pady=(0, 15))
        ttk.Label(spin_action_frame, text="Spin Action:", width=15, font=("Arial", 12)).pack(side="left")

        spin_action_options = [
            f"{i}. {action_name}"
            for i, action_name in enumerate(EVENT_CONFIGS_MAP[self._selected_event].spin_actions, start=1)
        ]

        initial_spin_display = (
            (f"{initial.spin_action}. {EVENT_CONFIGS_MAP[self._selected_event].spin_actions[initial.spin_action - 1]}")
            if initial
            else spin_action_options[0]
        )

        spin_action_var = tk.StringVar(value=initial_spin_display)
        spin_action_combobox = ttk.Combobox(
            spin_action_frame,
            textvariable=spin_action_var,
            values=spin_action_options,
            state="readonly",
            width=25,
            font=("Arial", 12),
        )
        spin_action_combobox.pack(side="left", padx=(10, 0), fill="x", expand=True)

        # Auto Close
        auto_close_frame = ttk.Frame(main_frame)
        auto_close_frame.pack(fill="x", pady=(0, 25))
        auto_close_var = tk.BooleanVar(value=(initial.close_when_jackpot_won if initial else True))
        auto_close_checkbox = ttk.Checkbutton(
            auto_close_frame,
            text="Auto Close when won Ultimate Prize",
            variable=auto_close_var,
        )
        auto_close_checkbox.pack(anchor="w")

        # Buttons
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill="x", pady=(0, 10))

        def handle_save() -> None:
            username = username_var.get().strip()
            password = password_var.get().strip()
            target_val = target_var.get()
            spin_action_display = spin_action_var.get()
            auto_close = auto_close_var.get()

            if not username:
                messagebox.showerror("Error", "Username is required!")
                return

            if not password:
                messagebox.showerror("Error", "Password is required!")
                return

            if target_val <= 0:
                messagebox.showerror("Error", "Target Jackpot must be greater than 0!")
                return

            # Parse spin action
            try:
                spin_action_val = int(spin_action_display.split(".")[0])
            except (ValueError, IndexError):
                messagebox.showerror("Error", "Invalid spin action selected!")
                return

            if on_submit(username, password, spin_action_val, target_val, auto_close):
                messagebox.showinfo("Success", f"Account '{username}' saved successfully!")
                dialog.destroy()

        save_btn = ttk.Button(buttons_frame, text="Save", style="Accent.TButton", width=10, command=handle_save)
        save_btn.pack(side="right", padx=(5, 0))

        cancel_btn = ttk.Button(buttons_frame, text="Cancel", width=10, command=lambda: dialog.destroy())
        cancel_btn.pack(side="right")

        # Center and focus
        dialog.update_idletasks()
        _, _, dw, dh, x, y = hp.get_window_position(child_frame=dialog, parent_frame=self._frame)
        dialog.geometry(f"{dw}x{dh}+{x}+{y}")
        dialog.resizable(False, False)

        username_entry.focus_set()
        username_entry.bind("<Return>", lambda e: password_entry.focus_set())
        password_entry.bind("<Return>", lambda e: target_entry.focus_set())
        target_entry.bind("<Return>", lambda e: spin_action_combobox.focus_set())
        spin_action_combobox.bind("<Return>", lambda e: auto_close_checkbox.focus_set())
        auto_close_checkbox.bind("<Return>", lambda e: handle_save())

        dialog.wait_window()

    def _add_account(self) -> None:
        def on_submit(
            username: str,
            password: str,
            spin_action: int,
            target_special_jackpot: int,
            auto_close: bool,
        ) -> bool:
            # Duplicate username check
            if username in {a.username for a in self._accounts}:
                messagebox.showerror("Error", f"Account with username '{username}' already exists!")
                return False

            self._accounts.append(
                Account(
                    username=username,
                    password=password,
                    spin_action=spin_action,
                    target_special_jackpot=target_special_jackpot,
                    close_when_jackpot_won=auto_close,
                )
            )
            self._save_accounts_to_config()
            self._refresh_accounts_list()
            return True

        self._open_account_dialog(title="Add New Account", initial=None, on_submit=on_submit)

    def _run_all_account(self) -> None:
        pending_accounts = [
            a
            for a in self._accounts
            if a.username not in self._running_usernames and not a.has_won and not a.marked_not_run
        ]
        if not pending_accounts:
            messagebox.showinfo("Info", "No accounts to run.")
            return

        for account in pending_accounts:
            self._on_account_run(
                account.username,
                account.password,
                account.spin_action,
                account.target_special_jackpot,
                account.close_when_jackpot_won,
            )

        self._running_usernames.update(a.username for a in pending_accounts)
        self._refresh_accounts_list()

    def _stop_all_account(self) -> None:
        if not self._running_usernames:
            messagebox.showinfo("Info", "No accounts to stop.")
            return

        for username in self._running_usernames:
            self._on_account_stop(username)

        self._running_usernames.clear()
        self._refresh_accounts_list()

    def _reset_winners(self) -> None:
        winning_accounts = {a for a in self._accounts if a.has_won}
        if not winning_accounts:
            messagebox.showinfo("Info", "No winning accounts to reset.")
            return

        result = messagebox.askyesno(
            "Confirm Reset",
            (
                f"Are you sure you want to reset {len(winning_accounts)} winning account(s)?\n"
                "This will allow them to run again."
            ),
            icon="warning",
        )

        if not result:
            return

        for account in winning_accounts:
            account.has_won = False

        self._save_accounts_to_config()
        self._refresh_accounts_list()

        messagebox.showinfo("Success", "All winning accounts have been reset.")

    def _run_account(self, account: Account) -> None:
        if account.has_won:
            messagebox.showinfo("Info", f"Account '{account.username}' has already won; cannot run winning accounts.")
            return

        if account.marked_not_run:
            messagebox.showinfo(
                "Info", f"Account '{account.username}' is marked as not run; cannot run marked accounts."
            )
            return

        self._on_account_run(
            account.username,
            account.password,
            account.spin_action,
            account.target_special_jackpot,
            account.close_when_jackpot_won,
        )

        self._running_usernames.add(account.username)
        self._refresh_accounts_list()

    def _stop_account(self, username: str) -> None:
        self._on_account_stop(username)

        self._running_usernames.remove(username)
        self._refresh_accounts_list()

    def _toggle_mark_not_run(self, account: Account) -> None:
        account.marked_not_run = not account.marked_not_run
        self._save_accounts_to_config()
        self._refresh_accounts_list()

    def _edit_account(self, account: Account) -> None:
        def on_submit(
            username: str,
            password: str,
            spin_action: int,
            target_special_jackpot: int,
            auto_close: bool,
        ) -> bool:
            # Duplicate username check (excluding current)
            if username in {a.username for a in self._accounts} and username != account.username:
                messagebox.showerror("Error", f"Account with username '{username}' already exists!")
                return False

            account.username = username
            account.password = password
            account.spin_action = spin_action
            account.target_special_jackpot = target_special_jackpot
            account.close_when_jackpot_won = auto_close

            self._save_accounts_to_config()
            self._refresh_accounts_list()
            return True

        self._open_account_dialog(title="Edit Account", initial=account, on_submit=on_submit)

    def _delete_account(self, account: Account) -> None:
        result = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete account '{account.username}'?",
            icon="warning",
        )

        if not result:
            return

        self._accounts.remove(account)
        self._save_accounts_to_config()
        self._refresh_accounts_list()

    def _load_accounts_from_config(self) -> List[Account]:
        try:
            configs = UserConfigManager.load_configs()
            return configs.accounts

        except Exception:
            return []

    def _save_accounts_to_config(self) -> None:
        try:
            configs = UserConfigManager.load_configs()
            configs.event = self._selected_event
            configs.accounts = self._accounts
            UserConfigManager.save_configs(configs)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save accounts: {e}")

    def _update_info_display(self, account: Account, is_running: bool) -> None:
        green, gray = "#22c55e", "#6b7280"
        positions = ("Top-Left", "Top-Right", "Bottom-Left", "Bottom-Right")

        def set_ok_or_unknown(label: ttk.Label, build_text: Callable[[], str], unknown_text: str) -> None:
            try:
                text = build_text()
                if text:
                    label.config(text=text, foreground=green)
                    return

            except Exception:
                pass

            label.config(text=unknown_text, foreground=gray)

        if not is_running:
            self._browser_position_label.config(text="Browser Position: Not Running", foreground=gray)
            self._user_info_label.config(text="User: Unknown", foreground=gray)
            self._fc_info_label.config(text="FC: Unknown", foreground=gray)
            return

        def browser_pos_text() -> str:
            idx = list(self._running_usernames).index(account.username)
            pos = positions[idx] if idx < len(positions) else "Center"
            return f"Browser Position: {pos}"

        def pick_display_name() -> Optional[str]:
            u = self._users_info[account.username]
            uname = account.username.casefold()

            for c in (u.nickname, u.account_name):
                if c and c.casefold() != uname:
                    return c

            return None

        set_ok_or_unknown(self._browser_position_label, browser_pos_text, "Browser Position: Unknown")
        set_ok_or_unknown(self._user_info_label, lambda: f"User: {pick_display_name()}", "User: Unknown")
        set_ok_or_unknown(self._fc_info_label, lambda: f"FC: {self._users_info[account.username].fc}", "FC: Unknown")
