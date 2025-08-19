import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
    from watchdog.events import FileSystemEvent, FileSystemEventHandler
    from watchdog.observers import Observer

    WATCHDOG_AVAILABLE = True

except ImportError:
    WATCHDOG_AVAILABLE = False


class AutoReloadHandler(FileSystemEventHandler):
    """Handles automatic reloading of Python files during development."""

    def __init__(self, callback: Callable[[], None], watch_paths: Optional[List[str]] = None) -> None:
        """
        Initialize the auto-reload handler.

        Args:
            callback: Function to call when files change
            watch_paths: List of paths to watch for changes
        """
        self.callback = callback
        self.watch_paths = watch_paths or ["src"]
        self.last_modified: Dict[Any, Any] = {}
        self.observer = Observer()

    def on_modified(self, event: FileSystemEvent) -> None:
        """
        Handle file modification events.

        Args:
            event: File system event
        """
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if file_path.suffix != ".py":
            return

        # Check if file was actually modified (not just accessed)
        try:
            current_mtime = os.path.getmtime(file_path)
            last_mtime = self.last_modified.get(file_path, 0)

            if current_mtime > last_mtime:
                self.last_modified[file_path] = current_mtime
                print(f"🔄 File changed: {file_path}")  # noqa: T201
                time.sleep(0.1)  # Small delay to ensure file is fully written
                self.callback()

        except OSError:
            pass  # File might be temporarily unavailable

    def start(self) -> None:
        """Start watching for file changes."""
        for path in self.watch_paths:
            if os.path.exists(path):
                self.observer.schedule(self, path, recursive=True)
                print(f"👀 Watching for changes in: {path}")  # noqa: T201

        self.observer.start()

    def stop(self) -> None:
        """Stop watching for file changes."""
        self.observer.stop()
        self.observer.join()


def auto_reload(
    callback: Optional[Callable[[], None]] = None,
    watch_paths: Optional[List[str]] = None,
) -> AutoReloadHandler:
    """
    Create and start an auto-reload handler.

    Args:
        callback: Function to call when files change
        watch_paths: List of paths to watch for changes

    Returns:
        AutoReloadHandler instance
    """
    callback = callback or (lambda: None)
    handler = AutoReloadHandler(callback, watch_paths)
    handler.start()
    return handler
