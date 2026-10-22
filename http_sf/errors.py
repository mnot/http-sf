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

    def __str__(self) -> str:
        # position and context are often filled in after construction, so
        # they're read here rather than baked into args.
        parts = [super().__str__()]
        if self.position is not None:
            parts.append(f"at position {self.position}")
        if self.context is not None:
            parts.append(f"(in {self.context!r})")
        return " ".join(part for part in parts if part)
