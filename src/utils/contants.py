from typing import Dict

from src.core.event_config import EventConfig

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
