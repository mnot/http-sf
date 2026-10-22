"""ser() serialises Tokens wrapping str subclasses (e.g., str Enums) from their value."""

import sys
import unittest
from enum import Enum, IntEnum
from typing import Any, Callable, Iterator

from http_sf import Token, parse, ser, to_json
from http_sf.compat import Dictionary, InnerList, Item, List


class Tok(str, Enum):
    Y = "y"
    SPACE = "a b"
    EMPTY = ""
    DIGIT = "1abc"


class LoudStr(str):
    def __str__(self) -> str:
        return "loud"

    def __format__(self, format_spec: str) -> str:
        return "LOUD"

    def __repr__(self) -> str:
        return "LOUD"


class LyingStr(str):
    def __len__(self) -> int:
        return 1

    def __iter__(self) -> Iterator[str]:
        return iter("a")

    def __getitem__(self, key: Any) -> str:  # type: ignore[override]
        return "a"


class ClassStr(str):
    @property  # type: ignore[misc]
    def __class__(self) -> type:  # type: ignore[override]
        return int


class Number(IntEnum):
    ONE = 1


class StrProxy:
    """Not a str, but claims to be one through __class__."""

    @property  # type: ignore[misc]
    def __class__(self) -> type:  # type: ignore[override]
        return str

    def __len__(self) -> int:
        return 3

    def __str__(self) -> str:
        return "abc"


class CustomToken(Token):
    def __str__(self) -> str:
        return "custom"


class SuperToken(Token):
    def __str__(self) -> str:
        return super().__str__()


ENUMS: list[tuple[str, Any]] = [("(str, Enum)", Tok)]
if sys.version_info >= (3, 11):
    from enum import StrEnum

    class StrTok(StrEnum):
        Y = "y"
        SPACE = "a b"
        EMPTY = ""
        DIGIT = "1abc"

    ENUMS.append(("StrEnum", StrTok))

# Each builds a structure with the given Token in one of the places a Token can go.
PLACES: list[tuple[str, Callable[[Any], Any]]] = [
    ("item", lambda t: t),
    ("item with parameters", lambda t: (t, {"p": 1})),
    ("parameter value", lambda t: (1, {"p": t})),
    ("list member", lambda t: [t]),
    ("inner list member", lambda t: [[t, 1]]),
    ("inner list parameter value", lambda t: [([1], {"p": t})]),
    ("dictionary member", lambda t: {"a": t}),
    ("dictionary member parameter value", lambda t: {"a": (1, {"p": t})}),
    ("dictionary inner list member", lambda t: {"a": [t]}),
]


class TestSerTokenEnums(unittest.TestCase):
    def test_top_level(self) -> None:
        for name, enum in ENUMS:
            with self.subTest(enum=name):
                self.assertEqual(ser(Token(enum.Y)), "y")

    def test_parameter_value(self) -> None:
        for name, enum in ENUMS:
            with self.subTest(enum=name):
                self.assertEqual(ser((1, {"p": Token(enum.Y)})), "1;p=y")

    def test_inner_list(self) -> None:
        for name, enum in ENUMS:
            with self.subTest(enum=name):
                self.assertEqual(ser([[Token(enum.Y), 1]]), "(y 1)")
                self.assertEqual(ser([([Token(enum.Y)], {"p": 1})]), "(y);p=1")

    def test_dictionary_member(self) -> None:
        for name, enum in ENUMS:
            with self.subTest(enum=name):
                self.assertEqual(ser({"a": Token(enum.Y)}), "a=y")
                self.assertEqual(
                    ser({"a": (Token(enum.Y), {"p": Token(enum.Y)})}), "a=y;p=y"
                )

    def test_every_place(self) -> None:
        for name, enum in ENUMS:
            for where, make in PLACES:
                with self.subTest(enum=name, where=where):
                    self.assertEqual(ser(make(Token(enum.Y))), ser(make(Token("y"))))

    def test_invalid_value_rejected_like_str(self) -> None:
        for name, enum in ENUMS:
            for member, plain in (
                (enum.SPACE, "a b"),
                (enum.EMPTY, ""),
                (enum.DIGIT, "1abc"),
            ):
                for where, make in PLACES:
                    with self.subTest(enum=name, value=plain, where=where):
                        with self.assertRaises(ValueError) as expected:
                            ser(make(Token(plain)))
                        with self.assertRaises(ValueError) as wrapped:
                            ser(make(Token(member)))
                        self.assertEqual(
                            str(expected.exception), str(wrapped.exception)
                        )

    def test_str_and_json(self) -> None:
        for name, enum in ENUMS:
            with self.subTest(enum=name):
                token = Token(enum.Y)
                self.assertEqual(str(token), "y")
                self.assertIs(type(str(token)), str)
                self.assertEqual(to_json(token), to_json(Token("y")))
                self.assertEqual(to_json(token), '{"__type": "token", "value": "y"}')


