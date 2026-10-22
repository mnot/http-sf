"""ser() serialises str-subclass keys (e.g., str Enum members) from their value."""

import sys
import unittest
from enum import Enum
from typing import Any, Callable, Iterator

from http_sf import ser


class Key(str, Enum):
    Y = "y"
    BAD = "Bad Key"


class LoudKey(str):
    def __str__(self) -> str:
        return "loud"

    def __format__(self, format_spec: str) -> str:
        return "LOUD"


class LyingKey(str):
    def __len__(self) -> int:
        return 1

    def __iter__(self) -> Iterator[str]:
        return iter("a")


KEY_TYPES: list[tuple[str, Any]] = [("(str, Enum)", Key)]
if sys.version_info >= (3, 11):
    from enum import StrEnum

    class StrKey(StrEnum):
        Y = "y"
        BAD = "Bad Key"

    KEY_TYPES.append(("StrEnum", StrKey))

# Each builds a structure with the given key in one of the places a key can go.
PLACES: list[tuple[str, Callable[[Any], Any]]] = [
    ("item parameters", lambda k: (1, {k: 2})),
    ("inner list parameters", lambda k: [([1], {k: 2})]),
    ("dictionary member parameters", lambda k: {"a": (1, {k: 2})}),
    ("dictionary key", lambda k: {k: 2}),
]


class TestSerParamKeys(unittest.TestCase):
    def test_item_param_key(self) -> None:
        for name, enum in KEY_TYPES:
            with self.subTest(enum=name):
                self.assertEqual(ser((1, {enum.Y: 2})), "1;y=2")
                self.assertEqual(ser((1, {enum.Y: True})), "1;y")

    def test_inner_list_param_key(self) -> None:
        for name, enum in KEY_TYPES:
            with self.subTest(enum=name):
                self.assertEqual(ser([([1, 2], {enum.Y: 3})]), "(1 2);y=3")

    def test_dictionary_member_param_key(self) -> None:
        for name, enum in KEY_TYPES:
            with self.subTest(enum=name):
                self.assertEqual(ser({"a": (1, {enum.Y: 2})}), "a=1;y=2")
                self.assertEqual(ser({"a": (True, {enum.Y: 2})}), "a;y=2")

    def test_dictionary_key(self) -> None:
        for name, enum in KEY_TYPES:
            with self.subTest(enum=name):
                self.assertEqual(ser({enum.Y: 1}), "y=1")
                self.assertEqual(ser({enum.Y: True}), "y")
                self.assertEqual(ser({enum.Y: (True, {"p": 1})}), "y;p=1")

    def test_overridden_str_and_format_ignored(self) -> None:
        self.assertEqual(ser((1, {LoudKey("y"): 2})), "1;y=2")
        self.assertEqual(ser({LoudKey("y"): 2}), "y=2")

    def test_invalid_key_rejected_like_str(self) -> None:
        for name, enum in KEY_TYPES:
            for where, make in PLACES:
                with self.subTest(enum=name, where=where):
                    with self.assertRaises(ValueError) as plain:
                        ser(make("Bad Key"))
                    with self.assertRaises(ValueError) as wrapped:
                        ser(make(enum.BAD))
                    self.assertEqual(str(plain.exception), str(wrapped.exception))

    def test_validation_uses_underlying_value(self) -> None:
        for where, make in PLACES:
            with self.subTest(where=where):
                with self.assertRaises(ValueError):
                    ser(make(LyingKey("a b")))

    def test_plain_str_keys_unchanged(self) -> None:
        self.assertEqual(ser((1, {"y": 2, "z": True})), "1;y=2;z")
        self.assertEqual(ser({"y": 2, "z": True}), "y=2, z")


if __name__ == "__main__":
    unittest.main()
