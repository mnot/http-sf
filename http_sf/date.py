from datetime import datetime

from .integer import parse_integer
from .state import ParserState
from .util import datetime_from_timestamp


def parse_date(state: ParserState) -> datetime:
    state.cursor += 1  # consume "@"
    number_start = state.cursor
    value = parse_integer(state)
    if not isinstance(value, int):
        # The "." is what made the number a Decimal.
        state.fail("Non-integer Date", state.data.index(b".", number_start))
    try:
        date = datetime_from_timestamp(value)
    except OverflowError as why:
        state.fail("Date value out of range", cause=why)
    return date


def ser_date(inval: datetime) -> str:
    if inval.tzinfo is None or inval.utcoffset() is None:
        raise ValueError(
            "Date must be timezone-aware; e.g., use tzinfo=datetime.timezone.utc"
        )
    return f"@{int(inval.timestamp())}"
