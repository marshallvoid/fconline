import contextlib
import time
import wave
from pathlib import Path

from loguru import logger
from notifypy import Notify

from src.utils import files
from src.utils.contants import PROGRAM_NAME


def _wav_duration(path: str | Path) -> float:
    with contextlib.closing(wave.open(str(path), "rb")) as f:
        frames = f.getnframes()
        rate = f.getframerate()

    return frames / rate if rate else 0.0


def send_notification(message: str, audio_name: str, loop_count: int = 3, extra_pause: float = 0.2) -> None:
    try:
        audio_path = Path(files.get_resource_path(f"assets/sounds/{audio_name}"))
        notification = Notify(
            default_notification_title=PROGRAM_NAME,
            default_notification_message=message,
            default_notification_application_name=PROGRAM_NAME,
            default_notification_icon=files.get_resource_path("assets/icon.ico"),
            default_notification_audio=str(audio_path),
        )

        gap = _wav_duration(audio_path) + extra_pause

        for _ in range(loop_count):
            notification.send(block=False)
            time.sleep(gap)

    except Exception as error:
        logger.error(f"Error sending notification: {error}")
