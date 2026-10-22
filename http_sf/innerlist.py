from typing import List, Optional, Union, cast

from .item import parse_item, ser_item
from .parameters import parse_params, ser_params
from .state import ParserState
from .types import (
    InnerListType,
    ItemOrInnerListType,
    ItemType,
    OnDuplicateKeyType,
    ParamsType,
)
from .util import discard_ows

PAREN_OPEN = ord(b"(")
PAREN_CLOSE = ord(b")")
INNERLIST_DELIMS = set(b" )")


def parse_innerlist(
    state: ParserState, on_duplicate_key: Optional[OnDuplicateKeyType] = None
) -> InnerListType:
    state.cursor += 1  # consume the "("
    inner_list: List[ItemType] = []
    params: ParamsType = {}
    while True:
        discard_ows(state)
        try:
            next_char = state.data[state.cursor]
        except IndexError as why:
            state.fail("End of inner list not found", cause=why)
        if next_char == PAREN_CLOSE:
            state.cursor += 1
            params = parse_params(state, on_duplicate_key)
            return (inner_list, params)
        item = parse_item(state, on_duplicate_key)
        inner_list.append(item)
        try:
            if state.data[state.cursor] not in INNERLIST_DELIMS:
                state.fail("Inner list bad delimitation")
        except IndexError as why:
            state.fail("End of inner list not found", cause=why)


def ser_innerlist(inner_list: InnerListType) -> str:
    if not isinstance(inner_list, tuple):
        inner_list = (inner_list, {})
    return (
        f"({' '.join([ser_item(i) for i in inner_list[0]])}){ser_params(inner_list[1])}"
    )


def parse_item_or_inner_list(
    state: ParserState, on_duplicate_key: Optional[OnDuplicateKeyType] = None
) -> Union[ItemType, InnerListType]:
    try:
        is_inner_list = state.data[state.cursor] == PAREN_OPEN
    except IndexError:
        is_inner_list = False
    if is_inner_list:
        return parse_innerlist(state, on_duplicate_key)
    return parse_item(state, on_duplicate_key)


def ser_item_or_inner_list(thing: ItemOrInnerListType) -> str:
    if not isinstance(thing, tuple):
        thing = cast(ItemType, (thing, {}))
    if isinstance(cast(InnerListType, thing)[0], List):
        return ser_innerlist(cast(InnerListType, thing))
    return ser_item(cast(ItemType, thing))
