from typing import Optional

from pydantic import AliasChoices, BaseModel, Field

from src.schemas.billboard import Billboard

JACKPOT_BILLBOARD_ALIASES = ("jackpot_billboard", "last_jackpot_infos")
MINI_JACKPOT_BILLBOARD_ALIASES = ("mini_jackpot_billboard", "last_mini_jackpot_infos")


class UserDetail(BaseModel):
    id: int
    uid: str
    account_id: str
    fc: int
    mc: int
    free_spin: Optional[int] = None
    accumulation: Optional[int] = None

    nickname: Optional[str] = None
    account_name: Optional[str] = None

    @property
    def normalized_nickname(self) -> str:
        return self.nickname.casefold() if self.nickname else ""

    @property
    def normalized_account_name(self) -> str:
        return self.account_name.casefold() if self.account_name else ""


class UserPayload(BaseModel):
    user: Optional[UserDetail] = None
    jackpot_billboard: Optional[Billboard] = Field(None, validation_alias=AliasChoices(*JACKPOT_BILLBOARD_ALIASES))
    mini_jackpot_billboard: Optional[Billboard] = Field(
        None,
        validation_alias=AliasChoices(*MINI_JACKPOT_BILLBOARD_ALIASES),
    )

    error_code: Optional[str] = None


class UserReponse(BaseModel):
    status: str
    payload: UserPayload

    @property
    def is_successful(self) -> bool:
        return self.status == "successful"
