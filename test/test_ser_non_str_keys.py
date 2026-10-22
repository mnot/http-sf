"""ser() rejects every key that isn't a str with TypeError."""

import unittest
from decimal import Decimal
from typing import Any, Callable

from http_sf import DisplayString, Token, ser
from http_sf.compat import Dictionary, InnerList, Item
from http_sf.util import ser_key

# Each builds a structure with the given key in one of the places a key can go.
PLACES: list[tuple[str, Callable[[Any], Any]]] = [
    ("item parameters", lambda k: (1, {k: 2})),
    ("inner list parameters", lambda k: [([1], {k: 2})]),
    ("dictionary member parameters", lambda k: {"a": (1, {k: 2})}),
    ("dictionary key", lambda k: {k: 2}),
]

# Hashable, so they can be keys in a dict. Tuples of one-character strings used
# to be serialised as their repr (or fail only in a dictionary key) because
# validation iterated over them; the others failed on a bad character or with
# an incidental TypeError.
SEQUENCE_KEYS: list[Any] = [("y",), ("a", "b"), ("-",), frozenset("y")]
OTHER_KEYS: list[Any] = [
    1,
    1.5,
    True,
    None,
    b"y",
    Token("y"),
    DisplayString("y"),
    Decimal("1.5"),
]


class TestNonStrKeys(unittest.TestCase):
    def test_sequence_keys_rejected(self) -> None:
        for key in SEQUENCE_KEYS:
            for where, make in PLACES:
                with self.subTest(key=repr(key), where=where):
                    with self.assertRaises(TypeError):
                        ser(make(key))

    def test_other_non_str_keys_rejected(self) -> None:
        for key in OTHER_KEYS:
            for where, make in PLACES:
                with self.subTest(key=repr(key), where=where):
                    with self.assertRaises(TypeError):
                        ser(make(key))

    def test_ser_key_rejects_unhashable_keys(self) -> None:
        # These can't be dict keys, but ser_key() can be called with them.
        unhashable: list[Any] = [["y"], {"y": 1}, bytearray(b"y"), ()]
        for key in unhashable:
            with self.subTest(key=repr(key)):
                with self.assertRaises(TypeError):
                    ser_key(key)

    def test_message_names_type(self) -> None:
        cases: list[tuple[Any, str]] = [
            (("y",), "tuple"),
            (frozenset("y"), "frozenset"),
            (1, "int"),
            (None, "NoneType"),
            (b"y", "bytes"),
            (Token("y"), "Token"),
        ]
        for key, name in cases:
            with self.subTest(key=repr(key)):
                with self.assertRaises(TypeError) as ctx:
                    ser_key(key)
                self.assertEqual(str(ctx.exception), f"Key must be a str, not {name}")

    def test_non_str_checked_before_content(self) -> None:
        # A tuple of characters that would fail str validation is still a
        # type error, not a value error.
        bad_content: list[Any] = [("A",), ("a b",), ()]
        for key in bad_content:
            with self.subTest(key=repr(key)):
                with self.assertRaises(TypeError):
                    ser((1, {key: 2}))


ZERO_LENGTH = "Zero length key"
DISALLOWED = "Key contains disallowed characters"
BAD_START = "Key does not start with allowed character"
BAD_STR_MESSAGES = [
    ("", ZERO_LENGTH),
    ("Bad Key", DISALLOWED),
    ("a b", DISALLOWED),
    ("café", DISALLOWED),
    ("A", DISALLOWED),
    ("a;b", DISALLOWED),
    ("1a", BAD_START),
    ("-a", BAD_START),
    ("_", BAD_START),
]


class TestStrKeysUnchanged(unittest.TestCase):
    def test_bad_str_key_messages(self) -> None:
        class Sub(str):
            pass

        for key, message in BAD_STR_MESSAGES:
            for where, make in PLACES:
                for kind, value in (("str", key), ("subclass", Sub(key))):
                    with self.subTest(key=key, where=where, kind=kind):
                        with self.assertRaises(ValueError) as ctx:
                            ser(make(value))
                        self.assertEqual(str(ctx.exception), message)

    def test_checks_run_in_order(self) -> None:
        # Type first, then length, then characters, then the first character.
        with self.assertRaises(TypeError):
            ser_key(("",))  # type: ignore[arg-type]
        with self.assertRaises(ValueError) as ctx:
            ser_key("")
        self.assertEqual(str(ctx.exception), ZERO_LENGTH)
        with self.assertRaises(ValueError) as ctx:
            ser_key("1 a")
        self.assertEqual(str(ctx.exception), DISALLOWED)
        with self.assertRaises(ValueError) as ctx:
            ser_key("1a")
        self.assertEqual(str(ctx.exception), BAD_START)

    def test_bad_str_keys_raise_value_error(self) -> None:
        for key in ("", "Bad Key", "a b", "café", "1a"):
            for where, make in PLACES:
                with self.subTest(key=key, where=where):
                    with self.assertRaises(ValueError):
                        ser(make(key))

    def test_valid_str_keys_serialise(self) -> None:
        self.assertEqual(ser((1, {"y": 2, "z": True})), "1;y=2;z")
        self.assertEqual(ser([([1], {"y": 2})]), "(1);y=2")
        self.assertEqual(ser({"a": (1, {"y": 2})}), "a=1;y=2")
        self.assertEqual(ser({"y": 2, "z": True}), "y=2, z")
        self.assertEqual(ser_key("*a-b_c.d1"), "*a-b_c.d1")

    def test_str_subclass_keys_serialise(self) -> None:
        class Loud(str):
            def __str__(self) -> str:
                return "loud"

        self.assertEqual(ser((1, {Loud("y"): 2})), "1;y=2")
        self.assertEqual(ser({Loud("y"): 2}), "y=2")
        with self.assertRaises(ValueError):
            ser_key(Loud("Bad Key"))


class TestCompatNonStrKeys(unittest.TestCase):
    def test_item_params(self) -> None:
        for key in SEQUENCE_KEYS + OTHER_KEYS:
            with self.subTest(key=repr(key)):
                item = Item(1)
                item.params[key] = 2
                with self.assertRaises(TypeError):
                    str(item)

    def test_inner_list_params(self) -> None:
        for key in SEQUENCE_KEYS + OTHER_KEYS:
            with self.subTest(key=repr(key)):
                inner = InnerList([1, 2])
                inner.params[key] = 3
                with self.assertRaises(TypeError):
                    str(inner)

    def test_dictionary_key_and_member_params(self) -> None:
        for key in SEQUENCE_KEYS + OTHER_KEYS:
            with self.subTest(key=repr(key)):
                with self.assertRaises(TypeError):
                    str(Dictionary({key: 1}))
                member = Item(1)
                member.params[key] = 2
                with self.assertRaises(TypeError):
                    str(Dictionary({"a": member}))


if __name__ == "__main__":
    unittest.main()
