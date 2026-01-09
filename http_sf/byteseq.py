import base64
import binascii
from string import ascii_letters, digits
from .state import ParserState
from .errors import StructuredFieldError

BYTE_DELIMIT = ord(b":")
B64CONTENT = set((ascii_letters + digits + "+/=").encode("ascii"))


def parse_byteseq(state: ParserState) -> bytes:
    state.cursor += 1
    try:
        end_delimit = state.data[state.cursor :].index(BYTE_DELIMIT)
    except ValueError as why:
        raise StructuredFieldError(
            "Binary Sequence didn't contain ending ':'",
            position=len(state.data),
            offending_char=None,
        ) from why
    b64_content = state.data[state.cursor : state.cursor + end_delimit]
    state.cursor += end_delimit + 1
    if not all(c in B64CONTENT for c in b64_content):
        raise StructuredFieldError(
            "Binary Sequence contained disallowed character",
            position=state.cursor - 1,
            offending_char=None,
        )
    try:
        binary_content = base64.b64decode(b64_content, validate=True)
    except binascii.Error as why:
        raise StructuredFieldError(
            "Binary Sequence failed to decode",
            position=state.cursor - 1,
            offending_char=None,
        ) from why
    return binary_content


def ser_byteseq(byteseq: bytes) -> str:
    return f":{base64.standard_b64encode(byteseq).decode('ascii')}:"
