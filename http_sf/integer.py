from decimal import Decimal
from string import digits
from typing import Union

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
    data_len = len(state.data)
    if state.cursor < data_len and state.data[state.cursor] == MINUS:  # 4.
        state.cursor += 1
        sign = -1
    if state.cursor >= data_len:  # 5.
        state.fail("Number input lacked a number")
    if state.data[state.cursor] not in DIGITS:  # 6.
        state.fail("Number doesn't start with a DIGIT")
    number_start = state.cursor
    decimal_index = 0
    while state.cursor < data_len:  # 7.
        char = state.data[state.cursor]  # 7.1. consume
        state.cursor += 1
        if char in DIGITS:  # 7.2.
            pass
        elif not is_decimal and char == PERIOD:  # 7.3.
            if state.cursor - number_start - 1 > 12:  # before appending "."
                state.fail("Decimal too long.", state.cursor - 1)  # 7.3.1.
            is_decimal = True  # 7.3.2.
            decimal_index = state.cursor
        else:  # 7.4. prepend char to input_string
            state.cursor -= 1
            break
        input_length = state.cursor - number_start
        if not is_decimal and input_length > 15:  # 7.5.
            state.fail("Integer too long.", state.cursor - 1)
        if is_decimal and input_length > 16:  # 7.6.
            state.fail("Decimal too long.", state.cursor - 1)
    output_number: Union[int, Decimal]
    if not is_decimal:  # 8.
        output_number = int(state.data[number_start : state.cursor])  # 8.1.
    else:  # 9.
        if state.data[state.cursor - 1] == PERIOD:  # 9.1.
            state.fail("Decimal ends in '.'", state.cursor - 1)
        if state.cursor - decimal_index > 3:  # 9.2.
            # Report the first digit past the three allowed, not the last.
            state.fail("Decimal fractional component too long", decimal_index + 3)
        output_number = Decimal(  # 9.3.
            state.data[number_start : state.cursor].decode("ascii")
        )
    if sign < 0:  # 10. Multiplying or negating a Decimal rounds to the ambient
        # context; copy_negate() is exact.
        if isinstance(output_number, Decimal):
            output_number = output_number.copy_negate()
        else:
            output_number = -output_number
    return output_number  # 11.
