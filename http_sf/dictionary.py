from typing import Optional, cast

from .errors import StructuredFieldError
from .innerlist import parse_item_or_inner_list, ser_item_or_inner_list
from .parameters import parse_params, ser_params
from .state import ParserState
from .types import DictionaryType, ItemType, OnDuplicateKeyType
from .util import discard_http_ows, parse_key, ser_key

EQUALS = ord(b"=")
COMMA = ord(b",")


def parse_dictionary(
    state: ParserState, on_duplicate_key: Optional[OnDuplicateKeyType] = None
) -> DictionaryType:
    dictionary: DictionaryType = {}
    data_len = len(state.data)
    if state.cursor == data_len:
        return dictionary
    while True:
        this_key = parse_key(state)
        try:
            try:
                is_equals = state.data[state.cursor] == EQUALS
            except IndexError:
                is_equals = False
            if is_equals:
                state.cursor += 1  # consume the "="
                member = parse_item_or_inner_list(state, on_duplicate_key)
            else:
                params = parse_params(state, on_duplicate_key)
                member = (True, params)
        except StructuredFieldError as why:
            if why.context is None:
                why.context = this_key
            raise why
        if on_duplicate_key and this_key in dictionary:
            on_duplicate_key(this_key, "dictionary")
        dictionary[this_key] = member
        discard_http_ows(state)
        if state.cursor == data_len:
            return dictionary
        if state.data[state.cursor] != COMMA:
            if not is_equals:
                offending_char = state.data[state.cursor]
                raise StructuredFieldError(
                    f"'{this_key}' should be followed by '=', not {chr(offending_char)!r}",
                    position=state.cursor,
                    offending_char=offending_char,
                )
            raise StructuredFieldError(
                f"'{this_key}' has trailing characters after the value",
                position=state.cursor,
                offending_char=state.data[state.cursor],
            )
        state.cursor += 1
        discard_http_ows(state)
        if state.cursor == data_len:
            raise StructuredFieldError(
                "Dictionary has trailing comma",
                position=state.cursor,
                offending_char=None,
            )


def ser_dictionary(dictionary: DictionaryType) -> str:
    if len(dictionary) == 0:
        raise ValueError("No contents; field should not be emitted")
    members = []
    for member_name, member_value in dictionary.items():
        member = ser_key(member_name)
        if member_value is True:
            pass  # Boolean true without parameters: the key alone
        elif isinstance(member_value, tuple) and member_value[0] is True:
            member += ser_params(member_value[1])
        else:
            member += f"={ser_item_or_inner_list(cast(ItemType, member_value))}"
        members.append(member)
    return ", ".join(members)
