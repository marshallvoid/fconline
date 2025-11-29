from app.main.cli.factory import CLIFactory


def run_cli() -> None:
    cli_factory = CLIFactory()
    cli_app = cli_factory.make()
    cli_app()
