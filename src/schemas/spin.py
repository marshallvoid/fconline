from typing import List, Optional

from pydantic import BaseModel


class SpinResult(BaseModel):
    reward_name: str
    image: str
    dice_result: int
    step_type: int
    extra_value: None
    accumulation_point: int
    spin_result_reward_id: int


class Payload(BaseModel):
    jackpot_value: int
    spin_results: List[SpinResult]


class SpinResponse(BaseModel):
    status: str
    payload: Optional[Payload] = None
    error_code: Optional[str] = None

    @property
    def is_successful(self) -> bool:
        return self.status == "successful"
