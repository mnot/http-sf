from decimal import Decimal
from string import digits
from typing import Union

from .errors import StructuredFieldError
from .state import ParserState

MAX_INT = 999999999999999
MIN_INT = -999999999999999

DIGITS = set(digits.encode("ascii"))
NUMBER_START_CHARS = set((digits + "-").encode("ascii"))
PERIOD = ord(b".")
MINUS = ord(b"-")


def parse_integer(state: ParserState) -> Union[int, Decimal]:
    return parse_number(state)


def ser_integer(inval: int) -> str:
    if not MIN_INT <= inval <= MAX_INT:
        raise ValueError("Input is out of Integer range.")
    output = ""
    if inval < 0:
        output += "-"
    output += str(abs(inval))
    return output


def parse_number(state: ParserState) -> Union[int, Decimal]:
    # Step numbers are those of RFC 9651 section 4.2.4.
    is_decimal = False  # 1. type is "integer" or "decimal"
    sign = 1  # 2.
    # 3. input_number is data[number_start:cursor]
    if state.has_data() and state.data[state.cursor] == MINUS:  # 4.
        state.cursor += 1
        sign = -1
    if not state.has_data():  # 5.
        raise StructuredFieldError(
            "Number input lacked a number", position=state.cursor, offending_char=None
        )
    if state.data[state.cursor] not in DIGITS:  # 6.
        raise StructuredFieldError(
            "Number doesn't start with a DIGIT",
            position=state.cursor,
            offending_char=state.data[state.cursor],
        )
    number_start = state.cursor
    decimal_index = 0
    while state.has_data():  # 7.
        char = state.data[state.cursor]  # 7.1. consume
        state.cursor += 1
        if char in DIGITS:  # 7.2.
            pass
        elif not is_decimal and char == PERIOD:  # 7.3.
            if state.cursor - number_start - 1 > 12:  # 7.3.1. before appending "."
                raise StructuredFieldError(
                    "Decimal too long.", position=state.cursor - 1, offending_char=None
                )
            is_decimal = True  # 7.3.2.
            decimal_index = state.cursor
        else:  # 7.4. prepend char to input_string
            state.cursor -= 1
            break
        input_length = state.cursor - number_start
        if not is_decimal and input_length > 15:  # 7.5.
            raise StructuredFieldError(
                "Integer too long.", position=state.cursor - 1, offending_char=None
            )
        if is_decimal and input_length > 16:  # 7.6.
            raise StructuredFieldError(
                "Decimal too long.", position=state.cursor - 1, offending_char=None
            )
    if not is_decimal:  # 8.
        output_integer = int(state.data[number_start : state.cursor])  # 8.1.
        return output_integer * sign  # 10.
    if state.data[state.cursor - 1] == PERIOD:  # 9.1.
        raise StructuredFieldError(
            "Decimal ends in '.'", position=state.cursor - 1, offending_char=None
        )
    if state.cursor - decimal_index > 3:  # 9.2.
        raise StructuredFieldError(
            "Decimal fractional component too long",
            position=state.cursor - 1,
            offending_char=None,
        )
    # 9.3. Decimal() is exact whatever the ambient context; arithmetic isn't,
    # so negate with copy_negate() rather than multiplying (10.).
    output_decimal = Decimal(state.data[number_start : state.cursor].decode("ascii"))
    return output_decimal.copy_negate() if sign < 0 else output_decimal
