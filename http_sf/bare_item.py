from datetime import datetime
from decimal import Decimal
from typing import cast

from http_sf.boolean import parse_boolean, ser_boolean
from http_sf.byteseq import parse_byteseq, ser_byteseq, BYTE_DELIMIT
from http_sf.date import parse_date, ser_date
from http_sf.decimal import ser_decimal
from http_sf.display_string import parse_display_string, ser_display_string
from http_sf.integer import parse_number, ser_integer, NUMBER_START_CHARS
from http_sf.string import parse_string, ser_string, DQUOTE
from http_sf.token import parse_token, ser_token, TOKEN_START_CHARS
from http_sf.types import BareItemType, Token, DisplayString

from .errors import StructuredFieldError
from .state import ParserState

_parse_map = {
    DQUOTE: parse_string,
    BYTE_DELIMIT: parse_byteseq,
    ord(b"?"): parse_boolean,
    ord(b"%"): parse_display_string,
    ord(b"@"): parse_date,
}
for c in TOKEN_START_CHARS:
    _parse_map[c] = parse_token
for c in NUMBER_START_CHARS:
    _parse_map[c] = parse_number


def parse_bare_item(state: ParserState) -> BareItemType:
    if not state.has_data():
        try:
            char = state.data[state.cursor]
        except IndexError:
            char = None
        raise StructuredFieldError(
            "Empty item", position=state.cursor, offending_char=char
        )
    try:
        next_char = state.data[state.cursor]
        return cast(BareItemType, _parse_map[next_char](state))
    except KeyError as why:
        if next_char == ord(b"'"):
            raise StructuredFieldError(
                "String items must be double-quoted",
                position=state.cursor,
                offending_char=next_char,
            ) from why
        raise StructuredFieldError(
            f"There is no Structured Field item starting with '{chr(next_char)}'",
            position=state.cursor,
            offending_char=next_char,
        ) from why


_ser_map = {
    int: ser_integer,
    float: ser_decimal,
    str: ser_string,
    bool: ser_boolean,
    bytes: ser_byteseq,
}


def ser_bare_item(item: BareItemType) -> str:
    try:
        return _ser_map[type(item)](item)  # type: ignore
    except KeyError:
        pass
    if isinstance(item, Token):
        return ser_token(item)
    if isinstance(item, Decimal):
        return ser_decimal(item)
    if isinstance(item, datetime):
        return ser_date(item)
    if isinstance(item, DisplayString):
        return ser_display_string(item)
    raise ValueError(f"Can't serialise; unrecognised item with type {type(item)}")
