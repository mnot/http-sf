"""DisplayStrings wrapping str subclasses (e.g., str Enums) use the underlying value."""

import json
import sys
import unittest
from enum import Enum, IntEnum
from typing import Any, Iterator

from http_sf import DisplayString, Token, parse, ser, to_json
from http_sf.compat import Dictionary, InnerList, Item, List


class Disp(str, Enum):
    D = "d"
    UNICODE = 'café ☃ %"'
    EMPTY = ""


class Number(IntEnum):
    ONE = 1


class LoudStr(str):
    def __str__(self) -> str:
        return "loud"

    def __format__(self, format_spec: str) -> str:
        return "LOUD"


class LyingStr(str):
    def __len__(self) -> int:
        return 1

    def __iter__(self) -> Iterator[str]:
        return iter("a")

    def __getitem__(self, key: Any) -> str:  # type: ignore[override]
        return "a"


class StrProxy:
    """Not a str, but claims to be one through __class__."""

    @property  # type: ignore[misc]
    def __class__(self) -> type:  # type: ignore[override]
        return str

    def __str__(self) -> str:
        return "abc"


ENUMS: list[tuple[str, Any]] = [("(str, Enum)", Disp)]
if sys.version_info >= (3, 11):
    from enum import StrEnum

    class StrDisp(StrEnum):
        D = "d"
        UNICODE = 'café ☃ %"'
        EMPTY = ""

    ENUMS.append(("StrEnum", StrDisp))


def value_of(token_json: str) -> Any:
    return json.loads(token_json)["value"]


class TestDisplayStringEnums(unittest.TestCase):
    def test_str_and_format(self) -> None:
        for name, enum in ENUMS:
            with self.subTest(enum=name):
                display = DisplayString(enum.D)
                self.assertEqual(str(display), "d")
                self.assertIs(type(str(display)), str)
                self.assertEqual(f"{display}", "d")
                self.assertEqual("%s" % display, "d")

    def test_to_json(self) -> None:
        for name, enum in ENUMS:
            with self.subTest(enum=name):
                self.assertEqual(
                    to_json(DisplayString(enum.D)),
                    '{"__type": "displaystring", "value": "d"}',
                )
                self.assertEqual(
                    value_of(to_json(DisplayString(enum.UNICODE))),
                    'café ☃ %"',
                )
                self.assertEqual(value_of(to_json(DisplayString(enum.EMPTY))), "")

    def test_ser_agrees_with_to_json(self) -> None:
        for name, enum in ENUMS:
            for member in (enum.D, enum.UNICODE, enum.EMPTY):
                with self.subTest(enum=name, member=member.name):
                    plain = DisplayString(str.__str__(member))
                    wrapped = DisplayString(member)
                    self.assertEqual(ser(wrapped), ser(plain))
                    self.assertEqual(to_json(wrapped), to_json(plain))

    def test_ser(self) -> None:
        for name, enum in ENUMS:
            with self.subTest(enum=name):
                self.assertEqual(ser(DisplayString(enum.D)), '%"d"')
                self.assertEqual(
                    ser(DisplayString(enum.UNICODE)), '%"caf%c3%a9 %e2%98%83 %25%22"'
                )
                self.assertEqual(ser(DisplayString(enum.EMPTY)), '%""')
                self.assertEqual(ser((1, {"p": DisplayString(enum.D)})), '1;p=%"d"')
                self.assertEqual(ser([[DisplayString(enum.D)]]), '(%"d")')
                self.assertEqual(ser({"a": DisplayString(enum.D)}), 'a=%"d"')

    def test_compat(self) -> None:
        for name, enum in ENUMS:
            with self.subTest(enum=name):
                self.assertEqual(str(Item(DisplayString(enum.D))), '%"d"')
                self.assertEqual(str(InnerList([DisplayString(enum.D)])), '(%"d")')
                self.assertEqual(str(List([DisplayString(enum.D)])), '%"d"')
                self.assertEqual(
                    str(Dictionary({"a": DisplayString(enum.D)})), 'a=%"d"'
                )


class TestDisplayStringStrSubclasses(unittest.TestCase):
    def test_overridden_str_and_format_ignored(self) -> None:
        display = DisplayString(LoudStr("y"))
        self.assertEqual(str(display), "y")
        self.assertEqual(f"{display}", "y")
        self.assertEqual(ser(display), '%"y"')
        self.assertEqual(value_of(to_json(display)), "y")

    def test_lying_length_iteration_and_indexing(self) -> None:
        display = DisplayString(LyingStr("abc"))
        self.assertEqual(str(display), "abc")
        self.assertEqual(ser(display), '%"abc"')
        self.assertEqual(value_of(to_json(display)), "abc")

    def test_object_faking_str_class_unchanged(self) -> None:
        proxy = StrProxy()
        self.assertTrue(isinstance(proxy, str))
        self.assertEqual(str(DisplayString(proxy)), "abc")  # type: ignore[arg-type]

    def test_non_str_data_stringified_as_before(self) -> None:
        for data in (None, 5, Number.ONE):
            with self.subTest(data=repr(data)):
                display = DisplayString(data)  # type: ignore[arg-type]
                self.assertEqual(str(display), str(data))
        self.assertEqual(str(DisplayString(None)), "None")  # type: ignore[arg-type]


class TestPlainDisplayStrings(unittest.TestCase):
    def test_unchanged(self) -> None:
        display = DisplayString("abc")
        self.assertEqual(str(display), "abc")
        self.assertEqual(f"{display}", "abc")
        self.assertEqual(repr(display), 'DisplayString("abc")')
        self.assertEqual(display, DisplayString("abc"))
        self.assertEqual(display, "abc")
        self.assertEqual(hash(display), hash("abc"))
        self.assertEqual(ser(display), '%"abc"')
        self.assertEqual(
            to_json(display), '{"__type": "displaystring", "value": "abc"}'
        )

    def test_non_ascii_round_trip(self) -> None:
        for text in ("café", "☃ snow", 'q"u%o', "\U0001f600", ""):
            with self.subTest(text=text):
                wire = ser(DisplayString(text))
                parsed = parse(wire.encode("ascii"), tltype="item")
                assert isinstance(parsed, tuple)
                display = parsed[0]
                assert isinstance(display, DisplayString)
                self.assertIs(type(display.data), str)
                self.assertEqual(str(display), text)
                self.assertEqual(value_of(to_json(display)), text)
                self.assertEqual(ser(parsed), wire)

    def test_parsed_string_matches_enum_wire_form(self) -> None:
        wire = ser(DisplayString(Disp.UNICODE))
        parsed = parse(wire.encode("ascii"), tltype="item")
        assert isinstance(parsed, tuple)
        self.assertEqual(str(parsed[0]), str.__str__(Disp.UNICODE))


class TestJsonTokensAndDisplayStrings(unittest.TestCase):
    def test_both_types_in_one_structure(self) -> None:
        for name, enum in ENUMS:
            with self.subTest(enum=name):
                structure = [Token("t"), DisplayString(enum.D), (1, {"p": enum.D})]
                self.assertEqual(
                    json.loads(to_json(structure)),
                    [
                        {"__type": "token", "value": "t"},
                        {"__type": "displaystring", "value": "d"},
                        [1, {"p": "d"}],
                    ],
                )


if __name__ == "__main__":
    unittest.main()
