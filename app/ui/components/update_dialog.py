import asyncio
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Optional

import app
from app.core.managers.update import update_mgr
from app.utils import helpers as hlp


class UpdateDialog(tk.Toplevel):
    """Dialog for checking and installing updates."""

    def __init__(self, parent: tk.Tk):
        super().__init__(parent)
        self.title("Software Update")
        self.geometry("600x500")

        # Center the dialog on screen
        self.update_idletasks()
        _, _, dw, dh, x, y = hlp.get_window_position(child_frame=self, parent_frame=parent)
        self.geometry(f"{dw}x{dh}+{x}+{y}")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

        # State
        self.has_update = False
        self.latest_version: Optional[str] = None
        self.release_notes: Optional[str] = None
        self.download_path: Optional[Path] = None
        self.checking = False
        self.downloading = False
        self.installing = False

        self._setup_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Start checking immediately
        self.after(100, self._start_check)

    def _setup_ui(self) -> None:
        """Setup dialog UI."""
        # Main frame
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill="both", expand=True)

        # Title label
        self.title_label = ttk.Label(main_frame, text="Checking for updates...", font=("", 14, "bold"))
        self.title_label.pack(pady=(0, 20))

        # Version info frame
        version_frame = ttk.LabelFrame(main_frame, text="Version Information", padding="10")
        version_frame.pack(fill="x", pady=(0, 10))

        current_version = app.__version__
        ttk.Label(version_frame, text=f"Current Version: {current_version}").pack(anchor="w")
        self.latest_label = ttk.Label(version_frame, text="Latest Version: Checking...")
        self.latest_label.pack(anchor="w", pady=(5, 0))

        # Release notes frame
        notes_frame = ttk.LabelFrame(main_frame, text="Release Notes", padding="10")
        notes_frame.pack(fill="both", expand=True, pady=(0, 10))

        # Text widget with scrollbar
        text_container = ttk.Frame(notes_frame)
        text_container.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(text_container)
        scrollbar.pack(side="right", fill="y")

        self.notes_text = tk.Text(
            text_container, wrap="word", height=10, yscrollcommand=scrollbar.set, state="disabled"
        )
        self.notes_text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.notes_text.yview)

        # Progress bar
        self.progress_frame = ttk.Frame(main_frame)
        self.progress_frame.pack(fill="x", pady=(0, 10))
        self.progress_frame.pack_forget()  # Hide initially

        self.progress_label = ttk.Label(self.progress_frame, text="")
        self.progress_label.pack(anchor="w", pady=(0, 5))

        self.progress_bar = ttk.Progressbar(self.progress_frame, mode="determinate", length=560)
        self.progress_bar.pack(fill="x")

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x")

        self.install_button = ttk.Button(
            button_frame, text="Download and Install", command=self._start_download, state="disabled"
        )
        self.install_button.pack(side="left", padx=(0, 5))

        self.close_button = ttk.Button(button_frame, text="Close", command=self._on_close)
        self.close_button.pack(side="left")

    def _start_check(self) -> None:
        """Start checking for updates in background thread."""
        if self.checking:
            return

        self.checking = True
        thread = threading.Thread(target=self._check_updates, daemon=True)
        thread.start()

    def _check_updates(self) -> None:
        """Check for updates (runs in background thread)."""
        try:
            # Run async check in new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            has_update, latest_version, release_notes = loop.run_until_complete(update_mgr.check_for_updates())
            loop.close()

            # Update UI in main thread
            self.after(0, lambda: self._on_check_complete(has_update, latest_version, release_notes))
        except Exception as e:
            error_msg = str(e)
            self.after(0, lambda: self._on_check_error(error_msg))
        finally:
            self.checking = False

    def _on_check_complete(self, has_update: bool, latest_version: Optional[str], release_notes: Optional[str]) -> None:
        """Handle check completion."""
        self.has_update = has_update
        self.latest_version = latest_version
        self.release_notes = release_notes

        if has_update and latest_version:
            self.title_label.config(text="New version available!")
            self.latest_label.config(text=f"Latest Version: {latest_version}")
            self.install_button.config(state="normal")

            # Show release notes
            if release_notes:
                self.notes_text.config(state="normal")
                self.notes_text.delete("1.0", "end")
                self.notes_text.insert("1.0", release_notes)
                self.notes_text.config(state="disabled")
        else:
            self.title_label.config(text="You're up to date!")
            self.latest_label.config(text=f"Latest Version: {app.__version__}")
            self.notes_text.config(state="normal")
            self.notes_text.delete("1.0", "end")
            self.notes_text.insert("1.0", "No updates available at this time.")
            self.notes_text.config(state="disabled")

    def _on_check_error(self, error: str) -> None:
        """Handle check error."""
        self.title_label.config(text="Error checking for updates")
        self.latest_label.config(text="Latest Version: Unknown")
        self.notes_text.config(state="normal")
        self.notes_text.delete("1.0", "end")
        self.notes_text.insert("1.0", f"Error: {error}")
        self.notes_text.config(state="disabled")

    def _start_download(self) -> None:
        """Start downloading update in background thread."""
        if self.downloading or not self.has_update:
            return

        self.downloading = True
        self.install_button.config(state="disabled")
        self.close_button.config(state="disabled")
        self.progress_frame.pack(fill="x", pady=(0, 10))
        self.progress_label.config(text="Downloading update...")

        thread = threading.Thread(target=self._download_update, daemon=True)
        thread.start()

    def _download_update(self) -> None:
        """Download update (runs in background thread)."""
        try:
            # Progress callback
            def on_progress(current: int, total: int) -> None:
                percent = int((current / total) * 100) if total > 0 else 0
                self.after(0, lambda: self._update_progress(percent, current, total))

            # Run async download in new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            download_path = loop.run_until_complete(update_mgr.download_update(on_progress))
            loop.close()

            # Update UI in main thread
            if download_path:
                self.after(0, lambda: self._on_download_complete(download_path))
            else:
                self.after(0, lambda: self._on_download_error("Failed to download update"))
        except Exception as e:
            error_msg = str(e)
            self.after(0, lambda: self._on_download_error(error_msg))
        finally:
            self.downloading = False

    def _update_progress(self, percent: int, current: int, total: int) -> None:
        """Update progress bar."""
        self.progress_bar["value"] = percent
        current_mb = current / (1024 * 1024)
        total_mb = total / (1024 * 1024)
        self.progress_label.config(text=f"Downloading update... {percent}% ({current_mb:.1f}/{total_mb:.1f} MB)")

    def _on_download_complete(self, download_path: Path) -> None:
        """Handle download completion."""
        self.download_path = download_path
        self.progress_label.config(text="Download complete! Installing...")
        self.progress_bar["value"] = 100

        # Start installation
        self.after(500, self._start_install)

    def _on_download_error(self, error: str) -> None:
        """Handle download error."""
        self.progress_label.config(text=f"Download failed: {error}")
        self.install_button.config(state="normal")
        self.close_button.config(state="normal")
        messagebox.showerror("Download Error", f"Failed to download update:\n{error}")

    def _start_install(self) -> None:
        """Start installing update in background thread."""
        if self.installing or not self.download_path:
            return

        self.installing = True
        thread = threading.Thread(target=self._install_update, daemon=True)
        thread.start()

    def _install_update(self) -> None:
        """Install update (runs in background thread)."""
        if not self.download_path:
            return

        try:
            success = update_mgr.install_update(self.download_path)
            self.after(0, lambda: self._on_install_complete(success))
        except Exception as e:
            error_msg = str(e)
            self.after(0, lambda: self._on_install_error(error_msg))
        finally:
            self.installing = False

    def _on_install_complete(self, success: bool) -> None:
        """Handle installation completion."""
        if success:
            self.progress_label.config(text="Update installed! Application will restart...")
            messagebox.showinfo(
                "Update Complete", "Update has been installed successfully.\nThe application will now restart."
            )
            # Application will restart automatically
        else:
            self.progress_label.config(text="Installation failed")
            self.close_button.config(state="normal")
            messagebox.showerror(
                "Installation Error", "Failed to install update. Please try again or download manually."
            )

    def _on_install_error(self, error: str) -> None:
        """Handle installation error."""
        self.progress_label.config(text=f"Installation failed: {error}")
        self.close_button.config(state="normal")
        messagebox.showerror("Installation Error", f"Failed to install update:\n{error}")

    def _on_close(self) -> None:
        """Handle dialog close."""
        if self.downloading or self.installing:
            if not messagebox.askyesno(
                "Operation in Progress", "An operation is in progress. Are you sure you want to cancel?"
            ):
                return
        self.destroy()
