import re

from .state import ParserState

DQUOTE = ord('"')
BACKSLASH = ord("\\")
DQUOTEBACKSLASH = set([DQUOTE, BACKSLASH])
# Characters that need no special handling (not %x00-1F, %x7F-FF, DQUOTE or
# backslash), so a run of them can be copied at once
STRING_RUN_RE = re.compile(rb'[^\x00-\x1f\x7f-\xff"\\]+')


def parse_string(state: ParserState) -> str:
    output_string = bytearray()
    state.cursor += 1  # consume DQUOTE
    while True:
        try:
            char = state.data[state.cursor]
        except IndexError as why:
            state.fail(
                "Reached end of input without finding a closing DQUOTE", cause=why
            )
        state.cursor += 1
        if char == BACKSLASH:
            try:
                next_char = state.data[state.cursor]
            except IndexError as why:
                state.fail("Last character of input was a backslash", cause=why)
            state.cursor += 1
            if next_char not in DQUOTEBACKSLASH:
                state.fail(
                    f"Backslash before disallowed character {chr(next_char)!r}",
                    state.cursor - 1,
                )
            output_string.append(next_char)
        elif char == DQUOTE:
            return output_string.decode("ascii")
        elif not 31 < char < 127:
            state.fail("String contains disallowed character", state.cursor - 1)
        else:
            # char, and the ordinary characters after it
            run = STRING_RUN_RE.match(state.data, state.cursor - 1)
            assert run  # can't fail; char is ordinary
            output_string += run.group()
            state.cursor = run.end()


def ser_string(inval: str) -> str:
    if not all(31 < ord(char) < 127 for char in inval):
        raise ValueError("String contains disallowed characters")
    escaped = inval.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
