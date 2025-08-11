import json
import re
from typing import Callable, Optional

from loguru import logger
from playwright.async_api import Page, WebSocket


class WebSocketMonitor:
    """Monitors WebSocket connections for real-time jackpot updates."""

    def __init__(self) -> None:
        """Initialize the WebSocket monitor."""
        self._special_jackpot: int = 0
        self._mini_jackpot: int = 0

        # Callbacks for GUI updates
        self.message_callback: Optional[Callable[[str, str], None]] = None
        self.special_jackpot_callback: Optional[Callable[[], None]] = None

    def setup_websocket_listeners(self, page: Page) -> None:
        """
        Setup WebSocket listeners for real-time jackpot updates.

        Args:
            page: Playwright page instance
        """

        def handle_websocket(websocket: WebSocket) -> None:
            async def on_framereceived(frame: bytes | str) -> None:
                if not frame or not isinstance(frame, str):
                    return
                self._process_frame(frame=frame)

            websocket.on("framereceived", on_framereceived)
            websocket.on("framesent", lambda frame: logger.info(f"🔗 WebSocket frame sent: {frame}"))
            websocket.on("close", lambda ws: logger.info(f"🔌 WebSocket[{ws.url}] connection closed"))

        page.on("websocket", handle_websocket)

    def _process_frame(self, frame: str) -> None:  # noqa: C901
        """
        Process WebSocket frame data for jackpot updates.

        Args:
            frame: Raw WebSocket frame string
        """
        # Handle Socket.IO format: 42["message",{"content":{...}}]
        if not frame.startswith("42["):
            return

        # Extract JSON part after "42"
        json_match = re.search(r"42(\[.*\])", frame)
        if not json_match:
            return

        json_str = json_match.group(1)
        try:
            # Socket.IO format is usually ["event_name", event_data (dict)]
            socket_data = json.loads(json_str)
            if not isinstance(socket_data, list) or len(socket_data) < 2:
                return

            event_data = socket_data[1]
            if not isinstance(event_data, dict):
                return

            # Check nested content
            content = event_data.get("content")
            if not content or not isinstance(content, dict):
                return

            type = content.get("type")
            value = content.get("value")
            if not isinstance(type, str) or not type or not isinstance(value, int) or value is None:
                return

            match type:
                case "jackpot_value":
                    logger.success(f"🎰 Special Jackpot: {value}")
                    prev_jackpot = self._special_jackpot
                    self._special_jackpot = value

                    # Use special jackpot callback to update user info instead of message
                    if self.special_jackpot_callback:
                        self.special_jackpot_callback()

                    # Only show message when target is reached
                    if value >= self._target_special_jackpot and self.message_callback:
                        self.message_callback(
                            f"🎯 Special Jackpot has reached {self._target_special_jackpot}",
                            "target",
                        )

                        # If target just reached (wasn't reached before), trigger auto-spin
                        if prev_jackpot < self._target_special_jackpot:
                            self._on_target_reached()

                case "mini_jackpot":
                    logger.success(f"🎯 Mini Jackpot: {value}")
                    self._mini_jackpot = value

                    if self.message_callback:
                        self.message_callback(f"🎯 Mini Jackpot: {value}", "event")

        except json.JSONDecodeError:
            pass  # Ignore JSON decode errors

    def set_target_jackpot(self, target: int) -> None:
        """
        Set the target jackpot value for auto-spin triggering.

        Args:
            target: Target jackpot value
        """
        self._target_special_jackpot = target

    def set_auto_spin_callback(self, callback: Callable[[], None]) -> None:
        """
        Set callback for when target jackpot is reached.

        Args:
            callback: Function to call when target is reached
        """
        self._on_target_reached = callback

    @property
    def special_jackpot(self) -> int:
        """Get current special jackpot value."""
        return self._special_jackpot

    @property
    def mini_jackpot(self) -> int:
        """Get current mini jackpot value."""
        return self._mini_jackpot
