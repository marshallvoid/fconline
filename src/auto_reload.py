import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from loguru import logger

try:
    from watchdog.events import DirModifiedEvent, FileModifiedEvent, FileSystemEventHandler
    from watchdog.observers import Observer

    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False


class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, callback: Callable[[], None], extensions: tuple = (".py",)) -> None:
        self.callback = callback
        self.extensions = extensions
        self.last_modified: Dict[Any, Any] = {}
        self.debounce_time = 2  # Seconds to wait before triggering reload

    def on_modified(self, event: DirModifiedEvent | FileModifiedEvent) -> None:
        if event.is_directory:
            return

        file_path = event.src_path
        if not any(file_path.endswith(ext) for ext in self.extensions):
            return

        # Debounce rapid file changes
        current_time = time.time()
        if file_path in self.last_modified:
            if current_time - self.last_modified[file_path] < self.debounce_time:
                return

        self.last_modified[file_path] = current_time

        # Schedule callback after debounce period
        threading.Timer(self.debounce_time, self.callback).start()


class AutoReloader:
    def __init__(self, callback: Callable[[], None]) -> None:
        self.callback = callback
        self.observer: Optional[Observer] = None  # type: ignore
        self.watching = False

    def start_watching(self, paths: Optional[list[str]] = None) -> bool:
        """Start watching for file changes"""
        if not WATCHDOG_AVAILABLE:
            logger.warning("watchdog not available. Install with: pip install watchdog")
            return False

        if self.watching:
            return True

        if paths is None:
            # Default to watching the src directory
            current_dir = Path(__file__).parent
            paths = [str(current_dir)]

        try:
            self.observer = Observer()
            if not self.observer:
                logger.error("Failed to create Observer instance")
                return False

            handler = FileChangeHandler(self.callback)

            for path in paths:
                if os.path.exists(path):
                    self.observer.schedule(handler, path, recursive=True)
                    logger.info("Watching for changes in: {}", path)

            self.observer.start()
            self.watching = True
            return True

        except Exception as e:
            logger.error("Failed to start file watcher: {}", e)
            return False

    def stop_watching(self) -> None:
        """Stop watching for file changes"""
        if self.observer and self.watching:
            self.observer.stop()
            self.observer.join()
            self.watching = False
            logger.info("Stopped watching for file changes")

    def restart_application(self) -> None:
        """Restart the current Python application"""
        logger.info("Restarting application...")

        # Stop watching before restart
        self.stop_watching()

        # Get current script path and arguments
        script_path = sys.argv[0]
        args = sys.argv[1:]

        # Restart with same arguments
        os.execv(sys.executable, [sys.executable, script_path] + args)


def enable_auto_reload(
    watch_paths: Optional[list[str]] = None,
    callback: Optional[Callable[[], None]] = None,
) -> AutoReloader:
    """
    Enable auto-reload functionality

    Args:
        callback: Function to call when files change (default: restart application)
        watch_paths: List of paths to watch (default: current src directory)

    Returns:
        AutoReloader instance
    """
    if callback is None:
        # Create a dummy reloader for the static method call
        dummy_reloader = AutoReloader(lambda: None)
        callback = dummy_reloader.restart_application

    reloader = AutoReloader(callback)

    if reloader.start_watching(watch_paths):
        logger.info("Auto-reload enabled! The application will restart when you save Python files.")
    else:
        logger.error("Could not enable auto-reload")

    return reloader
