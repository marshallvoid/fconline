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
    target_sjp: int = 19000
    close_on_jp_win: bool = True
    has_won: bool = False
    marked_not_run: bool = False

    @property
    def available(self) -> bool:
        return not self.has_won and not self.marked_not_run

    def spin_action_name(self, selected_event: str) -> str:
        return EVENT_CONFIGS_MAP[selected_event].spin_actions[self.spin_action - 1]

    def running_message(self, selected_event: str) -> str:
        spin_action_name = self.spin_action_name(selected_event)
        return f"Running account '{self.username}' (Action: '{spin_action_name}' - Target: '{self.target_sjp:,}')"


class Config(BaseModel):
    event: str = list(EVENT_CONFIGS_MAP.keys())[0]
    accounts: List[Account] = []
    notifications: List[Notification] = []

    @property
    def first_account(self) -> Account:
        return self.accounts[0] if self.accounts else Account()
