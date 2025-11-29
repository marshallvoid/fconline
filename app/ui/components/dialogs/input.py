import tkinter as tk
from tkinter import simpledialog
from typing import Optional


class CustomInputDialog(simpledialog.Dialog):
    def __init__(
        self,
        title: str,
        prompt: str,
        parent: Optional[tk.Misc] = None,
        initialvalue: Optional[str] = None,
        width: int = 60,
    ) -> None:
        self.prompt = prompt
        self.initialvalue = initialvalue
        self.width = width
        self.result: Optional[str] = None
        super().__init__(parent, title)

    def body(self, master: tk.Frame) -> tk.Entry:
        tk.Label(master, text=self.prompt).pack(padx=10, pady=(10, 5), anchor="w")

        self.entry = tk.Entry(master, width=self.width)
        self.entry.pack(padx=10, pady=(0, 10))

        if self.initialvalue:
            self.entry.insert(0, self.initialvalue)
            self.entry.select_range(0, tk.END)

        return self.entry

    def apply(self) -> None:
        self.result = self.entry.get()


def ask_string_custom(
    title: str,
    prompt: str,
    parent: Optional[tk.Misc] = None,
    initialvalue: Optional[str] = None,
    width: int = 60,
) -> Optional[str]:
    dialog = CustomInputDialog(
        title=title,
        prompt=prompt,
        parent=parent,
        initialvalue=initialvalue,
        width=width,
    )
    return dialog.result
