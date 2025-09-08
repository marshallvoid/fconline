from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

PROGRAM_NAME: str = "FC Online Automation Tool"
DUPLICATE_WINDOW_SECONDS: int = 60

BROWSER_POSITIONS: Dict[Tuple[int, int], str] = {
    (0, 0): "Top-Left",
    (0, 1): "Top-Right",
    (1, 0): "Bottom-Left",
    (1, 1): "Bottom-Right",
}


@dataclass
class EventConfig:
    event_name: str = ""
    tab_attr_name: str = ""
    spin_actions: List[str] = field(default_factory=list)

    base_url: str = ""
    user_endpoint: str = "api/user/get"
    spin_endpoint: str = "api/user/spin"

    params: Dict[str, Any] = field(default_factory=dict)

    login_btn_selector: str = "a[href='/user/login']"
    logout_btn_selector: str = "a[href='/user/logout']"
    username_input_selector: str = "form input[type='text']"
    password_input_selector: str = "form input[type='password']"
    submit_btn_selector: str = "form button[type='submit']"


EVENT_CONFIGS_MAP: Dict[str, EventConfig] = {
    "Bi Lắc": EventConfig(
        event_name="Bi Lắc",
        tab_attr_name="_bilac_tab",
        spin_actions=["10 FC Spin", "190 FC Spin", "900 FC Spin"],
        base_url="https://bilac.fconline.garena.vn",
    ),
    "Tỷ Phú": EventConfig(
        event_name="Tỷ Phú",
        tab_attr_name="_typhu_tab",
        spin_actions=["20 FC Spin", "190 FC Spin", "900 FC Spin", "1800 FC Spin"],
        base_url="https://typhu.fconline.garena.vn",
    ),
    "Vòng Quanh Thế Giới": EventConfig(
        event_name="Vòng Quanh Thế Giới",
        tab_attr_name="_vqtg_tab",
        spin_actions=["20 FC Spin", "190 FC Spin", "900 FC Spin"],
        base_url="https://vqtg.fconline.garena.vn",
        spin_endpoint="api/reward/spin",
        params={"is_free": False, "use_topup_deal": False},
    ),
    "Tuyển Chọn Siêu Sao": EventConfig(
        event_name="Tuyển Chọn Siêu Sao",
        tab_attr_name="_tcss_tab",
        spin_actions=["20 FC Spin", "190 FC Spin", "900 FC Spin", "1800 FC Spin"],
        base_url="https://tcss.fconline.garena.vn",
        login_btn_selector='header a:has-text("Đăng nhập")',
    ),
}
