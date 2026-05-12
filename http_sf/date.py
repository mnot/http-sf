from datetime import datetime, timezone

from .errors import StructuredFieldError
from .integer import parse_integer
from .state import ParserState


def parse_date(state: ParserState) -> datetime:
    state.cursor += 1  # consume "@"
    value = parse_integer(state)
    if not isinstance(value, int):
        raise StructuredFieldError(
            "Non-integer Date", position=state.cursor, offending_char=None
        )
    try:
        return datetime.fromtimestamp(value, tz=timezone.utc)
    except (ValueError, OSError) as why:
        raise StructuredFieldError(
            "Date value out of range", position=state.cursor, offending_char=None
        ) from why


def ser_date(inval: datetime) -> str:
    return f"@{int(inval.timestamp())}"
