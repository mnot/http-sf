"""Parsing and serialising Decimals must not depend on the global decimal context."""

import decimal
import unittest

from http_sf import parse, ser


class TestDecimalContext(unittest.TestCase):
    def test_parse_with_low_precision(self):
        with decimal.localcontext() as ctx:
            ctx.prec = 5
            self.assertEqual(
                parse(b"123456789.123", tltype="item")[0],
                decimal.Decimal("123456789.123"),
            )
            self.assertEqual(
                parse(b"-123456789.123", tltype="item")[0],
                decimal.Decimal("-123456789.123"),
            )

    def test_ser_with_low_precision(self):
        with decimal.localcontext() as ctx:
            ctx.prec = 5
            self.assertEqual(ser(decimal.Decimal("123456789.123")), "123456789.123")
            self.assertEqual(ser(decimal.Decimal("-0.5")), "-0.5")

    def test_ser_ignores_rounding_mode(self):
        # RFC 9651 says to round half to even.
        for mode in (decimal.ROUND_DOWN, decimal.ROUND_UP, decimal.ROUND_HALF_UP):
            with decimal.localcontext() as ctx:
                ctx.rounding = mode
                self.assertEqual(ser(decimal.Decimal("0.0015")), "0.002")
                self.assertEqual(ser(decimal.Decimal("0.0025")), "0.002")

    def test_ser_ignores_traps(self):
        with decimal.localcontext() as ctx:
            ctx.traps[decimal.Inexact] = True
            self.assertEqual(ser(decimal.Decimal("0.0015")), "0.002")

    def test_ser_float_ignores_float_operation_trap(self):
        with decimal.localcontext() as ctx:
            ctx.traps[decimal.FloatOperation] = True
            self.assertEqual(ser(0.5), "0.5")
            self.assertEqual(ser(0.1), "0.1")

    def test_ser_ignores_rounded_trap(self):
        with decimal.localcontext() as ctx:
            ctx.traps[decimal.Rounded] = True
            self.assertEqual(ser(decimal.Decimal("1.23456")), "1.235")

    def test_caller_flags_untouched(self):
        with decimal.localcontext() as ctx:
            ctx.clear_flags()
            ser(decimal.Decimal("1.23456"))
            self.assertFalse(ctx.flags[decimal.Inexact])
            self.assertFalse(ctx.flags[decimal.Rounded])

    def test_negative_zero_unchanged(self):
        value = parse(b"-0.0", tltype="item")[0]
        self.assertEqual(str(value), "-0.0")
        self.assertEqual(ser(value), "0.0")


if __name__ == "__main__":
    unittest.main()