class TestSerTokenStrSubclasses(unittest.TestCase):
    def test_overridden_str_and_format_ignored(self) -> None:
        for where, make in PLACES:
            with self.subTest(where=where):
                self.assertEqual(ser(make(Token(LoudStr("y")))), ser(make(Token("y"))))

    def test_validation_uses_underlying_value(self) -> None:
        for where, make in PLACES:
            with self.subTest(where=where):
                with self.assertRaises(ValueError):
                    ser(make(Token(LyingStr("a b"))))

    def test_lying_length_does_not_hide_empty(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            ser(Token(LyingStr("")))
        self.assertEqual(str(ctx.exception), "Token is empty")

    def test_lying_iteration_does_not_change_output(self) -> None:
        self.assertEqual(ser(Token(LyingStr("abc"))), "abc")

    def test_class_override_ignored(self) -> None:
        self.assertEqual(ser(Token(ClassStr("y"))), "y")

    def test_object_faking_str_class_unchanged(self) -> None:
        proxy = StrProxy()
        self.assertTrue(isinstance(proxy, str))
        self.assertEqual(str(Token(proxy)), "abc")  # type: ignore[arg-type]
        self.assertEqual(ser(Token(proxy)), "abc")  # type: ignore[arg-type]

    def test_result_is_plain_str(self) -> None:
        for value in (Tok.Y, LoudStr("y"), LyingStr("y"), "y"):
            with self.subTest(value=type(value).__name__):
                self.assertIs(type(ser(Token(value))), str)


class TestPlainTokens(unittest.TestCase):
    def test_plain_token_unchanged(self) -> None:
        self.assertEqual(ser(Token("foo")), "foo")
        self.assertEqual(ser(Token("*foo:/bar")), "*foo:/bar")
        self.assertEqual(ser((1, {"p": Token("foo")})), "1;p=foo")
        self.assertEqual(str(Token("foo")), "foo")
        self.assertEqual(repr(Token("foo")), 'Token("foo")')

    def test_plain_invalid_tokens_unchanged(self) -> None:
        for value, message in (
            ("", "Token is empty"),
            ("1abc", "Token didn't start with legal character"),
            ("a b", "Token contains disallowed characters"),
        ):
            with self.subTest(value=value):
                with self.assertRaises(ValueError) as ctx:
                    ser(Token(value))
                self.assertEqual(str(ctx.exception), message)

    def test_parse_unaffected(self) -> None:
        parsed = parse(b"foo;p=bar", tltype="item")
        assert isinstance(parsed, tuple)
        token, params = parsed
        self.assertEqual(token, Token("foo"))
        assert isinstance(token, Token)
        self.assertIs(type(token.data), str)
        self.assertIs(type(params["p"].data), str)
        self.assertEqual(ser(parsed), "foo;p=bar")

    def test_non_str_data_raises_type_error(self) -> None:
        for data in (None, True, False, 0, 5, 1.5, Number.ONE):
            for where, make in PLACES:
                with self.subTest(data=repr(data), where=where):
                    with self.assertRaises(TypeError):
                        ser(make(Token(data)))  # type: ignore[arg-type]

    def test_token_subclass_str_override_honoured(self) -> None:
        self.assertEqual(ser(CustomToken("abc")), "custom")
        self.assertEqual(ser(CustomToken(Tok.Y)), "custom")
        self.assertEqual(ser((1, {"p": CustomToken("abc")})), "1;p=custom")

    def test_token_subclass_calling_super_str(self) -> None:
        self.assertEqual(ser(SuperToken(Tok.Y)), "y")
        with self.assertRaises(ValueError):
            ser(SuperToken(Tok.SPACE))

    def test_token_from_token(self) -> None:
        self.assertEqual(ser(Token(Token(Tok.Y))), "y")  # type: ignore[arg-type]


class TestCompatTokens(unittest.TestCase):
    def test_item(self) -> None:
        for name, enum in ENUMS:
            with self.subTest(enum=name):
                self.assertEqual(str(Item(Token(enum.Y))), "y")
                item = Item(1)
                item.params["p"] = Token(enum.Y)
                self.assertEqual(str(item), "1;p=y")

    def test_inner_list(self) -> None:
        for name, enum in ENUMS:
            with self.subTest(enum=name):
                inner = InnerList([Token(enum.Y), 1])
                inner.params["p"] = Token(enum.Y)
                self.assertEqual(str(inner), "(y 1);p=y")

    def test_list_and_dictionary(self) -> None:
        for name, enum in ENUMS:
            with self.subTest(enum=name):
                self.assertEqual(str(List([Token(enum.Y), 1])), "y, 1")
                self.assertEqual(str(Dictionary({"a": Token(enum.Y)})), "a=y")

    def test_invalid_value_rejected(self) -> None:
        for name, enum in ENUMS:
            with self.subTest(enum=name):
                with self.assertRaises(ValueError):
                    str(Item(Token(enum.SPACE)))
                with self.assertRaises(ValueError):
                    str(Dictionary({"a": Token(enum.EMPTY)}))


if __name__ == "__main__":
    unittest.main()
