import typer

from app.core.async_typer import AsyncTyper
from app.core.providers.factory import make_container
from app.core.settings import settings
from app.main.ui.app import run_ui
from app.presentation.cli.license.main import license_commands


class CLIFactory:
    def make(self) -> typer.Typer:
        container = make_container(settings)

        cli_app = AsyncTyper(
            rich_markup_mode="rich",
            context_settings={
                "obj": {
                    "container": container,
                    "settings": settings,
                },
            },
        )

        # Add a callback to prevent single command from being treated as default
        @cli_app.callback()
        def main_callback() -> None:
            """FC Online Automation CLI"""

        self.add_ui_command(app=cli_app)
        self.add_app_commands(app=cli_app)

        return cli_app

    def add_ui_command(self, app: AsyncTyper) -> None:
        @app.command(name="ui")
        def ui_command(ctx: typer.Context) -> None:
            """[green]Run[/green] application UI."""
            ctx_container = ctx.obj["container"]
            ctx_settings = ctx.obj["settings"]
            run_ui(container=ctx_container, settings=ctx_settings)

    def add_app_commands(self, app: AsyncTyper) -> None:
        app.add_typer(license_commands, name="license")
