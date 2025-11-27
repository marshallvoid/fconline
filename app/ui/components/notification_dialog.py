import tkinter as tk
from tkinter import ttk
from typing import List

from app.schemas.configs import Notification
from app.ui.utils.ui_factory import UIFactory
from app.ui.utils.ui_helpers import UIHelpers
from app.utils.helpers import get_window_position


class NotificationDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        notifications: List[Notification],
        on_clear_all: callable,
    ) -> None:
        super().__init__(master=parent)

        self._notifications = notifications
        self._on_clear_all = on_clear_all

        self.title(string="Notifications")
        self.resizable(width=False, height=False)
        self.geometry(newGeometry="400x500")

        # Make menu floating (always on top)
        self.attributes("-topmost", True)
        self.transient(master=parent)  # type: ignore

        # Center the menu window
        self.update_idletasks()
        _, _, _, _, x, y = get_window_position(child_frame=self, parent_frame=parent)
        self.geometry(newGeometry=f"400x500+{x}+{y}")

        # Configure menu appearance
        self._configure_appearance()
        self._setup_ui()

    def _configure_appearance(self) -> None:
        self.configure(bg="#1f2937")
        self.option_add(pattern="*TFrame*background", value="#1f2937")
        self.option_add(pattern="*TLabel*background", value="#1f2937")
        self.option_add(pattern="*TButton*background", value="#374151")

    def _setup_ui(self) -> None:
        main_frame = ttk.Frame(master=self, padding=20)
        main_frame.pack(fill="both", expand=True)

        # Title
        title_label = ttk.Label(
            master=main_frame,
            font=("Arial", 16, "bold"),
            foreground="#fbbf24",
            text="🔔 Notifications",
        )
        title_label.pack(pady=(0, 20))

        # Content area
        content_frame = ttk.Frame(master=main_frame)
        content_frame.pack(fill="both", expand=True)

        if not self._notifications:
            self._setup_empty_state(parent=content_frame)
        else:
            self._setup_notifications_list(parent=content_frame)

        # Buttons - always at the bottom
        self._setup_buttons(parent=main_frame)

    def _setup_empty_state(self, parent: tk.Misc) -> None:
        no_notifications_label = ttk.Label(
            parent,
            font=("Arial", 14),
            foreground="#6b7280",
            text="📭 No notifications",
        )
        no_notifications_label.pack(expand=True)

    def _setup_notifications_list(self, parent: tk.Misc) -> None:
        # Create scrollable frame using helper
        canvas, scrollbar, scrollable_frame = UIHelpers.create_scrollable_frame(parent=parent)

        # Sort notifications: unseen first, then by timestamp descending
        sorted_notifications = sorted(
            self._notifications,
            key=lambda x: (x.is_seen, x.timestamp),
            reverse=True,
        )

        # Add each notification
        for notification in sorted_notifications:
            self._create_notification_item(parent=scrollable_frame, notification=notification)

        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _create_notification_item(self, parent: tk.Misc, notification: Notification) -> None:
        notification_frame = ttk.Frame(master=parent)
        notification_frame.pack(fill="x", pady=(0, 10))

        # Notification content
        notification_content_frame = ttk.Frame(master=notification_frame, padding=10)
        notification_content_frame.pack(fill="x")

        # Timestamp
        time_label = ttk.Label(
            master=notification_content_frame,
            font=("Arial", 10),
            foreground="#9ca3af",
            text=f"Time: {notification.timestamp}",
        )
        time_label.pack(anchor="w", pady=(0, 5))

        # Nickname
        nickname_label = ttk.Label(
            master=notification_content_frame,
            font=("Arial", 12, "bold"),
            foreground="#22c55e",
            text=f"User: {notification.nickname}",
        )
        nickname_label.pack(anchor="w")

        # Jackpot value
        jackpot_label = ttk.Label(
            master=notification_content_frame,
            font=("Arial", 14, "bold"),
            foreground="#f97316",
            text=f"Reward: {notification.jackpot_value}",
        )
        jackpot_label.pack(anchor="w", pady=(5, 0))

    def _setup_buttons(self, parent: tk.Misc) -> None:
        button_frame = ttk.Frame(master=parent)
        button_frame.pack(side="bottom", fill="x", pady=(20, 0))

        if self._notifications:
            # Clear all button
            clear_btn = UIFactory.create_button(
                parent=button_frame,
                text="Clear All",
                command=self._on_clear_all,
            )
            clear_btn.pack(side="left")

        # Close button (always visible)
        close_btn = UIFactory.create_button(
            parent=button_frame,
            text="Close",
            command=self.destroy,
        )
        close_btn.pack(side="right")
