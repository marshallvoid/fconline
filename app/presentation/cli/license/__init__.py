import os
import secrets
from datetime import datetime
from pathlib import Path
from typing import List, Set

import requests
import rich
import typer
from dotenv import load_dotenv

from app.schemas.app_config import Configs

load_dotenv()

github_token = os.getenv("GITHUB_TOKEN")
gist_id = os.getenv("GIST_ID")
gist_filename = os.getenv("GIST_FILENAME")


def _get_gist_headers() -> dict:
    return {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def generate_multiple_licenses(count: int) -> list[str]:
    licenses: Set[str] = set()
    while len(licenses) < count:
        licenses.add(generate_license_key())
    return sorted(licenses)


def generate_license_key() -> str:
    segments = []
    for _ in range(4):
        # Generate 4 random uppercase alphanumeric characters
        segment = "".join(secrets.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(4))
        segments.append(segment)

    return f"FCOL-{'-'.join(segments)}"


def save_licenses_to_file(licenses: List[str], filename: str = ".licenses") -> Path:
    filepath = Path(filename)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with filepath.open("a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for license_key in licenses:
            f.write(f"{timestamp} - {license_key}\n")

    return filepath


def fetch_gist_config() -> Configs:
    if not all([github_token, gist_id, gist_filename]):
        rich.print("❌ [bold red]Missing environment variables (GITHUB_TOKEN, GIST_ID, GIST_FILENAME)[/bold red]")
        raise typer.Exit(1)

    rich.print("\n📡 [cyan]Fetching current Gist data...[/cyan]")

    response = requests.get(f"https://api.github.com/gists/{gist_id}", headers=_get_gist_headers(), timeout=10)
    response.raise_for_status()

    gist_data = response.json()
    file_content = gist_data["files"][gist_filename]["content"]
    config = Configs.model_validate_json(file_content)

    return config


def update_gist_config(config: Configs) -> None:
    if not all([github_token, gist_id, gist_filename]):
        rich.print("❌ [bold red]Missing environment variables (GITHUB_TOKEN, GIST_ID, GIST_FILENAME)[/bold red]")
        raise typer.Exit(1)

    rich.print("\n🔄 [cyan]Updating Gist...[/cyan]")

    response = requests.patch(
        f"https://api.github.com/gists/{gist_id}",
        headers=_get_gist_headers(),
        json={
            "files": {
                gist_filename: {
                    "content": config.model_dump_json(
                        indent=2,
                        exclude_none=True,
                    ),
                },
            },
        },
        timeout=10,
    )
    response.raise_for_status()

    rich.print("✅ [bold green]Successfully updated Gist![/bold green]")
