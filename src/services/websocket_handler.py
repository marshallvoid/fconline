import asyncio
import json
import re
from typing import Callable, Optional, Tuple

from browser_use.browser.types import Page
from loguru import logger
from playwright.async_api import WebSocket  # noqa: DEP003

from src.infrastructure.clients.fco import FCOnlineClient
from src.schemas.enums.message_tag import MessageTag
from src.schemas.user_response import UserReponse
from src.utils import methods as md
from src.utils import sounds
from src.utils.contants import EventConfig


class WebsocketHandler:
    # Regex pattern to extract socket payload from websocket frames
    # Format: 42[{"content": {...}}] where 42 is the socket.io message prefix
    _SOCKET_PAYLOAD_RE = re.compile(r"42(\[.*\])")

    def __init__(
        self,
        page: Page,
        event_config: EventConfig,
        username: str,
        spin_action: int,
        target_special_jackpot: int,
        current_jackpot: int,
        on_account_won: Optional[Callable[[str], None]] = None,
        on_add_message: Optional[Callable[[MessageTag, str], None]] = None,
        on_add_notification: Optional[Callable[[str, str], None]] = None,
        on_update_current_jackpot: Optional[Callable[[int], None]] = None,
        on_update_ultimate_prize_winner: Optional[Callable[[str, str], None]] = None,
        on_update_mini_prize_winner: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        self._page = page
        self._event_config = event_config
        self._username = username
        self._spin_action = spin_action
        self._target_special_jackpot = target_special_jackpot
        self._current_jackpot = current_jackpot

        self._on_account_won = on_account_won
        self._on_add_message = on_add_message
        self._on_add_notification = on_add_notification
        self._on_update_current_jackpot = on_update_current_jackpot
        self._on_update_ultimate_prize_winner = on_update_ultimate_prize_winner
        self._on_update_mini_prize_winner = on_update_mini_prize_winner

        self._is_logged_in: bool = False
        self._user_info: Optional[UserReponse] = None
        self._fconline_client: Optional[FCOnlineClient] = None

        # Task management for spin operations
        self._spin_lock = asyncio.Lock()
        self._spin_task: Optional[asyncio.Task] = None

        # Epoch counter to track jackpot resets and prevent stale spin operations
        self._jackpot_epoch: int = 0

    @property
    def is_logged_in(self) -> bool:
        return self._is_logged_in

    @is_logged_in.setter
    def is_logged_in(self, new_is_logged_in: bool) -> None:
        self._is_logged_in = new_is_logged_in

    @property
    def fconline_client(self) -> Optional[FCOnlineClient]:
        return self._fconline_client

    @fconline_client.setter
    def fconline_client(self, new_fconline_client: FCOnlineClient) -> None:
        self._fconline_client = new_fconline_client

    @property
    def user_info(self) -> Optional[UserReponse]:
        return self._user_info

    @user_info.setter
    def user_info(self, new_user_info: UserReponse) -> None:
        self._user_info = new_user_info

    def setup_websocket(self) -> None:
        logger.info(f"🔌 Monitoring WebSocket on {self._page.url}")

        def _on_websocket(websocket: WebSocket) -> None:
            # Only process websocket events when logged in
            if not self._is_logged_in:
                return

            logger.info(f"🔌 WebSocket opened: {websocket.url}")

            async def _on_framereceived(frame: bytes | str) -> None:
                # Convert frame to string and parse for jackpot events
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

        self._page.on("websocket", _on_websocket)  # type: ignore

    async def _parse_socket_frame(self, frame: str) -> Optional[Tuple[str, int | str, str]]:
        # Extract the JSON payload from socket.io message format
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
            data = content.get("data", {})
            value = content.get("value") or data.get("jackpot_prize")
            nickname = content.get("nickname") or data.get("account_name")

            if not isinstance(etype, str) or not isinstance(value, (int, str)):
                return None

            return etype, value, nickname

        except json.JSONDecodeError:
            logger.info("🔌 WebSocket frame received but failed to parse JSON")
            return None

    async def _handle_jackpot_event(self, kind: str, value: int | str, nickname: str = "") -> None:
        try:
            match kind:
                case "jackpot_value" | "prize_change":
                    md.should_execute_callback(self._on_add_message, MessageTag.WEBSOCKET, f"Jackpot value: {value}")

                    # Handle real-time jackpot value updates
                    new_value = int(value)
                    prev_value = self._current_jackpot

                    # Detect jackpot reset/drop - increase epoch and cancel pending spins
                    if new_value < prev_value:
                        self._jackpot_epoch += 1
                        self._cancel_spin_task()

                    self._current_jackpot = new_value

                    # Check if special jackpot target reached
                    if new_value >= self._target_special_jackpot:
                        md.should_execute_callback(
                            self._on_add_message,
                            MessageTag.REACHED_GOAL,
                            f"Special Jackpot has reached {self._target_special_jackpot:,}",
                        )

                        # Trigger immediate spin when target is reached
                        if not self._spin_task or self._spin_task.done():
                            epoch_snapshot = self._jackpot_epoch
                            self._spin_task = asyncio.create_task(self._attempt_spin(epoch_snapshot))

                    md.should_execute_callback(self._on_update_current_jackpot, new_value)

                case "jackpot" | "mini_jackpot":
                    # Stop auto spin when any jackpot is won by anyone
                    self._cancel_spin_task()

                    is_jackpot = kind == "jackpot"
                    if is_jackpot:
                        # Reset jackpot value and increment epoch when ultimate prize is won
                        self._jackpot_epoch += 1
                        self._current_jackpot = 0

                    self._check_winner(is_jackpot=is_jackpot, target_nickname=nickname, target_value=value)

                case _:
                    logger.warning("Unknown event type: {}", kind)

        except asyncio.CancelledError:
            logger.warning("Spin aborted: jackpot reset/drop")

        except Exception as e:
            logger.error(f"Spin API error: {e}")
            md.should_execute_callback(self._on_add_message, MessageTag.ERROR, f"Spin API error: {e}")

    async def _attempt_spin(self, epoch_snapshot: int) -> None:
        if not self._fconline_client:
            return

        try:
            async with self._spin_lock:
                # Verify epoch hasn't changed (jackpot wasn't reset)
                if epoch_snapshot != self._jackpot_epoch:
                    logger.warning(f"⛔ Spin aborted: epoch changed (was {epoch_snapshot}, now {self._jackpot_epoch})")
                    return

                # Verify jackpot value still meets target threshold
                if self._current_jackpot < self._target_special_jackpot:
                    logger.warning(f"⛔ Spin aborted: jackpot dropped to {self._current_jackpot}")
                    return

                # Execute the spin operation
                await self._fconline_client.spin(spin_type=self._spin_action, params=self._event_config.params)

        except asyncio.CancelledError:
            logger.warning("Spin aborted: jackpot reset/drop")

        except Exception as e:
            logger.error(f"Spin API error: {e}")
            md.should_execute_callback(self._on_add_message, MessageTag.ERROR, f"Spin API error: {e}")

        finally:
            self._spin_task = None

    def _check_winner(self, is_jackpot: bool, target_nickname: str, target_value: int | str) -> None:
        try:
            user = self._user_info and self._user_info.payload and self._user_info.payload.user
            nickname_lower = target_nickname.lower()
            is_me = bool(
                user
                and (
                    (user.nickname and nickname_lower == user.nickname.lower())
                    or (user.account_name and nickname_lower == user.account_name.lower())
                )
            )

        except Exception:
            is_me = False

        tag = MessageTag.OTHER_PLAYER
        prefix = "You" if is_me else f"User '{target_nickname}'"
        suffix = "Ultimate Prize" if is_jackpot else "Mini Prize"
        msg = f"{prefix} won {suffix}: {str(target_value)}"

        if is_me:
            tag = MessageTag.JACKPOT if is_jackpot else MessageTag.MINI_JACKPOT
            audio_name = "coin-1" if is_jackpot else "coin-2"

            md.should_execute_callback(self._on_add_notification, target_nickname, str(target_value))
            sounds.send_notification(msg, audio_name=audio_name)
            md.should_execute_callback(self._on_account_won, self._username)

        md.should_execute_callback(self._on_add_message, tag, msg)

        if is_jackpot:
            md.should_execute_callback(self._on_update_ultimate_prize_winner, target_nickname, str(target_value))
        else:
            md.should_execute_callback(self._on_update_mini_prize_winner, target_nickname, str(target_value))

    def _cancel_spin_task(self) -> None:
        if self._spin_task and not self._spin_task.done():
            logger.info(f"🧹 Cancel pending spin task (epoch {self._jackpot_epoch})")
            self._spin_task.cancel()
        self._spin_task = None
