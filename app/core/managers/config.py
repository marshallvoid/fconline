import base64
import json
import os
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet
from loguru import logger

from app.core.managers.file import file_mgr
from app.core.managers.platform import platform_mgr
from app.schemas.configs import Config
from app.utils.decorators.singleton import singleton


@singleton
class ConfigManager:
    def load_configs(self) -> Config:
        configs = Config()
        try:
            configs_file = os.path.join(file_mgr.get_configs_directory(), "configs.json")
            if not os.path.exists(configs_file):
                return configs

            with open(configs_file, "r", encoding="utf-8") as f:
                encrypted_configs = json.load(f)

            if "accounts" in encrypted_configs and isinstance(encrypted_configs["accounts"], list):
                encrypted_configs["accounts"] = [
                    {
                        **account,
                        "username": self._decrypt_data(value=account.get("username")),
                        "password": self._decrypt_data(value=account.get("password")),
                    }
                    for account in encrypted_configs["accounts"]
                ]

            return Config.model_validate(encrypted_configs)

        except Exception:
            logger.exception("Failed to load configs")

        return configs

    def save_configs(self, configs: Config) -> None:
        try:
            encrypted_configs: Dict[str, Any] = {
                **configs.model_dump(exclude={"accounts", "notifications"}),
                "accounts": [
                    {
                        "username": self._encrypt_data(value=account.username),
                        "password": self._encrypt_data(value=account.password),
                        **account.model_dump(exclude={"username", "password"}),
                    }
                    for account in configs.accounts
                ],
                "notifications": [notification.model_dump() for notification in configs.notifications],
            }

            configs_file = os.path.join(file_mgr.get_configs_directory(), "configs.json")
            with open(configs_file, "w", encoding="utf-8") as f:
                json.dump(encrypted_configs, f, indent=2, ensure_ascii=False)

        except Exception:
            logger.exception("Failed to save configs")

    def _encrypt_data(self, value: Optional[str] = None) -> str:
        if not value:
            return ""

        try:
            # Use Fernet symmetric encryption for sensitive data
            f = Fernet(self._get_encryption_key())
            encrypted_data = f.encrypt(value.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()

        except Exception:
            # Fallback to simple base64 encoding if encryption fails
            return base64.urlsafe_b64encode(value.encode()).decode()

    def _decrypt_data(self, value: Optional[str] = None) -> str:
        if not value:
            return ""

        try:
            # Use Fernet symmetric encryption for sensitive data
            f = Fernet(self._get_encryption_key())
            decrypted_data = f.decrypt(base64.urlsafe_b64decode(value.encode()))
            return decrypted_data.decode()

        except Exception:
            # Fallback to simple base64 decoding if decryption fails
            return base64.urlsafe_b64decode(value.encode()).decode()

    def _get_encryption_key(self) -> bytes:
        config_data_dir = file_mgr.get_configs_directory()
        key_file = os.path.join(config_data_dir, ".key")

        try:
            # Try to load existing key
            if os.path.exists(key_file):
                with open(key_file, "rb") as f:
                    return f.read()

            # Generate new key if doesn't exist
            key = Fernet.generate_key()
            with open(key_file, "wb") as f:
                f.write(key)

            # Make key file hidden and read-only on Unix systems
            if not platform_mgr.is_windows():
                os.chmod(key_file, 0o600)

            return key

        except Exception:
            # Fallback to a simple key based on machine info
            machine_id = platform_mgr.node() + platform_mgr.machine()
            key = base64.urlsafe_b64encode(machine_id.encode().ljust(32)[:32])
            return key


config_mgr = ConfigManager()
