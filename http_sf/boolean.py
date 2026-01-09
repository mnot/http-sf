from .state import ParserState
from .errors import StructuredFieldError

QUESTION = ord(b"?")
ONE = ord(b"1")
ZERO = ord(b"0")

_boolean_map = {ONE: (2, True), ZERO: (2, False)}


def parse_boolean(state: ParserState) -> bool:
    try:
        val = _boolean_map[state.data[state.cursor + 1]]
    except (KeyError, IndexError) as exc:
        raise StructuredFieldError(
            "No Boolean value found", position=state.cursor, offending_char=None
        ) from exc
    state.cursor += 2
    return val[1]


def ser_boolean(inval: bool) -> str:
    return f"?{inval and '1' or '0'}"
