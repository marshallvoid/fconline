import tkinter as tk

from app.schemas.app_config import Configs
from app.schemas.local_config import LocalConfigs


class BaseHandler:
    def __init__(self, root: tk.Tk, configs: Configs, local_configs: LocalConfigs) -> None:
        self._root = root
        self._app_configs = configs.app_configs
        self._event_configs = configs.event_configs
        self._local_configs = local_configs
