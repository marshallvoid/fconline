from typing import List, Optional

from pydantic import AliasChoices, BaseModel, Field

SPIN_RESULT_ALIASES = ("spin_results", "receive_reward_infos")
REWARD_NAME_ALIASES = ("reward_name", "item_name")


class SpinResult(BaseModel):
    reward_name: str = Field(validation_alias=AliasChoices(*REWARD_NAME_ALIASES))


class SpinPayload(BaseModel):
    spin_results: List[SpinResult] = Field(validation_alias=AliasChoices(*SPIN_RESULT_ALIASES))


class SpinResponse(BaseModel):
    error_code: Optional[str] = None

    status: str
    payload: Optional[SpinPayload] = None

    @property
    def is_successful(self) -> bool:
        return self.status == "successful"

    @property
    def invalid_response(self) -> bool:
        return bool(not self.payload or not self.is_successful or self.error_code)

    @property
    def invalid_message(self) -> str:
        is_free_spin = self.error_code == "balance_not_enough"
        spin_type = "Free spin" if is_free_spin else "Spin"
        return f"{spin_type} failed: {self.error_code or 'Unknown error'}"
