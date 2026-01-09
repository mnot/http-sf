from string import ascii_letters, digits
from http_sf.types import Token
from http_sf.state import ParserState

TOKEN_START_CHARS = set((ascii_letters + "*").encode("ascii"))
TOKEN_CHARS = set((ascii_letters + digits + ":/!#$%&'*+-.^_`|~").encode("ascii"))


def parse_token(state: ParserState) -> Token:
    start_cursor = state.cursor
    state.cursor += 1  # consume start char
    size = len(state.data)
    while state.cursor < size:
        if state.data[state.cursor] not in TOKEN_CHARS:
            return Token(state.data[start_cursor : state.cursor].decode("ascii"))
        state.cursor += 1
    return Token(state.data[start_cursor : state.cursor].decode("ascii"))


def ser_token(token: Token) -> str:
    if token and ord(str(token)[0]) not in TOKEN_START_CHARS:
        raise ValueError("Token didn't start with legal character")
    if not all(ord(char) in TOKEN_CHARS for char in str(token)):
        raise ValueError("Token contains disallowed characters")
    return str(token)
