import base64
import json
import os
import platform
from typing import Any, Dict

from cryptography.fernet import Fernet


class CredentialManager:
    """Manages encrypted storage and retrieval of user credentials."""

    def __init__(self) -> None:
        """Initialize the credential manager."""
        self._config_file = os.path.join(self._get_user_data_directory(), "config.json")

    @staticmethod
    def _get_user_data_directory() -> str:
        """Get or create user data directory."""
        system = platform.system().lower()

        if system == "windows":  # Windows
            app_data = os.environ.get("APPDATA", os.path.expanduser("~"))
            user_data_dir = os.path.join(app_data, "FCOnlineAutomation")
        else:  # macOS and Linux
            user_data_dir = os.path.expanduser("~/.fconline-automation")

        # Create directory if it doesn't exist
        os.makedirs(user_data_dir, exist_ok=True)
        return user_data_dir

    @staticmethod
    def _get_encryption_key() -> bytes:
        """Get or create encryption key for data protection."""
        user_data_dir = CredentialManager._get_user_data_directory()
        key_file = os.path.join(user_data_dir, ".key")

        try:
            # Try to load existing key
            if os.path.exists(key_file):
                with open(key_file, "rb") as f:
                    return f.read()
            else:
                # Generate new key if doesn't exist
                key = Fernet.generate_key()
                with open(key_file, "wb") as f:
                    f.write(key)
                # Make key file hidden and read-only on Unix systems
                if platform.system().lower() != "windows":
                    os.chmod(key_file, 0o600)
                return key
        except Exception:
            # Fallback to a simple key based on machine info
            machine_id = platform.node() + platform.machine()
            key = base64.urlsafe_b64encode(machine_id.encode().ljust(32)[:32])
            return key

    @staticmethod
    def encrypt_data(data: str) -> str:
        """Encrypt sensitive data."""
        try:
            key = CredentialManager._get_encryption_key()
            f = Fernet(key)
            encrypted_data = f.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception:
            # Fallback to simple base64 encoding if encryption fails
            return base64.urlsafe_b64encode(data.encode()).decode()

    @staticmethod
    def decrypt_data(encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        try:
            key = CredentialManager._get_encryption_key()
            f = Fernet(key)
            data_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = f.decrypt(data_bytes)
            return decrypted_data.decode()
        except Exception:
            # Fallback to simple base64 decoding if decryption fails
            try:
                return base64.urlsafe_b64decode(encrypted_data.encode()).decode()
            except Exception:
                return ""

    @classmethod
    def load_credentials(cls) -> Dict[str, Any]:
        """Load saved credentials from config file."""
        config_file = os.path.join(cls._get_user_data_directory(), "config.json")
        try:
            if os.path.exists(config_file):
                with open(config_file, "r", encoding="utf-8") as f:
                    encrypted_data = json.load(f)

                # Decrypt sensitive data
                credentials = {}
                for key, value in encrypted_data.items():
                    if key in ["username", "password"]:
                        # Decrypt sensitive fields
                        credentials[key] = cls.decrypt_data(value) if value else ""
                    else:
                        # Keep non-sensitive fields as is
                        credentials[key] = value

                return credentials
        except Exception:
            # Silent fail - just return empty dict if can't load
            pass

        return {}

    @classmethod
    def save_credentials(cls, credentials_dict: Dict[str, Any]) -> None:
        """Save credentials to config file."""
        config_file = os.path.join(cls._get_user_data_directory(), "config.json")
        try:
            # Prepare credentials with encryption for sensitive data
            encrypted_credentials = {}
            for key, value in credentials_dict.items():
                if key in ["username", "password"]:
                    # Encrypt sensitive fields
                    encrypted_credentials[key] = cls.encrypt_data(value) if value else ""
                else:
                    # Keep non-sensitive fields as is
                    encrypted_credentials[key] = value

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(encrypted_credentials, f, indent=2, ensure_ascii=False)

        except Exception:
            # Silent fail - don't crash the app if can't save
            pass
