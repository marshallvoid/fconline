from pydantic import BaseModel


class UserConfig(BaseModel):
    event: str = ""
    username: str = ""
    password: str = ""
    spin_action: int = 1
    target_special_jackpot: int = 10000
