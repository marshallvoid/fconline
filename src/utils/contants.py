from typing import Dict

from src.core.event_config import EventConfig

EVENT_CONFIGS_MAP: Dict[str, EventConfig] = {
    "Bi Lắc": EventConfig(
        tab_attr_name="_bilac_tab",
        spin_actions={1: "Free Spin", 2: "10 FC Spin", 3: "190 FC Spin", 4: "900 FC Spin"},
        base_url="https://bilac.fconline.garena.vn",
        user_endpoint="api/user/get",
        spin_endpoint="api/user/spin",
    ),
    "Tỷ Phú": EventConfig(
        tab_attr_name="_typhu_tab",
        spin_actions={1: "20 FC Spin", 2: "190 FC Spin", 3: "900 FC Spin", 4: "1800 FC Spin"},
        base_url="https://typhu.fconline.garena.vn",
        user_endpoint="api/user/get",
        spin_endpoint="api/user/spin",
    ),
}
