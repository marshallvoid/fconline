import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable, Dict, List, Optional, Set

from src.schemas.configs import Account
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

    @property
    def running_usernames(self) -> Set[str]:
        return self._running_usernames

    @running_usernames.setter
    def running_usernames(self, new_running_usernames: Set[str]) -> None:
        self._running_usernames = new_running_usernames
        self._refresh_accounts_list()

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
        accounts_frame = ttk.LabelFrame(main_content_frame, text="Saved Accounts", padding=10)
        accounts_frame.pack(side="left", fill="both", expand=True)

        # Configure columns for Treeview
        columns: Dict[str, Dict[str, Any]] = {
            "Username": {"width": 220, "anchor": "w"},
            "Status": {"width": 100, "anchor": "center"},
            "Spin Action": {"width": 120, "anchor": "center"},
            "Target": {"width": 120, "anchor": "center"},
            "Auto Close": {"width": 120, "anchor": "center"},
        }

        # Calculate total width for visible columns
        visible_width = columns["Username"]["width"] + columns["Status"]["width"] + 100

        # Create a frame to constrain treeview width
        tree_container = ttk.Frame(accounts_frame, width=visible_width)
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
        action_buttons_frame = ttk.LabelFrame(main_content_frame, text="Actions", padding=10)
        action_buttons_frame.pack(side="right", fill="y", padx=(10, 0))

        self._add_account_btn = ttk.Button(
            action_buttons_frame,
            text="Add Account",
            style="Accent.TButton",
            width=15,
            command=self._add_account,
        )
        self._add_account_btn.pack(fill="x", pady=(0, 20))

        self._run_all_btn = ttk.Button(
            action_buttons_frame,
            text="Run All",
            style="Accent.TButton",
            width=15,
            state="normal",
            command=self._run_all_account,
        )
        self._run_all_btn.pack(fill="x", pady=(0, 20))

        self._stop_all_btn = ttk.Button(
            action_buttons_frame,
            text="Stop All",
            style="Accent.TButton",
            width=15,
            state="disabled",
            command=self._stop_all_account,
        )
        self._stop_all_btn.pack(fill="x", pady=(0, 20))

        # Frame for Delete buttons
        self._delete_frame = ttk.Frame(action_buttons_frame)
        self._delete_frame.pack(fill="x")

        # Bind selection event
        self._accounts_tree.bind("<<TreeviewSelect>>", self._on_account_selected)
        self._accounts_tree.bind("<Double-1>", self._on_tree_double_click)
        self._accounts_tree.bind("<Shift-Double-1>", self._on_tree_shift_double_click)

        # Refresh the accounts list
        self._refresh_accounts_list()

    def _on_account_selected(self, _event: tk.Event) -> None:
        selection = self._accounts_tree.selection()

        # Clear previous buttons
        for widget in self._delete_frame.winfo_children():
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

        # Create Run/Edit/Delete buttons reflecting enabled state and running status
        is_running = username in self._running_usernames

        run_btn = ttk.Button(
            self._delete_frame,
            text="Run",
            style="Accent.TButton",
            width=15,
            state="disabled" if is_running else "normal",
            command=lambda: self._run_account(selected_account),
        )
        run_btn.pack(fill="x", pady=(0, 10))

        stop_btn = ttk.Button(
            self._delete_frame,
            text="Stop",
            style="Accent.TButton",
            width=15,
            state="disabled" if not is_running else "normal",
            command=lambda: self._stop_account(selected_account.username),
        )
        stop_btn.pack(fill="x", pady=(0, 10))

        edit_btn = ttk.Button(
            self._delete_frame,
            text="Edit",
            width=15,
            state="disabled" if is_running else "normal",
            command=lambda: self._edit_account(selected_account),
        )
        edit_btn.pack(fill="x", pady=(0, 10))

        delete_btn = ttk.Button(
            self._delete_frame,
            text="Delete",
            width=15,
            state="disabled" if is_running else "normal",
            command=lambda: self._delete_account(selected_account),
        )
        delete_btn.pack(fill="x")

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

        self._on_account_run(
            account.username,
            account.password,
            account.spin_action,
            account.target_special_jackpot,
            account.close_when_jackpot_won,
        )

        return "break"

    def _refresh_accounts_list(self) -> None:
        # Clear existing items
        for item in self._accounts_tree.get_children():
            self._accounts_tree.delete(item)

        # Clear Delete buttons
        for widget in self._delete_frame.winfo_children():
            widget.destroy()

        if not self._accounts and self._accounts_tree.master.master:
            # Show no accounts message above the accounts frame
            self._no_accounts_label.pack(before=self._accounts_tree.master.master, pady=(0, 20))
            return

        # Hide no accounts message
        self._no_accounts_label.pack_forget()

        # Add accounts to treeview
        for account in self._accounts:
            username = account.username
            status = "Running" if account.username in self._running_usernames else "Stopped"
            spin_action = EVENT_CONFIGS_MAP[self._selected_event].spin_actions[account.spin_action - 1]
            target_special_jackpot = account.target_special_jackpot
            close_when_jackpot_won = account.close_when_jackpot_won

            self._accounts_tree.insert(
                "",
                "end",
                values=(
                    username,
                    status,
                    spin_action,
                    target_special_jackpot,
                    close_when_jackpot_won,
                ),
            )

        # Enable if there is at least one account not running
        any_pending = any(a.username not in self._running_usernames for a in self._accounts)
        self._run_all_btn.config(state="normal" if any_pending else "disabled")

    def _run_all_account(self) -> None:
        pending_accounts = [a for a in self._accounts if a.username not in self._running_usernames]
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

        self._run_all_btn.config(state="disabled")
        self._stop_all_btn.config(state="normal")

        self._running_usernames.update(a.username for a in pending_accounts)
        self._refresh_accounts_list()

    def _run_account(self, account: Account) -> None:
        self._on_account_run(
            account.username,
            account.password,
            account.spin_action,
            account.target_special_jackpot,
            account.close_when_jackpot_won,
        )

        self._running_usernames.add(account.username)

        self._stop_all_btn.config(state="normal")
        if len(self._running_usernames) == len(self._accounts):
            self._run_all_btn.config(state="disabled")

        self._refresh_accounts_list()

    def _stop_all_account(self) -> None:
        if not self._running_usernames:
            messagebox.showinfo("Info", "No accounts to stop.")
            return

        for username in self._running_usernames:
            self._on_account_stop(username)

        self._run_all_btn.config(state="normal")
        self._stop_all_btn.config(state="disabled")

        self._running_usernames.clear()
        self._refresh_accounts_list()

    def _stop_account(self, username: str) -> None:
        self._on_account_stop(username)

        self._running_usernames.remove(username)

        self._run_all_btn.config(state="normal")
        if len(self._running_usernames) == 0:
            self._stop_all_btn.config(state="disabled")

        self._refresh_accounts_list()

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
        w, h = dialog.winfo_width(), dialog.winfo_height()
        x = (dialog.winfo_screenwidth() - w) // 2
        y = (dialog.winfo_screenheight() - h) // 2
        dialog.geometry(f"{w}x{h}+{x}+{y}")
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

        self._open_account_dialog(title=f"Edit Account: {account.username}", initial=account, on_submit=on_submit)

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
