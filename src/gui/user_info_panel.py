import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING, Any, Optional

from .base_component import BaseComponent

if TYPE_CHECKING:
    from src.models import UserInfo


class UserInfoPanel(BaseComponent):
    """User info panel component for displaying user information."""

    def __init__(self, parent: tk.Widget, **kwargs: Any) -> None:
        """
        Initialize the user info panel.

        Args:
            parent: Parent widget
            **kwargs: Additional keyword arguments
        """
        self.user_info_label: Optional[ttk.Label] = None

        super().__init__(parent, **kwargs)

    def _setup_ui(self) -> None:
        """Setup the user info panel UI."""
        self.frame = ttk.LabelFrame(self.parent, text="User Information", padding=10)

        # Create user info container
        user_info_container = ttk.Frame(self.frame)
        user_info_container.pack(fill="x")

        # Main user info label with better font
        not_logged_text = (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🔒 NOT LOGGED IN\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "   Please enter your credentials and start the tool"
        )
        self.user_info_label = ttk.Label(
            user_info_container,
            text=not_logged_text,
            foreground="#757575",
            font=("Consolas", 12),
        )
        self.user_info_label.pack(anchor="w")

    def update_user_info(self, user_info: Optional["UserInfo"], special_jackpot: int = 0) -> None:
        """
        Update user info display.

        Args:
            user_info: User information object or None
            special_jackpot: Current special jackpot value
        """
        if not user_info or not user_info.payload.user:
            not_logged_text = (
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "🔒 NOT LOGGED IN\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "   Please enter your credentials and start the tool"
            )
            self.user_info_label.config(text=not_logged_text, foreground="#757575")
            return

        user = user_info.payload.user

        # Create formatted info text with better styling including special jackpot
        info_text = (
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 ACCOUNT INFORMATION\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"User ID    : {user.uid}\n"
            f"Username   : {user.nickname}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 CURRENCY & RESOURCES\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Free Spins : {user.free_spin:,}\n"
            f"FC Points  : {user.fc:,}\n"
            f"MC Points  : {user.mc:,}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎰 SPECIAL JACKPOT: {special_jackpot:,} 💰\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        self.user_info_label.config(text=info_text, foreground="#4caf50")
