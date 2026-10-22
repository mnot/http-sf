"""Number length limits, as RFC 9651 section 4.2.4 steps 7.3.1, 7.5 and 7.6 set them."""

import unittest
from decimal import Decimal

from http_sf import StructuredFieldError, parse


def failure(value: bytes, tltype: str = "item") -> StructuredFieldError:
    try:
        parse(value, tltype=tltype)
    except StructuredFieldError as why:
        return why
    raise AssertionError(f"{value!r} parsed")


class TestIntegerLength(unittest.TestCase):
    def test_min_int(self):
        # The shared suite covers the positive limit and 15 characters with
        # leading zeros, but not this one.
        self.assertEqual(
            parse(b"-999999999999999", tltype="item"), (-999999999999999, {})
        )

    def test_sixteen_characters_fail(self):
        # Step 7.5 counts characters, not magnitude; leading zeros count.
        values = [
            b"1000000000000000",
            b"0777777777777775",
            b"0000000000000001",
            b"0000000000000000",
            b"-1000000000000000",
            b"-0000000000000001",
        ]
        for value in values:
            with self.subTest(value=value):
                why = failure(value)
                self.assertEqual(why.args[0], "Integer too long.")
                # The 16th character, after the sign if any.
                self.assertEqual(why.position, 15 + value.startswith(b"-"))
                self.assertIsNone(why.offending_char)

    def test_sixteen_fail_in_context(self):
        # (value, header type, index of the 16th digit)
        cases = [
            (b"0000000000000001;a", "item", 15),
            (b"a;b=0000000000000001", "item", 19),
            (b"1, 0000000000000001", "list", 18),
            (b"(1 0000000000000001)", "list", 18),
            (b"a=0000000000000001", "dictionary", 17),
            (b"@0000000000000001", "item", 16),
            (b"0000000000000001,", "list", 15),
        ]
        for value, tltype, position in cases:
            with self.subTest(value=value):
                why = failure(value, tltype)
                self.assertEqual(why.args[0], "Integer too long.")
                self.assertEqual(why.position, position)

    def test_stops_at_sixteenth(self):
        # The parser stops there; it doesn't scan to the end of the digits.
        why = failure(b"12345678901234567890")
        self.assertEqual(why.args[0], "Integer too long.")
        self.assertEqual(why.position, 15)


class TestDecimalLength(unittest.TestCase):
    def test_limits_parse(self):
        cases = {
            b"123456789012.123": Decimal("123456789012.123"),
            b"-123456789012.123": Decimal("-123456789012.123"),
            b"000000000012.100": Decimal("12.100"),
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                result = parse(value, tltype="item")[0]
                self.assertIsInstance(result, Decimal)
                self.assertEqual(result, expected)

    def test_integer_part_too_long(self):
        # Step 7.3.1: more than 12 characters before the ".".
        # Reported at the ".", the character just consumed.
        for value in [
            b"1234567890123.1",
            b"12345678901234.1",
            b"0000000000000.1",
            b"1234567890123.",
        ]:
            with self.subTest(value=value):
                why = failure(value)
                self.assertEqual(why.args[0], "Decimal too long.")
                self.assertEqual(why.position, value.index(b"."))
                self.assertIsNone(why.offending_char)

    def test_sixteen_digits_then_period(self):
        # Step 7.5 fires on the 16th digit, before the "." is reached.
        why = failure(b"1234567890123456.1")
        self.assertEqual(why.args[0], "Integer too long.")
        self.assertEqual(why.position, 15)

    def test_total_too_long(self):
        # Step 7.6: 17 characters including the ".".
        for value in [b"123456789012.1234", b"-123456789012.1234"]:
            with self.subTest(value=value):
                why = failure(value)
                self.assertEqual(why.args[0], "Decimal too long.")
                self.assertEqual(why.position, 16 + value.startswith(b"-"))
                self.assertIsNone(why.offending_char)

    def test_fraction_too_long(self):
        # Step 9.2, reached when the total is within 16 characters.
        why = failure(b"1.1234")
        self.assertEqual(why.args[0], "Decimal fractional component too long")
        self.assertEqual(why.position, 5)

    def test_ends_in_period(self):
        why = failure(b"123456789012.")
        self.assertEqual(why.args[0], "Decimal ends in '.'")
        self.assertEqual(why.position, 12)


if __name__ == "__main__":
    unittest.main()
