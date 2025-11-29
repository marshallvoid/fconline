import asyncio
import threading

from dishka import AsyncContainer

from app.core.settings import Settings
from app.ui.windows.main import MainWindow


class UIFactory:
    def __init__(self, container: AsyncContainer, settings: Settings) -> None:
        self._container = container
        self._settings = settings

    def make(self) -> MainWindow:
        ui_app = MainWindow(container=self._container, settings=self._settings)

        # Run async initialization in separate thread
        def _run_async_init() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(ui_app.initialize_configurations())
            loop.close()

        init_thread = threading.Thread(target=_run_async_init, daemon=False)
        init_thread.start()
        init_thread.join()  # Wait for initialization to complete

        # Initialize UI in main thread (Tkinter requirement)
        ui_app.initialize_ui()

        return ui_app
