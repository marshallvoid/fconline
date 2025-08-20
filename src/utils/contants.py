from typing import Dict

from src.core.event_config import EventConfig

# Application name displayed in UI and notifications
PROGRAM_NAME = "FC Online Automation Tool"

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
