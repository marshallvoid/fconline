import asyncio
import json
import re
from typing import Callable, Dict, Optional, Self

import aiohttp
from browser_use.browser.types import Page
from loguru import logger
from playwright.async_api import WebSocket

from src.core.event_config import EventConfig
from src.schemas.enums.message_tag import MessageTag
from src.schemas.spin_response import SpinResponse
from src.schemas.user_response import UserReponse
from src.utils import methods as md
from src.utils import sounds
from src.utils.requests import RequestManager


class WebsocketHandler:
    _page: Page

    is_logged_in: bool = False
    cookies: Dict[str, str] = {}
    headers: Dict[str, str] = {}
    user_info: Optional[UserReponse] = None

    _event_config: EventConfig
    _spin_action: int
    _special_jackpot: int
    _mini_jackpot: int
    _target_special_jackpot: int

    _message_callback: Optional[Callable[[str, str], None]] = None
    _jackpot_callback: Optional[Callable[[int], None]] = None
    _notification_callback: Optional[Callable[[str, str], None]] = None

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
        jackpot_billboard_callback: Optional[Callable[[str, str], None]] = None,
    ) -> type[Self]:
        cls._page = page
        cls._event_config = event_config
        cls._spin_action = spin_action
        cls._special_jackpot = special_jackpot
        cls._mini_jackpot = mini_jackpot
        cls._target_special_jackpot = target_special_jackpot
        cls._message_callback = message_callback
        cls._jackpot_callback = jackpot_callback
        cls._notification_callback = jackpot_billboard_callback

        cls._spin_task = None

        return cls

    @classmethod
    def run(cls) -> None:
        logger.info(f"🔌 Starting WebSocket monitoring for {cls._page.url}")

        def _on_websocket(websocket: WebSocket) -> None:
            if not cls.is_logged_in:
                return

            logger.info(f"🔌 WebSocket connection established: {websocket.url}")

            async def _on_framereceived(frame: bytes | str) -> None:
                if not frame:
                    return

                if isinstance(frame, bytes):
                    frame = frame.decode("utf-8")

                logger.info(f"🔌 WebSocket frame received: {frame}")

                await cls._extract_frame(frame=frame)

            websocket.on("framereceived", _on_framereceived)
            websocket.on("framesent", lambda frame: logger.debug(f"🔌 WebSocket frame sent: {frame}"))
            websocket.on("close", lambda ws: logger.info(f"🔌 WebSocket connection closed: {ws.url}"))

        cls._page.on("websocket", _on_websocket)

    @classmethod
    async def _extract_frame(cls, frame: str) -> None:
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
            if type is None or not isinstance(type, str) or value is None or not isinstance(value, (int, str)):
                return

            await cls._handle_jackpot(type=type, value=value, nickname=content.get("nickname", ""))

        except json.JSONDecodeError:
            logger.debug("🔌 WebSocket frame received but failed to parse JSON")

    @classmethod
    async def _handle_jackpot(cls, type: str, value: int | str, nickname: str = "") -> None:
        is_me = False
        if cls.user_info and cls.user_info.payload.user:
            is_me = nickname.lower() == cls.user_info.payload.user.nickname.lower()

        match type:
            case "jackpot_value":
                value = int(value)
                cls._special_jackpot = value

                if value >= cls._target_special_jackpot:
                    msg = f"Special Jackpot has reached {cls._target_special_jackpot:,}"
                    md.should_execute_callback(cls._message_callback, MessageTag.JACKPOT.name, msg)

                    # Trigger immediate spin when target is reached
                    if not cls._spin_task or cls._spin_task.done():
                        logger.info("🎯 Target jackpot reached - triggering immediate spin")
                        cls._spin_task = asyncio.create_task(cls._execute_single_spin())

                md.should_execute_callback(cls._jackpot_callback, value)

            case "jackpot":
                msg = f"You won jackpot: {value}" if is_me else f"User '{nickname}' won jackpot: {value}"
                tag = MessageTag.WINNER.name if is_me else MessageTag.INFO.name

                md.should_execute_callback(cls._notification_callback, nickname, value) if is_me else None
                md.should_execute_callback(cls._message_callback, tag, msg)
                sounds.send_notification(msg, audio_name="coin_flip" if is_me else "game_bonus")

            case "mini_jackpot":
                msg = f"You won mini jackpot: {value}" if is_me else f"User '{nickname}' won mini jackpot: {value}"
                tag = MessageTag.WINNER.name if is_me else MessageTag.INFO.name

                md.should_execute_callback(cls._message_callback, tag, msg)

            case _:
                md.should_execute_callback(cls._message_callback, MessageTag.ERROR.name, f"Unknown event type: {type}")

    @classmethod
    async def _execute_single_spin(cls) -> None:
        cookies, headers, connector = cls.cookies, cls.headers, RequestManager.connector()
        url = f"{cls._event_config.base_url}/{cls._event_config.spin_endpoint}"
        payload = {"spin_type": cls._spin_action, "payment_type": 1}

        try:
            async with aiohttp.ClientSession(cookies=cookies, headers=headers, connector=connector) as session:
                async with session.post(url=url, json=payload) as response:
                    if not response.ok:
                        logger.error(f"❌ Spin API request failed with status: {response.status}")
                        md.should_execute_callback(
                            cls._message_callback,
                            MessageTag.ERROR.name,
                            f"Spin API failed: HTTP {response.status}",
                        )
                        return

                    spin_response = SpinResponse.model_validate(await response.json())
                    if not spin_response.payload or not spin_response.is_successful or spin_response.error_code:
                        msg = f"Spin failed: {spin_response.error_code or 'Unknown error'}"
                        logger.error(f"❌ {msg}")
                        md.should_execute_callback(cls._message_callback, MessageTag.ERROR.name, msg)
                        return

                    md.should_execute_callback(
                        cls._message_callback,
                        MessageTag.REWARD.name,
                        md.format_spin_block_compact(
                            spin_results=spin_response.payload.spin_results,
                            jackpot_value=spin_response.payload.jackpot_value,
                        ),
                    )
                    logger.info("✅ Single spin executed successfully")

        except Exception as e:
            logger.error(f"❌ Spin API error: {e}")
            md.should_execute_callback(cls._message_callback, MessageTag.ERROR.name, f"Spin API error: {e}")

        finally:
            cls._spin_task = None
