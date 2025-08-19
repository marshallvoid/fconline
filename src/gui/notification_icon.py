import tkinter as tk
from tkinter import ttk
from typing import List, Optional, Tuple

from src.utils.user_config import UserConfigManager


class NotificationIcon:
    def __init__(self, parent: tk.Misc) -> None:
        self._parent: tk.Misc = parent

        # List of (nickname, jackpot_value, timestamp, is_seen) tuples
        self._notifications: List[Tuple[str, str, str, bool]] = []
        self._menu_window: Optional[tk.Toplevel] = None

        try:
            config = UserConfigManager.load_configs()
            self._notifications = config.notifications

        except Exception:
            self._notifications = []

        self._build()

    @property
    def frame(self) -> ttk.Frame:
        return self._frame

    def add_notification(self, nickname: str, jackpot_value: str, timestamp: str) -> None:
        self._notifications.append((nickname, jackpot_value, timestamp, False))
        self._update_icon()
        self._save_notifications_to_config()

    def clear_notifications(self) -> None:
        self._notifications.clear()
        self._update_icon()
        self._save_notifications_to_config()

    def _save_notifications_to_config(self) -> None:
        try:
            config = UserConfigManager.load_configs()
            config.notifications = self._notifications
            UserConfigManager.save_configs(config)

        except Exception:
            pass

    def _build(self) -> None:
        self._frame: ttk.Frame = ttk.Frame(self._parent)

        # Notification icon button
        self._icon_label: ttk.Label = ttk.Label(
            self._frame,
            text="🔔",
            font=("Arial", 16),
            foreground="#6b7280",
            cursor="hand2",
        )
        self._icon_label.pack(side="left")
        self._icon_label.bind("<Button-1>", lambda e: self._on_icon_click())

        # Notification count badge
        self._count_label: ttk.Label = ttk.Label(
            self._frame,
            text="0",
            foreground="#ffffff",
            background="#ef4444",
            font=("Arial", 10, "bold"),
            padding=(4, 2),
        )

        # Initially hidden
        self._count_label.pack_forget()

        # Update icon to reflect loaded notifications
        self._update_icon()

    def _on_icon_click(self) -> None:
        # Close existing menu if any
        if self._menu_window:
            try:
                self._menu_window.destroy()

            except tk.TclError:
                pass

        self._mark_all_as_seen()
        if self._count_label.winfo_exists():
            self._count_label.pack_forget()

        # Create menu window
        self._menu_window = tk.Toplevel(self._parent)
        self._menu_window.title("Notifications")
        self._menu_window.resizable(False, False)

        # Make menu floating (always on top)
        self._menu_window.attributes("-topmost", True)
        self._menu_window.transient(self._parent)  # type: ignore

        # Position menu near the notification icon
        icon_x: int = self._frame.winfo_rootx() + self._frame.winfo_width()
        icon_y: int = self._frame.winfo_rooty()

        # Get screen dimensions to prevent window from going off-screen
        screen_width: int = self._menu_window.winfo_screenwidth()
        screen_height: int = self._menu_window.winfo_screenheight()

        # Adjust position if window would go off-screen
        if icon_x + 400 > screen_width:
            icon_x = max(0, screen_width - 400)
        if icon_y + 500 > screen_height:
            icon_y = max(0, screen_height - 500)

        # Ensure the window appears near the notification icon
        self._menu_window.geometry(f"400x500+{icon_x}+{icon_y}")

        # Configure menu appearance
        self._menu_window.configure(bg="#1f2937")
        self._menu_window.option_add("*TFrame*background", "#1f2937")
        self._menu_window.option_add("*TLabel*background", "#1f2937")
        self._menu_window.option_add("*TButton*background", "#374151")

        # Menu content
        main_frame: ttk.Frame = ttk.Frame(self._menu_window, padding=20)
        main_frame.pack(fill="both", expand=True)

        # Title
        title_label: ttk.Label = ttk.Label(
            main_frame,
            text="🔔 Notifications",
            font=("Arial", 16, "bold"),
            foreground="#fbbf24",
        )
        title_label.pack(pady=(0, 20))

        # Content area that will expand to fill available space
        content_frame: ttk.Frame = ttk.Frame(main_frame)
        content_frame.pack(fill="both", expand=True)

        if not self._notifications:
            # Show "No notifications" message centered in content area
            no_notifications_label: ttk.Label = ttk.Label(
                content_frame,
                text="📭 No notifications",
                font=("Arial", 14),
                foreground="#6b7280",
            )
            no_notifications_label.pack(expand=True)  # This centers the text both horizontally and vertically
        else:
            # Notifications list
            # Create a container frame for the scrollable area
            scroll_container: ttk.Frame = ttk.Frame(content_frame)
            scroll_container.pack(fill="both", expand=True)

            # Create scrollable frame for notifications
            canvas: tk.Canvas = tk.Canvas(scroll_container, bg="#1f2937", highlightthickness=0)
            scrollbar: ttk.Scrollbar = ttk.Scrollbar(scroll_container, orient="vertical", command=canvas.yview)
            scrollable_frame: ttk.Frame = ttk.Frame(canvas, padding=10)

            scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

            # Create the window in canvas
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            # Ensure scrollable frame expands to fill canvas width
            def _update_scroll_region(event: tk.Event) -> None:
                canvas.configure(scrollregion=canvas.bbox("all"))
                # Update the width of the scrollable frame to match canvas
                canvas.itemconfig(canvas.find_all()[0], width=event.width)

            canvas.bind("<Configure>", _update_scroll_region)

            # Sort notifications: unseen first, then by timestamp in descending order (newest first)
            sorted_notifications = sorted(self._notifications, key=lambda x: (x[3], x[2]), reverse=True)

            # Add each notification
            for nickname, jackpot_value, timestamp, _ in sorted_notifications:
                notification_frame: ttk.Frame = ttk.Frame(scrollable_frame)
                notification_frame.pack(fill="x", pady=(0, 10))

                # Notification content - removed the LabelFrame to eliminate blue-gray color
                notification_content_frame: ttk.Frame = ttk.Frame(notification_frame, padding=10)
                notification_content_frame.pack(fill="x")

                # Timestamp
                time_label: ttk.Label = ttk.Label(
                    notification_content_frame,
                    text=f"Time: {timestamp}",
                    font=("Arial", 10),
                    foreground="#9ca3af",
                )
                time_label.pack(anchor="w", pady=(0, 5))

                winner_label: ttk.Label = ttk.Label(
                    notification_content_frame,
                    text=f"User: {nickname}",
                    font=("Arial", 12, "bold"),
                    foreground="#22c55e",
                )
                winner_label.pack(anchor="w")

                jackpot_label: ttk.Label = ttk.Label(
                    notification_content_frame,
                    text=f"Reward: {jackpot_value}",
                    font=("Arial", 14, "bold"),
                    foreground="#f97316",
                )
                jackpot_label.pack(anchor="w", pady=(5, 0))

            # Pack canvas and scrollbar to fill the entire container
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

        # Buttons - always at the bottom
        button_frame: ttk.Frame = ttk.Frame(main_frame)
        button_frame.pack(side="bottom", fill="x", pady=(20, 0))

        if self._notifications:
            # Clear all button
            clear_btn: ttk.Button = ttk.Button(button_frame, text="Clear All", command=self._clear_all_notifications)
            clear_btn.pack(side="left")

        # Close button (always visible)
        close_btn: ttk.Button = ttk.Button(button_frame, text="Close", command=self._menu_window.destroy)
        close_btn.pack(side="right")

    def _mark_all_as_seen(self) -> None:
        for i in range(len(self._notifications)):
            nickname, jackpot_value, timestamp, _ = self._notifications[i]
            self._notifications[i] = (nickname, jackpot_value, timestamp, True)
        self._save_notifications_to_config()

    def _update_icon(self) -> None:
        unread_count: int = sum(1 for _, _, _, is_seen in self._notifications if not is_seen)

        if unread_count == 0:
            self._icon_label.config(text="🔔", foreground="#6b7280", font=("Arial", 16))
            self._count_label.pack_forget()
            return

        # Show notification count badge
        self._icon_label.config(text="🔔", foreground="#f97316", font=("Arial", 16, "bold"))
        self._count_label.config(
            text=str(unread_count),
            foreground="#ffffff",
            background="#ef4444",
            font=("Arial", 10, "bold"),
        )
        self._count_label.pack()

    def _clear_all_notifications(self) -> None:
        self._notifications.clear()
        self._update_icon()
        self._save_notifications_to_config()

        if self._menu_window:
            self._menu_window.destroy()
