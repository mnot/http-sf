import re

from .state import ParserState
from .types import DisplayString

PERCENT = ord("%")
DQUOTE = ord('"')
# Characters that need no special handling (not %x00-1F, %x7F-FF, DQUOTE or
# PERCENT), so a run of them can be copied at once
ORDINARY_RE = re.compile(rb'[^\x00-\x1f\x7f-\xff"%]+')


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
                state.fail("Invalid UTF-8", state.cursor - 1, cause=why)
            return DisplayString(output_string)
        elif 31 < char < 127:
            run = ORDINARY_RE.match(state.data, state.cursor - 1)  # char, and more
            assert run  # can't fail; char is ordinary
            output_array += run.group()
            state.cursor = run.end()
        else:
            state.fail("String contains disallowed character", state.cursor - 1)


def ser_display_string(inval: DisplayString) -> str:
    byte_array = inval.encode("utf-8")
    escaped = []
    for byte in byte_array:
        if byte in [PERCENT, DQUOTE] or not 0x20 <= byte <= 0x7E:
            escaped.append(f"%{byte:02x}")
        else:
            escaped.append(chr(byte))
    return f'%"{"".join(escaped)}"'
