from .state import ParserState

ONE = ord(b"1")
ZERO = ord(b"0")

_boolean_map = {ONE: (2, True), ZERO: (2, False)}


def parse_boolean(state: ParserState) -> bool:
    try:
        val = _boolean_map[state.data[state.cursor + 1]]
    except (KeyError, IndexError) as exc:
        # Report the byte after '?', where the value should be.
        state.fail("No Boolean value found", state.cursor + 1, cause=exc)
    state.cursor += 2
    return val[1]


def ser_boolean(inval: bool) -> str:
    return f"?{inval and '1' or '0'}"
