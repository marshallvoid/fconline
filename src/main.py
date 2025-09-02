try:
    import os
    import sys
    import tkinter as tk
    import traceback
    from tkinter import messagebox

    from loguru import logger

    import src.infrastructure.logger  # noqa: F401
    from src.gui.main_window import MainWindow
    from src.services.files import FileManager

    def main() -> None:
        # Create and run main application window
        app = MainWindow()
        app.run()

    if __name__ == "__main__":
        main()

except ImportError as e:
    error_msg = f"{e}\nMake sure you have installed all required dependencies:\npip install -r requirements.txt"
    logger.error(f"Import error: {error_msg}")

    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Import Error", error_msg)
    sys.exit(1)

except Exception as error:
    error_msg = f"Failed to start GUI application: {error}"
    logger.error(error_msg)

    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Error", error_msg)

    # Also write to file as backup
    try:
        config_dir = FileManager.get_configs_dicrectory()
        log_file = os.path.join(config_dir, "errors.log")
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(traceback.format_exc() + "\n")
            f.write(error_msg)

    except Exception:
        pass

    sys.exit(1)
