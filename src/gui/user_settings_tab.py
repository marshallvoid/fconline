import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, List


class UserSettingsTab:
    def __init__(
        self,
        parent: tk.Misc,
        title: str,
        username_var: tk.StringVar,
        password_var: tk.StringVar,
        spin_action_var: tk.IntVar,
        target_special_jackpot_var: tk.IntVar,
        close_when_jackpot_won_var: tk.BooleanVar,
        spin_actions: List[str],
        on_spin_action_changed: Callable[[], None],
        on_save_account: Callable[[str, str], None],
    ) -> None:
        self._frame = ttk.Frame(parent)
        self._title = title
        self._username_var = username_var
        self._password_var = password_var
        self._spin_action_var = spin_action_var
        self._target_special_jackpot_var = target_special_jackpot_var
        self._close_when_jackpot_won_var = close_when_jackpot_won_var
        self._spin_actions = spin_actions
        self._on_spin_action_changed = on_spin_action_changed
        self._on_save_account = on_save_account

        self._build()

    @property
    def frame(self) -> ttk.Frame:
        return self._frame

    @property
    def title(self) -> str:
        return self._title

    def set_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"

        self._username_entry.config(state=state)
        self._password_entry.config(state=state)
        self._target_special_jackpot_entry.config(state=state)
        self._close_when_jackpot_won_checkbox.config(state=state)
        self._save_account_btn.config(state=state)

        for radio_btn in self._radio_buttons:
            radio_btn.config(state=state)

    def _build(self) -> None:
        title_label = ttk.Label(self._frame, text="User Settings", font=("Arial", 14, "bold"))
        title_label.pack(pady=(10, 20))

        container = ttk.Frame(self._frame)
        container.pack(fill="both", expand=True, padx=20)

        # Username
        username_frame = ttk.Frame(container)
        username_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(username_frame, text="Username:", width=20, font=("Arial", 12)).pack(side="left")
        self._username_entry = ttk.Entry(username_frame, textvariable=self._username_var, width=30, font=("Arial", 12))
        self._username_entry.pack(side="left", padx=(10, 0), fill="x", expand=True)

        # Password
        password_frame = ttk.Frame(container)
        password_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(password_frame, text="Password:", width=20, font=("Arial", 12)).pack(side="left")
        self._password_entry = ttk.Entry(
            password_frame,
            textvariable=self._password_var,
            show="*",
            width=30,
            font=("Arial", 12),
        )
        self._password_entry.pack(side="left", padx=(10, 0), fill="x", expand=True)

        # Target Special Jackpot
        target_frame = ttk.Frame(container)
        target_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(target_frame, text="Target Special Jackpot:", width=20, font=("Arial", 12)).pack(side="left")
        self._target_special_jackpot_entry = ttk.Entry(
            target_frame,
            textvariable=self._target_special_jackpot_var,
            width=30,
            font=("Arial", 12),
        )
        self._target_special_jackpot_entry.pack(side="left", padx=(10, 0), fill="x", expand=True)

        # Save Account Button - moved here, right below Target Special Jackpot
        save_account_frame = ttk.Frame(container)
        save_account_frame.pack(fill="x", pady=(10, 0))

        self._save_account_btn = ttk.Button(
            save_account_frame,
            text="Save Account",
            command=self._save_account,
            style="Accent.TButton",
        )
        self._save_account_btn.pack(anchor="e")

        # Close when won checkboxes
        close_options_frame = ttk.LabelFrame(container, text="Auto Close Options", padding=10)
        close_options_frame.pack(fill="x", pady=(0, 10))

        # Close when jackpot won checkbox
        close_jackpot_frame = ttk.Frame(close_options_frame)
        close_jackpot_frame.pack(fill="x", pady=(0, 5))
        self._close_when_jackpot_won_checkbox = ttk.Checkbutton(
            close_jackpot_frame,
            text="Close when won Ultimate Prize",
            variable=self._close_when_jackpot_won_var,
        )
        self._close_when_jackpot_won_checkbox.pack(anchor="w")

        # Spin Action
        spin_action_frame = ttk.LabelFrame(container, text="Spin Action", padding=10)
        spin_action_frame.pack(fill="x", pady=(0, 20))

        radio_container = ttk.Frame(spin_action_frame)
        radio_container.pack(fill="x")

        self._radio_buttons: List[ttk.Radiobutton] = []
        for index, value in enumerate(self._spin_actions, start=1):
            radio_btn = ttk.Radiobutton(
                radio_container,
                text=value,
                variable=self._spin_action_var,
                value=index,
                command=self._on_spin_action_changed,
            )
            radio_btn.pack(side="left", padx=(0, 20))
            self._radio_buttons.append(radio_btn)

    def _save_account(self) -> None:
        username = self._username_var.get().strip()
        password = self._password_var.get().strip()

        if not username:
            messagebox.showerror("Error", "Username is required to save account!")
            return

        if not password:
            messagebox.showerror("Error", "Password is required to save account!")
            return

        # Call the callback to save the account
        self._on_save_account(username, password)

        messagebox.showinfo("Success", f"Account '{username}' saved successfully!")
