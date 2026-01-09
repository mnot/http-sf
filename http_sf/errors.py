from typing import Optional


class StructuredFieldError(ValueError):
    def __init__(
        self,
        *args: object,
        position: Optional[int] = None,
        offending_char: Optional[int] = None,
        context: Optional[str] = None,
    ) -> None:
        self.position = position
        self.offending_char = offending_char
        self.context = context
        super().__init__(*args)
