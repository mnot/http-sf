from decimal import Decimal
from string import digits
from typing import Union, cast

from .errors import StructuredFieldError
from .state import ParserState

MAX_INT = 999999999999999
MIN_INT = -999999999999999

DIGITS = set(digits.encode("ascii"))
NUMBER_START_CHARS = set((digits + "-").encode("ascii"))
PERIOD = ord(b".")
MINUS = ord(b"-")
INTEGER = "integer"
DECIMAL = "decimal"


def parse_integer(state: ParserState) -> int:
    return cast(int, parse_number(state))


def ser_integer(inval: int) -> str:
    if not MIN_INT <= inval <= MAX_INT:
        raise ValueError("Input is out of Integer range.")
    output = ""
    if inval < 0:
        output += "-"
    output += str(abs(inval))
    return output


def parse_number(state: ParserState) -> Union[int, Decimal]:
    _type = INTEGER
    _sign = 1
    num_start = state.cursor
    decimal_index = 0
    num_length = 0
    if state.has_data() and state.data[state.cursor] == MINUS:
        state.cursor += 1
        num_start += 1
        _sign = -1
    if not state.has_data():
        raise StructuredFieldError(
            "Number input lacked a number", position=state.cursor, offending_char=None
        )
    if not state.data[state.cursor] in DIGITS:
        raise StructuredFieldError(
            "Number doesn't start with a DIGIT",
            position=state.cursor,
            offending_char=state.data[state.cursor],
        )
    while True:
        try:
            char = state.data[state.cursor]
        except IndexError:
            break
        num_length = state.cursor - num_start
        if char in DIGITS:
            pass
        elif _type is INTEGER and char == PERIOD:
            # spec says 12, but character is appended afterwards
            if num_length > 13:
                raise ValueError("Decimal too long.")
        state.cursor += 1
        num_length = state.cursor - num_start - 1
        if char in DIGITS:
            pass
        elif _type is INTEGER and char == PERIOD:
            if num_length > 12:
                raise StructuredFieldError(
                    "Decimal too long.",
                    position=state.cursor,
                    offending_char=state.data[state.cursor],
                )
            _type = DECIMAL
            decimal_index = state.cursor
        else:
            state.cursor -= 1
            num_length -= 1
            break
    if _type == INTEGER:
        if num_length > 15:
            # We don't have usage position here as the cursor is already moved
            raise StructuredFieldError(
                "Integer too long.", position=state.cursor - 1, offending_char=None
            )
        output_int = int(state.data[num_start : state.cursor]) * _sign
        if not MIN_INT <= output_int <= MAX_INT:
            raise StructuredFieldError(
                "Integer outside allowed range",
                position=state.cursor - 1,
                offending_char=None,
            )
        return output_int
    # Decimal
    if num_length > 16:
        raise StructuredFieldError(
            "Decimal too long.", position=state.cursor - 1, offending_char=None
        )
    if state.data[state.cursor - 1] == PERIOD:
        raise StructuredFieldError(
            "Decimal ends in '.'", position=state.cursor - 1, offending_char=None
        )
    if state.cursor - decimal_index > 3:
        raise StructuredFieldError(
            "Decimal fractional component too long",
            position=state.cursor - 1,
            offending_char=None,
        )
    output_float = Decimal(state.data[num_start : state.cursor].decode("ascii")) * _sign
    return output_float
