import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict, Optional, Tuple

from .base_component import BaseComponent


class UserSettingsPanel(BaseComponent):
    """User settings panel component for form inputs."""

    def __init__(
        self,
        parent: tk.Widget,
        username_var: Optional[tk.StringVar] = None,
        password_var: Optional[tk.StringVar] = None,
        target_jackpot_var: Optional[tk.IntVar] = None,
        spin_action_var: Optional[tk.IntVar] = None,
        on_credentials_changed: Optional[Callable] = None,
        on_config_changed: Optional[Callable] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the user settings panel.

        Args:
            parent: Parent widget
            username_var: Username string variable
            password_var: Password string variable
            target_jackpot_var: Target jackpot int variable
            spin_action_var: Spin action int variable
            on_credentials_changed: Callback for credential changes
            on_config_changed: Callback for config changes
            **kwargs: Additional keyword arguments
        """
        self.username_var = username_var or tk.StringVar()
        self.password_var = password_var or tk.StringVar()
        self.target_jackpot_var = target_jackpot_var or tk.IntVar()
        self.spin_action_var = spin_action_var or tk.IntVar()
        self.on_credentials_changed = on_credentials_changed
        self.on_config_changed = on_config_changed

        self.username_entry: Optional[ttk.Entry] = None
        self.password_entry: Optional[ttk.Entry] = None
        self.target_jackpot_entry: Optional[ttk.Entry] = None
        self.radio_buttons: list = []

        super().__init__(parent, **kwargs)

    def _setup_ui(self) -> None:
        """Setup the user settings panel UI."""
        self.frame = ttk.Frame(self.parent)

        # Title
        title_label = ttk.Label(self.frame, text="User Settings", font=("Arial", 14, "bold"))
        title_label.pack(pady=(10, 20))

        # Username field
        username_frame = ttk.Frame(self.frame)
        username_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(username_frame, text="Username:", width=20, font=("Arial", 12)).pack(side="left")
        self.username_entry = ttk.Entry(username_frame, textvariable=self.username_var, width=30, font=("Arial", 12))
        self.username_entry.pack(side="left", padx=(10, 0), fill="x", expand=True)

        # Password field
        password_frame = ttk.Frame(self.frame)
        password_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(password_frame, text="Password:", width=20, font=("Arial", 12)).pack(side="left")
        self.password_entry = ttk.Entry(
            password_frame, textvariable=self.password_var, show="*", width=30, font=("Arial", 12)
        )
        self.password_entry.pack(side="left", padx=(10, 0), fill="x", expand=True)

        # Target Special Jackpot field
        target_frame = ttk.Frame(self.frame)
        target_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(target_frame, text="Target Special Jackpot:", width=20, font=("Arial", 12)).pack(side="left")
        self.target_jackpot_entry = ttk.Entry(
            target_frame, textvariable=self.target_jackpot_var, width=30, font=("Arial", 12)
        )
        self.target_jackpot_entry.pack(side="left", padx=(10, 0), fill="x", expand=True)

        # Spin Action Radio Buttons
        spin_action_frame = ttk.LabelFrame(self.frame, text="Spin Action", padding=10)
        spin_action_frame.pack(fill="x", pady=(0, 20))

        radio_container = ttk.Frame(spin_action_frame)
        radio_container.pack(fill="x")

        radio_options = [(1, "Free"), (2, "10FC"), (3, "190FC"), (4, "900FC")]

        for value, text in radio_options:
            radio_btn = ttk.Radiobutton(
                radio_container,
                text=text,
                variable=self.spin_action_var,
                value=value,
                command=self._on_spin_action_changed,
            )
            radio_btn.pack(side="left", padx=(0, 20))
            self.radio_buttons.append(radio_btn)

        # Add trace callbacks
        self._setup_trace_callbacks()

    def _setup_trace_callbacks(self) -> None:
        """Setup trace callbacks for variable changes."""
        self.username_var.trace_add("write", self._on_credentials_changed)
        self.password_var.trace_add("write", self._on_credentials_changed)
        self.target_jackpot_var.trace_add("write", self._on_config_changed)
        self.spin_action_var.trace_add("write", self._on_config_changed)

    def _on_credentials_changed(self, *args: str) -> None:
        """Handle credential changes."""
        if self.on_credentials_changed:
            self.on_credentials_changed()

    def _on_config_changed(self, *args: str) -> None:
        """Handle configuration changes."""
        if self.on_config_changed:
            self.on_config_changed()

    def _on_spin_action_changed(self) -> None:
        """Handle spin action radio button changes."""
        if self.on_config_changed:
            self.on_config_changed()

    def get_credentials(self) -> Dict[str, Any]:
        """Get current credentials."""
        return {
            "username": self.username_var.get(),
            "password": self.password_var.get(),
            "target_special_jackpot": self.target_jackpot_var.get(),
            "spin_action": self.spin_action_var.get(),
        }

    def set_credentials(self, credentials: Dict[str, Any]) -> None:
        """Set credentials from dictionary."""
        if "username" in credentials:
            self.username_var.set(credentials["username"])
        if "password" in credentials:
            self.password_var.set(credentials["password"])
        if "target_special_jackpot" in credentials:
            self.target_jackpot_var.set(credentials["target_special_jackpot"])
        if "spin_action" in credentials:
            self.spin_action_var.set(credentials["spin_action"])

    def toggle_inputs(self, enabled: bool) -> None:
        """Enable or disable input widgets."""
        state = "normal" if enabled else "disabled"
        self.username_entry.config(state=state)
        self.password_entry.config(state=state)
        self.target_jackpot_entry.config(state=state)
        for radio_btn in self.radio_buttons:
            radio_btn.config(state=state)

    def validate_inputs(self) -> Tuple[bool, str]:
        """Validate form inputs."""
        if not self.username_var.get().strip():
            return False, "Username cannot be empty!"

        if not self.password_var.get().strip():
            return False, "Password cannot be empty!"

        try:
            target_value = self.target_jackpot_var.get()
            if target_value <= 0:
                return False, "Target Jackpot must be a positive number!"
        except ValueError:
            return False, "Target Jackpot must be a positive number!"

        return True, ""
