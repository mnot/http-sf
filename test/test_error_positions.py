"""Errors that report the fault itself: Non-integer Date and Invalid UTF-8."""

import unittest

from http_sf import StructuredFieldError, parse
from http_sf.date import parse_date
from http_sf.state import ParserState


def failure(value: bytes, tltype: str) -> StructuredFieldError:
    try:
        parse(value, tltype=tltype)
    except StructuredFieldError as why:
        return why
    raise AssertionError(f"{value!r} parsed")


class PositionTestCase(unittest.TestCase):
    def check(self, cases):
        for value, tltype, message, position in cases:
            with self.subTest(value=value, tltype=tltype):
                why = failure(value, tltype)
                self.assertEqual(why.args[0], message)
                self.assertEqual(why.position, position)
                if position < len(value):
                    self.assertEqual(why.offending_char, value[position])
                else:
                    self.assertIsNone(why.offending_char)


class TestNonIntegerDate(PositionTestCase):
    MESSAGE = "Non-integer Date"

    def test_period_is_the_fault(self):
        self.check(
            [
                (b"@1.5,", "list", self.MESSAGE, 2),
                (b"@1.5", "item", self.MESSAGE, 2),
                (b"@1.5 ", "item", self.MESSAGE, 2),
                (b"@1.567", "item", self.MESSAGE, 2),
                (b"@0.0", "item", self.MESSAGE, 2),
                (b"@12.5", "item", self.MESSAGE, 3),
            ]
        )

    def test_negative(self):
        self.check(
            [
                (b"@-1.5", "item", self.MESSAGE, 3),
                (b"@-0.0", "item", self.MESSAGE, 3),
                (b"@-123.456", "item", self.MESSAGE, 5),
            ]
        )

    def test_long_integer_part(self):
        # 12 digits is as long as a Decimal's integer part gets.
        self.check(
            [
                (b"@123456789012.5", "item", self.MESSAGE, 13),
                (b"@-123456789012.5", "item", self.MESSAGE, 14),
            ]
        )

    def test_after_the_number(self):
        # A second period, or an exponent, is not part of the number.
        self.check(
            [
                (b"@1.5.", "item", self.MESSAGE, 2),
                (b"@1.5e3", "item", self.MESSAGE, 2),
                (b"@1.5.5", "item", self.MESSAGE, 2),
            ]
        )

    def test_contexts(self):
        self.check(
            [
                (b"a, @1.5", "list", self.MESSAGE, 5),
                (b"(@1.5)", "list", self.MESSAGE, 3),
                (b"(1 @2.5)", "list", self.MESSAGE, 5),
                (b"a=@1.5", "dictionary", self.MESSAGE, 4),
                (b"a=1, b=@1.5", "dictionary", self.MESSAGE, 9),
                (b"a=(1 @2.5)", "dictionary", self.MESSAGE, 7),
                (b"a;b=@1.5", "item", self.MESSAGE, 6),
                (b"a;b=1;c=@1.5, d", "list", self.MESSAGE, 10),
                (b"a=1;b=@1.5", "dictionary", self.MESSAGE, 8),
                (b"(a;b=@1.5)", "list", self.MESSAGE, 7),
            ]
        )

    def test_context_is_kept(self):
        self.assertEqual(failure(b"a=1, b=@1.5", "dictionary").context, "b")
        self.assertEqual(failure(b"a;b=@1.5", "item").context, "b")

    def test_same_position_as_number_errors(self):
        # Number errors are reported at the byte that causes them, and so is
        # this one.
        self.check(
            [
                (b"@1.", "item", "Decimal ends in '.'", 2),
                (b"1.", "item", "Decimal ends in '.'", 1),
                (b"@1234567890123.5", "item", "Decimal too long.", 14),
                (b"1234567890123.5", "item", "Decimal too long.", 13),
            ]
        )

    def test_direct_call(self):
        state = ParserState(b"xx@1.5")
        state.cursor = 2
        with self.assertRaises(StructuredFieldError) as ctx:
            parse_date(state)
        self.assertEqual(ctx.exception.position, 4)
        self.assertEqual(ctx.exception.offending_char, ord("."))
        self.assertEqual(state.cursor, 6)

    def test_cursor_is_after_the_number(self):
        state = ParserState(b"@1.5,")
        with self.assertRaises(StructuredFieldError):
            parse_date(state)
        self.assertEqual(state.cursor, 4)

    def test_no_cause(self):
        why = failure(b"@1.5", "item")
        self.assertIsNone(why.__cause__)
        self.assertFalse(why.__suppress_context__)

    def test_unchanged(self):
        # Not Non-integer Date errors; these stay where they were.
        self.check(
            [
                (b"@1e5", "item", "Trailing characters after value (missing comma?)", 2),
                (b"@+1", "item", "Number doesn't start with a DIGIT", 1),
                (b"@.5", "item", "Number doesn't start with a DIGIT", 1),
                (b"@", "item", "Number input lacked a number", 1),
                (b"@999999999999999", "item", "Date value out of range", 16),
                (b"@-999999999999999", "item", "Date value out of range", 17),
                (b"@253402300800", "item", "Date value out of range", 13),
            ]
        )

    def test_integers_parse(self):
        for value in (b"@1", b"@-1", b"@0", b"@-0", b"@253402300799", b"@-62135596800"):
            with self.subTest(value=value):
                parse(value, tltype="item")
        parse(b"a=@1, b;c=@-2", tltype="dictionary")
        parse(b"@1, (@2 @3;a=@4)", tltype="list")


if __name__ == "__main__":
    unittest.main()
