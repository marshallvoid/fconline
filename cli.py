from __future__ import annotations

import argparse
import asyncio
import contextlib
import os
import signal
from getpass import getpass
from typing import Optional

from icecream import ic
from loguru import logger
from src.core.event_config import EventConfig
from src.core.main_tool import MainTool


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="fcon-auto",
        description="FC Online automation tool (login + spin + user panel updates)",
    )

    parser.add_argument("--username", "-u", help="Account username. Can be omitted to read from ENV FC_USERNAME.")
    parser.add_argument("--password", "-p", help="Account password. Can be omitted to read from ENV FC_PASSWORD.")
    parser.add_argument("--spin-action", type=int, default=1, help="Spin type (default: 1).")
    parser.add_argument(
        "--target-special-jackpot",
        type=int,
        default=10_000,
        help="Special Jackpot threshold to stop auto (default: 10000).",
    )

    # Event/API configuration
    parser.add_argument("--base-url", required=True, help="Event base URL, e.g., https://typhu.fconline.garena.vn")
    parser.add_argument(
        "--user-endpoint",
        default="api/user/get",
        help="User info endpoint (default: api/user/get).",
    )
    parser.add_argument(
        "--spin-endpoint",
        default="api/user/spin",
        help="Spin endpoint (default: api/user/spin).",
    )

    # Run until Ctrl+C or a fixed duration
    parser.add_argument(
        "--duration",
        type=int,
        default=None,
        help="If set, the tool runs for N seconds then exits. Default: run until Ctrl+C.",
    )

    # Logging
    parser.add_argument(
        "--log-level",
        choices=["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Log level (default: INFO).",
    )

    return parser


def _resolve_credential(arg_value: Optional[str], env_key: str, prompt: str, *, is_password: bool = False) -> str:
    """Resolve a credential from CLI arg, then ENV, then interactive input."""
    if arg_value:
        return arg_value

    env_val: Optional[str] = os.getenv(env_key)
    if env_val:
        return env_val

    return getpass(prompt) if is_password else input(prompt)


async def _run_main(args: argparse.Namespace) -> None:
    """Async runner that wires signals, instantiates MainTool, and manages lifecycle."""
    # Logging sink
    logger.remove()
    logger.add(lambda msg: ic(msg), level=args.log_level)

    # Initialize tool
    tool: MainTool = MainTool(
        event_config=EventConfig(
            tab_attr_name="",
            spin_actions={},
            base_url=str(args.base_url).rstrip("/"),
            user_endpoint=str(args.user_endpoint).lstrip("/"),
            spin_endpoint=str(args.spin_endpoint).lstrip("/"),
        ),
        username=_resolve_credential(args.username, "FC_USERNAME", "Username: "),
        password=_resolve_credential(args.password, "FC_PASSWORD", "Password: ", is_password=True),
        spin_action=int(args.spin_action),
        target_special_jackpot=int(args.target_special_jackpot),
    )

    # Cooperative stop flag
    stop_event: asyncio.Event = asyncio.Event()

    def _cancel_handler() -> None:
        logger.warning("🛑 Received termination signal — shutting down gracefully…")
        tool.is_running = False
        stop_event.set()

    loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _cancel_handler)
        except NotImplementedError:
            # Some platforms (notably Windows) may not support this fully
            pass

    # Start
    tool.is_running = True

    async def _guard_run() -> None:
        try:
            await tool.run()
        except Exception as e:  # noqa: BLE001
            logger.error(f"❌ Tool crashed: {e}")
        finally:
            await tool.close()
            stop_event.set()

    runner: asyncio.Task[None] = asyncio.create_task(_guard_run())

    # Optional timed run
    if args.duration and int(args.duration) > 0:
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=float(args.duration))
        except asyncio.TimeoutError:
            logger.info(f"⏰ Duration {args.duration}s elapsed — stopping the tool.")
        finally:
            tool.is_running = False
            await tool.close()
    else:
        # Wait until Ctrl+C or tool stops by itself
        await stop_event.wait()

    if not runner.done():
        runner.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await runner


def main() -> None:
    """CLI entrypoint."""
    parser: argparse.ArgumentParser = build_parser()
    args: argparse.Namespace = parser.parse_args()

    try:
        asyncio.run(_run_main(args))
    except KeyboardInterrupt:
        logger.warning("🛑 Stopped by user.")
    except Exception as e:  # noqa: BLE001
        logger.error(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()
