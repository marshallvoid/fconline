from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class UserDetail(BaseModel):
    id: int
    uid: str
    nickname: str
    free_spin: int
    fc: int
    mc: int


class UserPayload(BaseModel):
    user: Optional[UserDetail] = None


class UserReponse(BaseModel):
    payload: UserPayload
