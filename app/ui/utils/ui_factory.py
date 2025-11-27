import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict, List, Optional, Tuple


class UIFactory:
    @staticmethod
    def create_label_frame(parent: tk.Misc, text: str, padding: int = 10, **kwargs: Any) -> ttk.LabelFrame:
        """Create a standardized LabelFrame.

        Args:
            parent: Parent widget
            text: Frame label text
            padding: Frame padding
            **kwargs: Additional ttk.LabelFrame arguments

        Returns:
            Configured LabelFrame widget
        """
        return ttk.LabelFrame(master=parent, text=text, padding=padding, **kwargs)

    @staticmethod
    def create_button(
        parent: tk.Misc,
        text: str,
        command: Optional[Callable[[], None]] = None,
        style: Optional[str] = None,
        width: Optional[int] = None,
        state: str = "normal",
        **kwargs: Any,
    ) -> ttk.Button:
        """Create a standardized button.

        Args:
            parent: Parent widget
            text: Button text
            command: Button command callback
            style: Button style (e.g., "Accent.TButton")
            width: Button width
            state: Button state ("normal", "disabled")
            **kwargs: Additional ttk.Button arguments

        Returns:
            Configured Button widget
        """
        button_kwargs: Dict[str, Any] = {"master": parent, "text": text, "state": state}

        if command:
            button_kwargs["command"] = command

        if style:
            button_kwargs["style"] = style

        if width:
            button_kwargs["width"] = width

        button_kwargs.update(kwargs)
        return ttk.Button(**button_kwargs)

    @staticmethod
    def create_entry(
        parent: tk.Misc,
        textvariable: Optional[tk.StringVar] = None,
        width: int = 25,
        font: Tuple[str, int] = ("Arial", 12),
        show: Optional[str] = None,
        validate: Optional[str] = None,
        validatecommand: Optional[Tuple[Any, ...]] = None,
        **kwargs: Any,
    ) -> ttk.Entry:
        """Create a standardized entry widget.

        Args:
            parent: Parent widget
            textvariable: Variable to bind to entry
            width: Entry width
            font: Entry font
            show: Character to show instead of actual text (for passwords)
            validate: Validation mode
            validatecommand: Validation command
            **kwargs: Additional ttk.Entry arguments

        Returns:
            Configured Entry widget
        """
        entry_kwargs: Dict[str, Any] = {"master": parent, "width": width, "font": font}

        if textvariable:
            entry_kwargs["textvariable"] = textvariable

        if show:
            entry_kwargs["show"] = show

        if validate:
            entry_kwargs["validate"] = validate

        if validatecommand:
            entry_kwargs["validatecommand"] = validatecommand

        entry_kwargs.update(kwargs)
        return ttk.Entry(**entry_kwargs)

    @staticmethod
    def create_combobox(
        parent: tk.Misc,
        textvariable: Optional[tk.StringVar] = None,
        values: Optional[List[str]] = None,
        width: int = 25,
        font: Tuple[str, int] = ("Arial", 12),
        state: str = "readonly",
        **kwargs: Any,
    ) -> ttk.Combobox:
        """Create a standardized combobox.

        Args:
            parent: Parent widget
            textvariable: Variable to bind to combobox
            values: List of combobox values
            width: Combobox width
            font: Combobox font
            state: Combobox state
            **kwargs: Additional ttk.Combobox arguments

        Returns:
            Configured Combobox widget
        """
        combo_kwargs: Dict[str, Any] = {"master": parent, "width": width, "font": font, "state": state}

        if textvariable:
            combo_kwargs["textvariable"] = textvariable

        if values:
            combo_kwargs["values"] = values

        combo_kwargs.update(kwargs)
        return ttk.Combobox(**combo_kwargs)

    @staticmethod
    def create_text_widget(
        parent: tk.Misc,
        height: int = 10,
        wrap: str = tk.WORD,
        font: Tuple[str, int] = ("Arial", 12),
        bg: str = "#2b2b2b",
        fg: str = "#e0e0e0",
        state: str = "normal",
        with_scrollbar: bool = True,
        **kwargs: Any,
    ) -> Tuple[tk.Text, Optional[ttk.Scrollbar]]:
        """Create a text widget with optional scrollbar.

        Args:
            parent: Parent widget
            height: Text widget height
            wrap: Text wrapping mode
            font: Text font
            bg: Background color
            fg: Foreground color
            state: Widget state
            with_scrollbar: Whether to create scrollbar
            **kwargs: Additional tk.Text arguments

        Returns:
            Tuple of (Text widget, Scrollbar or None)
        """
        text_kwargs: Dict[str, Any] = {
            "master": parent,
            "wrap": wrap,
            "height": height,
            "font": font,
            "bg": bg,
            "fg": fg,
            "relief": "flat",
            "borderwidth": 0,
            "state": state,
            "insertbackground": fg,
            "selectbackground": "#404040",
            "selectforeground": "#ffffff",
        }
        text_kwargs.update(kwargs)

        text_widget = tk.Text(**text_kwargs)

        scrollbar = None
        if with_scrollbar:
            scrollbar = ttk.Scrollbar(master=parent, orient="vertical", command=text_widget.yview)
            text_widget.configure(yscrollcommand=scrollbar.set)

        return text_widget, scrollbar

    @staticmethod
    def create_form_row(
        parent: tk.Misc,
        label_text: str,
        widget_type: str = "entry",
        label_width: int = 15,
        label_font: Tuple[str, int] = ("Arial", 12),
        **widget_kwargs: Any,
    ) -> Tuple[ttk.Frame, tk.Widget]:
        """Create a form row with label and input widget.

        Args:
            parent: Parent widget
            label_text: Label text
            widget_type: Type of widget ("entry", "combobox", "text")
            label_width: Label width
            label_font: Label font
            **widget_kwargs: Arguments to pass to widget creation

        Returns:
            Tuple of (Frame containing the row, Input widget)
        """
        frame = ttk.Frame(master=parent)

        label = ttk.Label(master=frame, text=label_text, width=label_width, font=label_font)
        label.pack(side="left")

        if widget_type == "entry":
            widget = UIFactory.create_entry(parent=frame, **widget_kwargs)
        elif widget_type == "combobox":
            widget = UIFactory.create_combobox(parent=frame, **widget_kwargs)
        elif widget_type == "text":
            widget, _ = UIFactory.create_text_widget(parent=frame, with_scrollbar=False, **widget_kwargs)
        else:
            msg = f"Unknown widget type: {widget_type}"
            raise ValueError(msg)

        widget.pack(side="left", padx=(10, 0), fill="x", expand=True)

        return frame, widget

    @staticmethod
    def create_button_group(
        parent: tk.Misc,
        buttons: List[Dict[str, Any]],
        orientation: str = "horizontal",
        spacing: int = 5,
    ) -> Tuple[ttk.Frame, List[ttk.Button]]:
        """Create a group of buttons.

        Args:
            parent: Parent widget
            buttons: List of button configurations (dicts with text, command, etc.)
            orientation: "horizontal" or "vertical"
            spacing: Spacing between buttons

        Returns:
            Tuple of (Frame containing buttons, List of button widgets)
        """
        frame = ttk.Frame(master=parent)
        button_widgets = []

        for i, btn_config in enumerate(buttons):
            btn = UIFactory.create_button(parent=frame, **btn_config)

            if orientation == "horizontal":
                padx = (0, spacing) if i < len(buttons) - 1 else 0
                btn.pack(side="left", fill="x", expand=True, padx=padx)
            else:
                pady = (0, spacing) if i < len(buttons) - 1 else 0
                btn.pack(fill="x", pady=pady)

            button_widgets.append(btn)

        return frame, button_widgets
