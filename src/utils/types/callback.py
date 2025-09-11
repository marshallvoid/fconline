from typing import TYPE_CHECKING, ParamSpec, Protocol, TypeVar

if TYPE_CHECKING:
    from src.schemas.configs import Account
    from src.schemas.enums.message_tag import MessageTag
    from src.schemas.user_response import UserDetail

P = ParamSpec("P")  # parameter specification
R = TypeVar("R", covariant=True)  # return type


class Callback(Protocol[P, R]):
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R: ...


class OnAccountWonCallback(Protocol):
    def __call__(self, username: str, is_jackpot: bool) -> None: ...


class OnAddMessageCallback(Protocol):
    def __call__(self, tag: "MessageTag", message: str, compact: bool = False) -> None: ...


class OnAddNotificationCallback(Protocol):
    def __call__(self, nickname: str, jackpot_value: str) -> None: ...


class OnUpdateCurrentJackpotCallback(Protocol):
    def __call__(self, value: int) -> None: ...


class OnUpdateWinnerCallback(Protocol):
    def __call__(self, nickname: str, value: str, is_jackpot: bool = False) -> None: ...


class OnUpdateUserInfoCallback(Protocol):
    def __call__(self, username: str, user: "UserDetail") -> None: ...


class OnAccountRunCallback(Protocol):
    def __call__(self, account: "Account") -> None: ...


class OnAccountStopCallback(Protocol):
    def __call__(self, username: str) -> None: ...


class OnRefreshPageCallback(Protocol):
    def __call__(self, username: str) -> None: ...
