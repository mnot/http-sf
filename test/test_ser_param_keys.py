"""ser() serialises str-subclass keys (e.g., str Enum members) from their value."""

import sys
import unittest
from enum import Enum
from typing import Any, Callable, Iterator

from http_sf import ser
from http_sf.compat import Dictionary, InnerList, Item


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


class HashKey(str):
    def __hash__(self) -> int:
        return 1

    def __eq__(self, other: object) -> bool:
        return False


class ClassKey(str):
    @property  # type: ignore[misc]
    def __class__(self) -> type:  # type: ignore[override]
        return int


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

    def test_hash_eq_and_class_overrides_ignored(self) -> None:
        for key in (HashKey("y"), ClassKey("y")):
            with self.subTest(key=type(key).__name__):
                self.assertEqual(ser((1, {key: 2})), "1;y=2")
                self.assertEqual(ser({key: 2}), "y=2")


class TestCompatKeys(unittest.TestCase):
    def test_item_params(self) -> None:
        for name, enum in KEY_TYPES:
            with self.subTest(enum=name):
                item = Item(1)
                item.params[enum.Y] = 2
                self.assertEqual(str(item), "1;y=2")

    def test_inner_list_params(self) -> None:
        for name, enum in KEY_TYPES:
            with self.subTest(enum=name):
                inner = InnerList([1, 2])
                inner.params[enum.Y] = 3
                self.assertEqual(str(inner), "(1 2);y=3")

    def test_dictionary_key_and_member_params(self) -> None:
        for name, enum in KEY_TYPES:
            with self.subTest(enum=name):
                dictionary = Dictionary({enum.Y: 1})
                self.assertEqual(str(dictionary), "y=1")
                member = Item(1)
                member.params[enum.Y] = 2
                dictionary["z"] = member
                self.assertEqual(str(dictionary), "y=1, z=1;y=2")

    def test_invalid_key_rejected(self) -> None:
        for name, enum in KEY_TYPES:
            with self.subTest(enum=name):
                item = Item(1)
                item.params[enum.BAD] = 2
                with self.assertRaises(ValueError):
                    str(item)
                with self.assertRaises(ValueError):
                    str(Dictionary({enum.BAD: 1}))


if __name__ == "__main__":
    unittest.main()
