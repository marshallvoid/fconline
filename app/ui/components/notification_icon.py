import contextlib
import tkinter as tk
from tkinter import ttk
from typing import List, Optional

from app.core.managers.config import config_mgr
from app.schemas.configs import Config, Notification
from app.utils import helpers as hlp


class NotificationIcon:
    def __init__(self, parent: tk.Misc, configs: Optional[Config] = None) -> None:
        self._parent: tk.Misc = parent

        self._frame: ttk.Frame = ttk.Frame(master=parent)
        self._menu_window: Optional[tk.Toplevel] = None

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
        # Close existing menu if any
        if (win := self._menu_window) is not None:
            with contextlib.suppress(tk.TclError):
                win.destroy()

        # Mark all notifications as seen
        for notification in self._notifications:
            notification.is_seen = True

        self._save_notifications_to_config()

        # Remove count badge as all are now seen
        if self._count_label.winfo_exists():
            self._count_label.pack_forget()

        # Create menu window
        self._menu_window = tk.Toplevel(master=self._parent)
        self._menu_window.title(string="Notifications")
        self._menu_window.resizable(width=False, height=False)
        self._menu_window.geometry(newGeometry="400x500")

        # Make menu floating (always on top)
        self._menu_window.attributes("-topmost", True)
        self._menu_window.transient(master=self._parent)  # type: ignore

        # Center the menu window
        self._menu_window.update_idletasks()
        _, _, _, _, x, y = hlp.get_window_position(child_frame=self._menu_window, parent_frame=self._parent)
        self._menu_window.geometry(newGeometry=f"400x500+{x}+{y}")

        # Configure menu appearance
        self._menu_window.configure(bg="#1f2937")
        self._menu_window.option_add(pattern="*TFrame*background", value="#1f2937")
        self._menu_window.option_add(pattern="*TLabel*background", value="#1f2937")
        self._menu_window.option_add(pattern="*TButton*background", value="#374151")

        # Menu content
        main_frame = ttk.Frame(master=self._menu_window, padding=20)
        main_frame.pack(fill="both", expand=True)

        # Title
        title_label = ttk.Label(
            master=main_frame,
            font=("Arial", 16, "bold"),
            foreground="#fbbf24",
            text="🔔 Notifications",
        )
        title_label.pack(pady=(0, 20))

        # Content area that will expand to fill available space
        content_frame = ttk.Frame(master=main_frame)
        content_frame.pack(fill="both", expand=True)

        if not self._notifications:
            # Show "No notifications" message centered in content area
            no_notifications_label = ttk.Label(
                content_frame,
                font=("Arial", 14),
                foreground="#6b7280",
                text="📭 No notifications",
            )
            no_notifications_label.pack(expand=True)  # This centers the text both horizontally and vertically
        else:
            # Notifications list
            # Create a container frame for the scrollable area
            scroll_container = ttk.Frame(master=content_frame)
            scroll_container.pack(fill="both", expand=True)

            # Create scrollable frame for notifications
            canvas = tk.Canvas(master=scroll_container, bg="#1f2937", highlightthickness=0)
            scrollbar = ttk.Scrollbar(master=scroll_container, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(master=canvas, padding=10)

            scrollable_frame.bind(
                sequence="<Configure>",
                func=lambda _: canvas.configure(scrollregion=canvas.bbox("all")),
            )

            # Create the window in canvas
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            # Ensure scrollable frame expands to fill canvas width
            def _update_scroll_region(event: tk.Event) -> None:
                canvas.configure(scrollregion=canvas.bbox("all"))
                # Update the width of the scrollable frame to match canvas
                canvas.itemconfig(tagOrId=canvas.find_all()[0], width=event.width)

            canvas.bind(sequence="<Configure>", func=_update_scroll_region)

            # Sort notifications: unseen first, then by timestamp in descending order (newest first)
            sorted_notifications = sorted(self._notifications, key=lambda x: (x.is_seen, x.timestamp), reverse=True)

            # Add each notification
            for notification in sorted_notifications:
                notification_frame = ttk.Frame(master=scrollable_frame)
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

                nickname_label = ttk.Label(
                    master=notification_content_frame,
                    font=("Arial", 12, "bold"),
                    foreground="#22c55e",
                    text=f"User: {notification.nickname}",
                )
                nickname_label.pack(anchor="w")

                jackpot_label = ttk.Label(
                    master=notification_content_frame,
                    font=("Arial", 14, "bold"),
                    foreground="#f97316",
                    text=f"Reward: {notification.jackpot_value}",
                )
                jackpot_label.pack(anchor="w", pady=(5, 0))

            # Pack canvas and scrollbar to fill the entire container
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

        # Buttons - always at the bottom
        button_frame = ttk.Frame(master=main_frame)
        button_frame.pack(side="bottom", fill="x", pady=(20, 0))

        if self._notifications:
            # Clear all button
            clear_btn = ttk.Button(master=button_frame, text="Clear All", command=self._clear_all_notifications)
            clear_btn.pack(side="left")

        # Close button (always visible)
        close_btn = ttk.Button(master=button_frame, text="Close", command=self._menu_window.destroy)
        close_btn.pack(side="right")

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

        if self._menu_window:
            self._menu_window.destroy()

    def _save_notifications_to_config(self) -> None:
        self._configs.notifications = self._notifications
        config_mgr.save_configs(configs=self._configs)
