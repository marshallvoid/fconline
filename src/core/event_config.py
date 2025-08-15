from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class EventConfig:
    name: str

    # URLs
    base_url: str
    api_url: str

    # Login/logout selectors
    login_btn_selector: str
    logout_btn_selector: str
    username_input_selector: str
    password_input_selector: str
    submit_btn_selector: str

    # Mapping: action number -> (css_selector, display_label)
    spin_action_selectors: Dict[int, Tuple[str, str]]
