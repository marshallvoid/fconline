import asyncio
import sys
import threading
import tkinter as tk
from tkinter import messagebox

from loguru import logger

try:
    from app.core.providers.factory import make_container
    from app.core.settings import settings
    from app.infrastructure.logging import init_logger
    from app.ui.windows.main import MainWindow

    container = make_container(settings=settings)
    init_logger(debug=settings.debug)

    def main() -> None:
        app = MainWindow(container=container, settings=settings)

        # Run async initialization in separate thread
        def run_async_init() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(app.initialize_configurations())
            loop.close()

        init_thread = threading.Thread(target=run_async_init, daemon=False)
        init_thread.start()
        init_thread.join()  # Wait for initialization to complete

        # Initialize UI in main thread (Tkinter requirement)
        app.initialize_ui()

        app.run()

    if __name__ == "__main__":
        main()

except ImportError as e:
    error_msg = f"{e}\nMake sure you have installed all required dependencies:\npip install -r requirements.txt"
    logger.exception(f"Import error: {error_msg}")

    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Import Error", error_msg)
    sys.exit(1)

except Exception as error:
    error_msg = f"Failed to start GUI application: {error}"
    logger.exception(error_msg)

    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Error", error_msg)

    sys.exit(1)
