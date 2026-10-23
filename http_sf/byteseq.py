import base64
import binascii
from string import ascii_letters, digits

from .state import ParserState

BYTE_DELIMIT = ord(b":")
B64CONTENT = set((ascii_letters + digits + "+/=").encode("ascii"))


def _padding_fault(b64_content: bytes) -> int:
    """
    Offset in b64_content of the first byte that breaks the padding rules, or
    len(b64_content), the end of the value, if none does (a bad length is a
    fault in the whole value, not in a byte).

    Padding is one or two "=" at the end, after at least one data character, so
    a "=" with no data before it, a third "=", and any data character after
    the first "=" are rejected.
    """
    first = b64_content.find(b"=")
    if first == -1:
        return len(b64_content)
    if first == 0:
        return 0
    run = b64_content[first:]
    return first + min(len(run) - len(run.lstrip(b"=")), 2)


def parse_byteseq(state: ParserState) -> bytes:
    state.cursor += 1
    try:
        end_delimit = state.data.index(BYTE_DELIMIT, state.cursor) - state.cursor
    except ValueError as why:
        state.fail(
            "Binary Sequence didn't contain ending ':'", len(state.data), cause=why
        )
    start = state.cursor
    b64_content = state.data[start : start + end_delimit]
    state.cursor += end_delimit + 1
    if not all(c in B64CONTENT for c in b64_content):
        # Report the first byte outside the alphabet ('=' is in it; where
        # padding may appear is checked below).
        bad = next(i for i, c in enumerate(b64_content) if c not in B64CONTENT)
        state.fail("Binary Sequence contained disallowed character", start + bad)
    # RFC 9651 section 4.2.7: parsers SHOULD NOT fail on missing padding, so
    # normalise it rather than requiring exactly what an encoder would emit.
    # Padding is still only valid at the end, at most two characters long, and
    # after at least one data character.
    unpadded = b64_content.rstrip(b"=")
    pad_len = len(b64_content) - len(unpadded)
    if pad_len > 2 or (pad_len and not unpadded):
        state.fail(
            "Binary Sequence failed to decode", start + _padding_fault(b64_content)
        )
    padded = unpadded + b"=" * (-len(unpadded) % 4)
    try:
        binary_content = base64.b64decode(padded, validate=True)
    except binascii.Error as why:
        state.fail(
            "Binary Sequence failed to decode",
            start + _padding_fault(b64_content),
            cause=why,
        )
    return binary_content


def ser_byteseq(byteseq: bytes) -> str:
    return f":{base64.standard_b64encode(byteseq).decode('ascii')}:"
