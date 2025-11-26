from typing import Any, Optional

from pydantic import AliasChoices, BaseModel, Field, model_validator

VALUE_ALIASES = ("value", "jackpot_prize", "mini_jackpot_prize")
NICKNAME_ALIASES = ("nickname", "account_name")


class Billboard(BaseModel):
    value: str = Field(validation_alias=AliasChoices(*VALUE_ALIASES))
    nickname: str = Field(validation_alias=AliasChoices(*NICKNAME_ALIASES))
    payment_type: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_aliases(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        for key in VALUE_ALIASES:
            if key in data:
                v, pay = data[key], data.get("payment_type")

                if isinstance(v, int):
                    data[key] = f"{v}{' ' + pay.upper() if isinstance(pay, str) and pay else ''}"

                break

        return data
