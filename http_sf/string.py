from .state import ParserState
from .errors import StructuredFieldError

DQUOTE = ord('"')
BACKSLASH = ord("\\")
DQUOTEBACKSLASH = set([DQUOTE, BACKSLASH])


def parse_string(state: ParserState) -> str:
    output_string = bytearray()
    state.cursor += 1  # consume DQUOTE
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
        if char == BACKSLASH:
            try:
                next_char = state.data[state.cursor]
            except IndexError as why:
                raise StructuredFieldError(
                    "Last character of input was a backslash",
                    position=state.cursor,
                    offending_char=None,
                ) from why
            state.cursor += 1
            if next_char not in DQUOTEBACKSLASH:
                raise StructuredFieldError(
                    f"Backslash before disallowed character '{chr(next_char)}'",
                    position=state.cursor - 1,
                    offending_char=next_char,
                )
            output_string.append(next_char)
        elif char == DQUOTE:
            return output_string.decode("ascii")
        elif not 31 < char < 127:
            raise StructuredFieldError(
                "String contains disallowed character",
                position=state.cursor - 1,
                offending_char=char,
            )
        else:
            output_string.append(char)


def ser_string(inval: str) -> str:
    if not all(31 < ord(char) < 127 for char in inval):
        raise ValueError("String contains disallowed characters")
    escaped = inval.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
