import json
import sys
from pathlib import Path

from loguru import logger

import app


class VersionManager:
    METADATA_FILE = "metadata.json"

    def __init__(self) -> None:
        self._version = self._load_version()

    @property
    def version(self) -> str:
        return self._version

    def _load_version(self) -> str:
        try:
            # Look for metadata.json in the same directory as the executable or script
            if getattr(sys, "frozen", False):
                base_path = Path(sys.executable).parent
            else:
                base_path = Path(__file__).parent.parent.parent.parent

            metadata_path = base_path / self.METADATA_FILE

            if metadata_path.exists():
                with open(metadata_path, "r") as f:
                    data = json.load(f)
                    version = data.get("version")
                    if version:
                        logger.info(f"Loaded version {version} from {metadata_path}")
                        return version

            logger.info(f"Using hardcoded version {app.__version__}")
            return app.__version__

        except Exception as e:
            logger.error(f"Error loading version metadata: {e}")
            return app.__version__

    def update_version(self, new_version: str) -> None:
        try:
            if getattr(sys, "frozen", False):
                base_path = Path(sys.executable).parent
            else:
                base_path = Path(__file__).parent.parent.parent.parent

            metadata_path = base_path / self.METADATA_FILE

            data = {}
            if metadata_path.exists():
                with open(metadata_path, "r") as f:
                    data = json.load(f)

            data["version"] = new_version

            with open(metadata_path, "w") as f:
                json.dump(data, f, indent=4)

            self._version = new_version
            logger.info(f"Updated version to {new_version} in {metadata_path}")

        except Exception as e:
            logger.error(f"Failed to update version metadata: {e}")


# Singleton instance
version_manager = VersionManager()
