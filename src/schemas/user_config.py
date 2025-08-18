from typing import List, Tuple

from pydantic import BaseModel


class UserConfig(BaseModel):
    event: str = ""
    username: str = ""
    password: str = ""
    spin_action: int = 1
    target_special_jackpot: int = 10000
    notifications: List[Tuple[str, str, str]] = []  # List of (nickname, jackpot_value, timestamp) tuples
