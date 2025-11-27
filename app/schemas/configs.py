from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.utils.constants import EVENT_CONFIGS_MAP


class Notification(BaseModel):
    timestamp: str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    nickname: str = ""
    jackpot_value: str = ""
    is_seen: bool = False


class Account(BaseModel):
    username: str = ""
    password: str = ""

    spin_type: int = 1  # 20 Spin, 190 Spin, 900 Spin, 1800 Spin
    payment_type: int = 1  # FC = 1, MC = 2
    close_on_jp_win: bool = True

    target_sjp: int = 19000
    target_mjp: Optional[int] = None
    spin_delay_seconds: float = 0.0

    has_won: bool = False
    marked_not_run: bool = False

    @property
    def available(self) -> bool:
        return not self.has_won and not self.marked_not_run

    def spin_type_name(self, selected_event: str) -> str:
        base_name = EVENT_CONFIGS_MAP[selected_event].spin_types[self.spin_type - 1]
        payment_prefix = "FC" if self.payment_type == 1 else "MC"
        return base_name.replace("Spin", f"{payment_prefix} Spin")

    def running_message(self, selected_event: str) -> str:
        spin_type_name = self.spin_type_name(selected_event)

        base_msg = f"Running account '{self.username}' (Action: '{spin_type_name}' - Target JP: '{self.target_sjp:,}')"

        if self.target_mjp is not None:
            return f"{base_msg} - Target Mini JP: '{self.target_mjp:,}'"

        return base_msg


class Config(BaseModel):
    event: str = list(EVENT_CONFIGS_MAP.keys())[0]
    auto_refresh: bool = True

    accounts: List[Account] = []
    notifications: List[Notification] = []
