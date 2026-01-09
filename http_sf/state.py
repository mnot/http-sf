from http_sf.errors import StructuredFieldError


class ParserState:
    def __init__(self, data: bytes):
        self.data = data
        self.cursor = 0

    def has_data(self) -> bool:
        return self.cursor < len(self.data)

    def peek(self) -> bytes:
        if not self.has_data():
            raise StructuredFieldError(
                "End of input", position=self.cursor, offending_char=None
            )
        return self.data[self.cursor : self.cursor + 1]

    def consume_char(self) -> bytes:
        if not self.has_data():
            raise StructuredFieldError(
                "End of input", position=self.cursor, offending_char=None
            )
        char = self.data[self.cursor : self.cursor + 1]
        self.cursor += 1
        return char
