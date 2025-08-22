from typing import Optional

from pydantic import BaseModel


class ReloadPayload(BaseModel):
    fc: int
    mc: int


class ReloadResponse(BaseModel):
    status: str
    payload: Optional[ReloadPayload] = None
    error_code: Optional[str] = None

    @property
    def is_successful(self) -> bool:
        return self.status == "successful"
