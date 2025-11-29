from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel

from app.schemas.app_config import EventConfigs
from app.schemas.enums.payment_type import PaymentType


class Notification(BaseModel):
    timestamp: str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    nickname: str = ""
    jackpot_value: str = ""
    is_seen: bool = False


class Account(BaseModel):
    username: str = ""
    password: str = ""

    target_sjp: int = 19000
    target_mjp: Optional[int] = None

    payment_type: PaymentType = PaymentType.FC
    spin_type: int = 1  # 20 Spin, 190 Spin, 900 Spin, 1800 Spin
    spin_delay_seconds: float = 0.0
    close_on_jp_win: bool = True

    has_won: bool = False
    marked_not_run: bool = False

    @property
    def available(self) -> bool:
        return not self.has_won and not self.marked_not_run

    def spin_type_name(self, event_configs: Dict[str, EventConfigs], selected_event: str) -> str:
        base_name = event_configs[selected_event].spin_types[self.spin_type - 1]
        payment_prefix = "FC" if self.payment_type == PaymentType.FC else "MC"
        return base_name.replace("Spin", f"{payment_prefix} Spin")

    def running_message(self, event_configs: Dict[str, EventConfigs], selected_event: str) -> str:
        spin_type_name = self.spin_type_name(event_configs=event_configs, selected_event=selected_event)
        message = f"Running account '{self.username}' - Action: '{spin_type_name}' - Target SJP: '{self.target_sjp:,}'"

        if self.target_mjp is not None:
            message = f"{message} - Target MJP: '{self.target_mjp:,}'"

        if self.spin_delay_seconds > 0:
            message = f"{message} - Spin delay: {self.spin_delay_seconds} seconds between spins"

        return message


class LocalConfigs(BaseModel):
    license_key: str = ""
    event: str = ""
    auto_refresh: bool = False

    accounts: List[Account] = []
    notifications: List[Notification] = []
