from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class User(BaseModel):
    id: int
    uid: str
    nickname: str
    free_spin: int
    fc: int
    mc: int


class Payload(BaseModel):
    user: Optional[User] = None


class UserReponse(BaseModel):
    payload: Payload
