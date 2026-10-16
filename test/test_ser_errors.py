"""ser() reports unserialisable values with ValueError, and never emits invalid output."""

import unittest
from decimal import Decimal

from http_sf import Token, ser


class TestSerErrors(unittest.TestCase):
    def test_non_finite(self):
        for value in (
            float("inf"),
            float("-inf"),
            float("nan"),
            Decimal("Infinity"),
            Decimal("NaN"),
            Decimal("sNaN"),
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                ser(value)

    def test_oversize(self):
        for value in (Decimal("1e30"), Decimal("-1e30"), 1e15, Decimal("1" * 13)):
            with self.subTest(value=value), self.assertRaises(ValueError):
                ser(value)

    def test_rounds_up_into_oversize(self):
        with self.assertRaises(ValueError):
            ser(Decimal("999999999999.9996"))

    def test_boundaries_still_serialise(self):
        self.assertEqual(ser(Decimal("999999999999.999")), "999999999999.999")
        self.assertEqual(ser(Decimal("-999999999999.999")), "-999999999999.999")
        self.assertEqual(ser(Decimal("0E+50")), "0.0")
        self.assertEqual(ser(Decimal("1e5")), "100000.0")

    def test_empty_token(self):
        with self.assertRaises(ValueError):
            ser(Token(""))
        with self.assertRaises(ValueError):
            ser({"a": (Token(""), {})})
        with self.assertRaises(ValueError):
            ser([(Token(""), {})])

    def test_token_unchanged(self):
        self.assertEqual(ser(Token("a")), "a")
        self.assertEqual(ser(Token("*foo/bar:baz")), "*foo/bar:baz")
        with self.assertRaises(ValueError):
            ser(Token("1a"))


if __name__ == "__main__":
    unittest.main()
