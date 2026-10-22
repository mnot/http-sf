class ParserState:
    def __init__(self, data: bytes):
        self.data = data
        self.cursor = 0

    def has_data(self) -> bool:
        return self.cursor < len(self.data)
