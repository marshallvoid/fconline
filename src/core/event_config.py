from dataclasses import dataclass, field
from typing import List


@dataclass
class EventConfig:
    tab_attr_name: str = ""
    spin_actions: List[str] = field(default_factory=list)

    base_url: str = ""
    user_endpoint: str = "api/user/get"
    spin_endpoint: str = "api/user/spin"

    login_btn_selector: str = "a[href='/user/login']"
    logout_btn_selector: str = "a[href='/user/logout']"
    username_input_selector: str = "form input[type='text']"
    password_input_selector: str = "form input[type='password']"
    submit_btn_selector: str = "form button[type='submit']"
