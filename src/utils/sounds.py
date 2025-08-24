import time
from pathlib import Path

from loguru import logger
from playsound3 import playsound

from src.utils import files


def send_notification(audio_name: str, loop_count: int = 3, extra_pause: float = 0.2) -> None:
    try:
        audio_path = Path(files.get_resource_path(f"assets/sounds/{audio_name}"))
        for _ in range(loop_count):
            sound = playsound(sound=audio_path, block=True)
            sound.wait()
            time.sleep(extra_pause)

    except Exception as error:
        logger.error(f"Error sending notification: {error}")
