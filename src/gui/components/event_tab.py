import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, List, Tuple

from loguru import logger


class EventTab:
    def __init__(
        self,
        parent: tk.Misc,
        title: str,
        username_var: tk.StringVar,
        password_var: tk.StringVar,
        spin_action_var: tk.IntVar,
        target_special_jackpot_var: tk.IntVar,
        spin_action_labels: Dict[int, Tuple[str, str]],
        on_spin_action_changed: Callable[[], None],
    ) -> None:
        self._frame = ttk.Frame(parent)
        self._title = title
        self._username_var = username_var
        self._password_var = password_var
        self._spin_action_var = spin_action_var
        self._target_special_jackpot_var = target_special_jackpot_var
        self._spin_action_labels = spin_action_labels
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

        for radio_btn in self._radio_buttons:
            radio_btn.config(state=state)

    def update_user_info_text(self, text: str, foreground: str = "#4caf50") -> None:
        self._user_info_label.config(text=text, foreground=foreground)

    def _build(self) -> None:
        logger.info(f"🔧 Initializing EventTab for event: {self._title}")

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

        # User info display
        user_info_frame = ttk.LabelFrame(container, text="User Information", padding=10)
        user_info_frame.pack(fill="x", pady=(0, 10))

        user_info_container = ttk.Frame(user_info_frame)
        user_info_container.pack(fill="x")

        info_text = (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "NOT LOGGED IN\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "   Please enter your credentials and start the tool"
        )
        self._user_info_label = ttk.Label(
            user_info_container,
            text=info_text,
            foreground="#757575",
            font=("Consolas", 12),
        )
        self._user_info_label.pack(anchor="w")

        # Spin Action
        spin_action_frame = ttk.LabelFrame(container, text="Spin Action", padding=10)
        spin_action_frame.pack(fill="x", pady=(0, 20))

        radio_container = ttk.Frame(spin_action_frame)
        radio_container.pack(fill="x")

        radio_label_indexes = list(self._spin_action_labels.keys())
        radio_label_texts = [text for _, text in self._spin_action_labels.values()]

        self._radio_buttons: List[ttk.Radiobutton] = []
        for index, text in zip(radio_label_indexes, radio_label_texts, strict=False):
            radio_btn = ttk.Radiobutton(
                radio_container,
                text=text,
                variable=self._spin_action_var,
                value=index,
                command=self._on_spin_action_changed,
            )
            radio_btn.pack(side="left", padx=(0, 20))
            self._radio_buttons.append(radio_btn)

        logger.success(f"✅ {self._title} EventTab initialized successfully")
