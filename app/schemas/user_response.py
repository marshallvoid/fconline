from typing import Optional

from pydantic import AliasChoices, BaseModel, Field

from app.schemas.billboard import Billboard

JACKPOT_BILLBOARD_ALIASES = ("jackpot_billboard", "last_jackpot_infos")
MINI_JACKPOT_BILLBOARD_ALIASES = ("mini_jackpot_billboard", "last_mini_jackpot_infos")


class UserDetail(BaseModel):
    free_spin: Optional[int] = None

    nickname: Optional[str] = None
    account_name: Optional[str] = None

    @property
    def nickname_norm(self) -> str:
        return self.nickname.casefold() if self.nickname else ""

    @property
    def account_name_norm(self) -> str:
        return self.account_name.casefold() if self.account_name else ""


class UserPayload(BaseModel):
    error_code: Optional[str] = None

    user: Optional[UserDetail] = None
    sjp_billboard: Optional[Billboard] = Field(None, validation_alias=AliasChoices(*JACKPOT_BILLBOARD_ALIASES))
    mjp_billboard: Optional[Billboard] = Field(None, validation_alias=AliasChoices(*MINI_JACKPOT_BILLBOARD_ALIASES))


class UserReponse(BaseModel):
    status: str
    payload: UserPayload

    @property
    def is_successful(self) -> bool:
        return self.status == "successful"

    @property
    def invalid_response(self) -> bool:
        return bool(not self.is_successful or self.payload.error_code)

    @property
    def invalid_message(self) -> str:
        return f"Lookup user info failed: {self.payload.error_code or 'Unknown error'}"
