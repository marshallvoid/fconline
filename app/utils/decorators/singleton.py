from typing import Any, Callable, Dict, Type, TypeVar

T = TypeVar("T")


def singleton(class_: Type[T]) -> Callable[..., T]:
    instances: Dict[Type[T], T] = {}

    def getinstance(*args: Any, **kwargs: Any) -> T:
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]

    return getinstance
