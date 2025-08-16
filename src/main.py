import os
import sys
import tkinter as tk
import traceback
from tkinter import messagebox

from loguru import logger

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    import src.infrastructure.logger  # noqa: F401
    from src.gui.main_window import MainWindow

    if __name__ == "__main__":
        app = MainWindow()
        app.run()

except ImportError as e:
    error_msg = (
        f"Import error: {e}\nMake sure you have installed all required dependencies:\npip install -r requirements.txt"
    )

    logger.error(traceback.format_exc())
    logger.error(error_msg)

    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Import Error", error_msg)
    sys.exit(1)

except Exception as e:
    error_msg = f"Failed to start GUI application: {e}"
    logger.error(traceback.format_exc())
    logger.error(error_msg)

    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Error", error_msg)

    # Also write to file as backup
    try:
        with open("app_error.log", "w") as f:
            f.write(traceback.format_exc() + "\n")
            f.write(error_msg)

    except Exception:
        pass

    sys.exit(1)
