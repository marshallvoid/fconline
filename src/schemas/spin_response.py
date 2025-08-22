from typing import List, Optional

from pydantic import AliasChoices, BaseModel, Field

SPIN_RESULT_ALIASES = ("spin_results", "receive_reward_infos")
REWARD_NAME_ALIASES = ("reward_name", "item_name")


class SpinResult(BaseModel):
    reward_name: str = Field(validation_alias=AliasChoices(*REWARD_NAME_ALIASES))


class SpinPayload(BaseModel):
    spin_results: List[SpinResult] = Field(validation_alias=AliasChoices(*SPIN_RESULT_ALIASES))


class SpinResponse(BaseModel):
    status: str
    payload: Optional[SpinPayload] = None
    error_code: Optional[str] = None

    @property
    def is_successful(self) -> bool:
        return self.status == "successful"
