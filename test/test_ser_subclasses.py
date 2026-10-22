"""ser() accepts subclasses of int and str, serialising their underlying value."""

import unittest
from enum import Enum, IntEnum, IntFlag

from http_sf import DisplayString, Token, ser


class Colour(IntEnum):
    RED = 1
    BLUE = -3


class Perm(IntFlag):
    READ = 4
    WRITE = 2


class Mode(str, Enum):
    FAST = "fast-mode"
    SLOW = "slow mode"


class Huge(IntEnum):
    TOO_BIG = 10**15


class LoudInt(int):
    def __str__(self) -> str:
        return "loud"


class LyingInt(int):
    def __int__(self) -> int:
        return 99


class LoudStr(str):
    def __str__(self) -> str:
        return "loud"

    def __repr__(self) -> str:
        return "LOUD"


class TokenStr(Token, str):  # a str that is also a Token
    pass


class DisplayStr(DisplayString, str):  # a str that is also a DisplayString
    pass


class TestSerSubclasses(unittest.TestCase):
    def test_int_enum_uses_value(self):
        self.assertEqual(ser(Colour.RED), "1")
        self.assertEqual(ser(Colour.BLUE), "-3")

    def test_int_flag(self):
        self.assertEqual(ser(Perm.READ | Perm.WRITE), "6")

    def test_int_subclass_ignores_str_override(self):
        self.assertEqual(ser(LoudInt(7)), "7")

    def test_int_subclass_ignores_int_override(self):
        self.assertEqual(ser(LyingInt(5)), "5")

    def test_int_subclass_range_checked(self):
        with self.assertRaises(ValueError):
            ser(Huge.TOO_BIG)

    def test_str_enum_uses_value_not_name(self):
        self.assertEqual(ser(Mode.FAST), '"fast-mode"')
        self.assertEqual(ser(Mode.SLOW), '"slow mode"')

    def test_str_subclass_ignores_overrides(self):
        self.assertEqual(ser(LoudStr("quiet")), '"quiet"')

    def test_str_subclass_validated_like_str(self):
        with self.assertRaises(ValueError):
            ser(LoudStr("café"))

    def test_nested(self):
        self.assertEqual(
            ser({"a": (Colour.RED, {"m": Mode.FAST}), "b": [Mode.SLOW, Perm.READ]}),
            'a=1;m="fast-mode", b=("slow mode" 4)',
        )
        self.assertEqual(
            ser([Colour.RED, (Mode.FAST, {"c": Colour.BLUE})]), '1, "fast-mode";c=-3'
        )

    def test_exact_types_unchanged(self):
        self.assertEqual(ser(True), "?1")
        self.assertEqual(ser(False), "?0")
        self.assertEqual(ser(1), "1")
        self.assertEqual(ser("a"), '"a"')

    def test_token_and_display_string_keep_their_behaviour(self):
        self.assertEqual(ser(Token("abc")), "abc")
        self.assertEqual(ser(DisplayString("abc")), '%"abc"')
        self.assertEqual(ser(TokenStr("abc")), "abc")
        self.assertEqual(ser(DisplayStr("abc")), '%"abc"')

    def test_unrecognised_still_rejected(self):
        for value in (None, object(), {1}):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    ser(value)


if __name__ == "__main__":
    unittest.main()
