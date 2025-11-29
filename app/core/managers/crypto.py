import base64
import os
from typing import Optional

from cryptography.fernet import Fernet

from app.core.managers.file import file_mgr
from app.core.managers.platform import platform_mgr
from app.utils.decorators.singleton import singleton


@singleton
class CryptoManager:
    def __init__(self) -> None:
        self._key = self._get_encryption_key()
        self._fernet = Fernet(self._key)

    def encrypt_data(self, value: Optional[str] = None) -> str:
        if not value:
            return ""

        try:
            # Use Fernet symmetric encryption for sensitive data
            encrypted_data = self._fernet.encrypt(value.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()

        except Exception:
            # Fallback to simple base64 encoding if encryption fails
            return base64.urlsafe_b64encode(value.encode()).decode()

    def decrypt_data(self, value: Optional[str] = None) -> str:
        if not value:
            return ""

        try:
            # Use Fernet symmetric encryption for sensitive data
            decrypted_data = self._fernet.decrypt(base64.urlsafe_b64decode(value.encode()))
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
            if not platform_mgr.is_windows:
                os.chmod(key_file, 0o600)

            return key

        except Exception:
            # Fallback to a simple key based on machine info
            machine_id = platform_mgr.node + platform_mgr.machine
            key = base64.urlsafe_b64encode(machine_id.encode().ljust(32)[:32])
            return key


crypto_mgr = CryptoManager()
