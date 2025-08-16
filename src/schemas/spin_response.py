from typing import List, Optional

from pydantic import BaseModel


class SpinResult(BaseModel):
    reward_name: str
    image: str
    dice_result: Optional[int] = None
    step_type: Optional[int] = None
    extra_value: Optional[int] = None
    accumulation_point: Optional[int] = None
    spin_result_reward_id: Optional[int] = None


class SpinPayload(BaseModel):
    jackpot_value: int
    spin_results: List[SpinResult]


class SpinResponse(BaseModel):
    status: str
    payload: Optional[SpinPayload] = None
    error_code: Optional[str] = None

    @property
    def is_successful(self) -> bool:
        return self.status == "successful"
