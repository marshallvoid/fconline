import sys
import tkinter as tk
from tkinter import messagebox

from loguru import logger

try:
    from src.core.configs import settings
    from src.core.providers.factory import make_container
    from src.gui.main_window import MainWindow
    from src.infrastructure.logging import init_logger

    container = make_container(settings=settings)

    init_logger(debug=settings.debug)

    def main() -> None:
        # Create and run main application window
        app = MainWindow(container=container, settings=settings)
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
