import asyncio
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING, Optional

import darkdetect
import sv_ttk

from src.core import FCOnlineTool
from src.utils.credentials import CredentialManager

from .control_panel import ControlPanel
from .header import Header
from .log_panel import LogPanel
from .styles import apply_styles
from .user_info_panel import UserInfoPanel
from .user_settings_panel import UserSettingsPanel

if TYPE_CHECKING:
    from src.models import UserInfo


class MainWindow:
    """Main GUI application for FC Online Automation Tool."""

    def __init__(self) -> None:
        """Initialize the main GUI application."""
        self._root = tk.Tk()
        self._root.title("FC Online Automation Tool")
        self._root.geometry("760x740")
        self._root.resizable(False, False)
        self._root.minsize(720, 680)
        self._root.iconbitmap("assets/icon.ico")

        # Pre-apply base styles (will be re-applied after theme set)
        apply_styles(self._root)

        # Load saved credentials
        saved_credentials = CredentialManager.load_credentials()

        # Variables for form inputs
        self._username_var = tk.StringVar(value=saved_credentials.get("username", ""))
        self._password_var = tk.StringVar(value=saved_credentials.get("password", ""))
        self._target_special_jackpot_var = tk.IntVar(value=saved_credentials.get("target_special_jackpot", 10000))
        self._spin_action_var = tk.IntVar(value=saved_credentials.get("spin_action", 1))

        # Running state
        self._is_running = False

        # Tool instance
        self._tool_instance = FCOnlineTool(
            username=self._username_var.get(),
            password=self._password_var.get(),
            target_special_jackpot=self._target_special_jackpot_var.get(),
            spin_action=self._spin_action_var.get(),
        )

        # Initialize components
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup main UI layout with control buttons and content area."""
        # Header with theme toggle
        self.header = Header(
            self._root,
            title="FC Online Automation Tool",
            subtitle="Automate spins • Monitor jackpots in real-time",
            on_toggle_theme=self._on_toggle_theme,
        )
        self.header.pack(side="top", fill="x", padx=16, pady=(12, 4))

        # Control panel at bottom
        self.control_panel = ControlPanel(self._root, on_start=self._start_tool, on_stop=self._stop_tool)
        self.control_panel.pack(side="bottom", fill="x", padx=16, pady=(6, 14))

        # Create main container
        main_container = ttk.Frame(self._root)
        main_container.pack(fill="both", expand=True, padx=16, pady=8)

        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill="both", expand=True)
        # Avoid focus outline on selected tab label
        try:
            self.notebook.configure(takefocus=0)
        except Exception:
            pass

        # Create App tab
        self.app_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.app_tab, text="Dashboard")

        # Create Log tab
        self.log_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.log_tab, text="Activity Log")

        # Setup tabs
        self._setup_app_tab()
        self._setup_log_tab()

        # Redirect focus to tab content so tab label doesn't keep focus ring
        self.notebook.bind(
            "<<NotebookTabChanged>>",
            lambda e: self._root.after(0, self._focus_current_tab_content),
            add=True,
        )
        self.notebook.bind(
            "<ButtonPress-1>",
            lambda e: self._root.after(0, self._focus_current_tab_content),
            add=True,
        )

    def _setup_app_tab(self) -> None:
        """Setup App tab with form inputs and user info display."""
        # Create main container
        container = ttk.Frame(self.app_tab)
        container.pack(fill="both", expand=True, padx=20, pady=10)

        # User settings panel
        self.user_settings_panel = UserSettingsPanel(
            container,
            username_var=self._username_var,
            password_var=self._password_var,
            target_jackpot_var=self._target_special_jackpot_var,
            spin_action_var=self._spin_action_var,
            on_credentials_changed=self._on_credentials_changed,
            on_config_changed=self._on_config_changed,
        )
        self.user_settings_panel.pack(fill="x", pady=(0, 10))

        # User info panel
        self.user_info_panel = UserInfoPanel(container)
        self.user_info_panel.pack(fill="x", pady=(0, 10))

    def _setup_log_tab(self) -> None:
        """Setup Log tab with messages display."""
        # Title
        title_label = ttk.Label(self.log_tab, text="Application Log", style="AppSubtitle.TLabel")
        title_label.pack(pady=(10, 20))

        # Create main container
        container = ttk.Frame(self.log_tab)
        container.pack(fill="both", expand=True, padx=20, pady=10)

        # Log panel
        self.log_panel = LogPanel(container)
        self.log_panel.pack(fill="both", expand=True)

    def _focus_current_tab_content(self) -> None:
        """Move focus to the current tab's content to hide tab label focus outline."""
        try:
            current = self.notebook.nametowidget(self.notebook.select())
            current.focus_set()
        except Exception:
            # If anything goes wrong, simply clear focus
            self._root.focus_set()

    def _on_toggle_theme(self) -> None:
        """Handle theme toggle from header."""
        mode = self.header.selected_mode
        if mode == "Auto":
            theme = darkdetect.theme() or "dark"
        elif mode == "Light":
            theme = "light"
        else:
            theme = "dark"
        sv_ttk.set_theme(theme)
        apply_styles(self._root)
        if hasattr(self, "log_panel"):
            self.log_panel.apply_theme(theme)

    def _on_credentials_changed(self) -> None:
        """Handle credential changes and update tool instance."""
        if not self._is_running and hasattr(self, "_tool_instance"):
            self._tool_instance.update_credentials(
                self._username_var.get(),
                self._password_var.get(),
            )
            self._tool_instance.update_config(
                target_special_jackpot=self._target_special_jackpot_var.get(), spin_action=self._spin_action_var.get()
            )
        self._save_credentials()

    def _on_config_changed(self) -> None:
        """Handle configuration changes and auto-save."""
        if not self._is_running and hasattr(self, "_tool_instance"):
            self._tool_instance.update_config(
                target_special_jackpot=self._target_special_jackpot_var.get(), spin_action=self._spin_action_var.get()
            )
            self._save_credentials()

    def _save_credentials(self) -> None:
        """Save current credentials to config file."""
        credentials = {
            "username": self._username_var.get(),
            "password": self._password_var.get(),
            "target_special_jackpot": self._target_special_jackpot_var.get(),
            "spin_action": self._spin_action_var.get(),
        }
        CredentialManager.save_credentials(credentials)

    def _update_user_info_display(self, user_info: Optional["UserInfo"]) -> None:
        """Update user info display in GUI."""
        current_special_jackpot = self._tool_instance.special_jackpot if hasattr(self, "_tool_instance") else 0
        self.user_info_panel.update_user_info(user_info, current_special_jackpot)

    def _add_message(self, message: str, code: str = "general") -> None:
        """Add message to the log panel with category code."""
        self.log_panel.add_message(message, code)

    def _update_config(self) -> None:
        """Update tool configuration and setup callbacks."""

        def message_callback(message: str, code: str = "general") -> None:
            """Thread-safe callback to update GUI with status messages (categorized)."""
            self._root.after(0, lambda: self._add_message(message, code))

        def user_info_callback() -> None:
            """Thread-safe callback to update user info display"""
            user_info = self._tool_instance.user_info
            self._root.after(0, lambda: self._update_user_info_display(user_info))

        def special_jackpot_callback() -> None:
            """Thread-safe callback to update user info when special jackpot changes"""
            self._root.after(0, lambda: self._update_user_info_display(self._tool_instance.user_info))

        # Set callbacks on the tool instance
        self._tool_instance.set_callbacks(
            message_callback=message_callback,
            user_info_callback=user_info_callback,
            special_jackpot_callback=special_jackpot_callback,
        )

        # Update credentials and configuration
        self._tool_instance.update_credentials(self._username_var.get(), self._password_var.get())
        self._tool_instance.update_config(
            target_special_jackpot=self._target_special_jackpot_var.get(), spin_action=self._spin_action_var.get()
        )

    def _stop_automation_task(self) -> None:
        """Stop automation task in separate event loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._tool_instance.close_browser())
        loop.close()

    def _stop_tool(self) -> None:
        """Stop automation tool and update UI state."""
        if not self._is_running:
            return

        # Update UI state
        self._is_running = False
        self.control_panel.set_stopping_status()

        # Update configuration
        self.user_settings_panel.toggle_inputs(enabled=True)

        # Start automation in separate thread
        self._tool_instance.stop()
        threading.Thread(target=self._stop_automation_task, daemon=True).start()

        self.control_panel.set_running_state(False)

    def _launch_automation_task(self) -> None:
        """Launch automation task in asyncio event loop."""
        try:
            self._root.after(0, lambda: self.control_panel.set_status("🚀 Status: Running..."))

            # Run the automation
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._tool_instance.run())

        except Exception as error:
            error_msg = f"❌ Automation failed: {str(error)}"
            self._root.after(0, lambda: messagebox.showerror("❌ Error", error_msg))

    def _start_tool(self) -> None:
        """Start automation tool with input validation and UI updates."""
        if self._is_running:
            return

        # Validate inputs
        is_valid, error_msg = self.user_settings_panel.validate_inputs()
        if not is_valid:
            messagebox.showerror("❌ Error", error_msg)
            return

        # Update UI state
        self._is_running = True
        self.control_panel.set_starting_status()

        # Update configuration
        self.user_settings_panel.toggle_inputs(enabled=False)
        self._update_config()
        self.log_panel.clear_messages()

        # Start automation in separate thread
        self._tool_instance.start()
        threading.Thread(target=self._launch_automation_task, daemon=True).start()

        self.control_panel.set_running_state(True)

    def _on_closing(self) -> None:
        """Handle application closing - save config and cleanup."""
        # Save configuration before closing
        self._save_credentials()

        # Stop tool if running
        if self._is_running:
            self._tool_instance.stop()

        # Close the application
        self._root.destroy()

    def run(self) -> None:
        """Run the main application."""
        self._root.protocol("WM_DELETE_WINDOW", self._on_closing)
        sv_ttk.set_theme(darkdetect.theme() or "dark")
        apply_styles(self._root)
        self._root.mainloop()


def main_window() -> None:
    """Main entry point for the GUI application."""
    app = MainWindow()
    app.run()
