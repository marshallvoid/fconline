from dataclasses import dataclass
from typing import Dict


@dataclass
class EventConfig:
    tab_attr_name: str
    spin_actions: Dict[int, str]

    base_url: str
    user_endpoint: str
    spin_endpoint: str

    login_btn_selector: str = "a[href='/user/login']"
    logout_btn_selector: str = "a[href='/user/logout']"
    username_input_selector: str = "form input[type='text']"
    password_input_selector: str = "form input[type='password']"
    submit_btn_selector: str = "form button[type='submit']"
