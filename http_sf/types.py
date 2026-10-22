from collections import UserString
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Dict, List, Tuple, TypeAlias, Union


class Token(UserString):
    def __init__(self, seq: str):  # pylint: disable=W0231
        self.data = seq

    def __str__(self) -> str:
        # Take the underlying value of a str subclass (e.g., a str Enum),
        # ignoring any __str__ or __format__ override. Plain str skips the
        # conversion, to keep the common case cheap; type() (not __class__)
        # because a subclass can't override it.
        data = self.data
        if type(data) is str:  # pylint: disable=unidiomatic-typecheck
            return data
        # issubclass(type()) rather than isinstance(), so an object that only
        # fakes a str __class__ is formatted as it always was
        if issubclass(type(data), str):
            return str.__str__(data)
        return str(data)

    def __repr__(self) -> str:
        return f'Token("{self.data}")'


class DisplayString(UserString):
    def __init__(self, seq: str):  # pylint: disable=W0231
        self.data = seq

    def __repr__(self) -> str:
        return f'DisplayString("{self.data}")'


BareItemType: TypeAlias = Union[
    int, float, str, bool, Decimal, bytes, Token, datetime, DisplayString
]
ParamsType: TypeAlias = Dict[str, BareItemType]
ItemType: TypeAlias = Union[BareItemType, Tuple[BareItemType, ParamsType]]
InnerListType: TypeAlias = Union[List[ItemType], Tuple[List[ItemType], ParamsType]]
ItemOrInnerListType: TypeAlias = Union[ItemType, InnerListType]
ListType: TypeAlias = List[Union[ItemType, InnerListType]]
DictionaryType: TypeAlias = Dict[str, Union[ItemType, InnerListType]]
StructuredType: TypeAlias = Union[ItemType, ListType, DictionaryType]
OnDuplicateKeyType: TypeAlias = Callable[[str, str], None]
JsonDict: TypeAlias = Dict[str, Any]
