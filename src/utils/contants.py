from dataclasses import dataclass, field
from typing import Dict, List

# Application name displayed in UI and notifications
PROGRAM_NAME = "FC Online Automation Tool"


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


# Configuration mapping for different FC Online game events
# Each event has specific spin actions and base URL
EVENT_CONFIGS_MAP: Dict[str, EventConfig] = {
    "Bi Lắc": EventConfig(
        tab_attr_name="_bilac_tab",
        spin_actions=["Free Spin", "10 FC Spin", "190 FC Spin", "900 FC Spin"],
        base_url="https://bilac.fconline.garena.vn",
    ),
    "Tỷ Phú": EventConfig(
        tab_attr_name="_typhu_tab",
        spin_actions=["20 FC Spin", "190 FC Spin", "900 FC Spin", "1800 FC Spin"],
        base_url="https://typhu.fconline.garena.vn",
    ),
}
