import tkinter as tk

from app.core.settings import Settings
from app.schemas.configs import Config


class BaseHandler:
    def __init__(self, settings: Settings, root: tk.Tk, configs: Config) -> None:
        self._settings = settings
        self._root = root
        self._configs = configs
