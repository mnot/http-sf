from datetime import datetime

from .errors import StructuredFieldError
from .integer import parse_integer
from .state import ParserState
from .util import datetime_from_timestamp


def parse_date(state: ParserState) -> datetime:
    state.cursor += 1  # consume "@"
    value = parse_integer(state)
    if not isinstance(value, int):
        raise StructuredFieldError(
            "Non-integer Date", position=state.cursor, offending_char=None
        )
    try:
        return datetime_from_timestamp(value)
    except (ValueError, OverflowError) as why:
        raise StructuredFieldError(
            "Date value out of range", position=state.cursor, offending_char=None
        ) from why


def ser_date(inval: datetime) -> str:
    if inval.tzinfo is None or inval.utcoffset() is None:
        raise ValueError(
            "Date must be timezone-aware; e.g., use tzinfo=datetime.timezone.utc"
        )
    return f"@{int(inval.timestamp())}"
