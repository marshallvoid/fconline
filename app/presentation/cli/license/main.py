import json
from typing import Annotated, List

import requests
import rich
import typer
from rich.table import Table

from app.core.async_typer import AsyncTyper
from app.presentation.cli.license import (
    fetch_gist_config,
    generate_multiple_licenses,
    save_licenses_to_file,
    update_gist_config,
)
from app.presentation.cli.license.enums import LicenseType

license_commands = AsyncTyper(
    name="license",
    help="[yellow]Manage[/yellow] License Keys",
)


@license_commands.command()
async def check(
    ctx: typer.Context,
    type: Annotated[
        LicenseType,
        typer.Argument(help="License keys to unblock"),
    ] = LicenseType.BOTH,
) -> None:
    """[green]Display[/green] valid, blocked, or both types of license keys."""
    rich.print("\n✅ [bold cyan]Display License Keys[/bold cyan]")
    rich.print("=" * 50)

    try:
        config = fetch_gist_config()

        valid_licenses = set(config.app_configs.valid_licenses)
        blocked_licenses = set(config.app_configs.blocked_licenses)

        table = Table()
        table.add_column("#", style="cyan", justify="right")
        table.add_column("License Key", style="green")
        table.add_column("Status", style="magenta")

        if type == LicenseType.VALID:
            table.title = f"Valid Licenses ({len(valid_licenses)})"
            for i, license_key in enumerate(valid_licenses, 1):
                table.add_row(str(i), license_key, "[green]Valid[/green]")
            rich.print(table)

        elif type == LicenseType.BLOCKED:
            table.title = f"Blocked Licenses ({len(blocked_licenses)})"
            for i, license_key in enumerate(blocked_licenses, 1):
                table.add_row(str(i), license_key, "[red]Blocked[/red]")
            rich.print(table)

        elif type == LicenseType.BOTH:
            if valid_licenses:
                table_valid = Table(title=f"Valid Licenses ({len(valid_licenses)})")
                table_valid.add_column("#", style="cyan", justify="right")
                table_valid.add_column("License Key", style="green")
                for i, license_key in enumerate(valid_licenses, 1):
                    table_valid.add_row(str(i), license_key)
                rich.print(table_valid)
            else:
                rich.print("[yellow]No valid licenses found.[/yellow]")

            rich.print("\n")  # Separator between tables

            if blocked_licenses:
                table_blocked = Table(title=f"Blocked Licenses ({len(blocked_licenses)})")
                table_blocked.add_column("#", style="cyan", justify="right")
                table_blocked.add_column("License Key", style="green")
                for i, license_key in enumerate(blocked_licenses, 1):
                    table_blocked.add_row(str(i), license_key)
                rich.print(table_blocked)
            else:
                rich.print("[yellow]No blocked licenses found.[/yellow]")

        rich.print("=" * 50)

    except requests.exceptions.RequestException as e:
        rich.print(f"❌ [bold red]Failed to fetch Gist config: {e}[/bold red]")
        raise typer.Exit(1)

    except Exception as e:
        msg = getattr(e, "detail", str(e))
        rich.print(f"❌ [bold red]Failed to display licenses - Error: {msg}[/bold red]")
        raise typer.Exit(1)


@license_commands.command()
async def generate(
    ctx: typer.Context,
    count: Annotated[
        int,
        typer.Argument(help="Number of licenses to generate"),
    ] = 1,
    no_upload: Annotated[
        bool,
        typer.Option("--no-upload", help="Skip uploading to GitHub Gist"),
    ] = False,
) -> None:
    """[green]Generate[/green] license keys, automatically save to file and upload to Gist."""
    rich.print("\n🔑 [bold cyan]FC Online License Generator[/bold cyan]")
    rich.print("=" * 50)

    if count < 1:
        rich.print("❌ [bold red]Count must be at least 1[/bold red]")
        raise typer.Exit(1)

    if count > 1000:
        rich.print("⚠️  [yellow]Generating more than 1000 licenses. This may take a while...[/yellow]")

    try:
        # Generate licenses
        rich.print(f"\n🔄 [cyan]Generating {count} license(s)...[/cyan]")
        licenses = generate_multiple_licenses(count=count)

        # Display licenses in a table
        table = Table(title=f"Generated {len(licenses)} License(s)")
        table.add_column("#", style="cyan", justify="right")
        table.add_column("License Key", style="green")

        for i, license_key in enumerate(licenses, 1):
            table.add_row(str(i), license_key)

        rich.print(table)

        # Save to local file
        filepath = save_licenses_to_file(licenses=licenses)
        rich.print(f"\n✅ [bold green]Licenses saved to: {filepath}[/bold green]")

        # Upload to Gist automatically
        if not no_upload:
            added, skipped = upload_to_gist(licenses)
            if added > 0 or skipped > 0:
                rich.print("\n📊 [bold]Summary:[/bold]")
                rich.print(f"  ✅ [green]Added: {added}[/green]")
                rich.print(f"  ⚠️  [yellow]Skipped: {skipped}[/yellow]")

        rich.print("=" * 50)

    except Exception as e:
        msg = getattr(e, "detail", str(e))
        rich.print(f"❌ [bold red]Failed to generate licenses - Error: {msg}[/bold red]")
        raise typer.Exit(1)


