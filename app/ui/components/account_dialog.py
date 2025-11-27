import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, List, Optional

from app.schemas.configs import Account
from app.ui.utils.ui_factory import UIFactory
from app.ui.utils.ui_helpers import UIHelpers
from app.utils.constants import EVENT_CONFIGS_MAP
from app.utils.helpers import get_window_position


class AccountDialog:
    def __init__(
        self,
        parent: tk.Misc,
        selected_event: str,
        existing_accounts: List[Account],
        account: Optional[Account] = None,
        on_save: callable = None,
    ) -> None:
        self._parent = parent
        self._selected_event = selected_event

        self._existing_accounts = existing_accounts
        self._account = account
        self._on_save = on_save

        # Determine dialog mode
        self._is_edit_mode = account is not None and account.username in {a.username for a in existing_accounts}

        self._dialog: Optional[tk.Toplevel] = None
        self._create_dialog()

    def _create_dialog(self) -> None:
        if self._is_edit_mode:
            title = "Edit Account"
        else:
            title = "Add New Account"

        self._dialog = tk.Toplevel(master=self._parent)
        self._dialog.title(string=title)
        self._dialog.transient(master=self._parent)  # type: ignore
        self._dialog.grab_set()

        main_frame = ttk.Frame(master=self._dialog, padding=20)
        main_frame.pack(fill="both", expand=True)

        # Title
        title_label = ttk.Label(master=main_frame, text=title, font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))

        # Form fields
        self._setup_form_fields(parent=main_frame)
        self._setup_buttons(parent=main_frame)

        # Center and focus
        self._dialog.update_idletasks()
        _, _, dw, dh, x, y = get_window_position(child_frame=self._dialog, parent_frame=self._parent)
        self._dialog.geometry(f"{dw}x{dh}+{x}+{y}")
        self._dialog.resizable(False, False)

        self._username_entry.focus_set()

        # Bind Enter key to all inputs
        UIHelpers.bind_enter_key(
            widgets=[
                self._username_entry,
                self._pwd_entry,
                self._target_sjp_entry,
                self._target_mjp_entry,
                self._spin_delay_entry,
                self._spin_type_combobox,
                self._close_on_jp_win_checkbox,
            ],
            callback=self._handle_save,
        )

        self._dialog.wait_window()

    def _setup_form_fields(self, parent: tk.Misc) -> None:
        # Username
        username_frame, self._username_entry = UIFactory.create_form_row(
            parent=parent,
            label_text="Username:",
            widget_type="entry",
        )
        username_frame.pack(fill="x", pady=(0, 15))
        self._username_var = tk.StringVar(value=(self._account.username if self._account else ""))
        self._username_entry.config(textvariable=self._username_var)

        # Password
        pwd_frame, self._pwd_entry = UIFactory.create_form_row(
            parent=parent,
            label_text="Password:",
            widget_type="entry",
            show="*",
        )
        pwd_frame.pack(fill="x", pady=(0, 15))
        self._pwd_var = tk.StringVar(value=(self._account.password if self._account else ""))
        self._pwd_entry.config(textvariable=self._pwd_var)

        # Target Special Jackpot
        target_sjp_frame, self._target_sjp_entry = UIFactory.create_form_row(
            parent=parent,
            label_text="Target Jackpot:",
            widget_type="entry",
        )
        target_sjp_frame.pack(fill="x", pady=(0, 15))
        self._target_sjp_var = tk.IntVar(value=(self._account.target_sjp if self._account else 18000))
        self._target_sjp_entry.config(textvariable=self._target_sjp_var)

        # Target Mini Jackpot (Optional)
        target_mjp_frame, self._target_mjp_entry = UIFactory.create_form_row(
            parent=parent,
            label_text="Target Mini JP:",
            widget_type="entry",
        )
        target_mjp_frame.pack(fill="x", pady=(0, 15))
        self._target_mjp_var = tk.StringVar(
            value=str(self._account.target_mjp) if self._account and self._account.target_mjp else ""
        )
        self._target_mjp_entry.config(textvariable=self._target_mjp_var)

        # Payment Type and Spin Action
        self._setup_payment_and_spin(parent=parent)

        # Spin Delay
        self._setup_spin_delay(parent=parent)

        # Close on Jackpot Win
        close_on_jp_win_frame = ttk.Frame(master=parent)
        close_on_jp_win_frame.pack(fill="x", pady=(0, 25))
        self._close_on_jp_win_var = tk.BooleanVar(value=(self._account.close_on_jp_win if self._account else True))
        self._close_on_jp_win_checkbox = ttk.Checkbutton(
            master=close_on_jp_win_frame,
            text="Auto Close when won Ultimate Prize",
            variable=self._close_on_jp_win_var,
        )
        self._close_on_jp_win_checkbox.pack(anchor="w")

    def _setup_payment_and_spin(self, parent: tk.Misc) -> None:
        # Payment Type
        payment_type_frame = ttk.Frame(master=parent)
        payment_type_frame.pack(fill="x", pady=(0, 15))
        ttk.Label(master=payment_type_frame, text="Payment Type:", width=15, font=("Arial", 12)).pack(side="left")

        initial_payment_type = "FC" if (self._account.payment_type if self._account else 1) == 1 else "MC"
        self._payment_type_var = tk.StringVar(value=initial_payment_type)

        # Spin Action
        spin_type_frame = ttk.Frame(master=parent)
        spin_type_frame.pack(fill="x", pady=(0, 15))
        ttk.Label(master=spin_type_frame, text="Spin Action:", width=15, font=("Arial", 12)).pack(side="left")

        def get_spin_type_options(payment_type: str) -> List[str]:
            payment_prefix = payment_type
            return [
                f"{i}. {action_name.replace('Spin', f'{payment_prefix} Spin')}"
                for i, action_name in enumerate(EVENT_CONFIGS_MAP[self._selected_event].spin_types, start=1)
            ]

        spin_type_options = get_spin_type_options(self._payment_type_var.get())

        initial_spin_display = (
            (f"{self._account.spin_type}. {self._account.spin_type_name(selected_event=self._selected_event)}")
            if self._account
            else spin_type_options[0]
        )

        self._spin_type_var = tk.StringVar(value=initial_spin_display)
        self._spin_type_combobox = UIFactory.create_combobox(
            parent=spin_type_frame,
            textvariable=self._spin_type_var,
            values=spin_type_options,
        )
        self._spin_type_combobox.pack(side="left", padx=(10, 0), fill="x", expand=True)

        def on_payment_type_changed(*args: Any) -> None:
            current_spin_display = self._spin_type_var.get()
            try:
                spin_index = int(current_spin_display.split(".")[0])
            except (ValueError, IndexError):
                spin_index = 1

            new_options = get_spin_type_options(self._payment_type_var.get())
            self._spin_type_combobox.config(values=new_options)

            if 1 <= spin_index <= len(new_options):
                self._spin_type_var.set(new_options[spin_index - 1])

        self._payment_type_var.trace_add("write", on_payment_type_changed)

        # Payment radio buttons
        payment_radio_frame = ttk.Frame(master=payment_type_frame)
        payment_radio_frame.pack(side="left", padx=(10, 0), fill="x", expand=True)

        payment_fc_radio = ttk.Radiobutton(
            master=payment_radio_frame,
            text="FC",
            variable=self._payment_type_var,
            value="FC",
        )
        payment_fc_radio.pack(side="left", padx=(0, 15))

        payment_mc_radio = ttk.Radiobutton(
            master=payment_radio_frame,
            text="MC",
            variable=self._payment_type_var,
            value="MC",
        )
        payment_mc_radio.pack(side="left")

    def _setup_spin_delay(self, parent: tk.Misc) -> None:
        spin_delay_frame = ttk.Frame(master=parent)
        spin_delay_frame.pack(fill="x", pady=(0, 15))
        ttk.Label(master=spin_delay_frame, text="Spin Delay (sec):", width=15, font=("Arial", 12)).pack(side="left")

        def validate_spin_delay(value: str) -> bool:
            if value == "":
                return True
            try:
                float(value)
                return True
            except ValueError:
                return False

        vcmd = (parent.register(validate_spin_delay), "%P")
        self._spin_delay_var = tk.StringVar(value=str(self._account.spin_delay_seconds if self._account else 0.0))
        self._spin_delay_entry = UIFactory.create_entry(
            parent=spin_delay_frame,
            textvariable=self._spin_delay_var,
            validate="key",
            validatecommand=vcmd,
        )
        self._spin_delay_entry.pack(side="left", padx=(10, 0), fill="x", expand=True)

    def _setup_buttons(self, parent: tk.Misc) -> None:
        buttons_frame, buttons = UIFactory.create_button_group(
            parent=parent,
            buttons=[
                {"text": "Cancel", "width": 10, "command": lambda: self._dialog.destroy() if self._dialog else None},
                {"text": "Save", "style": "Accent.TButton", "width": 10, "command": self._handle_save},
            ],
            spacing=5,
        )
        buttons_frame.pack(fill="x", pady=(0, 10))

    def _handle_save(self) -> None:
        spin_type_display = self._spin_type_var.get().strip()
        auto_close = self._close_on_jp_win_var.get()
        payment_type_val = 1 if self._payment_type_var.get() == "FC" else 2

        # Validate username
        if not (username := self._username_var.get().strip()):
            messagebox.showerror("Error", "Username is required!")
            return

        # Validate password
        if not (password := self._pwd_var.get().strip()):
            messagebox.showerror("Error", "Password is required!")
            return

        # Validate target jackpot
        if (target_val := self._target_sjp_var.get()) <= 0:
            messagebox.showerror("Error", "Target Jackpot must be greater than 0!")
            return

        # Validate target mini jackpot (optional)
        target_mjp_str = self._target_mjp_var.get().strip()
        target_mjp_val: Optional[int] = None
        if target_mjp_str:
            try:
                target_mjp_val = int(target_mjp_str)
                if target_mjp_val < 0:
                    messagebox.showerror("Error", "Target Mini Jackpot must be 0 or greater!")
                    return
            except ValueError:
                messagebox.showerror("Error", "Invalid Target Mini Jackpot value!")
                return

        # Validate spin delay
        try:
            spin_delay_val = float(self._spin_delay_var.get() or "0")
            if spin_delay_val < 0:
                messagebox.showerror("Error", "Spin Delay must be 0 or greater!")
                return
        except ValueError:
            messagebox.showerror("Error", "Invalid Spin Delay value!")
            return

        # Parse spin action
        try:
            spin_type_val = int(spin_type_display.split(".")[0])
        except (ValueError, IndexError):
            messagebox.showerror("Error", "Invalid spin action selected!")
            return

        # Handle different modes
        if self._is_edit_mode:
            assert self._account is not None
            if username != self._account.username and username in {a.username for a in self._existing_accounts}:
                messagebox.showerror("Error", f"Account with username '{username}' already exists!")
                return

            # Update existing account
            self._account.username = username
            self._account.password = password
            self._account.spin_type = spin_type_val
            self._account.payment_type = payment_type_val
            self._account.target_sjp = target_val
            self._account.target_mjp = target_mjp_val
            self._account.spin_delay_seconds = spin_delay_val
            self._account.close_on_jp_win = auto_close

        else:
            # Add mode
            if username in {a.username for a in self._existing_accounts}:
                messagebox.showerror("Error", f"Account with username '{username}' already exists!")
                return

            # Create new account
            self._account = Account(
                username=username,
                password=password,
                spin_type=spin_type_val,
                payment_type=payment_type_val,
                target_sjp=target_val,
                target_mjp=target_mjp_val,
                spin_delay_seconds=spin_delay_val,
                close_on_jp_win=auto_close,
            )

        # Call save callback
        if self._on_save:
            self._on_save(account=self._account, is_new=not self._is_edit_mode)

        action_text = "updated" if self._is_edit_mode else "created"
        messagebox.showinfo("Success", f"Account '{username}' {action_text} successfully!")

        if self._dialog:
            self._dialog.destroy()
