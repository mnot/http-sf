from decimal import (
    ROUND_HALF_EVEN,
    Context,
    Decimal,
    DivisionByZero,
    InvalidOperation,
    Overflow,
    localcontext,
)
from typing import Union

INT_DIGITS = 12
FRAC_DIGITS = 3
PRECISION = Decimal(10) ** -FRAC_DIGITS

# Fixed, so that the global decimal context can't change what we emit.
_CONTEXT = Context(
    prec=28,
    rounding=ROUND_HALF_EVEN,
    traps=[InvalidOperation, DivisionByZero, Overflow],
)


def ser_decimal(input_decimal: Union[Decimal, float]) -> str:
    with localcontext(_CONTEXT):
        if isinstance(input_decimal, float):
            input_decimal = Decimal(input_decimal)
        if not isinstance(input_decimal, Decimal):
            raise ValueError("decimal input is not decimal")
        if not input_decimal.is_finite():
            raise ValueError(f"decimal is not finite: {input_decimal}")
        if input_decimal and input_decimal.adjusted() >= INT_DIGITS:
            raise ValueError(
                "decimal with oversize integer component: "
                f"{input_decimal.adjusted() + 1} digits"
            )
        input_decimal = round(input_decimal, FRAC_DIGITS)
        abs_decimal = input_decimal.copy_abs()
        integer_component_s = str(int(abs_decimal))
        if len(integer_component_s) > INT_DIGITS:
            raise ValueError(
                f"decimal with oversize integer component {integer_component_s}"
            )
        fractional_component = abs_decimal.quantize(PRECISION).normalize() % 1
        return (
            f"{'-' if input_decimal < 0 else ''}{integer_component_s}."
            f"{str(fractional_component)[2:] if fractional_component else '0'}"
        )
