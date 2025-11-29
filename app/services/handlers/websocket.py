# pyright: reportOptionalMemberAccess=false
import asyncio
import contextlib
import json
import re
import threading
import time
from typing import TYPE_CHECKING, Any, Optional, Tuple

from loguru import logger
from playwright.async_api import WebSocket  # noqa: DEP003

from app.core.managers.notifier import notifier_mgr
from app.infrastructure.clients.main import MainClient
from app.schemas.enums.message_tag import MessageTag
from app.schemas.user_response import UserReponse
from app.utils.concurrency import run_in_thread
from app.utils.helpers import format_results_block
from app.utils.sounds import play_audio

if TYPE_CHECKING:
    from app.services.main import MainService


class WebsocketHandler:
    # Regex pattern to extract socket payload from websocket frames
    # Format: 42[{"content": {...}}] where 42 is the socket.io message prefix
    _SOCKET_PAYLOAD_RE = re.compile(r"42(\[.*\])")

    def __init__(self, main_service: "MainService") -> None:
        # Browser configs
        self._page = main_service._page

        # Account configs
        self._event_config = main_service._event_config
        self._account = main_service._account

        # Callbacks
        self._on_account_won = main_service._on_account_won
        self._on_add_message = main_service._on_add_message
        self._on_add_notification = main_service._on_add_notification
        self._on_update_current_jackpot = main_service._on_update_current_jackpot
        self._on_update_prize_winner = main_service._on_update_prize_winner

        # Internal state
        self._current_jackpot: int = 0
        self._is_logged_in: bool = False
        self._user_info: Optional[UserReponse] = None
        self._main_client: Optional[MainClient] = None

        # Special jackpot tracking
        self._jackpot_epoch: int = 0
        self._sjp_spin_lock = asyncio.Lock()
        self._sjp_spin_task: Optional[asyncio.Task[Any]] = None
        self._sjp_last_spin_time: float = 0.0

        # Mini jackpot tracking
        self._mjp_spin_lock = asyncio.Lock()
        self._mjp_spin_task: Optional[asyncio.Task[Any]] = None
        self._has_spun_for_mini_jackpot: bool = False

    @property
    def is_logged_in(self) -> bool:
        return self._is_logged_in

    @is_logged_in.setter
    def is_logged_in(self, new_is_logged_in: bool) -> None:
        self._is_logged_in = new_is_logged_in

    @property
    def user_info(self) -> Optional[UserReponse]:
        return self._user_info

    @user_info.setter
    def user_info(self, new_user_info: UserReponse) -> None:
        self._user_info = new_user_info

    @property
    def main_client(self) -> Optional[MainClient]:
        return self._main_client

    @main_client.setter
    def main_client(self, new_main_client: MainClient) -> None:
        self._main_client = new_main_client

    def setup_websocket(self) -> None:
        logger.info(f"Monitoring WebSocket on {self._page.url}")  # type: ignore[union-attr]

        def _on_websocket(websocket: WebSocket) -> None:
            # Only process websocket events when logged in
            if not self._is_logged_in:
                return

            logger.info(f"WebSocket opened: {websocket.url}")

            async def _on_framereceived(frame: bytes | str) -> None:
                # Convert frame to string and parse for jackpot events
                frame_str = frame if isinstance(frame, str) else frame.decode("utf-8", errors="ignore")
                logger.debug(f"Frame received: {frame_str[:256]}")

                results = await self._parse_socket_frame(frame=frame_str)
                if not results:
                    return

                kind, value, nickname = results
                await self._handle_jackpot_event(kind=kind, value=value, nickname=nickname)

            def _on_framesent(frame: bytes | str) -> None:
                frame_str = frame if isinstance(frame, str) else frame.decode("utf-8", errors="ignore")
                logger.debug(f"Frame sent: {frame_str[:256]}")

            def _on_close(ws: WebSocket) -> None:
                logger.info(f"WebSocket closed: {ws.url}")
                run_in_thread(coro_func=self._page.reload)  # type: ignore[union-attr]

            websocket.on("framereceived", _on_framereceived)
            websocket.on("framesent", _on_framesent)
            websocket.on("close", _on_close)

        self._page.on("websocket", _on_websocket)  # type: ignore[union-attr]

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

            kind = content.get("type")
            data = content.get("data", {})
            value = content.get("value") or data.get("jackpot_prize")
            nickname = content.get("nickname") or data.get("account_name")

            if not isinstance(kind, str) or not isinstance(value, (int, str)):
                return None

            return kind, value, nickname

        except json.JSONDecodeError:
            logger.exception("Failed to parse JSON from WebSocket frame")
            return None

    async def _handle_jackpot_event(self, kind: str, value: int | str, nickname: str = "") -> None:
        try:
            match kind:
                case "jackpot_value" | "prize_change":
                    message = f"Jackpot value: {int(value):,}"
                    self._on_add_message(tag=MessageTag.WEBSOCKET, message=message, compact=True)

                    # Handle real-time jackpot value updates
                    new_value = int(value)
                    prev_value = self._current_jackpot

                    # Detect jackpot reset/drop - increase epoch and cancel pending spins
                    if new_value < prev_value:
                        self._jackpot_epoch += 1
                        self._cancel_spin_task()

                    self._current_jackpot = new_value

                    # Check if mini jackpot target reached (spin once only)
                    if (
                        self._account.target_mjp is not None
                        and new_value >= self._account.target_mjp
                        and not self._has_spun_for_mini_jackpot
                    ):
                        # Clean up any completed tasks first
                        self._cleanup_completed_mjp_spin_task()

                        # Trigger one-time mini jackpot spin
                        if not self._mjp_spin_task:
                            message = f"Mini Jackpot target reached {self._account.target_mjp:,}, spinning once"
                            self._on_add_message(tag=MessageTag.REACHED_GOAL, message=message)

                            epoch_snapshot = self._jackpot_epoch
                            self._mjp_spin_task = asyncio.create_task(
                                self._attempt_spin(epoch_snapshot=epoch_snapshot, is_jackpot=False),
                                name=f"spin-mjp-{self._account.username}-{epoch_snapshot}",
                            )
                            logger.info(
                                f"Created one-time mini jackpot spin task for {self._account.username} "
                                f"at jackpot {new_value:,}"
                            )

                    # Check if special jackpot target reached (continuous spins)
                    elif new_value >= self._account.target_sjp:
                        # Clean up any completed tasks first
                        self._cleanup_completed_sjp_spin_task()

                        # Check if we should trigger a new spin based on delay
                        current_time = time.time()
                        time_since_last_spin = current_time - self._sjp_last_spin_time

                        # Trigger spin if: no active task AND (first spin OR enough delay passed)
                        should_spin = not self._sjp_spin_task and (
                            self._sjp_last_spin_time == 0.0 or time_since_last_spin >= self._account.spin_delay_seconds
                        )

                        if should_spin:
                            if self._sjp_last_spin_time == 0.0:
                                message = f"Special Jackpot has reached {self._account.target_sjp:,}"
                                self._on_add_message(tag=MessageTag.REACHED_GOAL, message=message)

                            epoch_snapshot = self._jackpot_epoch
                            self._sjp_spin_task = asyncio.create_task(
                                self._attempt_spin(epoch_snapshot=epoch_snapshot),
                                name=f"spin-{self._account.username}-{epoch_snapshot}",
                            )
                            self._sjp_last_spin_time = current_time
                            logger.info(f"Created spin task for {self._account.username} at jackpot {new_value:,}")

                    self._on_update_current_jackpot(value=new_value)

                case "jackpot" | "mini_jackpot":
                    # Stop auto spin when any jackpot is won by anyone
                    self._cancel_spin_task()
                    self._sjp_last_spin_time = 0.0

                    is_jackpot = kind == "jackpot"
                    if is_jackpot:
                        # Reset jackpot value and increment epoch when ultimate prize is won
                        self._jackpot_epoch += 1
                        self._current_jackpot = 0
                        self._has_spun_for_mini_jackpot = False  # Reset mini jackpot flag on ultimate prize win

                    await self._check_winner(is_jackpot=is_jackpot, target_nickname=nickname, target_value=value)

                case _:
                    logger.warning(f"Unknown event type: {kind}")

        except asyncio.CancelledError:
            logger.warning("Spin aborted: jackpot reset/drop")

        except Exception as error:
            logger.exception(f"Error handling jackpot event: {error}")

    async def _attempt_spin(self, epoch_snapshot: int, is_jackpot: bool = True) -> None:
        if not self._main_client:
            return

        spin_response = None
        target_jp = self._account.target_sjp if is_jackpot else (self._account.target_mjp or 0)
        spin_lock = self._sjp_spin_lock if is_jackpot else self._mjp_spin_lock

        try:
            # Quick validation without holding lock to maximize parallelism
            # Only check if is jackpot (not check for mini jackpot)
            if is_jackpot and epoch_snapshot != self._jackpot_epoch:
                logger.warning(f"Spin aborted: epoch changed (was {epoch_snapshot}, now {self._jackpot_epoch})")
                return

            if self._current_jackpot < target_jp:
                logger.warning(f"Spin aborted: jackpot dropped to {self._current_jackpot}")
                return

            # Use lock only for final validation and spin execution to minimize contention
            async with spin_lock:
                # Re-verify conditions under lock (double-checked locking pattern)
                # Only check if is jackpot (not check for mini jackpot)
                if is_jackpot and epoch_snapshot != self._jackpot_epoch:
                    logger.warning("Spin aborted: epoch changed during lock acquisition")
                    return

                if self._current_jackpot < target_jp:
                    logger.warning("Spin aborted: jackpot dropped during lock acquisition")
                    return

                # Execute the spin operation - this is protected from cancellation
                logger.info(f"Executing spin for {self._account.username} (epoch: {epoch_snapshot})")

                # Use asyncio.shield to protect the API call from cancellation
                spin_response = await asyncio.shield(
                    self._main_client.spin(
                        spin_type=self._account.spin_type,
                        payment_type=self._account.payment_type,
                        params=self._event_config.params,
                    )
                )

        except asyncio.CancelledError:
            logger.warning("Spin aborted: jackpot reset/drop")

        except Exception as error:
            logger.exception(f"Error attempting spin: {error}")

        finally:
            # Always process result if we got one, regardless of cancellation
            if spin_response and spin_response.payload and spin_response.payload.spin_results:
                message = format_results_block(results=spin_response.payload.spin_results)
                self._on_add_message(tag=MessageTag.REWARD, message=message)

            self._sjp_spin_task = None
            self._mjp_spin_task = None

            if not is_jackpot:
                self._has_spun_for_mini_jackpot = True

    async def _check_winner(self, is_jackpot: bool, target_nickname: str, target_value: int | str) -> None:
        try:
            user = self._user_info and self._user_info.payload and self._user_info.payload.user
            target_nickname = target_nickname.casefold()
            is_me = (
                (target_nickname == user.nickname_norm or target_nickname == user.account_name_norm) if user else False
            )

        except Exception:
            is_me = False

        prefix = "You" if is_me else f"User '{target_nickname}'"
        suffix = "Ultimate Prize" if is_jackpot else "Mini Prize"
        message = f"{prefix} won {suffix}: {str(target_value)}"
        tag = MessageTag.OTHER_PLAYER_JACKPOT if is_jackpot else MessageTag.OTHER_PLAYER_MINI_JACKPOT

        if is_me:
            tag = MessageTag.JACKPOT if is_jackpot else MessageTag.MINI_JACKPOT

            if is_jackpot:
                self._on_account_won(username=self._account.username)

            self._on_add_notification(nickname=target_nickname, jackpot_value=str(target_value))

            notifier_mgr.discord_winner_notifier(
                is_jackpot=is_jackpot,
                username=self._account.username,
                nickname=target_nickname,
                value=str(target_value),
            )

        is_compact = False if is_me else True
        self._on_add_message(tag=tag, message=message, compact=is_compact)
        self._on_update_prize_winner(nickname=target_nickname, value=str(target_value), is_jackpot=is_jackpot)

        threading.Thread(target=play_audio, kwargs={"audio_name": tag.sound_name}, daemon=True).start()

    def _cancel_spin_task(self) -> None:
        if self._sjp_spin_task and not self._sjp_spin_task.done():
            logger.info(f"Cancelling pending spin task for {self._account.username} (epoch {self._jackpot_epoch})")
            self._sjp_spin_task.cancel()
        self._sjp_spin_task = None
        self._sjp_last_spin_time = 0.0

    def _cleanup_completed_sjp_spin_task(self) -> None:
        if not self._sjp_spin_task or not self._sjp_spin_task.done():
            return

        with contextlib.suppress(Exception):
            # Get any exception from completed task
            exception = self._sjp_spin_task.exception()
            if exception and not isinstance(exception, asyncio.CancelledError):
                logger.warning(f"Spin task completed with exception: {exception}")
        self._sjp_spin_task = None

    def _cleanup_completed_mjp_spin_task(self) -> None:
        if not self._mjp_spin_task or not self._mjp_spin_task.done():
            return

        with contextlib.suppress(Exception):
            # Get any exception from completed task
            exception = self._mjp_spin_task.exception()
            if exception and not isinstance(exception, asyncio.CancelledError):
                logger.warning(f"Spin task completed with exception: {exception}")
        self._mjp_spin_task = None
