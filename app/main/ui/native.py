try:
    import sys
    import tkinter as tk
    from tkinter import messagebox

    from loguru import logger

    from app.core.providers.factory import make_container
    from app.core.settings import settings
    from app.infrastructure.logging import init_logger
    from app.main.ui.app import run_ui

    container = make_container(settings=settings)
    init_logger(debug=settings.debug)

    def main() -> None:
        run_ui(container=container, settings=settings)

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
