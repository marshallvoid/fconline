import contextlib
import tkinter as tk
from tkinter import ttk
from typing import List, Optional

from app.core.managers.config import config_mgr
from app.schemas.configs import Config, Notification
from app.ui.components.notification_dialog import NotificationDialog


class NotificationIcon:
    def __init__(self, parent: tk.Misc, configs: Optional[Config] = None) -> None:
        self._parent: tk.Misc = parent
        self._frame: ttk.Frame = ttk.Frame(master=parent)
        self._dialog: Optional[NotificationDialog] = None

        self._configs: Config = configs if configs is not None else config_mgr.load_configs()
        self._notifications: List[Notification] = self._configs.notifications

        self._setup_ui()

    @property
    def frame(self) -> ttk.Frame:
        return self._frame

    # ==================== Public Methods ====================
    def add_notification(self, nickname: str, jackpot_value: str) -> None:
        self._notifications.append(Notification(nickname=nickname, jackpot_value=jackpot_value))
        self._update_icon()
        self._save_notifications_to_config()

    # ==================== Private Methods ====================
    def _setup_ui(self) -> None:
        # Notification icon button
        self._icon_label = ttk.Label(
            master=self._frame,
            cursor="hand2",
            font=("Arial", 16),
            foreground="#fbbf24",
            text="🔔",
        )
        self._icon_label.pack(side="left")
        self._icon_label.bind(sequence="<Button-1>", func=lambda _: self._on_icon_click())

        # Notification count badge
        self._count_label = ttk.Label(
            master=self._frame,
            background="#ef4444",
            font=("Arial", 10, "bold"),
            foreground="#ffffff",
            padding=(4, 2),
            text="0",
        )

        # Initially hidden
        self._count_label.pack_forget()

        # Update icon to reflect loaded notifications
        self._update_icon()

    def _on_icon_click(self) -> None:
        # Close existing dialog if any
        if self._dialog is not None:
            with contextlib.suppress(tk.TclError):
                self._dialog.destroy()

        # Mark all notifications as seen
        for notification in self._notifications:
            notification.is_seen = True

        self._save_notifications_to_config()

        # Remove count badge as all are now seen
        if self._count_label.winfo_exists():
            self._count_label.pack_forget()

        # Create and show notification dialog
        self._dialog = NotificationDialog(
            parent=self._parent,
            notifications=self._notifications,
            on_clear_all=self._clear_all_notifications,
        )

    def _update_icon(self) -> None:
        unread_count: int = sum(1 for notification in self._notifications if not notification.is_seen)

        if unread_count == 0:
            self._icon_label.config(font=("Arial", 16), foreground="#6b7280")
            self._count_label.pack_forget()
            return

        # Show notification count badge
        self._icon_label.config(font=("Arial", 16, "bold"), foreground="#f97316")
        self._count_label.config(
            text=str(unread_count),
            background="#ef4444",
            font=("Arial", 10, "bold"),
            foreground="#ffffff",
        )
        self._count_label.pack()

    def _clear_all_notifications(self) -> None:
        self._notifications.clear()
        self._update_icon()
        self._save_notifications_to_config()

        if self._dialog:
            self._dialog.destroy()

    def _save_notifications_to_config(self) -> None:
        self._configs.notifications = self._notifications
        config_mgr.save_configs(configs=self._configs)
