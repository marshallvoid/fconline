import tkinter as tk
from tkinter import ttk
from typing import Callable, List


class EventTab:
    def __init__(
        self,
        parent: tk.Misc,
        title: str,
        username_var: tk.StringVar,
        password_var: tk.StringVar,
        spin_action_var: tk.IntVar,
        target_special_jackpot_var: tk.IntVar,
        target_mini_jackpot_var: tk.IntVar,
        close_when_jackpot_won_var: tk.BooleanVar,
        close_when_mini_jackpot_won_var: tk.BooleanVar,
        spin_actions: List[str],
        on_spin_action_changed: Callable[[], None],
    ) -> None:
        self._frame = ttk.Frame(parent)
        self._title = title
        self._username_var = username_var
        self._password_var = password_var
        self._spin_action_var = spin_action_var
        self._target_special_jackpot_var = target_special_jackpot_var
        self._target_mini_jackpot_var = target_mini_jackpot_var
        self._close_when_jackpot_won_var = close_when_jackpot_won_var
        self._close_when_mini_jackpot_won_var = close_when_mini_jackpot_won_var
        self._spin_actions = spin_actions
        self._on_spin_action_changed = on_spin_action_changed

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
        self._target_mini_jackpot_entry.config(state=state)

        for radio_btn in self._radio_buttons:
            radio_btn.config(state=state)

        # Handle checkbox states
        if enabled:
            # Re-apply the mini jackpot logic
            self._on_mini_jackpot_changed()
        else:
            # Disable both checkboxes when UI is disabled
            self._close_when_jackpot_won_checkbox.config(state="disabled")
            self._close_when_mini_jackpot_won_checkbox.config(state="disabled")

    def _on_mini_jackpot_changed(self) -> None:
        if self._close_when_mini_jackpot_won_var.get():
            self._close_when_jackpot_won_var.set(True)
            self._close_when_jackpot_won_checkbox.config(state="disabled")
            # Enable target mini jackpot input
            self._target_mini_jackpot_entry.config(state="normal")
        else:
            self._close_when_jackpot_won_checkbox.config(state="normal")
            # Disable and clear target mini jackpot input
            self._target_mini_jackpot_entry.config(state="disabled")
            self._target_mini_jackpot_var.set(0)

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

        # Target Mini Jackpot
        target_mini_frame = ttk.Frame(container)
        target_mini_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(target_mini_frame, text="Target Mini Jackpot:", width=20, font=("Arial", 12)).pack(side="left")
        self._target_mini_jackpot_entry = ttk.Entry(
            target_mini_frame,
            textvariable=self._target_mini_jackpot_var,
            width=30,
            font=("Arial", 12),
        )
        self._target_mini_jackpot_entry.pack(side="left", padx=(10, 0), fill="x", expand=True)

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

        # Close when mini jackpot won checkbox
        close_mini_frame = ttk.Frame(close_options_frame)
        close_mini_frame.pack(fill="x", pady=(0, 5))
        self._close_when_mini_jackpot_won_checkbox = ttk.Checkbutton(
            close_mini_frame,
            text="Close when won Mini Prize",
            variable=self._close_when_mini_jackpot_won_var,
            command=self._on_mini_jackpot_changed,
        )
        self._close_when_mini_jackpot_won_checkbox.pack(anchor="w")

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

        # Initialize the checkbox states based on current values
        self._on_mini_jackpot_changed()
