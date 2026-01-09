from typing import Tuple, Optional

from .bare_item import parse_bare_item, ser_bare_item
from .parameters import parse_params, ser_params
from .state import ParserState
from .types import BareItemType, ItemType, ParamsType, OnDuplicateKeyType

PAREN_OPEN = ord(b"(")
SEMICOLON = ord(b";")
EQUALS = ord(b"=")


def parse_item(
    state: ParserState, on_duplicate_key: Optional[OnDuplicateKeyType] = None
) -> Tuple[BareItemType, ParamsType]:
    value = parse_bare_item(state)
    params = parse_params(state, on_duplicate_key)
    return (value, params)


def ser_item(item: ItemType) -> str:
    if not isinstance(item, tuple):
        item = (item, {})
    return f"{ser_bare_item(item[0])}{ser_params(item[1])}"