def upload_to_gist(licenses: list[str]) -> tuple[int, int]:
    """Upload licenses to GitHub Gist. Returns (added_count, skipped_count)."""
    try:
        config = fetch_gist_config()

        current_licenses = set(config.app_configs.valid_licenses)
        rich.print(f"📊 [cyan]Current valid licenses: {len(current_licenses)}[/cyan]")

        added = []
        skipped = []

        for license_key in licenses:
            if license_key in current_licenses:
                skipped.append(license_key)
                rich.print(f"⚠️  [yellow]Skipped (already exists): {license_key}[/yellow]")
            else:
                current_licenses.add(license_key)
                added.append(license_key)
                rich.print(f"✅ [green]Added: {license_key}[/green]")

        if not added:
            rich.print("\n⚠️  [yellow]No new licenses to upload (all already exist)[/yellow]")
            return 0, len(skipped)

        config.app_configs.valid_licenses = sorted(current_licenses)

        rich.print(f"\n🔄 [cyan]Uploading {len(added)} new license(s) to Gist...[/cyan]")
        update_gist_config(config=config)

        rich.print(f"📊 [cyan]Total valid licenses: {len(current_licenses)}[/cyan]")

        return len(added), len(skipped)

    except requests.exceptions.RequestException as e:
        rich.print(f"❌ [bold red]Failed to update Gist: {e}[/bold red]")
        return 0, 0

    except (KeyError, json.JSONDecodeError) as e:
        rich.print(f"❌ [bold red]Failed to parse Gist data: {e}[/bold red]")
        return 0, 0


@license_commands.command()
async def remove(
    ctx: typer.Context,
    licenses: Annotated[
        List[str],
        typer.Argument(help="License keys to remove from valid licenses"),
    ],
) -> None:
    """[red]Remove[/red] license keys from valid licenses list."""
    rich.print("\n🗑️  [bold cyan]Remove License Keys[/bold cyan]")
    rich.print("=" * 50)

    try:
        config = fetch_gist_config()

        valid_licenses = set(config.app_configs.valid_licenses)
        rich.print(f"📊 [cyan]Current valid licenses: {len(valid_licenses)}[/cyan]")

        removed: List[str] = []
        not_found: List[str] = []

        for license_key in licenses:
            if license_key in valid_licenses:
                valid_licenses.remove(license_key)
                removed.append(license_key)
                rich.print(f"✅ [green]Removed: {license_key}[/green]")
            else:
                not_found.append(license_key)
                rich.print(f"❌ [red]Not found: {license_key}[/red]")

        if not removed:
            rich.print("\n⚠️  [yellow]No licenses were removed[/yellow]")
            raise typer.Exit(0)

        config.app_configs.valid_licenses = sorted(valid_licenses)
        update_gist_config(config=config)

        rich.print(f"📊 [cyan]Total valid licenses: {len(valid_licenses)}[/cyan]")
        rich.print("\n📊 [bold]Summary:[/bold]")
        rich.print(f"  ✅ [green]Removed: {len(removed)}[/green]")
        rich.print(f"  ❌ [red]Not found: {len(not_found)}[/red]")
        rich.print("=" * 50)

    except requests.exceptions.RequestException as e:
        rich.print(f"❌ [bold red]Failed to update Gist: {e}[/bold red]")
        raise typer.Exit(1)

    except Exception as e:
        msg = getattr(e, "detail", str(e))
        rich.print(f"❌ [bold red]Failed to remove licenses - Error: {msg}[/bold red]")
        raise typer.Exit(1)


