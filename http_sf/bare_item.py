from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Dict, Tuple, Type

from http_sf.boolean import parse_boolean, ser_boolean
from http_sf.byteseq import BYTE_DELIMIT, parse_byteseq, ser_byteseq
from http_sf.date import parse_date, ser_date
from http_sf.decimal import ser_decimal
from http_sf.display_string import parse_display_string, ser_display_string
from http_sf.integer import NUMBER_START_CHARS, parse_number, ser_integer
from http_sf.string import DQUOTE, parse_string, ser_string
from http_sf.token import TOKEN_START_CHARS, parse_token, ser_token
from http_sf.types import BareItemType, DisplayString, Token

from .state import ParserState

_parse_map: Dict[int, Callable[[ParserState], BareItemType]] = {
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
    if state.cursor >= len(state.data):
        state.fail("Empty item")
    next_char = state.data[state.cursor]
    parser = _parse_map.get(next_char)
    if parser is None:
        if next_char == ord(b"'"):
            state.fail("Strings must be double-quoted")
        if next_char == ord(b"("):
            state.fail("Inner Lists are not valid here")
        state.fail(
            f"There is no Structured Field item starting with {chr(next_char)!r}"
        )
    return parser(state)


_ser_map: Dict[Type[Any], Callable[[Any], str]] = {
    int: ser_integer,
    float: ser_decimal,
    str: ser_string,
    bool: ser_boolean,
    bytes: ser_byteseq,
}


# Checked in order when the exact-type lookup misses. Token and DisplayString
# (and the other types here) must stay ahead of the int, str, float and bytes
# entries so that nothing is shadowed. bool can't be subclassed, so the exact
# lookup has always handled it. Subclasses of int, str, float and bytes
# (IntEnum, str Enums, numpy.float64, ...) are serialised from their underlying
# value, ignoring any __int__, __str__, __float__ or __bytes__ override.
_ser_fallbacks: Tuple[Tuple[type, Callable[[Any], str]], ...] = (
    (Token, ser_token),
    (Decimal, ser_decimal),
    (datetime, ser_date),
    (DisplayString, ser_display_string),
    (int, lambda item: ser_integer(int.__int__(item))),
    (str, lambda item: ser_string(str.__str__(item))),
    (float, lambda item: ser_decimal(float.__float__(item))),
    # A full slice via bytes.__getitem__ yields an exact bytes copy whatever
    # the subclass overrides. This avoids bytes(), which honours __bytes__, and
    # memoryview(), which honours __buffer__ (Python 3.12 and later only).
    (bytes, lambda item: ser_byteseq(bytes.__getitem__(item, slice(None)))),
)


def ser_bare_item(item: BareItemType) -> str:
    try:
        return _ser_map[type(item)](item)
    except KeyError:
        pass
    for item_type, serialiser in _ser_fallbacks:
        if isinstance(item, item_type):
            return serialiser(item)
    raise ValueError(f"Can't serialise; unrecognised item with type {type(item)}")
