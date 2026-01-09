from typing import List, cast, Union, Optional

from .errors import StructuredFieldError
from .item import parse_item, ser_item
from .parameters import parse_params, ser_params
from .state import ParserState
from .types import (
    InnerListType,
    ItemType,
    ParamsType,
    ItemOrInnerListType,
    OnDuplicateKeyType,
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
        if state.data[state.cursor] == PAREN_CLOSE:
            state.cursor += 1
            params = parse_params(state, on_duplicate_key)
            return (inner_list, params)
        item = parse_item(state, on_duplicate_key)
        inner_list.append(item)
        try:
            if state.data[state.cursor] not in INNERLIST_DELIMS:
                raise StructuredFieldError(
                    "Inner list bad delimitation",
                    position=state.cursor,
                    offending_char=state.data[state.cursor],
                )
        except IndexError as why:
            raise StructuredFieldError(
                "End of inner list not found",
                position=state.cursor,
                offending_char=None,
            ) from why


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
        if state.data[state.cursor] == PAREN_OPEN:
            return parse_innerlist(state, on_duplicate_key)
    except IndexError:
        pass
    return parse_item(state, on_duplicate_key)


def ser_item_or_inner_list(thing: ItemOrInnerListType) -> str:
    if not isinstance(thing, tuple):
        thing = cast(ItemType, (thing, {}))
    if isinstance(cast(InnerListType, thing)[0], List):
        return ser_innerlist(cast(InnerListType, thing))
    return ser_item(cast(ItemType, thing))
