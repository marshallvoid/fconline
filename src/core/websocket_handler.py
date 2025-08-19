import asyncio
import json
import re
from typing import Callable, Optional, Tuple

from browser_use.browser.types import Page
from loguru import logger
from playwright.async_api import WebSocket

from src.core.event_config import EventConfig
from src.infrastructure.clients.fconline_api import FCOnlineClient
from src.schemas.enums.message_tag import MessageTag
from src.schemas.user_response import UserReponse
from src.utils import methods as md
from src.utils import sounds


class WebsocketHandler:
    _SOCKET_PAYLOAD_RE = re.compile(r"42(\[.*\])")

    def __init__(
        self,
        page: Page,
        event_config: EventConfig,
        spin_action: int,
        current_jackpot: int,
        target_special_jackpot: int,
        target_mini_jackpot: int,
        close_when_jackpot_won: bool,
        close_when_mini_jackpot_won: bool,
        add_message: Optional[Callable[[str, str], None]] = None,
        add_notification: Optional[Callable[[str, str], None]] = None,
        update_current_jackpot: Optional[Callable[[int], None]] = None,
        close_browser: Optional[Callable[[], None]] = None,
    ) -> None:
        self._page = page
        self._event_config = event_config
        self._spin_action = spin_action
        self._current_jackpot = current_jackpot
        self._target_special_jackpot = target_special_jackpot
        self._target_mini_jackpot = target_mini_jackpot
        self._close_when_jackpot_won = close_when_jackpot_won
        self._close_when_mini_jackpot_won = close_when_mini_jackpot_won
        self._add_message = add_message
        self._add_notification = add_notification
        self._update_current_jackpot = update_current_jackpot
        self._close_browser = close_browser

        self._is_logged_in: bool = False
        self._fconline_client: Optional[FCOnlineClient] = None
        self._user_info: Optional[UserReponse] = None

        self._spin_task: Optional[asyncio.Task] = None
        self._spin_lock = asyncio.Lock()
        self._jackpot_epoch: int = 0

    @property
    def is_logged_in(self) -> bool:
        return self._is_logged_in

    @is_logged_in.setter
    def is_logged_in(self, is_logged_in: bool) -> None:
        self._is_logged_in = is_logged_in

    @property
    def fconline_client(self) -> Optional[FCOnlineClient]:
        return self._fconline_client

    @fconline_client.setter
    def fconline_client(self, fconline_client: FCOnlineClient) -> None:
        self._fconline_client = fconline_client

    @property
    def user_info(self) -> Optional[UserReponse]:
        return self._user_info

    @user_info.setter
    def user_info(self, user_info: UserReponse) -> None:
        self._user_info = user_info

    def setup_websocket(self) -> None:
        logger.info(f"🔌 Monitoring WebSocket on {self._page.url}")

        def _on_websocket(websocket: WebSocket) -> None:
            if not self._is_logged_in:
                return

            logger.info(f"🔌 WebSocket opened: {websocket.url}")

            async def _on_framereceived(frame: bytes | str) -> None:
                frame_str = frame if isinstance(frame, str) else frame.decode("utf-8", errors="ignore")
                logger.info(f"🔌 Frame received: {frame_str[:256]}")

                result = await self._parse_socket_frame(frame=frame_str)
                if result:
                    type, value, nickname = result
                    await self._handle_jackpot_event(kind=type, value=value, nickname=nickname)

            def _on_framesent(frame: bytes | str) -> None:
                frame_str = frame if isinstance(frame, str) else frame.decode("utf-8", errors="ignore")
                logger.info("🔌 Frame sent: {}", frame_str[:256])

            def _on_close(ws: WebSocket) -> None:
                logger.info(f"🔌 WebSocket closed: {ws.url}")

            websocket.on("framereceived", _on_framereceived)
            websocket.on("framesent", _on_framesent)
            websocket.on("close", _on_close)

        self._page.on("websocket", _on_websocket)

    async def _parse_socket_frame(self, frame: str) -> Optional[Tuple[str, int | str, str]]:
        m = self._SOCKET_PAYLOAD_RE.search(frame)
        if not m:
            return None

        try:
            socket_data = json.loads(m.group(1))
            if not isinstance(socket_data, list) or len(socket_data) < 2:
                return None

            event_data = socket_data[1]
            if not isinstance(event_data, dict):
                return None

            content = event_data.get("content")
            if not isinstance(content, dict):
                return None

            etype = content.get("type")
            value = content.get("value")
            if not isinstance(etype, str) or not isinstance(value, (int, str)):
                return None

            return etype, value, content.get("nickname", "")

        except json.JSONDecodeError:
            logger.info("🔌 WebSocket frame received but failed to parse JSON")
            return None

    async def _handle_jackpot_event(self, kind: str, value: int | str, nickname: str = "") -> None:
        try:
            match kind:
                case "jackpot_value":
                    new_value = int(value)
                    prev_value = self._current_jackpot

                    # Detect reset/drop -> increase epoch & cancel pending spin task
                    if new_value < prev_value:
                        self._jackpot_epoch += 1
                        self._cancel_spin_task()

                    self._current_jackpot = new_value

                    if new_value >= self._target_special_jackpot:
                        md.should_execute_callback(
                            self._add_message,
                            MessageTag.REACHED_GOAL,
                            f"Special Jackpot has reached {self._target_special_jackpot:,}",
                        )

                        # Trigger immediate spin when target is reached
                        if not self._spin_task or self._spin_task.done():
                            epoch_snapshot = self._jackpot_epoch
                            self._spin_task = asyncio.create_task(self._attempt_spin(epoch_snapshot))

                    md.should_execute_callback(self._update_current_jackpot, new_value)

                case "jackpot" | "mini_jackpot":
                    try:
                        user = self._user_info and self._user_info.payload.user
                        is_me = bool(user and nickname and nickname.lower() == user.nickname.lower())
                    except Exception:
                        is_me = False

                    is_jackpot = kind == "jackpot"
                    if is_jackpot:
                        self._jackpot_epoch += 1
                        self._cancel_spin_task()
                        self._current_jackpot = 0

                    tag = (
                        MessageTag.JACKPOT
                        if is_jackpot and is_me
                        else MessageTag.OTHER_PLAYER if not is_me else MessageTag.MINI_JACKPOT
                    )
                    prefix = "You" if is_me else f"User '{nickname}'"
                    suffix = "Ultimate Prize" if is_jackpot else "Mini Prize"
                    msg = f"{prefix} won {suffix}: {value}"

                    if is_me:
                        audio_name = "coin-1" if is_jackpot else "coin-2"
                        md.should_execute_callback(self._add_notification, nickname, value)
                        sounds.send_notification(msg, audio_name=audio_name)

                        # Check if browser should be closed
                        if (is_jackpot and self._close_when_jackpot_won) or (
                            not is_jackpot and self._close_when_mini_jackpot_won
                        ):
                            md.should_execute_callback(self._close_browser)

                    md.should_execute_callback(self._add_message, tag, msg)

                case _:
                    logger.warning("Unknown event type: {}", kind)

        except asyncio.CancelledError:
            md.should_execute_callback(self._add_message, MessageTag.WARNING, "Spin aborted: jackpot reset/drop")

        except Exception as e:
            logger.error(f"Spin API error: {e}")
            md.should_execute_callback(self._add_message, MessageTag.ERROR, f"Spin API error: {e}")

    async def _attempt_spin(self, epoch_snapshot: int) -> None:
        if not self._fconline_client:
            return

        try:
            async with self._spin_lock:
                # Epoch must still match (not reset)
                if epoch_snapshot != self._jackpot_epoch:
                    logger.warning(f"⛔ Spin aborted: epoch changed (was {epoch_snapshot}, now {self._jackpot_epoch})")
                    return

                # Current value must still be >= target
                if self._current_jackpot < self._target_special_jackpot:
                    logger.warning(f"⛔ Spin aborted: jackpot dropped to {self._current_jackpot}")
                    return

                await self._fconline_client.spin(spin_type=self._spin_action, payment_type=1)

        except asyncio.CancelledError:
            md.should_execute_callback(self._add_message, MessageTag.WARNING, "Spin aborted: jackpot reset/drop")

        except Exception as e:
            logger.error(f"Spin API error: {e}")
            md.should_execute_callback(self._add_message, MessageTag.ERROR, f"Spin API error: {e}")

        finally:
            self._spin_task = None

    def _cancel_spin_task(self) -> None:
        if self._spin_task and not self._spin_task.done():
            logger.info(f"🧹 Cancel pending spin task (epoch {self._jackpot_epoch})")
            self._spin_task.cancel()
        self._spin_task = None
