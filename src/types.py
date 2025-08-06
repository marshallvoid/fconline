from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class User(BaseModel):
    id: int
    uid: str
    nickname: str
    account_id: str
    accumulation: int
    free_spin: int
    price_type: str
    free_type: str
    special_spins: Dict[str, Any]
    club_spins_claimed: int
    spin_accumulation_reward_history: List
    fc: int
    mc: int


class ResultDetail(BaseModel):
    field_1: Optional[int] = Field(None, alias="1")
    field_2: Optional[int] = Field(None, alias="2")
    field_3: Optional[int] = Field(None, alias="3")
    field_4: Optional[int] = Field(None, alias="4")
    field_5: Optional[int] = Field(None, alias="5")


class Reward(BaseModel):
    id: int
    desc: str
    image: str


class SpinSetting(BaseModel):
    result_detail: ResultDetail
    accumulation_point: int
    rewards: List[Reward]


class Reward1(BaseModel):
    desc: str
    image: str
    limit: None
    round_required: Optional[int]
    id: int


class SpinAccumulation(BaseModel):
    stage: int
    desc: Optional[str]
    player_type: str
    rewards: List[Reward1]


class JackpotBillboard(BaseModel):
    value: str
    nickname: str


class MiniJackpotBillboard(BaseModel):
    value: str
    nickname: str


class Payload(BaseModel):
    user: Optional[User] = None
    event_started: int
    socket_account_id: str
    socket_env: str
    jackpot_value: int
    spin_settings: List[SpinSetting]
    spin_accumulations: List[SpinAccumulation]
    current_datetime: str
    special_date: bool
    event_duration: str
    jackpot_billboard: JackpotBillboard
    mini_jackpot_billboard: MiniJackpotBillboard


class UserInfo(BaseModel):
    status: str
    payload: Payload
