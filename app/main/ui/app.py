from dishka import AsyncContainer

from app.core.settings import Settings
from app.main.ui.factory import UIFactory


def run_ui(container: AsyncContainer, settings: Settings) -> None:
    ui_factory = UIFactory(container=container, settings=settings)
    ui_app = ui_factory.make()
    ui_app.run()
