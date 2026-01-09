from typing import Optional

from .bare_item import parse_bare_item, ser_bare_item
from .errors import StructuredFieldError
from .state import ParserState
from .types import BareItemType, ParamsType, OnDuplicateKeyType
from .util import discard_ows, parse_key, ser_key

PAREN_OPEN = ord(b"(")
SEMICOLON = ord(b";")
EQUALS = ord(b"=")


def parse_params(
    state: ParserState, on_duplicate_key: Optional[OnDuplicateKeyType] = None
) -> ParamsType:
    params = {}
    while True:
        try:
            if state.data[state.cursor] != SEMICOLON:
                break
        except IndexError:
            break
        state.cursor += 1  # consume the ";"
        discard_ows(state)
        param_name = parse_key(state)
        param_value: BareItemType = True
        try:
            if state.data[state.cursor] == EQUALS:
                state.cursor += 1  # consume the "="
                try:
                    param_value = parse_bare_item(state)
                except StructuredFieldError as why:
                    why.context = param_name
                    raise why
        except IndexError:
            pass
        if on_duplicate_key and param_name in params:
            on_duplicate_key(param_name, "parameter")
        params[param_name] = param_value
    return params


def ser_params(params: ParamsType) -> str:
    return "".join(
        [
            f";{ser_key(k)}{f'={ser_bare_item(v)}' if v is not True else ''}"
            for k, v in params.items()
        ]
    )
