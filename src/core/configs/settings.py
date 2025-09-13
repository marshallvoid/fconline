from typing import Optional, Tuple, Type

from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


class NonEmptyEnvSource(EnvSettingsSource):
    def __call__(self) -> dict[str, str]:
        data = super().__call__()
        # filter out empty values
        return {k: v for k, v in data.items() if v not in (None, "")}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_nested_delimiter="__",
        nested_model_default_partial_update=False,
    )

    # Application settings
    program_name: str = "FC Online Automation Tool"
    secret_key: str = "secret_key"
    debug: bool = False

    # Discord webhook settings
    discord_developer_webhook_id: Optional[str] = None
    discord_developer_webhook_token: Optional[str] = None
    discord_developer_role_id: Optional[str] = None

    discord_fco_webhook_id: Optional[str] = None
    discord_fco_webhook_token: Optional[str] = None
    discord_fco_webhook_role_id: Optional[str] = None

    # OpenAI settings
    openai_api_key: Optional[str] = None
    openai_model: str = "o3"
    openai_temperature: float = 0.8
    openai_max_retries: int = 2

    # Anthropic settings
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-sonnet-4-20250514"
    anthropic_temperature: float = 0.8
    anthropic_max_retries: int = 2

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
