from typing import Optional

from pydantic import BaseModel


class ReloadPayload(BaseModel):
    fc: Optional[int] = None
    mc: Optional[int] = None
    error_code: Optional[str] = None


class ReloadResponse(BaseModel):
    status: str
    payload: ReloadPayload

    @property
    def is_successful(self) -> bool:
        return self.status == "successful"
