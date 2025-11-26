from typing import Any


class AutoProps:
    def __getattr__(self, name: str) -> Any:
        private_name = f"_{name}"

        if private_name in self.__dict__:
            return self.__dict__[private_name]

        raise AttributeError(name)

    def __setattr__(self, name: str, value: Any) -> None:
        private_name = f"_{name}"

        if name in self.__dict__ or private_name in self.__dict__:
            object.__setattr__(self, private_name, value)
            return

        object.__setattr__(self, name, value)
