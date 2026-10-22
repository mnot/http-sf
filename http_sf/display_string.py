from .state import ParserState
from .types import DisplayString

PERCENT = ord("%")
DQUOTE = ord('"')


def parse_display_string(state: ParserState) -> DisplayString:
    output_array = bytearray([])
    if state.data[state.cursor : state.cursor + 2] != b'%"':
        state.fail('Display string does not start with %"')
    state.cursor += 2  # consume PERCENT DQUOTE
    while True:
        try:
            char = state.data[state.cursor]
        except IndexError as why:
            state.fail(
                "Reached end of input without finding a closing DQUOTE", cause=why
            )
        state.cursor += 1
        if char == PERCENT:
            next_chars = state.data[state.cursor : state.cursor + 2]
            if len(next_chars) < 2:
                state.fail("Incomplete percent encoding")
            state.cursor += 2
            if next_chars.lower() != next_chars:
                state.fail("Uppercase percent encoding", state.cursor - 2)
            if not all(c in b"0123456789abcdef" for c in next_chars):
                state.fail("Invalid percent encoding", state.cursor - 2)
            output_array.append(int(next_chars, base=16))
        elif char == DQUOTE:
            try:
                output_string = output_array.decode("utf-8")
            except UnicodeDecodeError as why:
                state.fail("Invalid UTF-8", _utf8_error_position(state, why), cause=why)
            return DisplayString(output_string)
        elif 31 < char < 127:
            output_array.append(char)
        else:
            state.fail("String contains disallowed character", state.cursor - 1)


def _utf8_error_position(state: ParserState, why: UnicodeDecodeError) -> int:
    """
    Where the first bad sequence starts in the input. A sequence cut off by the
    closing DQUOTE is reported there, as it always was.
    """
    closing = state.cursor - 1
    if why.reason not in ("invalid start byte", "invalid continuation byte"):
        return closing
    # The content has no other DQUOTE, and an escape is three input bytes for
    # one decoded byte.
    position = state.data.rfind(b'"', 0, closing) + 1
    for _ in range(why.start):
        position += 3 if state.data[position] == PERCENT else 1
    return position


def ser_display_string(inval: DisplayString) -> str:
    byte_array = inval.encode("utf-8")
    escaped = []
    for byte in byte_array:
        if byte in [PERCENT, DQUOTE] or not 0x20 <= byte <= 0x7E:
            escaped.append(f"%{byte:02x}")
        else:
            escaped.append(chr(byte))
    return f'%"{"".join(escaped)}"'
