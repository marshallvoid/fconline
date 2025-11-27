from enum import Enum, unique
from typing import Optional


@unique
class MessageTag(Enum):
    # System messages
    DEFAULT = "#d1d5db"
    INFO = "#38bdf8"
    SUCCESS = "#22c55e"
    ERROR = "#ef4444"
    WARNING = "#f59e0b"

    WEBSOCKET = "#6366f1"

    # Game Events
    REACHED_GOAL = "#f97316"
    JACKPOT = "#fbbf24"  # Ultimate Prize
    MINI_JACKPOT = "#34d399"  # Mini Prize
    REWARD = "#a855f7"
    OTHER_PLAYER_JACKPOT = "#3b82f6"
    OTHER_PLAYER_MINI_JACKPOT = "#60a5fa"

    @property
    def sound_name(self) -> Optional[str]:
        if self == self.JACKPOT:
            return "coin-1.wav"

        if self == self.MINI_JACKPOT:
            return "coin-2.wav"

        return None

    @property
    def tab_name(self) -> str:
        if self in [self.REACHED_GOAL, self.OTHER_PLAYER_JACKPOT, self.OTHER_PLAYER_MINI_JACKPOT]:
            return "Game Events"

        if self in [self.JACKPOT, self.MINI_JACKPOT, self.REWARD]:
            return "Rewards"

        if self in [self.INFO, self.SUCCESS, self.ERROR, self.WARNING]:
            return "System"

        if self in [self.WEBSOCKET]:
            return "WebSockets"

        return "All"
