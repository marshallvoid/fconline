from pydantic import BaseModel


class UserDetail(BaseModel):
    id: int
    uid: str
    account_id: str
    nickname: str
    fc: int
    mc: int


class UserPayload(BaseModel):
    user: UserDetail


class UserReponse(BaseModel):
    status: str
    payload: UserPayload

    @property
    def is_successful(self) -> bool:
        return self.status == "successful"
