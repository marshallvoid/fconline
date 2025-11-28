import asyncio
import threading
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Optional

import markdown2
from tkhtmlview import HTMLText

from app.core.managers.update import update_mgr
from app.ui.utils.ui_factory import UIFactory
from app.utils.helpers import get_window_position


@dataclass
class _UpdateState:
    has_update: bool = False
    latest_version: Optional[str] = None
    release_notes: Optional[str] = None
    download_path: Optional[Path] = None
    checking: bool = False
    downloading: bool = False
    installing: bool = False


class UpdateDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Tk,
        latest_version: Optional[str] = None,
        release_notes: Optional[str] = None,
    ):
        super().__init__(parent)
        self.title("Software Update")
        self.geometry("700x600")  # Increased size for better reading

        # Center the dialog on screen
        self.update_idletasks()
        _, _, dw, dh, x, y = get_window_position(child_frame=self, parent_frame=parent)
        self.geometry(f"{dw}x{dh}+{x}+{y}")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

        # State management
        self._state = _UpdateState()

        # If data provided, update state immediately
        if latest_version:
            self._state.has_update = True
            self._state.latest_version = latest_version
            self._state.release_notes = release_notes

        self._setup_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Start checking only if data not provided
        if not latest_version:
            self.after(100, self._start_check)
        else:
            # Update UI with provided data
            self._on_check_complete(True, latest_version, release_notes)

    def _setup_ui(self) -> None:
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill="both", expand=True)

        # Title label
        self.title_label = ttk.Label(main_frame, text="Checking for updates...", font=("", 14, "bold"))
        self.title_label.pack(pady=(0, 20))

        self._setup_version_info(parent=main_frame)
        self._setup_release_notes(parent=main_frame)
        self._setup_progress_bar(parent=main_frame)
        self._setup_buttons(parent=main_frame)

    def _setup_version_info(self, parent: tk.Misc) -> None:
        version_frame = UIFactory.create_label_frame(parent=parent, text="Version Information")
        version_frame.pack(fill="x", pady=(0, 10))

        current_version = update_mgr.current_version
        ttk.Label(version_frame, text=f"Current Version: {current_version}").pack(anchor="w")
        self.latest_label = ttk.Label(version_frame, text="Latest Version: Checking...")
        self.latest_label.pack(anchor="w", pady=(5, 0))

    def _setup_release_notes(self, parent: tk.Misc) -> None:
        notes_frame = UIFactory.create_label_frame(parent=parent, text="Release Notes")
        notes_frame.pack(fill="both", expand=True, pady=(0, 10))

        text_container = ttk.Frame(notes_frame)
        text_container.pack(fill="both", expand=True)

        # Use HTMLText for Markdown rendering
        self.notes_text = HTMLText(
            text_container,
            html="<p>Checking for release notes...</p>",
            background="#ffffff",
            foreground="#000000",
            font=("Segoe UI", 10),
        )

        # Add scrollbar
        scrollbar = ttk.Scrollbar(text_container, orient="vertical", command=self.notes_text.yview)
        self.notes_text.configure(yscrollcommand=scrollbar.set)

        self.notes_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Fit height
        self.notes_text.fit_height()

    def _setup_progress_bar(self, parent: tk.Misc) -> None:
        self.progress_frame = ttk.Frame(parent)
        self.progress_frame.pack(fill="x", pady=(0, 10))
        self.progress_frame.pack_forget()  # Hide initially

        self.progress_label = ttk.Label(self.progress_frame, text="")
        self.progress_label.pack(anchor="w", pady=(0, 5))

        self.progress_bar = ttk.Progressbar(self.progress_frame, mode="determinate", length=560)
        self.progress_bar.pack(fill="x")

    def _setup_buttons(self, parent: tk.Misc) -> None:
        button_frame, buttons = UIFactory.create_button_group(
            parent=parent,
            buttons=[
                {"text": "Download and Install", "command": self._start_download, "state": "disabled"},
                {"text": "Close", "command": self._on_close},
            ],
            spacing=5,
        )
        button_frame.pack(fill="x")

        self.install_button = buttons[0]
        self.close_button = buttons[1]

    def _start_check(self) -> None:
        if self._state.checking:
            return

        self._state.checking = True
        thread = threading.Thread(target=self._check_updates, daemon=True)
        thread.start()

    def _check_updates(self) -> None:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            has_update, latest_version, release_notes = loop.run_until_complete(update_mgr.check_for_updates())
            loop.close()

            self.after(0, lambda: self._on_check_complete(has_update, latest_version, release_notes))
        except Exception as e:
            error_msg = str(e)
            self.after(0, lambda: self._on_check_error(error_msg))
        finally:
            self._state.checking = False

    def _on_check_complete(self, has_update: bool, latest_version: Optional[str], release_notes: Optional[str]) -> None:
        self._state.has_update = has_update
        self._state.latest_version = latest_version
        self._state.release_notes = release_notes

        if has_update and latest_version:
            self.title_label.config(text="New version available!")
            self.latest_label.config(text=f"Latest Version: {latest_version}")
            self.install_button.config(state="normal")

            if release_notes:
                # Convert Markdown to HTML
                html_content = markdown2.markdown(
                    release_notes, extras=["fenced-code-blocks", "tables", "break-on-newline"]
                )

                # Add some basic styling
                styled_html = f"""
                <div style="font-family: Segoe UI, sans-serif; padding: 10px;">
                    {html_content}
                </div>
                """
                self.notes_text.set_html(styled_html)
        else:
            self.title_label.config(text="You're up to date!")
            self.latest_label.config(text=f"Latest Version: {update_mgr.current_version}")
            self.notes_text.set_html("<p>No updates available at this time.</p>")

    def _on_check_error(self, error: str) -> None:
        self.title_label.config(text="Error checking for updates")
        self.latest_label.config(text="Latest Version: Unknown")
        self.notes_text.set_html(f"<p style='color: red;'>Error: {error}</p>")

    def _start_download(self) -> None:
        if self._state.downloading or not self._state.has_update:
            return

        self._state.downloading = True
        self.install_button.config(state="disabled")
        self.close_button.config(state="disabled")
        self.progress_frame.pack(fill="x", pady=(0, 10))
        self.progress_label.config(text="Downloading update...")

        thread = threading.Thread(target=self._download_update, daemon=True)
        thread.start()

    def _download_update(self) -> None:
        try:

            def on_progress(current: int, total: int) -> None:
                percent = int((current / total) * 100) if total > 0 else 0
                self.after(0, lambda: self._update_progress(percent, current, total))

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            download_path = loop.run_until_complete(update_mgr.download_update(on_progress))
            loop.close()

            if download_path:
                self.after(0, lambda: self._on_download_complete(download_path))
            else:
                self.after(0, lambda: self._on_download_error("Failed to download update"))
        except Exception as e:
            error_msg = str(e)
            self.after(0, lambda: self._on_download_error(error_msg))
        finally:
            self._state.downloading = False

    def _update_progress(self, percent: int, current: int, total: int) -> None:
        self.progress_bar["value"] = percent
        current_mb = current / (1024 * 1024)
        total_mb = total / (1024 * 1024)
        self.progress_label.config(text=f"Downloading update... {percent}% ({current_mb:.1f}/{total_mb:.1f} MB)")

    def _on_download_complete(self, download_path: Path) -> None:
        self._state.download_path = download_path
        self.progress_label.config(text="Download complete! Installing...")
        self.progress_bar["value"] = 100

        self.after(500, self._start_install)

    def _on_download_error(self, error: str) -> None:
        self.progress_label.config(text=f"Download failed: {error}")
        self.install_button.config(state="normal")
        self.close_button.config(state="normal")
        messagebox.showerror("Download Error", f"Failed to download update:\n{error}")

    def _start_install(self) -> None:
        if self._state.installing or not self._state.download_path:
            return

        self._state.installing = True
        thread = threading.Thread(target=self._install_update, daemon=True)
        thread.start()

    def _install_update(self) -> None:
        if not self._state.download_path:
            return

        try:
            success = update_mgr.install_update(self._state.download_path)
            self.after(0, lambda: self._on_install_complete(success))
        except Exception as e:
            error_msg = str(e)
            self.after(0, lambda: self._on_install_error(error_msg))
        finally:
            self._state.installing = False

    def _on_install_complete(self, success: bool) -> None:
        if success:
            self.progress_label.config(text="Update installed! Application will restart...")
            messagebox.showinfo(
                "Update Complete", "Update has been installed successfully.\nThe application will now restart."
            )
        else:
            self.progress_label.config(text="Installation failed")
            self.close_button.config(state="normal")
            messagebox.showerror(
                "Installation Error", "Failed to install update. Please try again or download manually."
            )

    def _on_install_error(self, error: str) -> None:
        self.progress_label.config(text=f"Installation failed: {error}")
        self.close_button.config(state="normal")
        messagebox.showerror("Installation Error", f"Failed to install update:\n{error}")

    def _on_close(self) -> None:
        if self._state.downloading or self._state.installing:
            if not messagebox.askyesno(
                "Operation in Progress", "An operation is in progress. Are you sure you want to cancel?"
            ):
                return
        self.destroy()
