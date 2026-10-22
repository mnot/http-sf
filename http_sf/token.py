import re
from string import ascii_letters, digits

from http_sf.state import ParserState
from http_sf.types import Token

TOKEN_START_CHARS = set((ascii_letters + "*").encode("ascii"))
TOKEN_CHARS = set((ascii_letters + digits + ":/!#$%&'*+-.^_`|~").encode("ascii"))
TOKEN_RE = re.compile(b"[" + re.escape(bytes(sorted(TOKEN_CHARS))) + b"]*")


def parse_token(state: ParserState) -> Token:
    start_cursor = state.cursor
    state.cursor += 1  # consume start char
    match = TOKEN_RE.match(state.data, state.cursor)  # consume tchars
    assert match  # can't fail; the pattern accepts zero characters
    state.cursor = match.end()
    return Token(state.data[start_cursor : state.cursor].decode("ascii"))


def ser_token(token: Token) -> str:
    data = token.data
    if not issubclass(type(data), str):
        len(data)  # data with no length (None, int, ...) raises TypeError, as ever
    # Validate and emit the same plain str, whatever the token wraps
    value = str(token)
    if not value:
        raise ValueError("Token is empty")
    if ord(value[0]) not in TOKEN_START_CHARS:
        raise ValueError("Token didn't start with legal character")
    if not all(ord(char) in TOKEN_CHARS for char in value):
        raise ValueError("Token contains disallowed characters")
    return value
