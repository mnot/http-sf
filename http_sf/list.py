from typing import Optional

from .errors import StructuredFieldError
from .innerlist import parse_item_or_inner_list, ser_item_or_inner_list
from .state import ParserState
from .types import ListType, OnDuplicateKeyType
from .util import discard_http_ows


COMMA = ord(b",")


def parse_list(
    state: ParserState, on_duplicate_key: Optional[OnDuplicateKeyType] = None
) -> ListType:
    _list = []
    data_len = len(state.data)
    while state.cursor < data_len:
        member = parse_item_or_inner_list(state, on_duplicate_key)
        _list.append(member)
        discard_http_ows(state)
        if state.cursor == data_len:
            return _list
        if state.data[state.cursor] != COMMA:
            raise StructuredFieldError(
                "Trailing text after item in list",
                position=state.cursor,
                offending_char=state.data[state.cursor],
            )
        state.cursor += 1
        discard_http_ows(state)
        if state.cursor == data_len:
            raise StructuredFieldError(
                "Trailing comma at end of list",
                position=state.cursor,
                offending_char=None,
            )
    return _list


def ser_list(_list: ListType) -> str:
    if len(_list) == 0:
        raise ValueError("No contents; field should not be emitted")
    return ", ".join([ser_item_or_inner_list(m) for m in _list])
