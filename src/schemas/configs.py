from datetime import datetime
from typing import List

from pydantic import BaseModel

from src.utils.contants import EVENT_CONFIGS_MAP


class Notification(BaseModel):
    timestamp: str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    nickname: str = ""
    jackpot_value: str = ""
    is_seen: bool = False


class Account(BaseModel):
    username: str = ""
    password: str = ""
    spin_action: int = 1
    target_special_jackpot: int = 19000
    close_when_jackpot_won: bool = True
    has_won: bool = False
    marked_not_run: bool = False


class Configs(BaseModel):
    event: str = list(EVENT_CONFIGS_MAP.keys())[0]
    accounts: List[Account] = []
    notifications: List[Notification] = []

    @property
    def first_account(self) -> Account:
        return self.accounts[0] if self.accounts else Account()
