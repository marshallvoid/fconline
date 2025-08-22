from enum import Enum, unique


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
    OTHER_PLAYER = "#3b82f6"

    @property
    def is_game_event(self) -> bool:
        return self in [self.REACHED_GOAL, self.JACKPOT, self.MINI_JACKPOT, self.OTHER_PLAYER]

    @property
    def is_reward(self) -> bool:
        return self in [self.REWARD]

    @property
    def is_websocket(self) -> bool:
        return self in [self.WEBSOCKET]

    @property
    def is_system(self) -> bool:
        return self in [self.INFO, self.SUCCESS, self.ERROR, self.WARNING]

    @property
    def tab_name(self) -> str:
        if self.is_game_event:
            return "Game Events"

        if self.is_reward:
            return "Rewards"

        if self.is_system:
            return "System"

        if self.is_websocket:
            return "WebSockets"

        msg = f"Invalid message tag: {self}"
        raise ValueError(msg)
