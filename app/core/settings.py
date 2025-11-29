from functools import lru_cache
from typing import Any, Dict, Tuple, Type

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


def get_build_config_values() -> Dict[str, Any]:
    try:
        from app.core import build_config  # type: ignore[attr-defined]

        # Dynamically get all UPPERCASE attributes from build_config
        config_values = {}
        for attr_name in dir(build_config):
            # Only process UPPERCASE attributes (constants)
            if attr_name.isupper() and not attr_name.startswith("_"):
                value = getattr(build_config, attr_name)
                # Convert UPPER_CASE to lower_case for pydantic field names
                field_name = attr_name.lower()
                config_values[field_name] = value

        return config_values

    except ImportError:
        return {}


class NonEmptyEnvSource(EnvSettingsSource):
    def __call__(self) -> dict[str, str]:
        data = super().__call__()
        # filter out empty values
        return {k: v for k, v in data.items() if v not in (None, "")}


class DiscordConfig(BaseSettings):
    # Format: {"channel_name": {"id": "webhook_id", "token": "webhook_token"}}
    webhooks: Dict[str, Dict[str, str]] = Field(default_factory=dict)

    # Format: {"role_name": "role_id"}
    roles: Dict[str, str] = Field(default_factory=dict)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_nested_delimiter="__",
        nested_model_default_partial_update=False,
    )

    # Application configuration
    program_name: str = Field(default="FC Online Automation", description="Application name")
    secret_key: str = Field(default="secret_key", description="Secret key for authentication")
    debug: bool = Field(default=False, description="Debug mode")

    # Github API configuration
    gist_url: str = Field(
        default="https://gist.githubusercontent.com/{username}/{gist_id}/raw/{gist_name}",
        description="GitHub Gist URL for application configuration and license validation",
    )
    release_url: str = Field(
        default="https://api.github.com/repos/{username}/{repo_name}/releases/latest",
        description="GitHub API URL for checking releases",
    )

    # Discord configuration
    discord: DiscordConfig = Field(default_factory=DiscordConfig, description="Discord configuration")

    def __init__(self, **kwargs: Any) -> None:
        """Initialize settings, prioritizing build_config.py over .env file."""
        # Get build config values (production) or empty dict (development)
        build_values = get_build_config_values()

        # Merge: build_config.py takes precedence over kwargs
        merged_values = {**build_values, **kwargs}

        super().__init__(**merged_values)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        source = [
            init_settings,
            NonEmptyEnvSource(settings_cls=settings_cls),
            DotEnvSettingsSource(settings_cls=settings_cls, env_file=".env"),
            file_secret_settings,
        ]

        return (*source,)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
