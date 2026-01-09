from .state import ParserState
from .errors import StructuredFieldError
from .types import DisplayString

PERCENT = ord("%")
DQUOTE = ord('"')


def parse_display_string(state: ParserState) -> DisplayString:
    output_array = bytearray([])
    if not state.has_data() or state.data[state.cursor : state.cursor + 2] != b'%"':
        try:
            char = state.data[state.cursor]
        except IndexError:
            char = None
        raise StructuredFieldError(
            'Display string does not start with %"',
            position=state.cursor,
            offending_char=char,
        )
    state.cursor += 2  # consume PERCENT DQUOTE
    while True:
        try:
            char = state.data[state.cursor]
        except IndexError as why:
            raise StructuredFieldError(
                "Reached end of input without finding a closing DQUOTE",
                position=state.cursor,
                offending_char=None,
            ) from why
        state.cursor += 1
        if char == PERCENT:
            try:
                next_chars = state.data[state.cursor : state.cursor + 2]
                if len(next_chars) < 2:
                    raise IndexError
            except IndexError as why:
                raise StructuredFieldError(
                    "Incomplete percent encoding",
                    position=state.cursor,
                    offending_char=None,
                ) from why
            state.cursor += 2
            if next_chars.lower() != next_chars:
                raise StructuredFieldError(
                    "Uppercase percent encoding",
                    position=state.cursor - 2,
                    offending_char=next_chars[0],
                )
            if not all(c in b"0123456789abcdef" for c in next_chars):
                raise StructuredFieldError(
                    "Invalid percent encoding",
                    position=state.cursor - 2,
                    offending_char=next_chars[0],
                )
            try:
                octet = int(next_chars, base=16)
            except ValueError as why:
                raise StructuredFieldError(
                    "Invalid percent encoding",
                    position=state.cursor - 2,
                    offending_char=next_chars[0],
                ) from why
            output_array.append(octet)
        elif char == DQUOTE:
            try:
                output_string = output_array.decode("utf-8")
            except UnicodeDecodeError as why:
                raise StructuredFieldError(
                    "Invalid UTF-8", position=state.cursor - 1, offending_char=None
                ) from why
            return DisplayString(output_string)
        elif 31 < char < 127:
            output_array.append(char)
        else:
            raise StructuredFieldError(
                "String contains disallowed character",
                position=state.cursor - 1,
                offending_char=char,
            )


def ser_display_string(inval: DisplayString) -> str:
    byte_array = inval.encode("utf-8")
    escaped = []
    for byte in byte_array:
        if byte in [PERCENT, DQUOTE] or not 31 <= byte <= 127:
            escaped.append(f"%{byte:x}")
        else:
            escaped.append(chr(byte))
    return f'%"{"".join(escaped)}"'
