from typing import Optional

from pydantic import AliasChoices, BaseModel, Field

from src.schemas.billboard import Billboard


class UserDetail(BaseModel):
    id: int
    uid: str
    account_id: str
    fc: int
    mc: int

    nickname: Optional[str] = None
    account_name: Optional[str] = None


class UserPayload(BaseModel):
    user: Optional[UserDetail] = None
    jackpot_billboard: Optional[Billboard] = Field(None, validation_alias=AliasChoices("last_jackpot_infos"))
    mini_jackpot_billboard: Optional[Billboard] = Field(None, validation_alias=AliasChoices("last_mini_jackpot_infos"))

    error_code: Optional[str] = None


class UserReponse(BaseModel):
    status: str
    payload: UserPayload

    @property
    def is_successful(self) -> bool:
        return self.status == "successful"
