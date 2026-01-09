from typing import cast, Optional

from .errors import StructuredFieldError
from .innerlist import parse_item_or_inner_list, ser_item_or_inner_list
from .parameters import parse_params, ser_params
from .state import ParserState
from .types import DictionaryType, ItemType, OnDuplicateKeyType
from .util import discard_http_ows, ser_key, parse_key


EQUALS = ord(b"=")
COMMA = ord(b",")


def parse_dictionary(
    state: ParserState, on_duplicate_key: Optional[OnDuplicateKeyType] = None
) -> DictionaryType:
    dictionary = {}
    data_len = len(state.data)
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
            why.context = this_key
            raise why
        if on_duplicate_key and this_key in dictionary:
            on_duplicate_key(this_key, "dictionary")
        dictionary[this_key] = member
        discard_http_ows(state)
        if state.cursor == data_len:
            return dictionary
        if state.data[state.cursor] != COMMA:
            raise StructuredFieldError(
                f"Dictionary member '{this_key}' has trailing characters",
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
    return ", ".join(
        [
            f"{ser_key(m)}"
            f"""{ser_params(n[1]) if
                (isinstance(n, tuple) and n[0] is True)
                else f'={ser_item_or_inner_list(cast(ItemType, n))}'}"""
            for m, n in dictionary.items()
        ]
    )
