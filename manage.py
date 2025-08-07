import os
import sys
import tkinter as tk

# from pathlib import Path
from tkinter import messagebox

# from src.auto_reload import enable_auto_reload

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)


try:
    from src.gui import main_gui

    if __name__ == "__main__":
        #   enable_auto_reload(watch_paths=[str(Path(project_root) / "src")])
        main_gui()

except ImportError as e:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(
        "Import Error",
        (
            f"Import error: {e}\n"
            "Make sure you have installed all required dependencies:\n"
            "pip install -r requirements.txt"
        ),
    )
    sys.exit(1)

except Exception as e:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Error", f"Error starting GUI: {e}")
    sys.exit(1)
