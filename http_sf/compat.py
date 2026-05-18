"""
Backwards-compatibility layer that mimics the object-oriented API of the
deprecated http_sfv package on top of http_sf's functional API.

Allows existing http_sfv users to migrate by changing only their imports:

    from http_sf.compat import Dictionary, List, Item, InnerList, Token, DisplayString
"""

from collections import UserDict, UserList
from typing import (
    Any,
    Dict as _Dict,
    Iterable,
    List as _List,
    Mapping,
    Optional,
    Union,
)

from typing_extensions import SupportsIndex

from . import parse as _parse, ser as _ser
from .innerlist import ser_innerlist
from .item import ser_item
from .parameters import ser_params
from .types import (
    BareItemType,
    DisplayString,
    Token,
)

__all__ = [
    "Dictionary",
    "List",
    "Item",
    "InnerList",
    "Parameters",
    "Token",
    "DisplayString",
    "structures",
]


class Parameters(dict):  # type: ignore[type-arg]
    """Parameter mapping with structured-field serialisation."""

    def __str__(self) -> str:
        return ser_params(self)


SingleItemType = Union[BareItemType, "Item"]


class Item:
    """A bare Item with optional Parameters."""

    def __init__(self, value: Optional[BareItemType] = None) -> None:
        self.value: Optional[BareItemType] = value
        self.params: Parameters = Parameters()

    def parse(self, data: bytes) -> None:
        result = _parse(data, tltype="item")
        assert isinstance(result, tuple)
        value, params = result
        self.value = value
        self.params = Parameters(params)

    def __str__(self) -> str:
        return ser_item((self.value, dict(self.params)))  # type: ignore[arg-type]

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Item):
            return bool(self.value == other.value)
        return bool(self.value == other)

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash(self.value)

    def __repr__(self) -> str:
        return f"<http_sf.compat.Item value={self.value!r} params={dict(self.params)!r}>"


AllItemType = Union[BareItemType, Item, "InnerList", _List[Any]]


def _itemise(thing: AllItemType) -> Union[Item, "InnerList"]:
    if isinstance(thing, (Item, InnerList)):
        return thing
    if isinstance(thing, list):
        return InnerList(thing)
    return Item(thing)


def _to_functional(thing: Union[Item, "InnerList"]) -> Any:
    if isinstance(thing, InnerList):
        members = [_to_functional(i) for i in thing.data]
        return (members, dict(thing.params))
    return (thing.value, dict(thing.params))


def _from_functional(value: Any) -> Union[Item, "InnerList"]:
    if isinstance(value, tuple):
        inner, params = value
        if isinstance(inner, list):
            il = InnerList()
            for elem in inner:
                il.data.append(_from_functional(elem))
            il.params = Parameters(params)
            return il
        item = Item(inner)
        item.params = Parameters(params)
        return item
    # bare value (shouldn't typically happen from parse, but ser accepts it)
    return Item(value)


class InnerList(UserList):  # type: ignore[type-arg]
    def __init__(self, values: Optional[Iterable[AllItemType]] = None) -> None:
        UserList.__init__(self, [_itemise(v) for v in values or []])
        self.params: Parameters = Parameters()

    def __str__(self) -> str:
        members = [_to_functional(i) for i in self.data]
        return ser_innerlist((members, dict(self.params)))

    def __setitem__(
        self,
        index: Union[SupportsIndex, slice],
        value: Union[AllItemType, Iterable[AllItemType]],
    ) -> None:
        if isinstance(index, slice):
            self.data[index] = [_itemise(v) for v in value]  # type: ignore[union-attr]
        else:
            self.data[index] = _itemise(value)  # type: ignore[arg-type]

    def append(self, item: AllItemType) -> None:
        self.data.append(_itemise(item))

    def insert(self, i: int, item: AllItemType) -> None:
        self.data.insert(i, _itemise(item))


class Dictionary(UserDict):  # type: ignore[type-arg]
    def __init__(
        self, data: Optional[Mapping[str, AllItemType]] = None
    ) -> None:
        UserDict.__init__(self)
        if data is not None:
            for key, val in data.items():
                self[key] = val

    def parse(self, data: bytes) -> None:
        parsed: _Dict[str, Any] = _parse(data, tltype="dictionary")  # type: ignore[assignment]
        self.data.clear()
        for key, val in parsed.items():
            self.data[key] = _from_functional(val)

    def __setitem__(self, key: str, value: AllItemType) -> None:
        self.data[key] = _itemise(value)

    def __str__(self) -> str:
        if not self.data:
            raise ValueError("No contents; field should not be emitted")
        return _ser({k: _to_functional(v) for k, v in self.data.items()})


class List(UserList):  # type: ignore[type-arg]
    def __init__(self, values: Optional[Iterable[AllItemType]] = None) -> None:
        UserList.__init__(self, [_itemise(v) for v in values or []])

    def parse(self, data: bytes) -> None:
        parsed: _List[Any] = _parse(data, tltype="list")  # type: ignore[assignment]
        self.data.clear()
        for elem in parsed:
            self.data.append(_from_functional(elem))

    def __str__(self) -> str:
        if not self.data:
            raise ValueError("No contents; field should not be emitted")
        return _ser([_to_functional(v) for v in self.data])

    def __setitem__(
        self,
        index: Union[SupportsIndex, slice],
        value: Union[AllItemType, Iterable[AllItemType]],
    ) -> None:
        if isinstance(index, slice):
            self.data[index] = [_itemise(v) for v in value]  # type: ignore[union-attr]
        else:
            self.data[index] = _itemise(value)  # type: ignore[arg-type]

    def append(self, item: AllItemType) -> None:
        self.data.append(_itemise(item))

    def insert(self, i: int, item: AllItemType) -> None:
        self.data.insert(i, _itemise(item))


structures = {"dictionary": Dictionary, "list": List, "item": Item}