@license_commands.command()
async def block(
    ctx: typer.Context,
    licenses: Annotated[
        List[str],
        typer.Argument(help="License keys to block"),
    ],
) -> None:
    """[yellow]Block[/yellow] license keys by adding them to blocked licenses list."""
    rich.print("\n🚫 [bold cyan]Block License Keys[/bold cyan]")
    rich.print("=" * 50)

    try:
        config = fetch_gist_config()

        valid_licenses = set(config.app_configs.valid_licenses)
        blocked_licenses = set(config.app_configs.blocked_licenses)
        rich.print(f"📊 [cyan]Current blocked licenses: {len(blocked_licenses)}[/cyan]")

        added: List[str] = []
        already_blocked: List[str] = []

        for license_key in licenses:
            if license_key in blocked_licenses:
                already_blocked.append(license_key)
                rich.print(f"⚠️  [yellow]Already blocked: {license_key}[/yellow]")
            else:
                blocked_licenses.add(license_key)
                added.append(license_key)
                rich.print(f"✅ [green]Blocked: {license_key}[/green]")

        if not added:
            rich.print("\n⚠️  [yellow]No new licenses were blocked[/yellow]")
            raise typer.Exit(0)

        config.app_configs.valid_licenses = sorted(valid_licenses - set(licenses))
        config.app_configs.blocked_licenses = sorted(blocked_licenses)
        update_gist_config(config=config)

        rich.print(f"📊 [cyan]Total blocked licenses: {len(blocked_licenses)}[/cyan]")
        rich.print("\n📊 [bold]Summary:[/bold]")
        rich.print(f"  ✅ [green]Blocked: {len(added)}[/green]")
        rich.print(f"  ⚠️  [yellow]Already blocked: {len(already_blocked)}[/yellow]")
        rich.print("=" * 50)

    except requests.exceptions.RequestException as e:
        rich.print(f"❌ [bold red]Failed to update Gist: {e}[/bold red]")
        raise typer.Exit(1)

    except Exception as e:
        msg = getattr(e, "detail", str(e))
        rich.print(f"❌ [bold red]Failed to block licenses - Error: {msg}[/bold red]")
        raise typer.Exit(1)


@license_commands.command()
async def unblock(
    ctx: typer.Context,
    licenses: Annotated[
        List[str],
        typer.Argument(help="License keys to unblock"),
    ],
) -> None:
    """[green]Unblock[/green] license keys by removing them from blocked licenses list."""
    rich.print("\n✅ [bold cyan]Unblock License Keys[/bold cyan]")
    rich.print("=" * 50)

    try:
        config = fetch_gist_config()

        blocked_licenses = set(config.app_configs.blocked_licenses)
        rich.print(f"📊 [cyan]Current blocked licenses: {len(blocked_licenses)}[/cyan]")

        removed: List[str] = []
        not_blocked: List[str] = []

        for license_key in licenses:
            if license_key in blocked_licenses:
                blocked_licenses.remove(license_key)
                removed.append(license_key)
                rich.print(f"✅ [green]Unblocked: {license_key}[/green]")
            else:
                not_blocked.append(license_key)
                rich.print(f"⚠️  [yellow]Not blocked: {license_key}[/yellow]")

        if not removed:
            rich.print("\n⚠️  [yellow]No licenses were unblocked[/yellow]")
            raise typer.Exit(0)

        config.app_configs.valid_licenses.extend(removed)
        config.app_configs.blocked_licenses = sorted(blocked_licenses)
        update_gist_config(config=config)

        rich.print(f"📊 [cyan]Total blocked licenses: {len(blocked_licenses)}[/cyan]")
        rich.print("\n📊 [bold]Summary:[/bold]")
        rich.print(f"  ✅ [green]Unblocked: {len(removed)}[/green]")
        rich.print(f"  ⚠️  [yellow]Not blocked: {len(not_blocked)}[/yellow]")
        rich.print("=" * 50)

    except requests.exceptions.RequestException as e:
        rich.print(f"❌ [bold red]Failed to update Gist: {e}[/bold red]")
        raise typer.Exit(1)

    except Exception as e:
        msg = getattr(e, "detail", str(e))
        rich.print(f"❌ [bold red]Failed to unblock licenses - Error: {msg}[/bold red]")
        raise typer.Exit(1)
