import base64
import json
import os
from typing import Optional

from cryptography.fernet import Fernet
from loguru import logger

from src.schemas.configs import Configs
from src.services.files import FileManager
from src.services.platforms import PlatformManager


class ConfigsManager:
    @classmethod
    def load_configs(cls) -> Configs:
        configs = Configs()
        try:
            configs_file = os.path.join(FileManager.get_configs_dicrectory(), "configs.json")
            if not os.path.exists(configs_file):
                return configs

            with open(configs_file, "r", encoding="utf-8") as f:
                encrypted_configs = json.load(f)

            if "accounts" in encrypted_configs and isinstance(encrypted_configs["accounts"], list):
                encrypted_configs["accounts"] = [
                    {
                        **account,
                        "username": cls._decrypt_data(value=account.get("username")),
                        "password": cls._decrypt_data(value=account.get("password")),
                    }
                    for account in encrypted_configs["accounts"]
                ]

            return Configs.model_validate(encrypted_configs)

        except Exception:
            logger.exception("Failed to load configs")

        return configs

    @classmethod
    def save_configs(cls, configs: Configs) -> None:
        try:
            encrypted_configs = {
                "event": configs.event,
                "accounts": [
                    {
                        "username": cls._encrypt_data(value=account.username),
                        "password": cls._encrypt_data(value=account.password),
                        **account.model_dump(exclude={"username", "password"}),
                    }
                    for account in configs.accounts
                ],
                "notifications": [notification.model_dump() for notification in configs.notifications],
            }

            configs_file = os.path.join(FileManager.get_configs_dicrectory(), "configs.json")
            with open(configs_file, "w", encoding="utf-8") as f:
                json.dump(encrypted_configs, f, indent=2, ensure_ascii=False)

        except Exception:
            logger.exception("Failed to save configs")

    @classmethod
    def _encrypt_data(cls, value: Optional[str] = None) -> str:
        if not value:
            return ""

        try:
            # Use Fernet symmetric encryption for sensitive data
            f = Fernet(cls._get_encryption_key())
            encrypted_data = f.encrypt(value.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()

        except Exception:
            # Fallback to simple base64 encoding if encryption fails
            return base64.urlsafe_b64encode(value.encode()).decode()

    @classmethod
    def _decrypt_data(cls, value: Optional[str] = None) -> str:
        if not value:
            return ""

        try:
            # Use Fernet symmetric encryption for sensitive data
            f = Fernet(cls._get_encryption_key())
            decrypted_data = f.decrypt(base64.urlsafe_b64decode(value.encode()))
            return decrypted_data.decode()

        except Exception:
            # Fallback to simple base64 decoding if decryption fails
            return base64.urlsafe_b64decode(value.encode()).decode()

    @classmethod
    def _get_encryption_key(cls) -> bytes:
        config_data_dir = FileManager.get_configs_dicrectory()
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
            if not PlatformManager.is_windows():
                os.chmod(key_file, 0o600)

            return key

        except Exception:
            # Fallback to a simple key based on machine info
            machine_id = PlatformManager.node() + PlatformManager.machine()
            key = base64.urlsafe_b64encode(machine_id.encode().ljust(32)[:32])
            return key
