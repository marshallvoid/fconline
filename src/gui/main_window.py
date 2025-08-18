import asyncio
import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING, Any, Optional

import darkdetect
import sv_ttk

from src.core.main_tool import MainTool
from src.gui.components.activity_log_tab import ActivityLogTab
from src.gui.components.event_tab import EventTab
from src.gui.components.notification_icon import NotificationIcon
from src.schemas.enums.message_tag import MessageTag
from src.schemas.user_config import UserConfig
from src.utils import files, sounds
from src.utils.contants import EVENT_CONFIGS_MAP
from src.utils.platforms import PlatformManager
from src.utils.user_config import UserConfigManager

if TYPE_CHECKING:
    from src.schemas.user_response import UserReponse


class MainWindow:
    def __init__(self) -> None:
         self._root = tk.Tk()
         self._root.title(string="FC Online Automation Tool")
         self._root.resizable(width=True, height=True)
         self._root.minsize(width=700, height=650)

         try:
            png_path = files.resource_path("assets/icon.png")
            icon = tk.PhotoImage(file=png_path)
            self._root.iconphoto(True, icon)
         except Exception:
            pass

         if PlatformManager.is_windows():
            try:
                  ico_path = files.resource_path("assets/icon.ico")
                  self._root.iconbitmap(ico_path)
            except Exception:
                  pass

         # Position window at top-right corner of screen
         self._screen_width = self._root.winfo_screenwidth()
         self._root.geometry(f"700x700+{self._screen_width - 700}+0")  # x=screen_width-700, y=0 (top-right corner)

         saved_configs = UserConfigManager.load_configs()

         self._username_var = tk.StringVar(value=saved_configs.username)
         self._password_var = tk.StringVar(value=saved_configs.password)
         self._spin_action_var = tk.IntVar(value=saved_configs.spin_action)
         self._target_special_jackpot_var = tk.IntVar(value=saved_configs.target_special_jackpot)

         self._is_running = False
         self._selected_event = saved_configs.event or "Bi Lắc"

         self._tool_instance = MainTool(
               screen_width=self._screen_width,
               event_config=EVENT_CONFIGS_MAP[self._selected_event],
               username=self._username_var.get(),
               password=self._password_var.get(),
               spin_action=self._spin_action_var.get(),
               target_special_jackpot=self._target_special_jackpot_var.get(),
         )

         self._setup_ui()

    def run(self) -> None:
        def on_close() -> None:
            if self._is_running:
                self._tool_instance.is_running = False

            self._root.destroy()

        self._root.protocol("WM_DELETE_WINDOW", on_close)

        sv_ttk.set_theme(darkdetect.theme() or "dark")

        try:
            style = ttk.Style(self._root)
            layout = style.layout("TNotebook.Tab")

            def _strip_focus(elements: Any) -> Any:
                if not isinstance(elements, (list, tuple)):
                    return elements

                cleaned = []
                for elem in elements:
                    if isinstance(elem, tuple) and elem:
                        name = elem[0]
                        opts = elem[1] if len(elem) > 1 else {}

                        if isinstance(name, str) and name.endswith(".focus"):
                            continue

                        if isinstance(opts, dict) and "children" in opts:
                            opts = dict(opts)
                            opts["children"] = _strip_focus(opts.get("children", []))
                            cleaned.append((name, opts))
                            continue

                        cleaned.append(elem)
                        continue

                    cleaned.append(elem)

                return cleaned

            cleaned_layout = _strip_focus(layout)
            style.layout("TNotebook.Tab", cleaned_layout)

        except Exception:
            pass

        self._root.mainloop()

    def _setup_ui(self) -> None:
        self._setup_notification_icon()
        self._setup_control_frame()
        self._setup_event_selection()
        self._setup_main_content()

        self._setup_trace_callbacks()

    def _setup_notification_icon(self) -> None:
        notification_frame = ttk.Frame(self._root)
        notification_frame.pack(side="top", fill="x", padx=10, pady=(10, 0))

        # Spacer to push icon to right
        spacer = ttk.Frame(notification_frame)
        spacer.pack(side="left", fill="x", expand=True)

        # Notification icon
        self._notification_icon = NotificationIcon(notification_frame)
        self._notification_icon.frame.pack(side="right")

    def _setup_control_frame(self) -> None:
        control_frame = ttk.Frame(self._root)
        control_frame.pack(side="bottom", fill="x", padx=10, pady=(5, 10))

        self._start_btn = ttk.Button(
            control_frame,
            text="Start",
            command=self._handle_click_start,
            style="Accent.TButton",
        )
        self._start_btn.pack(side="left", padx=(0, 5))

        self._stop_btn = ttk.Button(
            control_frame,
            text="Stop",
            command=self._handle_click_stop,
            state="disabled",
        )
        self._stop_btn.pack(side="left", padx=5)

        self._status_label = ttk.Label(control_frame, text="Status: Ready")
        self._status_label.pack(side="right")

    def _setup_event_selection(self) -> None:
        event_selection_frame = ttk.LabelFrame(self._root, padding=10)
        event_selection_frame.pack(fill="x", padx=10, pady=(10, 5))

        self._event_var = tk.StringVar(value=self._selected_event)

        # Create dropdown menu for event selection
        event_label = ttk.Label(event_selection_frame, text="Select Event:")
        event_label.pack(anchor="w", pady=(0, 5))

        self._event_combobox = ttk.Combobox(
            event_selection_frame,
            textvariable=self._event_var,
            values=list(EVENT_CONFIGS_MAP.keys()),
            state="readonly",
            width=30,
        )
        self._event_combobox.pack(anchor="w", fill="x")
        self._event_combobox.bind("<<ComboboxSelected>>", self._on_event_changed)

    def _setup_main_content(self) -> None:
        main_container = ttk.Frame(self._root)
        main_container.pack(fill="both", expand=True, padx=10, pady=5)

        # Create notebook for user settings and activity log
        self._notebook = ttk.Notebook(main_container, takefocus=False)
        self._notebook.pack(fill="both", expand=True)

        # Create event tab for current selected event
        self._event_tab = EventTab(
            parent=self._notebook,
            title=self._selected_event,
            username_var=self._username_var,
            password_var=self._password_var,
            spin_action_var=self._spin_action_var,
            target_special_jackpot_var=self._target_special_jackpot_var,
            spin_actions=EVENT_CONFIGS_MAP[self._selected_event].spin_actions,
            on_spin_action_changed=lambda: setattr(self._tool_instance, "spin_action", self._spin_action_var.get()),
        )
        self._notebook.add(self._event_tab.frame, text="User Settings")

        self._activity_log_tab = ActivityLogTab(parent=self._notebook)
        self._notebook.add(self._activity_log_tab.frame, text="Activity Log")

        self._focus_after_id: Optional[str] = None

        def _schedule_focus_current_tab() -> None:
            def _focus_current_tab() -> None:
                try:
                    current = self._notebook.nametowidget(self._notebook.select())
                    if current and isinstance(current, (tk.Frame, ttk.Frame)):
                        current.focus_set()
                except Exception:
                    pass

            if self._focus_after_id:
                try:
                    self._root.after_cancel(self._focus_after_id)
                except Exception:
                    pass
                finally:
                    self._focus_after_id = None

            self._focus_after_id = self._root.after(10, _focus_current_tab)

        def _on_tab_changed(_: object) -> None:
            try:
                current = self._notebook.nametowidget(self._notebook.select())
                if current and isinstance(current, (tk.Frame, ttk.Frame)):
                    current.focus_set()
            except Exception:
                pass

            _schedule_focus_current_tab()

        self._notebook.bind("<<NotebookTabChanged>>", _on_tab_changed)
        self._notebook.bind("<ButtonRelease-1>", lambda e: _schedule_focus_current_tab())
        self._root.after_idle(_schedule_focus_current_tab)

    def _save_configs(self) -> None:
        UserConfigManager.save_configs(
            config=UserConfig(
                event=self._selected_event,
                username=self._username_var.get(),
                password=self._password_var.get(),
                spin_action=self._spin_action_var.get(),
                target_special_jackpot=self._target_special_jackpot_var.get(),
            )
        )

    def _on_event_changed(self, _event: Optional[tk.Event] = None) -> None:
        # Get the selected event from combobox
        self._selected_event = self._event_var.get()

        # Update the event tab with new event configuration
        # Instead of recreating the tab, update the existing one
        self._event_tab = EventTab(
            parent=self._notebook,
            title=self._selected_event,
            username_var=self._username_var,
            password_var=self._password_var,
            spin_action_var=self._spin_action_var,
            target_special_jackpot_var=self._target_special_jackpot_var,
            spin_actions=EVENT_CONFIGS_MAP[self._selected_event].spin_actions,
            on_spin_action_changed=lambda: setattr(self._tool_instance, "spin_action", self._spin_action_var.get()),
        )

        # Replace the content of the first tab without changing tab selection
        self._notebook.forget(0)
        self._notebook.insert(0, self._event_tab.frame, text="User Settings")

        # Force the notebook to stay on the current tab
        self._notebook.select(0)

        # Update tool instance with new event config
        if not self._is_running:
            self._tool_instance.update_configs(event_config=EVENT_CONFIGS_MAP[self._selected_event])

        self._save_configs()

    def _setup_trace_callbacks(self) -> None:
        def _on_credentials_changed() -> None:
            if not self._is_running:
                self._tool_instance.update_credentials(self._username_var.get(), self._password_var.get())
                self._save_configs()

        self._username_var.trace_add("write", lambda *args: _on_credentials_changed())
        self._password_var.trace_add("write", lambda *args: _on_credentials_changed())
        self._spin_action_var.trace_add("write", lambda *args: self._save_configs())
        self._target_special_jackpot_var.trace_add("write", lambda *args: self._save_configs())

    def _update_user_panel(self, user_info: Optional["UserReponse"]) -> None:
        info_text = (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "NOT LOGGED IN\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "   Please enter your credentials and start the tool"
        )

        if user_info and user_info.payload.user:
            info_text = (
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"ACCOUNT INFORMATION\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"User ID    : {user_info.payload.user.uid}\n"
                f"Username   : {user_info.payload.user.nickname}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"CURRENCY & RESOURCES\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Free Spins : {user_info.payload.user.free_spin:,}\n"
                f"FC Points  : {user_info.payload.user.fc:,}\n"
                f"MC Points  : {user_info.payload.user.mc:,}\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )

        self._event_tab.update_user_info_text(info_text, foreground="#22c55e")

    def _update_running_status(self, is_running: bool, is_error: bool = False) -> None:
        self._is_running = is_running
        self._start_btn.config(state="disabled" if is_running else "normal")
        self._stop_btn.config(state="normal" if is_running else "disabled")

        status_text = "Status: Starting..." if is_running else "Status: Stopping..."
        if is_error:
            status_text = "Status: Running..." if is_running else "Status: Ready"

        self._status_label.config(text=status_text)

        # Disable/enable event selection combobox
        self._event_combobox.config(state="disabled" if is_running else "readonly")

        self._event_tab.set_enabled(enabled=not is_running)

    def _handle_click_start(self) -> None:
        if self._is_running:
            messagebox.showerror("❌ Error", "Tool is already running!")
            return

        if not self._username_var.get().strip():
            messagebox.showerror("❌ Error", "Username is required!")
            return

        if not self._password_var.get().strip():
            messagebox.showerror("❌ Error", "Password is required!")
            return

        try:
            target_value = self._target_special_jackpot_var.get()
            if target_value <= 0:
                raise ValueError("Target Jackpot must be a positive number!")  # noqa: EM101
        except ValueError as error:
            messagebox.showerror("❌ Error", str(error))
            return

        # Update UI
        self._update_running_status(is_running=True)
        self._notebook.select(self._notebook.index("end") - 1)
        self._activity_log_tab.clear_messages()
        self._activity_log_tab.update_special_jackpot(0)
        self._activity_log_tab.update_target_special_jackpot(target_value)

        spin_action_name = EVENT_CONFIGS_MAP[self._selected_event].spin_actions[self._spin_action_var.get() - 1]
        self._activity_log_tab.add_message(
            tag=MessageTag.INFO.name,
            message=(
                f"Using spin action '{spin_action_name}' to auto spin when target "
                f"'{target_value:,}' is reached at '{EVENT_CONFIGS_MAP[self._selected_event].base_url}'"
            ),
        )

        # Update configs of tool instance and callbacks
        def user_info_callback(user_info: Optional["UserReponse"]) -> None:
            self._root.after(0, lambda: self._update_user_panel(user_info=user_info))

        def message_callback(tag: str, message: str) -> None:
            self._root.after(0, lambda: self._activity_log_tab.add_message(tag=tag, message=message))

        def special_jackpot_callback(special_jackpot: int) -> None:
            self._root.after(0, lambda: self._activity_log_tab.update_special_jackpot(special_jackpot=special_jackpot))

        def _notification_callback(nickname: str, jackpot_value: str) -> None:
            self._root.after(
                0,
                lambda: self._notification_icon.add_notification(
                    nickname=nickname,
                    jackpot_value=jackpot_value,
                    timestamp=datetime.now().strftime("%H:%M:%S"),
                ),
            )

            sounds.send_notification(f"User {nickname} has won jackpot: {jackpot_value}")

        self._tool_instance.update_configs(
            is_running=True,
            event_config=EVENT_CONFIGS_MAP[self._selected_event],
            special_jackpot=0,
            mini_jackpot=0,
            spin_action=self._spin_action_var.get(),
            target_special_jackpot=target_value,
            user_info_callback=user_info_callback,
            message_callback=message_callback,
            special_jackpot_callback=special_jackpot_callback,
            jackpot_billboard_callback=_notification_callback,
        )

        # Start tool in a new thread
        def _handle_start_task() -> None:
            try:
                self._root.after(0, lambda: self._status_label.config(text="Status: Running..."))
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._tool_instance.run())
            except Exception as error:
                self._root.after(0, messagebox.showerror, "❌ Error", str(error))
                self._update_running_status(is_running=False, is_error=True)
                self._root.after(0, lambda: self._update_user_panel(user_info=self._tool_instance.user_info))

        threading.Thread(target=_handle_start_task, daemon=True).start()

    def _handle_click_stop(self) -> None:
        if not self._is_running:
            return

        # Update UI
        self._update_running_status(is_running=False)
        self._notebook.select(0)
        self._root.after(0, lambda: self._update_user_panel(user_info=self._tool_instance.user_info))

        # Update configs of tool instance
        self._tool_instance.update_configs(is_running=False)

        # Stop tool in a new thread
        def _handle_stop_task() -> None:
            try:
                self._root.after(0, lambda: self._status_label.config(text="Status: Ready"))
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._tool_instance.close())
                loop.close()
            except Exception as error:
                self._root.after(0, messagebox.showerror, "❌ Error", str(error))
                self._update_running_status(is_running=True, is_error=True)

        threading.Thread(target=_handle_stop_task, daemon=True).start()
