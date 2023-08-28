from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Generic, List, Type, TypeVar, cast

T = TypeVar("T")
EnumT = TypeVar("EnumT", bound=Enum)


def from_str(x: Any) -> str:
    assert isinstance(x, str)
    return x


def to_enum(c: Type[EnumT], x: Any) -> EnumT:
    assert isinstance(x, c)
    return x.value


def to_class(c: Type[T], x: Any) -> dict:
    assert isinstance(x, c)
    return cast(Any, x).to_dict()


def from_none(x: Any) -> Any:
    assert x is None
    return x


def from_union(fs, x):
    for f in fs:
        try:
            return f(x)
        except Exception:
            pass
    assert False


def from_default(defaultValue: Type[T], x: Type[T]) -> Type[T]:
    assert defaultValue is not None
    return x or defaultValue


def from_list(f: Callable[[Any], T], x: Any) -> List[T]:
    assert isinstance(x, list)
    return [f(y) for y in x]


class Defaultable(ABC, Generic[T]):
    @staticmethod
    @abstractmethod
    def from_default(x: Any) -> T:
        pass
