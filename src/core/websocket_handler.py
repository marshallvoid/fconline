import asyncio
import json
import re
from typing import Callable, Dict, Optional, Self

import aiohttp
from browser_use.browser.types import Page
from loguru import logger
from playwright.async_api import WebSocket

from src.core.event_config import EventConfig
from src.schemas.spin_response import SpinResponse
from src.utils.methods import format_spin_block_compact, should_execute_callback
from src.utils.requests import RequestManager


class WebsocketHandler:
    page: Page
    is_logged_in: bool = False
    cookies: Dict[str, str] = {}
    headers: Dict[str, str] = {}
    event_config: EventConfig
    spin_action: int
    special_jackpot: int
    mini_jackpot: int
    target_special_jackpot: int
    message_callback: Optional[Callable[[str, str], None]] = None
    jackpot_callback: Optional[Callable[[int], None]] = None

    _spin_task: Optional[asyncio.Task] = None
    _spin_lock = asyncio.Lock()

    @classmethod
    def setup(
        cls,
        page: Page,
        event_config: EventConfig,
        spin_action: int,
        special_jackpot: int,
        mini_jackpot: int,
        target_special_jackpot: int,
        message_callback: Optional[Callable[[str, str], None]] = None,
        jackpot_callback: Optional[Callable[[int], None]] = None,
    ) -> type[Self]:
        cls.page = page
        cls.event_config = event_config
        cls.spin_action = spin_action
        cls.special_jackpot = special_jackpot
        cls.mini_jackpot = mini_jackpot
        cls.target_special_jackpot = target_special_jackpot
        cls.message_callback = message_callback
        cls.jackpot_callback = jackpot_callback

        cls._spin_task = None  # Reset spin state on setup to avoid stale tasks
        return cls

    @classmethod
    def run(cls) -> None:
        logger.info(f"🔌 Starting WebSocket monitoring for {cls.page.url}")

        def _on_websocket(websocket: WebSocket) -> None:
            if not cls.is_logged_in:
                return

            logger.info(f"🔌 WebSocket connection established: {websocket.url}")

            def _on_framereceived(frame: bytes | str) -> None:
                cls._extract_frame(frame=frame)

            websocket.on("framereceived", _on_framereceived)
            websocket.on("framesent", lambda frame: logger.info(f"🔌 WebSocket frame sent: {frame}"))
            websocket.on("close", lambda ws: logger.info(f"🔌 WebSocket connection closed: {ws.url}"))

        cls.page.on("websocket", _on_websocket)

    @classmethod
    def _extract_frame(cls, frame: bytes | str) -> None:
        if not frame:
            return

        if isinstance(frame, bytes):
            frame = frame.decode("utf-8")

        logger.info(f"🔌 WebSocket frame received: {frame}")

        json_match = re.search(r"42(\[.*\])", frame)
        if not json_match:
            return

        json_str = json_match.group(1)
        try:
            socket_data = json.loads(json_str)
            if not isinstance(socket_data, list) or len(socket_data) < 2:
                return

            event_data = socket_data[1]
            if not isinstance(event_data, dict):
                return

            content = event_data.get("content")
            if not content or not isinstance(content, dict):
                return

            type, value = content.get("type"), content.get("value")
            if type is None or not isinstance(type, str) or value is None or not isinstance(value, int):
                return

            cls._handle_jackpot(type=type, value=value)

        except json.JSONDecodeError:
            logger.debug("🔌 WebSocket frame received but failed to parse JSON")

    @classmethod
    def _handle_jackpot(cls, type: str, value: int) -> None:
        match type:
            case "jackpot_value":
                logger.info(f"Special Jackpot: {value:,}")
                cls.special_jackpot = value

                if value >= cls.target_special_jackpot:
                    msg = f"Special Jackpot has reached {cls.target_special_jackpot:,}"
                    logger.success(f"🔌 {msg}")
                    should_execute_callback(cls.message_callback, "jackpot", msg)

                # Start/stop spin task depending on live value
                asyncio.create_task(cls._ensure_spin_state())

                should_execute_callback(cls.jackpot_callback, value)

            case "mini_jackpot":
                logger.info(f"Mini Jackpot: {value:,}")
                cls.mini_jackpot = value

            case _:
                should_execute_callback(cls.message_callback, "error", f"Unknown event type: {type}: {value}")

    @classmethod
    async def _ensure_spin_state(cls) -> None:
        """Start spin when jackpot >= target; stop otherwise. Single flight."""
        async with cls._spin_lock:
            should_spin = cls.special_jackpot >= cls.target_special_jackpot
            task_alive = cls._spin_task and not cls._spin_task.done()

            if should_spin and not task_alive:
                logger.info("▶️ Starting auto-spin API task")
                cls._spin_task = asyncio.create_task(cls._auto_spin_api())

            elif not should_spin and task_alive:
                logger.info("⏹️ Stopping auto-spin task (jackpot below target)")
                if cls._spin_task:
                    cls._spin_task.cancel()
                    try:
                        await cls._spin_task
                    except asyncio.CancelledError:
                        pass
                    finally:
                        cls._spin_task = None

    @classmethod
    async def _auto_spin_api(cls) -> None:
        try:
            async with aiohttp.ClientSession(
                cookies=cls.cookies,
                headers=cls.headers,
                connector=RequestManager.connector(),
            ) as session:
                while True:
                    # Live condition
                    if cls.special_jackpot < cls.target_special_jackpot:
                        logger.info("✅ Jackpot dropped below target — stopping auto-spin API")
                        break

                    if getattr(cls.page, "is_closed", lambda: False)():
                        logger.warning("🛑 Page is closed; stopping auto-spin API")
                        break

                    try:
                        async with session.post(
                            url=f"{cls.event_config.base_url}/{cls.event_config.spin_endpoint}",
                            json={"spin_type": cls.spin_action, "payment_type": 1},
                        ) as response:
                            if not response.ok:
                                logger.error(f"❌ API request failed with status: {response.status}")
                                break

                            schema = SpinResponse.model_validate(await response.json())
                            if not schema.payload or not schema.is_successful or schema.error_code:
                                msg = f"Auto-spin failed: {schema.error_code or 'Unknown error'}"
                                logger.error(f"❌ {msg}")
                                should_execute_callback(cls.message_callback, "error", msg)
                                break

                            should_execute_callback(
                                cls.message_callback,
                                "reward",
                                format_spin_block_compact(
                                    spin_results=schema.payload.spin_results,
                                    jackpot_value=schema.payload.jackpot_value,
                                ),
                            )

                    except Exception as e:
                        logger.error(f"❌ Auto-spin API error: {e}")
                        should_execute_callback(cls.message_callback, "error", f"Auto-spin API error: {e}")
                        break

                    await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info("🌀 Auto-spin API task cancelled")
            raise

        finally:
            # Ensure spin task is cleaned up
            if cls._spin_task and not cls._spin_task.done():
                cls._spin_task.cancel()
                try:
                    await cls._spin_task
                except asyncio.CancelledError:
                    pass
                finally:
                    cls._spin_task = None
