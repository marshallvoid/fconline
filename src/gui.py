import asyncio
import base64
import json
import os
import platform
import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING, Optional

import darkdetect
import sv_ttk
from cryptography.fernet import Fernet

from src.tool import FCOnlineTool

if TYPE_CHECKING:
    from src.types import UserInfo


class FCOnlineGUI:
    """GUI application for FC Online automation tool."""

    def __init__(self) -> None:
        """Initialize GUI components and tool instance."""
        self._root = tk.Tk()
        self._root.title("FC Online Automation Tool")
        self._root.geometry("700x600")
        self._root.resizable(False, False)
        self._root.minsize(700, 550)

        # Create user data directory
        self._user_data_dir = self._get_user_data_dir()
        self._config_file = os.path.join(self._user_data_dir, "config.json")

        # Load saved credentials or use defaults
        saved_credentials = self._load_credentials()

        # Variables for form inputs
        self._username_var = tk.StringVar(value=saved_credentials.get("username", ""))
        self._password_var = tk.StringVar(value=saved_credentials.get("password", ""))
        self._target_special_jackpot_var = tk.IntVar(value=saved_credentials.get("target_special_jackpot", 10000))
        self._spin_action_var = tk.IntVar(value=saved_credentials.get("spin_action", 1))

        # Add trace callbacks for credential changes
        self._username_var.trace_add("write", self._on_credentials_changed)
        self._password_var.trace_add("write", self._on_credentials_changed)
        self._target_special_jackpot_var.trace_add("write", self._on_config_changed)
        self._spin_action_var.trace_add("write", self._on_config_changed)

        # Running state
        self._is_running = False
        self._tool_instance = FCOnlineTool(
            username=self._username_var.get(),
            password=self._password_var.get(),
            target_special_jackpot=self._target_special_jackpot_var.get(),
            spin_action=self._spin_action_var.get(),
        )

        self._setup_ui()

    def _get_user_data_dir(self) -> str:
        """Get user data directory path that works across different systems.

        Returns:
            Path to user data directory
        """
        system = platform.system().lower()

        if system == "windows":  # Windows
            app_data = os.environ.get("APPDATA", os.path.expanduser("~"))
            user_data_dir = os.path.join(app_data, "FCOnlineAutomation")
        else:  # macOS and Linux
            user_data_dir = os.path.expanduser("~/.fconline-automation")

        # Create directory if it doesn't exist
        os.makedirs(user_data_dir, exist_ok=True)
        return user_data_dir

    def _get_encryption_key(self) -> bytes:
        """Get or create encryption key for data protection.

        Returns:
            Encryption key bytes
        """
        key_file = os.path.join(self._user_data_dir, ".key")

        try:
            # Try to load existing key
            if os.path.exists(key_file):
                with open(key_file, "rb") as f:
                    return f.read()
            else:
                # Generate new key if doesn't exist
                key = Fernet.generate_key()
                with open(key_file, "wb") as f:
                    f.write(key)
                # Make key file hidden and read-only on Unix systems
                if platform.system().lower() != "windows":
                    os.chmod(key_file, 0o600)
                return key
        except Exception:
            # Fallback to a simple key based on machine info
            machine_id = platform.node() + platform.machine()
            key = base64.urlsafe_b64encode(machine_id.encode().ljust(32)[:32])
            return key

    def _encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data.

        Args:
            data: String data to encrypt

        Returns:
            Encrypted data as base64 string
        """
        try:
            key = self._get_encryption_key()
            f = Fernet(key)
            encrypted_data = f.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception:
            # Fallback to simple base64 encoding if encryption fails
            return base64.urlsafe_b64encode(data.encode()).decode()

    def _decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data.

        Args:
            encrypted_data: Base64 encoded encrypted data

        Returns:
            Decrypted string data
        """
        try:
            key = self._get_encryption_key()
            f = Fernet(key)
            data_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = f.decrypt(data_bytes)
            return decrypted_data.decode()
        except Exception:
            # Fallback to simple base64 decoding if decryption fails
            try:
                return base64.urlsafe_b64decode(encrypted_data.encode()).decode()
            except Exception:
                return ""

    def _load_credentials(self) -> dict:
        """Load saved credentials from config file.

        Returns:
            Dictionary containing saved credentials or empty dict if file doesn't exist
        """
        try:
            if os.path.exists(self._config_file):
                with open(self._config_file, "r", encoding="utf-8") as f:
                    encrypted_data = json.load(f)

                # Decrypt sensitive data
                credentials = {}
                for key, value in encrypted_data.items():
                    if key in ["username", "password"]:
                        # Decrypt sensitive fields
                        credentials[key] = self._decrypt_data(value) if value else ""
                    else:
                        # Keep non-sensitive fields as is
                        credentials[key] = value

                return credentials
        except Exception:
            # Silent fail - just return empty dict if can't load
            pass

        return {}

    def _save_credentials(self) -> None:
        """Save current credentials to config file."""
        try:
            # Prepare credentials with encryption for sensitive data
            credentials = {
                "username": self._encrypt_data(self._username_var.get()) if self._username_var.get() else "",
                "password": self._encrypt_data(self._password_var.get()) if self._password_var.get() else "",
                "target_special_jackpot": self._target_special_jackpot_var.get(),
                "spin_action": self._spin_action_var.get(),
            }

            with open(self._config_file, "w", encoding="utf-8") as f:
                json.dump(credentials, f, indent=2, ensure_ascii=False)

        except Exception:
            # Silent fail - don't crash the app if can't save
            pass

    def _setup_ui(self) -> None:
        """Setup main UI layout with control buttons and content area."""
        # Control buttons at bottom
        control_frame = ttk.Frame(self._root)
        control_frame.pack(side="bottom", fill="x", padx=10, pady=(5, 10))

        self.start_btn = ttk.Button(
            control_frame,
            text="Start",
            command=self._start_tool,
            style="Accent.TButton",
        )
        self.start_btn.pack(side="left", padx=(0, 5))

        self.stop_btn = ttk.Button(
            control_frame,
            text="Stop",
            command=self._stop_tool,
            state="disabled",
        )
        self.stop_btn.pack(side="left", padx=5)

        # Status label
        self.status_label = ttk.Label(control_frame, text="✅ Status: Ready")
        self.status_label.pack(side="right")

        # Create main container
        main_container = ttk.Frame(self._root)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        self._setup_main_tab(main_container)

    def _setup_main_tab(self, parent: ttk.Frame) -> None:
        """Setup main tab with form inputs and message displays.

        Args:
            parent: Parent frame widget
        """
        # Title
        title_label = ttk.Label(parent, text="FC Online Automation Settings", font=("Arial", 14, "bold"))
        title_label.pack(pady=(10, 20))

        # Create main container
        container = ttk.Frame(parent)
        container.pack(fill="both", expand=True, padx=20)

        # Username field
        username_frame = ttk.Frame(container)
        username_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(username_frame, text="Username:", width=20).pack(side="left")
        self.username_entry = ttk.Entry(username_frame, textvariable=self._username_var, width=30)
        self.username_entry.pack(side="left", padx=(10, 0), fill="x", expand=True)

        # Password field
        password_frame = ttk.Frame(container)
        password_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(password_frame, text="Password:", width=20).pack(side="left")
        self.password_entry = ttk.Entry(password_frame, textvariable=self._password_var, show="*", width=30)
        self.password_entry.pack(side="left", padx=(10, 0), fill="x", expand=True)

        # Target Special Jackpot field
        target_special_jackpot_frame = ttk.Frame(container)
        target_special_jackpot_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(target_special_jackpot_frame, text="Target Special Jackpot:", width=20).pack(side="left")
        self.target_special_jackpot_entry = ttk.Entry(
            target_special_jackpot_frame,
            textvariable=self._target_special_jackpot_var,
            width=30,
        )
        self.target_special_jackpot_entry.pack(side="left", padx=(10, 0), fill="x", expand=True)

        # User Info Display
        user_info_frame = ttk.LabelFrame(container, text="User Information", padding=10)
        user_info_frame.pack(fill="x", pady=(0, 10))

        self.user_info_label = ttk.Label(user_info_frame, text="Not logged in", foreground="gray")
        self.user_info_label.pack(anchor="w")

        # Spin Action Radio Buttons
        spin_action_frame = ttk.LabelFrame(container, text="Spin Action", padding=10)
        spin_action_frame.pack(fill="x", pady=(0, 20))

        radio_container = ttk.Frame(spin_action_frame)
        radio_container.pack(fill="x")

        self.radio_buttons = []
        radio_options = [(1, "Free"), (2, "10FC"), (3, "..."), (4, "...")]

        for value, text in radio_options:
            radio_btn = ttk.Radiobutton(
                radio_container,
                text=text,
                variable=self._spin_action_var,
                value=value,
                command=self._on_spin_action_changed,
            )
            radio_btn.pack(side="left", padx=(0, 20))
            self.radio_buttons.append(radio_btn)

        # Messages with fixed height
        self.messages_frame = ttk.LabelFrame(container, text="Messages", padding=10)
        self.messages_frame.pack(fill="x", pady=(10, 0))

        # Fixed height configuration
        self.messages_frame.configure(height=200)
        self.messages_frame.pack_propagate(False)

        # Create main container for two columns
        main_text_container = ttk.Frame(self.messages_frame)
        main_text_container.pack(fill="both", expand=True)

        # Left column for general messages
        left_frame = ttk.LabelFrame(main_text_container, text="General Messages", padding=5)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

        left_text_container = ttk.Frame(left_frame)
        left_text_container.pack(fill="both", expand=True)

        self.general_text_widget = tk.Text(
            left_text_container,
            wrap=tk.WORD,
            height=6,
            width=30,
            font=("Arial", 11),
            bg="#2b2b2b",
            fg="#e0e0e0",
            relief="flat",
            borderwidth=0,
            state="disabled",
            insertbackground="#e0e0e0",
        )

        # Right column for target reached messages
        right_frame = ttk.LabelFrame(main_text_container, text="Target Alerts", padding=5)
        right_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))

        right_text_container = ttk.Frame(right_frame)
        right_text_container.pack(fill="both", expand=True)

        self.alerts_text_widget = tk.Text(
            right_text_container,
            wrap=tk.WORD,
            height=6,
            width=30,
            font=("Arial", 11),
            bg="#2b2b2b",
            fg="#e0e0e0",
            relief="flat",
            borderwidth=0,
            state="disabled",
            insertbackground="#e0e0e0",
        )

        # Configure text tags for both widgets
        for widget in [self.general_text_widget, self.alerts_text_widget]:
            widget.tag_configure("general", foreground="#4caf50", font=("Arial", 12, "bold"))
            widget.tag_configure("target_reached", foreground="#ff9800", font=("Arial", 12, "bold"))
            widget.tag_configure("error", foreground="#f44336", font=("Arial", 11, "bold"))
            widget.tag_configure("info", foreground="#2196f3")
            widget.tag_configure("default", foreground="#e0e0e0")

        # Create scrollbars for both text widgets
        left_scrollbar = ttk.Scrollbar(left_text_container, orient="vertical", command=self.general_text_widget.yview)
        self.general_text_widget.configure(yscrollcommand=left_scrollbar.set)

        right_scrollbar = ttk.Scrollbar(right_text_container, orient="vertical", command=self.alerts_text_widget.yview)
        self.alerts_text_widget.configure(yscrollcommand=right_scrollbar.set)

        # Pack text widgets and scrollbars
        self.general_text_widget.pack(side="left", fill="both", expand=True)
        left_scrollbar.pack(side="right", fill="y")

        self.alerts_text_widget.pack(side="left", fill="both", expand=True)
        right_scrollbar.pack(side="right", fill="y")

    def _get_message_tag(self, message: str) -> str:
        """Get appropriate message tag based on content.

        Args:
            message: Message text to analyze

        Returns:
            Tag name for styling
        """
        message_lower = message.lower()

        if "jackpot has reached" in message_lower:
            return "target_reached"

        if "jackpot" in message_lower or "mini jackpot" in message_lower:
            return "general"

        return "general"

    def _on_credentials_changed(self, *args: str) -> None:
        """Handle credential changes and update tool instance.

        Args:
            *args: Trace callback arguments (unused)
        """
        _ = args
        if not self._is_running and hasattr(self, "_tool_instance"):
            self._tool_instance.update_credentials(
                self._username_var.get(),
                self._password_var.get(),
            )
            # Auto-save credentials when they change
            self._save_credentials()

    def _on_config_changed(self, *args: str) -> None:
        """Handle configuration changes and auto-save.

        Args:
            *args: Trace callback arguments (unused)
        """
        _ = args
        if not self._is_running:
            # Auto-save configuration when it changes
            self._save_credentials()

    def _update_user_info_display(self, user_info: Optional["UserInfo"]) -> None:
        """Update user info display in GUI.

        Args:
            user_info: User information object or None
        """
        if not user_info or not user_info.payload.user:
            self.user_info_label.config(text="Not logged in", foreground="gray")
            return

        user = user_info.payload.user
        info_text = (
            f"UID: {user.uid}\nUsername: {user.nickname}\n" f"Free Spin: {user.free_spin}\nFC: {user.fc}\nMC: {user.mc}"
        )
        self.user_info_label.config(text=info_text, foreground="green")

    def _add_message(self, message: str) -> None:
        """Add timestamped message to appropriate text widget.

        Args:
            message: Message text to display
        """
        # Skip empty or whitespace-only messages
        if not message or not message.strip():
            return

        # Add timestamp to message
        timestamp = datetime.now().strftime("%H:%M:%S")
        timestamped_message = f"[{timestamp}] {message.strip()}"

        # Determine which widget to use based on message content
        message_lower = message.lower()
        is_target_reached = "jackpot has reached" in message_lower

        # Choose the appropriate widget
        target_widget = self.alerts_text_widget if is_target_reached else self.general_text_widget
        target_widget.config(state="normal")

        # Check if this is the first message in this widget
        current_text = target_widget.get("1.0", tk.END).strip()
        if not current_text:
            # First message - no newline needed
            start_pos = "1.0"
        else:
            # Add new line for next message
            target_widget.insert(tk.END, "\n")
            start_pos = target_widget.index(tk.END + "-1c linestart")

        # Insert the timestamped message
        target_widget.insert(tk.END, timestamped_message)
        end_pos = target_widget.index(tk.END + "-1c")

        # Apply styling based on message content
        tag = self._get_message_tag(message=message.strip())
        target_widget.tag_add(tag, start_pos, end_pos)

        # Auto-scroll to bottom and make read-only
        target_widget.see(tk.END)
        target_widget.config(state="disabled")

    def _reapply_styling(self, text_widget: tk.Text) -> None:
        content = text_widget.get("1.0", tk.END)
        lines = content.split("\n")

        for i, line in enumerate(lines):
            if not line.strip():
                continue

            line_start = f"{i + 1}.0"
            line_end = f"{i + 1}.end"

            # Apply appropriate styling
            tag = self._get_message_tag(line)
            text_widget.tag_add(tag, line_start, line_end)

    def _reset_display(self) -> None:
        for widget in [self.general_text_widget, self.alerts_text_widget]:
            widget.config(state="normal")
            widget.delete("1.0", tk.END)
            widget.config(state="disabled")

    def _toggle_inputs(self, enabled: bool) -> None:
        """Enable or disable input widgets.

        Args:
            enabled: Whether to enable or disable inputs
        """
        state = "normal" if enabled else "disabled"
        self.username_entry.config(state=state)
        self.password_entry.config(state=state)
        self.target_special_jackpot_entry.config(state=state)

        for radio_btn in self.radio_buttons:
            radio_btn.config(state=state)

    def _on_spin_action_changed(self) -> None:
        """Handle spin action radio button changes."""
        if hasattr(self, "_tool_instance"):
            self._tool_instance.spin_action = self._spin_action_var.get()
            # Auto-save when spin action changes
            if not self._is_running:
                self._save_credentials()

    def _update_config(self) -> None:
        """Update tool configuration and setup callbacks."""

        def message_callback(message: str) -> None:
            """Thread-safe callback to update GUI with status messages"""
            self._root.after(0, lambda: self._add_message(message))

        def user_info_callback() -> None:
            """Thread-safe callback to update user info display"""
            user_info = self._tool_instance.user_info
            self._root.after(0, lambda: self._update_user_info_display(user_info))

        # Set callbacks on the tool instance
        self._tool_instance.message_callback = message_callback
        self._tool_instance.user_info_callback = user_info_callback

        # Update credentials
        self._tool_instance.update_credentials(self._username_var.get(), self._password_var.get())
        self._tool_instance.target_special_jackpot = self._target_special_jackpot_var.get()
        self._tool_instance.spin_action = self._spin_action_var.get()

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
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status_label.config(text="⏹️ Status: Stopping...")

        # Update configuration
        self._toggle_inputs(enabled=True)

        # Start automation in separate thread
        self._tool_instance.stop()
        threading.Thread(target=self._stop_automation_task, daemon=True).start()

        self.status_label.config(text="✅ Status: Ready")

    def _launch_automation_task(self) -> None:
        """Launch automation task in asyncio event loop.

        Raises:
            Exception: For automation errors
        """
        # No need to call init_logger() - it's auto-initialized
        try:
            self._root.after(0, lambda: self.status_label.config(text="🚀 Status: Running..."))

            # Run the automation
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            loop.run_until_complete(self._tool_instance.run())

        except Exception as error:
            error_msg = f"❌ Automation failed: {str(error)}"
            self._root.after(0, lambda: messagebox.showerror("❌ Error", error_msg))

    def _start_tool(self) -> None:
        """Start automation tool with input validation and UI updates.

        Raises:
            ValueError: For invalid input values
        """
        if self._is_running:
            return

        # Validate inputs
        if not self._username_var.get().strip():
            messagebox.showerror("❌ Error", "Username cannot be empty!")
            return

        if not self._password_var.get().strip():
            messagebox.showerror("❌ Error", "Password cannot be empty!")
            return

        # Validate target jackpot
        try:
            target_value = self._target_special_jackpot_var.get()
            if target_value <= 0:
                msg = "Target must be positive"
                raise ValueError(msg)
        except ValueError:
            messagebox.showerror("❌ Error", "Target Jackpot must be a positive number!")
            return

        # Update UI state
        self._is_running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status_label.config(text="🚀 Status: Starting...")

        # Update configuration
        self._toggle_inputs(enabled=False)
        self._update_config()
        self._reset_display()

        # Start automation in separate thread
        self._tool_instance.start()
        threading.Thread(target=self._launch_automation_task, daemon=True).start()

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
        """Run the GUI application with theme setup."""
        # Setup closing protocol
        self._root.protocol("WM_DELETE_WINDOW", self._on_closing)

        sv_ttk.set_theme(darkdetect.theme() or "dark")
        self._root.mainloop()


def main_gui() -> None:
    """Main entry point for GUI application."""
    app = FCOnlineGUI()
    app.run()


if __name__ == "__main__":
    import src.logger  # noqa: F401

    main_gui()
