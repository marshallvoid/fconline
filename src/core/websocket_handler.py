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

    _jackpot_epoch: int = 0
    _last_jackpot_value: int = 0

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

        try:
            match type:
                case "jackpot_value":
                    value = int(value)

                    # Detect reset/drop -> increase epoch & cancel pending spin task
                    if value < cls._special_jackpot:
                        cls._jackpot_epoch += 1
                        cls._cancel_spin_task()

                    cls._special_jackpot = value
                    cls._last_jackpot_value = value

                    if value >= cls._target_special_jackpot:
                        md.should_execute_callback(
                            cls._message_callback,
                            MessageTag.JACKPOT.name,
                            f"Special Jackpot has reached {cls._target_special_jackpot:,}",
                        )

                        # Trigger immediate spin when target is reached
                        if not cls._spin_task or cls._spin_task.done():
                            epoch_snapshot = cls._jackpot_epoch
                            logger.info("🎯 Target jackpot reached - triggering immediate spin")
                            cls._spin_task = asyncio.create_task(cls._execute_single_spin(epoch_snapshot))

                    md.should_execute_callback(cls._jackpot_callback, value)

                case "jackpot":
                    msg = f"You won jackpot: {value}" if is_me else f"User '{nickname}' won jackpot: {value}"
                    tag = MessageTag.WINNER.name if is_me else MessageTag.INFO.name

                    # Jackpot payout ⇒ reset epoch & cancel pending spin task
                    cls._jackpot_epoch += 1
                    cls._cancel_spin_task()
                    cls._special_jackpot = 0
                    cls._last_jackpot_value = 0

                    if is_me:
                        md.should_execute_callback(cls._notification_callback, nickname, value)
                        sounds.send_notification(msg, audio_name="coin-1")
                    md.should_execute_callback(cls._message_callback, tag, msg)

                case "mini_jackpot":
                    msg = f"You won mini jackpot: {value}" if is_me else f"User '{nickname}' won mini jackpot: {value}"
                    tag = MessageTag.WINNER.name if is_me else MessageTag.INFO.name

                    md.should_execute_callback(cls._message_callback, tag, msg)

                case _:
                    md.should_execute_callback(
                        cls._message_callback, MessageTag.ERROR.name, f"Unknown event type: {type}"
                    )

        except asyncio.CancelledError:
            msg = "Spin aborted: jackpot reset/drop"
            logger.info(f"🛑 {msg}")
            md.should_execute_callback(cls._message_callback, MessageTag.ERROR.name, msg)

        except Exception as e:
            msg = f"Spin API error: {e}"
            logger.error(f"❌ {msg}")
            md.should_execute_callback(cls._message_callback, MessageTag.ERROR.name, msg)

    @classmethod
    async def _execute_single_spin(cls, epoch_snapshot: int) -> None:
        if cls._special_jackpot < cls._target_special_jackpot:
            return

        cookies, headers, connector = cls.cookies, cls.headers, RequestManager.connector()
        url = f"{cls._event_config.base_url}/{cls._event_config.spin_endpoint}"
        payload = {"spin_type": cls._spin_action, "payment_type": 1}

        try:
            async with cls._spin_lock:
                # 1) Epoch must still match (not reset)
                if epoch_snapshot != cls._jackpot_epoch:
                    logger.info(f"⛔ Spin aborted: epoch changed (was {epoch_snapshot}, now {cls._jackpot_epoch})")
                    return

                # 2) Current value must still be >= target
                if cls._special_jackpot < cls._target_special_jackpot:
                    logger.info(f"⛔ Spin aborted: jackpot dropped to {cls._special_jackpot}")
                    return

                async with aiohttp.ClientSession(cookies=cookies, headers=headers, connector=connector) as session:
                    async with session.post(url=url, json=payload) as response:
                        if not response.ok:
                            msg = f"Spin API request failed with status: {response.status}"
                            logger.error(f"❌ {msg}")
                            md.should_execute_callback(cls._message_callback, MessageTag.ERROR.name, msg)
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

        except asyncio.CancelledError:
            msg = "Spin aborted: jackpot reset/drop"
            logger.info(f"🛑 {msg}")
            md.should_execute_callback(cls._message_callback, MessageTag.ERROR.name, msg)

        except Exception as e:
            msg = f"Spin API error: {e}"
            logger.error(f"❌ {msg}")
            md.should_execute_callback(cls._message_callback, MessageTag.ERROR.name, msg)

        finally:
            cls._spin_task = None

    @classmethod
    def _cancel_spin_task(cls) -> None:
        if cls._spin_task and not cls._spin_task.done():
            logger.info("🧹 Jackpot reset/dropped — cancelling pending spin task")
            cls._spin_task.cancel()
        cls._spin_task = None
