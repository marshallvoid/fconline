import asyncio
import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

import darkdetect
import sv_ttk

from src.logger import init_logger
from src.tool import FCOnlineTool


class FCOnlineGUI:
    def __init__(self) -> None:
        self._root = tk.Tk()
        self._root.title("FC Online Automation Tool")
        self._root.geometry("700x550")  # Increased height slightly for better layout
        self._root.resizable(False, False)
        self._root.minsize(700, 500)  # Set minimum size to prevent UI breaking

        # Variables for form inputs
        self._username_var = tk.StringVar(value="b.vip250")
        self._password_var = tk.StringVar(value="Hau11111@")
        self._target_special_jackpot_var = tk.IntVar(value=10000)
        self._spin_action_var = tk.IntVar(value=1)

        # Running state
        self._is_running = False
        self._tool_instance = FCOnlineTool(
            username=self._username_var.get(),
            password=self._password_var.get(),
            target_special_jackpot=self._target_special_jackpot_var.get(),
            spin_action=self._spin_action_var.get(),
        )

        self._setup_ui()

    def _setup_ui(self) -> None:
        # Create main container instead of notebook
        main_container = ttk.Frame(self._root)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        self._setup_main_tab(main_container)

        # Control buttons frame - always at bottom
        control_frame = ttk.Frame(self._root)
        control_frame.pack(fill="x", padx=10, pady=(5, 10), side="bottom")  # Pack at bottom

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

    def _setup_main_tab(self, parent: ttk.Frame) -> None:
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

        # Instructions
        self.instructions_frame = ttk.LabelFrame(container, text="Messages", padding=10)
        self.instructions_frame.pack(fill="both", expand=True, pady=(10, 0))

        # Create main container for two columns
        main_text_container = ttk.Frame(self.instructions_frame)
        main_text_container.pack(fill="both", expand=True)

        # Left column for general messages
        left_frame = ttk.LabelFrame(main_text_container, text="General Messages", padding=5)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

        left_text_container = ttk.Frame(left_frame)
        left_text_container.pack(fill="both", expand=True)

        self.general_text_widget = tk.Text(
            left_text_container,
            wrap=tk.WORD,
            height=8,
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
            height=8,
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
        message_lower = message.lower()

        if "jackpot has reached" in message_lower:
            return "target_reached"

        if "jackpot" in message_lower or "mini jackpot" in message_lower:
            return "general"

        return "general"  # default

    def _add_message(self, message: str) -> None:
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

            line_start = f"{i+1}.0"
            line_end = f"{i+1}.end"

            # Apply appropriate styling
            style = self._get_message_tag(line)
            text_widget.tag_add(style, line_start, line_end)

    def _reset_display(self) -> None:
        for widget in [self.general_text_widget, self.alerts_text_widget]:
            widget.config(state="normal")
            widget.delete("1.0", tk.END)
            widget.config(state="disabled")

    def _toggle_inputs(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.username_entry.config(state=state)
        self.password_entry.config(state=state)
        self.target_special_jackpot_entry.config(state=state)

        for radio_btn in self.radio_buttons:
            radio_btn.config(state=state)

    def _on_spin_action_changed(self) -> None:
        """Called when radio button selection changes"""
        if hasattr(self, "_tool_instance"):
            self._tool_instance.spin_action = self._spin_action_var.get()

    def _update_config(self) -> None:
        self._tool_instance.username = self._username_var.get()
        self._tool_instance.password = self._password_var.get()
        self._tool_instance.target_special_jackpot = self._target_special_jackpot_var.get()
        self._tool_instance.spin_action = self._spin_action_var.get()

    def _stop_automation_task(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._tool_instance.close_browser())
        loop.close()

    def _stop_tool(self) -> None:
        if not self._is_running:
            return

        # Update UI state
        self._is_running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status_label.config(text="⏹️ Status: Stopping...")

        # Update configuration
        self._toggle_inputs(enabled=True)
        #   self._reset_display()

        # Start automation in separate thread
        self._tool_instance.stop()
        threading.Thread(target=self._stop_automation_task, daemon=True).start()

        self.status_label.config(text="✅ Status: Ready")

    def _launch_automation_task(self) -> None:
        init_logger()
        try:
            self._root.after(0, lambda: self.status_label.config(text="🚀 Status: Running..."))

            # Run the automation with message callback
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            def message_callback(message: str) -> None:
                """Thread-safe callback to update GUI with status messages"""
                self._root.after(0, lambda: self._add_message(message))

            loop.run_until_complete(self._tool_instance.run(message_callback=message_callback))

        except Exception as error:
            error_msg = f"❌ Automation failed: {str(error)}"
            self._root.after(0, lambda: messagebox.showerror("❌ Error", error_msg))

    def _start_tool(self) -> None:
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

    def run(self) -> None:
        sv_ttk.set_theme(darkdetect.theme() or "dark")
        self._root.mainloop()


def main_gui() -> None:
    app = FCOnlineGUI()
    app.run()


if __name__ == "__main__":
    main_gui()
