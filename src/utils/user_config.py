import base64
import json
import os
from typing import Optional

from cryptography.fernet import Fernet

from src.schemas.configs import Configs
from src.utils.platforms import PlatformManager


class UserConfigManager:
    @classmethod
    def load_configs(cls) -> Configs:
        try:
            configs_file = os.path.join(cls._get_config_data_directory(), "configs.json")
            if not os.path.exists(configs_file):
                return Configs()

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

            configs = Configs.model_validate(encrypted_configs)

            return configs

        except Exception:
            pass

        return Configs()

    @classmethod
    def save_configs(cls, configs: Configs) -> None:
        try:
            encrypted_accounts = [
                {
                    "username": cls._encrypt_data(value=account.username),
                    "password": cls._encrypt_data(value=account.password),
                    **account.model_dump(exclude={"username", "password"}),
                }
                for account in configs.accounts
            ]

            encrypted_configs = {
                "event": configs.event,
                "accounts": encrypted_accounts,
                "notifications": [notification.model_dump() for notification in configs.notifications],
            }

            config_file = os.path.join(cls._get_config_data_directory(), "configs.json")
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(encrypted_configs, f, indent=2, ensure_ascii=False)

        except Exception:
            pass

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
            f = Fernet(cls._get_encryption_key())
            decrypted_data = f.decrypt(base64.urlsafe_b64decode(value.encode()))
            return decrypted_data.decode()

        except Exception:
            # Fallback to simple base64 decoding if decryption fails
            return base64.urlsafe_b64decode(value.encode()).decode()

    @classmethod
    def _get_config_data_directory(cls) -> str:
        user_data_dir = os.path.expanduser("~/.fconline-automation")  # default: macos and linux

        if PlatformManager.is_windows():  # Windows
            app_data = os.environ.get("APPDATA", os.path.expanduser("~"))
            user_data_dir = os.path.join(app_data, "FCOnlineAutomation")

        # Create directory if it doesn't exist
        os.makedirs(user_data_dir, exist_ok=True)
        return user_data_dir

    @classmethod
    def _get_encryption_key(cls) -> bytes:
        config_data_dir = cls._get_config_data_directory()
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
