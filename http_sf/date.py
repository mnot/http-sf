from datetime import datetime
from .state import ParserState
from .errors import StructuredFieldError
from .integer import parse_integer


def parse_date(state: ParserState) -> datetime:
    state.cursor += 1  # consume "@"
    value = parse_integer(state)
    if not isinstance(value, int):
        raise StructuredFieldError(
            "Non-integer Date", position=state.cursor, offending_char=None
        )
    return datetime.fromtimestamp(value)


def ser_date(inval: datetime) -> str:
    return f"@{int(inval.timestamp())}"
