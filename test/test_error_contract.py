"""
Tests that all parse errors raise StructuredFieldError, never bare ValueError
or OSError, regardless of input. Covers cases where the SF integer range
permits values that downstream Python APIs reject.
"""
import sys
from http_sf import parse, StructuredFieldError


def test_date_out_of_range():
    print("Testing out-of-range Date values raise StructuredFieldError...")

    # Max SF integer — year ~31 million, far outside datetime's year 1-9999 range
    try:
        parse(b"@999999999999999", tltype="item")
        print("  Test 1: FAIL (no exception raised)")
        sys.exit(1)
    except StructuredFieldError:
        print("  Test 1: OK (large positive timestamp)")
    except (ValueError, OSError) as e:
        print(f"  Test 1: FAIL (wrong exception type {type(e).__name__}: {e})")
        sys.exit(1)

    # Min SF integer — far before year 1
    try:
        parse(b"@-999999999999999", tltype="item")
        print("  Test 2: FAIL (no exception raised)")
        sys.exit(1)
    except StructuredFieldError:
        print("  Test 2: OK (large negative timestamp)")
    except (ValueError, OSError) as e:
        print(f"  Test 2: FAIL (wrong exception type {type(e).__name__}: {e})")
        sys.exit(1)

    print("All Date out-of-range tests passed.")


def test_decimal_too_long():
    print("Testing overlong decimal integer part raises StructuredFieldError...")

    # 14 digits before decimal point — exceeds the 12-digit SF limit
    try:
        parse(b"12345678901234.1", tltype="item")
        print("  Test 1: FAIL (no exception raised)")
        sys.exit(1)
    except StructuredFieldError:
        print("  Test 1: OK (14-digit integer part)")
    except ValueError as e:
        print(f"  Test 1: FAIL (wrong exception type ValueError: {e})")
        sys.exit(1)

    # Exactly at the boundary — 13 digits before decimal (also invalid per spec)
    try:
        parse(b"1234567890123.1", tltype="item")
        print("  Test 2: FAIL (no exception raised)")
        sys.exit(1)
    except StructuredFieldError:
        print("  Test 2: OK (13-digit integer part)")
    except ValueError as e:
        print(f"  Test 2: FAIL (wrong exception type ValueError: {e})")
        sys.exit(1)

    print("All Decimal too-long tests passed.")


def test_decimal_too_long_at_end_of_input():
    print("Testing overlong decimal at end of input raises StructuredFieldError...")

    # 13 digits then a period as the last byte; used to raise IndexError, or
    # (inside a parameter) to be silently accepted as a bare parameter.
    cases = [
        (b"1234567890123.", "item"),
        (b"1234567890123.", "list"),
        (b"1;a=1234567890123.", "item"),
        (b"a;b=1111111111111.", "dictionary"),
        (b"a=1;b=1234567890123.", "dictionary"),
    ]
    for value, tltype in cases:
        try:
            parse(value, tltype=tltype)
            print(f"  {value!r} as {tltype}: FAIL (no exception raised)")
            sys.exit(1)
        except StructuredFieldError as e:
            assert e.offending_char is None, e.offending_char
            assert e.position == len(value), e.position
            print(f"  {value!r} as {tltype}: OK")
        except Exception as e:  # pylint: disable=broad-except
            print(f"  {value!r} as {tltype}: FAIL ({type(e).__name__}: {e})")
            sys.exit(1)

    print("All end-of-input decimal tests passed.")


if __name__ == "__main__":
    test_date_out_of_range()
    print()
    test_decimal_too_long()
    print()
    test_decimal_too_long_at_end_of_input()
