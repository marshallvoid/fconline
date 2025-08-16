from typing import TYPE_CHECKING, Any, Callable, Counter, List, Optional

if TYPE_CHECKING:
    from src.schemas.spin_response import SpinResult


def should_execute_callback(callback: Optional[Callable], *args: Any, **kwargs: Any) -> None:
    if callback is None:
        return

    callback(*args, **kwargs)


def format_spin_block(spin_results: List["SpinResult"], jackpot_value: int) -> str:
    lines: list[str] = [f"Auto-spin Results (jackpot: {jackpot_value})"]

    for r in spin_results:
        lines.append(f"  • {r.reward_name}")

    return "\n".join(lines)


def format_spin_block_compact(spin_results: List["SpinResult"], jackpot_value: int) -> str:
    counter = Counter(r.reward_name for r in spin_results)
    lines: list[str] = [f"Auto-spin Results (jackpot: {jackpot_value})"]

    for name, cnt in counter.items():
        suffix = f" × {cnt}" if cnt > 1 else ""
        lines.append(f"  • {name}{suffix}")

    return "\n".join(lines)
