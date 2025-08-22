from enum import Enum, unique


@unique
class AccountTag(Enum):
    WINNER = ("#fbbf24", "#000000")
    RUNNING = ("#90EE90", "#000000")
    STOPPED = ("#FFB6C1", "#000000")
