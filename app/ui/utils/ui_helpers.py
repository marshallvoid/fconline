import contextlib
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, List, Optional, Tuple


class UIHelpers:
    @staticmethod
    def setup_focus_management(root_or_frame: tk.Misc, notebook: ttk.Notebook) -> None:
        """Setup focus management for a notebook to prevent text selection issues.

        Args:
            root_or_frame: Root window or frame for scheduling after callbacks
            notebook: Notebook widget to manage focus for
        """
        focus_after_id: Optional[str] = None

        def schedule_focus_current_tab() -> None:
            nonlocal focus_after_id

            def _focus_current_tab() -> None:
                with contextlib.suppress(tk.TclError):
                    current = notebook.nametowidget(name=notebook.select())
                    if current and isinstance(current, (tk.Frame, ttk.Frame)):
                        current.focus_set()

            if focus_after_id:
                with contextlib.suppress(Exception):
                    root_or_frame.after_cancel(id=focus_after_id)
                focus_after_id = None

            focus_after_id = root_or_frame.after(ms=10, func=_focus_current_tab)

        def on_notebook_tab_changed() -> None:
            with contextlib.suppress(tk.TclError):
                current = notebook.nametowidget(name=notebook.select())
                if current and isinstance(current, (tk.Frame, ttk.Frame)):
                    current.focus_set()

            schedule_focus_current_tab()

        notebook.bind(sequence="<<NotebookTabChanged>>", func=lambda _: on_notebook_tab_changed())
        notebook.bind(sequence="<ButtonRelease-1>", func=lambda _: schedule_focus_current_tab())
        root_or_frame.after_idle(func=schedule_focus_current_tab)

    @staticmethod
    def bind_enter_key(widgets: List[tk.Widget], callback: Callable[[], None]) -> None:
        """Bind Enter key to multiple widgets.

        Args:
            widgets: List of widgets to bind Enter key to
            callback: Callback to execute on Enter key press
        """
        for widget in widgets:
            widget.bind("<Return>", lambda _: callback())

    @staticmethod
    def create_scrollable_frame(
        parent: tk.Misc,
        bg: str = "#1f2937",
        padding: int = 10,
    ) -> Tuple[tk.Canvas, ttk.Scrollbar, ttk.Frame]:
        """Create a scrollable frame using canvas.

        Args:
            parent: Parent widget
            bg: Background color
            padding: Frame padding

        Returns:
            Tuple of (Canvas, Scrollbar, Scrollable Frame)
        """
        canvas = tk.Canvas(master=parent, bg=bg, highlightthickness=0)
        scrollbar = ttk.Scrollbar(master=parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(master=canvas, padding=padding)

        scrollable_frame.bind(
            sequence="<Configure>",
            func=lambda _: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def _update_scroll_region(event: tk.Event) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Update the width of the scrollable frame to match canvas
            if canvas.find_all():
                canvas.itemconfig(tagOrId=canvas.find_all()[0], width=event.width)

        canvas.bind(sequence="<Configure>", func=_update_scroll_region)

        return canvas, scrollbar, scrollable_frame

    @staticmethod
    def prevent_text_selection(text_widget: tk.Text) -> None:
        """Prevent text selection in a Text widget.

        Args:
            text_widget: Text widget to prevent selection in
        """
        text_widget.bind(sequence="<Button-1>", func=lambda _: text_widget.tag_remove("sel", "1.0", tk.END))
        text_widget.bind(sequence="<B1-Motion>", func=lambda _: text_widget.tag_remove("sel", "1.0", tk.END))
        text_widget.bind(sequence="<Double-Button-1>", func=lambda _: text_widget.tag_remove("sel", "1.0", tk.END))

    @staticmethod
    def show_blocking_error(root: tk.Tk, message: str) -> None:
        """Show blocking error dialog and close application.

        Args:
            root: Root window to close
            message: Error message to display
        """
        messagebox.showerror("Access Denied", message)
        root.destroy()
