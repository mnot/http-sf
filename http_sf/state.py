from typing import NoReturn, Optional

from http_sf.errors import StructuredFieldError


class ParserState:
    def __init__(self, data: bytes):
        self.data = data
        self.cursor = 0

    def has_data(self) -> bool:
        return self.cursor < len(self.data)

    def fail(
        self,
        message: str,
        position: Optional[int] = None,
        *,
        cause: Optional[BaseException] = None,
    ) -> NoReturn:
        """
        Fail parsing, as the RFC's "fail parsing" does.

        The error is reported at position (default: the cursor), with the byte
        there as offending_char; it's None when position is at or past the end.
        cause is chained as the error's __cause__ (raise ... from cause).
        """
        if position is None:
            position = self.cursor
        error = StructuredFieldError(
            message,
            position=position,
            offending_char=self.data[position] if position < len(self.data) else None,
        )
        if cause is None:
            raise error
        raise error from cause
