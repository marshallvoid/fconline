from typing import List, Tuple

from pydantic import BaseModel


class UserConfig(BaseModel):
    event: str = ""
    username: str = ""
    password: str = ""
    spin_action: int = 1
    target_special_jackpot: int = 19000
    close_when_jackpot_won: bool = True

    # List of (nickname, jackpot_value, timestamp, is_seen) tuples
    notifications: List[Tuple[str, str, str, bool]] = []
