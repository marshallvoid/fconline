from typing import Dict

from src.core.event_config import EventConfig

EVENT_CONFIGS_MAP: Dict[str, EventConfig] = {
    "Bi Lắc": EventConfig(
        tab_name="_bilac_tab",
        title="Bi Lắc",
        base_url="https://bilac.fconline.garena.vn/",
        user_api_url="https://bilac.fconline.garena.vn/api/user/get",
        spin_api_url="https://bilac.fconline.garena.vn/api/user/spin",
        login_btn_selector="a.btn-header.btn-header--login",
        logout_btn_selector="a.btn-header.btn-header--logout",
        username_input_selector="form input[type='text']",
        password_input_selector="form input[type='password']",
        submit_btn_selector="form button[type='submit']",
        spin_action_selectors={
            1: ("div.spin__actions a.spin__actions--1", "Free Spin"),
            2: ("div.spin__actions a.spin__actions--2", "10 FC Spin"),
            3: ("div.spin__actions a.spin__actions--3", "190 FC Spin"),
            4: ("div.spin__actions a.spin__actions--4", "900 FC Spin"),
        },
    ),
    "Tỷ Phú": EventConfig(
        tab_name="_typhu_tab",
        title="Tỷ Phú",
        base_url="https://typhu.fconline.garena.vn/",
        user_api_url="https://typhu.fconline.garena.vn/api/user/get",
        spin_api_url="https://typhu.fconline.garena.vn/api/user/spin",
        login_btn_selector="a[href='/user/login']",
        logout_btn_selector="a[href='/user/logout']",
        username_input_selector="form input[type='text']",
        password_input_selector="form input[type='password']",
        submit_btn_selector="form button[type='submit']",
        spin_action_selectors={
            1: ("div.spin__actions__plays a.btn-spin.btn-spin--1", "20 FC Spin"),
            2: ("div.spin__actions__plays a.btn-spin.btn-spin--10", "190 FC Spin"),
            3: ("div.spin__actions__plays a.btn-spin.btn-spin--50", "900 FC Spin"),
            4: ("div.spin__actions__plays a.btn-spin.btn-spin--100", "1800 FC Spin"),
        },
    ),
}
