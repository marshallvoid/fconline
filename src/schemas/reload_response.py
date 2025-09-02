from typing import Optional

from pydantic import AliasChoices, AliasPath, BaseModel, Field


class ReloadPayload(BaseModel):
    fc: Optional[int] = Field(None, validation_alias=AliasChoices("fc", AliasPath("user", "fc")))
    mc: Optional[int] = Field(None, validation_alias=AliasChoices("mc", AliasPath("user", "mc")))
    error_code: Optional[str] = None


class ReloadResponse(BaseModel):
    status: str
    payload: ReloadPayload

    @property
    def is_successful(self) -> bool:
        return self.status == "successful"
