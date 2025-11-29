from typing import Any, Dict, List

from pydantic import BaseModel


class AppConfigs(BaseModel):
    is_active: bool = False
    message: str = "Application is under maintenance."
    blocked_licenses: List[str] = []
    blocked_license_message: str = "Your license has been revoked. Please contact support."
    valid_licenses: List[str] = []
    invalid_license_message: str = "Invalid license key. Please contact support."


class EventConfigs(BaseModel):
    base_url: str = ""
    user_endpoint: str = "api/user/get"
    spin_endpoint: str = "api/user/spin"
    params: Dict[str, Any] = {}
    spin_types: List[str] = []

    login_btn_selector: str = "a[href='/user/login']"
    logout_btn_selector: str = "a[href='/user/logout']"
    username_input_selector: str = "form input[type='text']"
    password_input_selector: str = "form input[type='password']"
    submit_btn_selector: str = "form button[type='submit']"


class Configs(BaseModel):
    app_configs: AppConfigs
    event_configs: Dict[str, EventConfigs] = {}  # Format: { event_name: EventConfigs }
