import time
from pathlib import Path
from typing import Optional

from loguru import logger
from playsound3 import playsound

from app.core.managers.file import file_mgr


def play_audio(audio_name: Optional[str], loop_count: int = 3, extra_pause: float = 0.2) -> None:
    if not audio_name:
        return

    try:
        audio_path = Path(file_mgr.get_resource_path(f"assets/sounds/{audio_name}"))
        for _ in range(loop_count):
            playsound(sound=audio_path)
            time.sleep(extra_pause)

    except Exception as error:
        logger.exception(f"Error sending notification: {error}")
