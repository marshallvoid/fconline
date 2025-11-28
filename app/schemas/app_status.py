from typing import List

from pydantic import BaseModel


class AppStatus(BaseModel):
    is_active: bool = False
    message: str = "Application is under maintenance."
    valid_licenses: List[str] = []
    blocked_licenses: List[str] = []
    blocked_message: str = "Your license has been revoked. Please contact support."
    invalid_license_message: str = "Invalid license key. Please contact support."
