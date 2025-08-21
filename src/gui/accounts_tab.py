import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, List

from src.schemas.user_config import Account


class AccountsTab:
    def __init__(
        self,
        parent: tk.Misc,
        accounts: List[Account],
        on_account_use: Callable[[str, str, int], None],
        on_accounts_changed: Callable[[List[Account]], None],
    ) -> None:
        self._frame = ttk.Frame(parent)
        self._accounts = accounts
        self._on_account_use = on_account_use
        self._on_accounts_changed = on_accounts_changed
        self._is_enabled: bool = True

        self._build()

    @property
    def frame(self) -> ttk.Frame:
        return self._frame

    def set_enabled(self, enabled: bool) -> None:
        self._is_enabled = enabled
        state = "normal" if enabled else "disabled"

        # Toggle Add Account button
        try:
            self._add_account_btn.config(state=state)
        except Exception:
            pass

        # Toggle Use/Delete buttons if they exist
        try:
            for child in self._use_delete_frame.winfo_children():
                try:
                    child.config(state=state)  # type: ignore
                except Exception:
                    pass
        except Exception:
            pass

    def update_accounts(self, accounts: List[Account]) -> None:
        self._accounts = accounts
        self._refresh_accounts_list()

    def _build(self) -> None:
        # Title and Add Account button row
        title_frame = ttk.Frame(self._frame)
        title_frame.pack(fill="x", pady=(10, 20))

        title_label = ttk.Label(title_frame, text="Accounts", font=("Arial", 16, "bold"))
        title_label.pack(side="left")

        container = ttk.Frame(self._frame)
        container.pack(fill="both", expand=True, padx=20)

        # Instructions
        instructions_label = ttk.Label(
            container,
            text="Manage your saved accounts. Click on a username to see actions.",
            font=("Arial", 12),
            foreground="#6b7280",
            wraplength=500,
        )
        instructions_label.pack(pady=(0, 20))

        # No accounts message - moved above the accounts frame
        self._no_accounts_label = ttk.Label(
            container,
            text="No accounts saved yet.\nSave accounts from the User Settings tab.",
            font=("Arial", 14),
            foreground="#6b7280",
            justify="center",
        )

        # Main content area with treeview and action buttons side by side
        main_content_frame = ttk.Frame(container)
        main_content_frame.pack(fill="both", expand=True)

        # Left side: Accounts list frame
        accounts_frame = ttk.LabelFrame(main_content_frame, text="Saved Accounts", padding=10)
        accounts_frame.pack(side="left", fill="both", expand=True)

        # Create Treeview for accounts list (username + target jackpot)
        columns = ("Username", "Target Jackpot")
        self._accounts_tree = ttk.Treeview(accounts_frame, columns=columns, show="headings", height=8)

        # Configure columns
        self._accounts_tree.heading("Username", text="Username")
        self._accounts_tree.heading("Target Jackpot", text="Target Jackpot")
        self._accounts_tree.column("Username", width=240, anchor="w")
        self._accounts_tree.column("Target Jackpot", width=140, anchor="center")

        # Scrollbar
        scrollbar = ttk.Scrollbar(accounts_frame, orient="vertical", command=self._accounts_tree.yview)
        self._accounts_tree.configure(yscrollcommand=scrollbar.set)

        # Pack treeview and scrollbar
        self._accounts_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Right side: Action buttons frame - ALWAYS VISIBLE
        self._action_buttons_frame = ttk.LabelFrame(main_content_frame, text="Actions", padding=10)
        self._action_buttons_frame.pack(side="right", fill="y", padx=(10, 0))

        # Add Account button - ALWAYS SHOWN
        self._add_account_btn = ttk.Button(
            self._action_buttons_frame,
            text="Add Account",
            style="Accent.TButton",
            command=self._add_account,
            width=15,
        )
        self._add_account_btn.pack(fill="x", pady=(0, 20))

        # Frame for Use/Delete buttons - initially empty
        self._use_delete_frame = ttk.Frame(self._action_buttons_frame)
        self._use_delete_frame.pack(fill="x")

        # Bind selection event
        self._accounts_tree.bind("<<TreeviewSelect>>", self._on_account_selected)
        # Bind double-click to quickly use the selected account
        self._accounts_tree.bind("<Double-1>", self._on_account_double_click)

        # Refresh the accounts list
        self._refresh_accounts_list()

    def _refresh_accounts_list(self) -> None:
        # Clear existing items
        for item in self._accounts_tree.get_children():
            self._accounts_tree.delete(item)

        # Clear Use/Delete buttons
        for widget in self._use_delete_frame.winfo_children():
            widget.destroy()

        if not self._accounts and self._accounts_tree.master.master:
            # Show no accounts message above the accounts frame
            self._no_accounts_label.pack(before=self._accounts_tree.master.master, pady=(0, 20))
            return

        # Hide no accounts message
        self._no_accounts_label.pack_forget()

        # Add accounts to treeview
        for account in self._accounts:
            self._accounts_tree.insert("", "end", values=(account.username, account.target_special_jackpot))

    def _on_account_double_click(self, _event: tk.Event) -> None:
        selection = self._accounts_tree.selection()
        if not selection:
            return

        item = self._accounts_tree.item(selection[0])
        values = item.get("values", [])
        if not values:
            return

        username = values[0]
        for account in self._accounts:
            if account.username == username:
                self._use_account(account)
                break

    def _on_account_selected(self, _event: tk.Event) -> None:
        selection = self._accounts_tree.selection()

        # Clear previous Use/Delete buttons
        for widget in self._use_delete_frame.winfo_children():
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

        # Create Use/Delete buttons reflecting enabled state
        btn_state = "normal" if self._is_enabled else "disabled"

        use_btn = ttk.Button(
            self._use_delete_frame,
            text="Use",
            style="Accent.TButton",
            command=lambda: self._use_account(selected_account),
            width=15,
            state=btn_state,
        )
        use_btn.pack(fill="x", pady=(0, 10))

        delete_btn = ttk.Button(
            self._use_delete_frame,
            text="Delete",
            command=lambda: self._delete_account(selected_account),
            width=15,
            state=btn_state,
        )
        delete_btn.pack(fill="x")

    def _use_account(self, account: Account) -> None:
        self._on_account_use(account.username, account.password, account.target_special_jackpot)

    def _delete_account(self, account: Account) -> None:
        result = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete account '{account.username}'?",
            icon="warning",
        )

        if not result:
            return

        self._accounts.remove(account)
        self._on_accounts_changed(self._accounts)
        self._refresh_accounts_list()

    def _add_account(self) -> None:
        # Create a new window for adding account
        add_window = tk.Toplevel(self._frame)
        add_window.title("Add New Account")
        add_window.transient(self._frame)  # type: ignore
        add_window.grab_set()  # Make window modal

        # Main container
        main_frame = ttk.Frame(add_window, padding=20)
        main_frame.pack(fill="both", expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="Add New Account", font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))

        # Username field
        username_frame = ttk.Frame(main_frame)
        username_frame.pack(fill="x", pady=(0, 15))
        ttk.Label(username_frame, text="Username:", width=15, font=("Arial", 12)).pack(side="left")
        username_var = tk.StringVar()
        username_entry = ttk.Entry(username_frame, textvariable=username_var, width=25, font=("Arial", 12))
        username_entry.pack(side="left", padx=(10, 0), fill="x", expand=True)

        # Password field
        password_frame = ttk.Frame(main_frame)
        password_frame.pack(fill="x", pady=(0, 15))
        ttk.Label(password_frame, text="Password:", width=15, font=("Arial", 12)).pack(side="left")
        password_var = tk.StringVar()
        password_entry = ttk.Entry(password_frame, textvariable=password_var, show="*", width=25, font=("Arial", 12))
        password_entry.pack(side="left", padx=(10, 0), fill="x", expand=True)

        # Target Special Jackpot field
        target_frame = ttk.Frame(main_frame)
        target_frame.pack(fill="x", pady=(0, 25))
        ttk.Label(target_frame, text="Target Jackpot:", width=15, font=("Arial", 12)).pack(side="left")
        target_var = tk.IntVar(value=19000)
        target_entry = ttk.Entry(target_frame, textvariable=target_var, width=25, font=("Arial", 12))
        target_entry.pack(side="left", padx=(10, 0), fill="x", expand=True)

        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill="x", pady=(0, 10))

        def save_account() -> None:
            username = username_var.get().strip()
            password = password_var.get().strip()
            target_val = target_var.get()

            if not username:
                messagebox.showerror("Error", "Username is required!")
                return

            if not password:
                messagebox.showerror("Error", "Password is required!")
                return

            if target_val <= 0:
                messagebox.showerror("Error", "Target Jackpot must be greater than 0!")
                return

            # Check if username already exists
            for existing_account in self._accounts:
                if existing_account.username == username:
                    messagebox.showerror("Error", f"Account with username '{username}' already exists!")
                    return

            # Create new account
            new_account = Account(username=username, password=password, target_special_jackpot=target_val)
            self._accounts.append(new_account)

            # Update accounts list and notify parent
            self._on_accounts_changed(self._accounts)
            self._refresh_accounts_list()

            # Show success message and close window
            messagebox.showinfo("Success", f"Account '{username}' added successfully!")
            add_window.destroy()

        def cancel() -> None:
            add_window.destroy()

        # Save button
        save_btn = ttk.Button(buttons_frame, text="Save", command=save_account, style="Accent.TButton", width=10)
        save_btn.pack(side="right", padx=(5, 0))

        # Cancel button
        cancel_btn = ttk.Button(buttons_frame, text="Cancel", command=cancel, width=10)
        cancel_btn.pack(side="right")

        # Center the window
        add_window.update_idletasks()
        w, h = add_window.winfo_width(), add_window.winfo_height()
        x = (add_window.winfo_screenwidth() - w) // 2
        y = (add_window.winfo_screenheight() - h) // 2
        add_window.geometry(f"{w}x{h}+{x}+{y}")
        add_window.resizable(False, False)

        # Set focus to username entry and bind Enter key
        username_entry.focus_set()
        username_entry.bind("<Return>", lambda e: password_entry.focus_set())
        password_entry.bind("<Return>", lambda e: target_entry.focus_set())
        target_entry.bind("<Return>", lambda e: save_account())

        # Wait for window to close
        add_window.wait_window()
