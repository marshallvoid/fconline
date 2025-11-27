import sys
from functools import lru_cache
from pathlib import Path
from typing import Optional, Tuple, Type

from loguru import logger
from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


def get_env_file_path() -> Path:
    """Get the correct path to .env file, handling PyInstaller bundled apps."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # Running as PyInstaller bundle
        base_path = Path(sys._MEIPASS)
        logger.debug(f"[PyInstaller] Loading .env from bundle: {base_path}")
    else:
        # Running in development
        base_path = Path(__file__).parent.parent.parent
        logger.debug(f"[Development] Loading .env from: {base_path}")

    env_file = base_path / ".env"
    logger.info(f"[Settings] .env file path: {env_file}")
    logger.info(f"[Settings] .env file exists: {env_file.exists()}")

    return env_file


class NonEmptyEnvSource(EnvSettingsSource):
    def __call__(self) -> dict[str, str]:
        data = super().__call__()
        # filter out empty values
        return {k: v for k, v in data.items() if v not in (None, "")}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=str(get_env_file_path()),
        env_nested_delimiter="__",
        nested_model_default_partial_update=False,
    )

    # Application settings
    program_name: str = "FC Online Automation Tool"
    secret_key: str = "secret_key"
    debug: bool = False

    # Github API settings
    release_url: str = "github_api_url"

    # Internal API settings
    internal_api_host: Optional[str] = None

    # Discord webhook settings
    discord_webhook_id: Optional[str] = None
    discord_webhook_token: Optional[str] = None
    discord_role_id: Optional[str] = None

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        env_file = get_env_file_path()
        source = [
            init_settings,
            NonEmptyEnvSource(settings_cls=settings_cls),
            DotEnvSettingsSource(settings_cls=settings_cls, env_file=str(env_file)),
            file_secret_settings,
        ]

        return (*source,)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
