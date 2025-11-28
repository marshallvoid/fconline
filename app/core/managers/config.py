import json
import os
from typing import Any, Dict

from loguru import logger

from app.core.managers.crypto import crypto_mgr
from app.core.managers.file import file_mgr
from app.schemas.configs import Config
from app.utils.decorators.singleton import singleton


@singleton
class ConfigManager:
    def save_configs(self, configs: Config) -> None:
        try:
            encrypted_configs: Dict[str, Any] = {
                **configs.model_dump(mode="json", exclude={"accounts", "notifications"}),
                "accounts": [
                    {
                        "username": crypto_mgr.encrypt_data(value=account.username),
                        "password": crypto_mgr.encrypt_data(value=account.password),
                        **account.model_dump(mode="json", exclude={"username", "password"}),
                    }
                    for account in configs.accounts
                ],
                "notifications": [notification.model_dump(mode="json") for notification in configs.notifications],
            }

            configs_file = os.path.join(file_mgr.get_configs_directory(), "configs.json")
            with open(configs_file, "w", encoding="utf-8") as f:
                json.dump(encrypted_configs, f, indent=2, ensure_ascii=False)

        except Exception:
            logger.exception("Failed to save configs")

    def load_configs(self) -> Config:
        configs = Config()
        try:
            configs_file = os.path.join(file_mgr.get_configs_directory(), "configs.json")
            if not os.path.exists(configs_file):
                return configs

            with open(configs_file, "r", encoding="utf-8") as f:
                try:
                    encrypted_configs = json.load(f)

                except json.JSONDecodeError:
                    return configs

            if "accounts" in encrypted_configs and isinstance(encrypted_configs["accounts"], list):
                encrypted_configs["accounts"] = [
                    {
                        **account,
                        "username": crypto_mgr.decrypt_data(value=account.get("username")),
                        "password": crypto_mgr.decrypt_data(value=account.get("password")),
                    }
                    for account in encrypted_configs["accounts"]
                ]

            return Config.model_validate(encrypted_configs)

        except Exception:
            logger.exception("Failed to load configs")

        return configs


config_mgr = ConfigManager()
