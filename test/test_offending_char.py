"""offending_char is the byte at position, and None only at the end of the input."""

import binascii
import json
import unittest
from pathlib import Path

from http_sf import StructuredFieldError, parse
from http_sf.state import ParserState

SUITE = Path(__file__).resolve().parent / "tests"


def failure(value: bytes, tltype: str) -> StructuredFieldError:
    try:
        parse(value, tltype=tltype)
    except StructuredFieldError as why:
        return why
    raise AssertionError(f"{value!r} parsed")


class TestOffendingChar(unittest.TestCase):
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

    def test_boolean(self):
        self.check(
            [
                (b"?x", "item", "No Boolean value found", 0),
                (b"?", "item", "No Boolean value found", 0),
            ]
        )

    def test_byteseq(self):
        # These are reported at the closing ":".
        self.check(
            [
                (
                    b":aGVs.G8=:",
                    "item",
                    "Binary Sequence contained disallowed character",
                    9,
                ),
                (b":=:", "item", "Binary Sequence failed to decode", 2),
                (b":aGVsbG8===:", "item", "Binary Sequence failed to decode", 11),
                (b":a:", "item", "Binary Sequence failed to decode", 2),
                (b":aGVsbG8=", "item", "Binary Sequence didn't contain ending ':'", 9),
            ]
        )

    def test_date(self):
        self.check(
            [
                (b"@1.5,", "list", "Non-integer Date", 4),
                (b"@1.5", "item", "Non-integer Date", 4),
                (b"@999999999999999", "item", "Date value out of range", 16),
                (b"@999999999999999,", "list", "Date value out of range", 16),
            ]
        )

    def test_display_string(self):
        self.check(
            [
                (b'%"abc%a', "item", "Incomplete percent encoding", 6),
                (b'%"abc%', "item", "Incomplete percent encoding", 6),
                (b'%"%c3"', "item", "Invalid UTF-8", 5),
                (
                    b'%"abc',
                    "item",
                    "Reached end of input without finding a closing DQUOTE",
                    5,
                ),
                (b'%"%C3%A9"', "item", "Uppercase percent encoding", 3),
                (b'%"%gg"', "item", "Invalid percent encoding", 3),
                (b'%"\x7f"', "item", "String contains disallowed character", 2),
                (b"%abc", "item", 'Display string does not start with %"', 0),
            ]
        )

    def test_integer(self):
        self.check(
            [
                (b"1234567890123.1", "item", "Decimal too long.", 13),
                (b"123456789012.1234", "item", "Decimal too long.", 16),
                (b"1234567890123456", "item", "Integer too long.", 15),
                (b"123456789012.", "item", "Decimal ends in '.'", 12),
                (b"1.1234", "item", "Decimal fractional component too long", 5),
                (b"-", "item", "Number input lacked a number", 1),
                (b"-a", "item", "Number doesn't start with a DIGIT", 1),
            ]
        )

    def test_string(self):
        self.check(
            [
                (
                    b'"abc',
                    "item",
                    "Reached end of input without finding a closing DQUOTE",
                    4,
                ),
                (b'"abc\\', "item", "Last character of input was a backslash", 5),
                (b'"a\\b"', "item", "Backslash before disallowed character 'b'", 3),
                (b'"\x7f"', "item", "String contains disallowed character", 1),
            ]
        )

    def test_inner_list(self):
        self.check(
            [
                # Out of input at the top of the loop, then after an item.
                (b"(", "list", "End of inner list not found", 1),
                (b"(a ", "list", "End of inner list not found", 3),
                (b"(a", "list", "End of inner list not found", 2),
                (b"(a\x7f)", "list", "Inner list bad delimitation", 2),
            ]
        )

    def test_list_and_dictionary(self):
        self.check(
            [
                (b"a, b c", "list", "Trailing text after item in list", 5),
                (b"a, ", "list", "Trailing comma at end of list", 3),
                (
                    b"a=1 b",
                    "dictionary",
                    "'a' has trailing characters after the value",
                    4,
                ),
                (b"a b", "dictionary", "'a' should be followed by '=', not 'b'", 2),
                (b"a=1, ", "dictionary", "Dictionary has trailing comma", 5),
            ]
        )

    def test_bare_item_and_keys(self):
        self.check(
            [
                (b"", "item", "Empty item", 0),
                (b"'a'", "item", "Strings must be double-quoted", 0),
                (b"(", "item", "Inner Lists are not valid here", 0),
                (
                    b"!",
                    "item",
                    "There is no Structured Field item starting with '!'",
                    0,
                ),
                (
                    b"a, \x1b",
                    "list",
                    "There is no Structured Field item starting with '\\x1b'",
                    3,
                ),
                (b"a b", "item", "Trailing characters after value (missing comma?)", 2),
                (b"a;", "item", "Trailing delimiter", 2),
                (b"a;B=1", "item", "Key cannot begin with an uppercase character", 2),
                (b"a;1", "item", "Key does not begin with lcalpha or *", 2),
            ]
        )

    def test_error_raised_without_position(self):
        # An error from a duplicate key callback has no position of its own;
        # parse() fills it in from the cursor.
        def callback(key, context):
            raise StructuredFieldError(f"duplicate {key}")

        for value, position in [(b"a=1, a=2, b=3", 8), (b"a=1, a=2", 8)]:
            with self.subTest(value=value):
                with self.assertRaises(StructuredFieldError) as ctx:
                    parse(value, tltype="dictionary", on_duplicate_key=callback)
                self.assertEqual(ctx.exception.position, position)
                self.assertEqual(
                    ctx.exception.offending_char,
                    value[position] if position < len(value) else None,
                )


class TestChaining(unittest.TestCase):
    """The causes passed as cause=... to state.fail()."""

    def test_causes(self):
        cases = [
            (b"?x", "item", KeyError),
            (b"?", "item", IndexError),
            (b":aGVsbG8=", "item", ValueError),
            (b":a:", "item", binascii.Error),
            (b"@999999999999999", "item", OverflowError),
            (b'"abc', "item", IndexError),
            (b'"abc\\', "item", IndexError),
            (b'%"abc', "item", IndexError),
            (b'%"%c3"', "item", UnicodeDecodeError),
            (b"(", "list", IndexError),
            (b"(a", "list", IndexError),
        ]
        for value, tltype, cause in cases:
            with self.subTest(value=value):
                why = failure(value, tltype)
                self.assertIsInstance(why.__cause__, cause)
                self.assertTrue(why.__suppress_context__)
                self.assertIs(why.__context__, why.__cause__)

    def test_no_cause(self):
        cases = [
            (b":=:", "item"),
            (b"1234567890123.", "item"),
            (b"a, b c", "list"),
        ]
        for value, tltype in cases:
            with self.subTest(value=value):
                why = failure(value, tltype)
                self.assertIsNone(why.__cause__)
                self.assertFalse(why.__suppress_context__)
                self.assertIsNone(why.__context__)


class TestSuite(unittest.TestCase):
    """offending_char for every error the shared test suite provokes."""

    def test_suite_errors(self):
        errors = 0
        for path in sorted(SUITE.glob("*.json")):
            with open(path, encoding="utf-8") as fh:
                tests = json.load(fh)
            for test in tests:
                if "raw" not in test:
                    continue
                value = b", ".join(line.encode("utf-8") for line in test["raw"])
                with self.subTest(file=path.name, name=test["name"]):
                    try:
                        parse(value, tltype=test["header_type"])
                    except StructuredFieldError as why:
                        errors += 1
                        self.assertIsNotNone(why.position)
                        if why.position < len(value):
                            self.assertEqual(why.offending_char, value[why.position])
                        else:
                            self.assertIsNone(why.offending_char)
                    else:
                        # can_fail: the library legitimately accepts some of these.
                        self.assertFalse(test.get("must_fail", False))
        self.assertGreater(errors, 100)


class TestFail(unittest.TestCase):
    def test_default_position_is_cursor(self):
        state = ParserState(b"abc")
        state.cursor = 1
        with self.assertRaises(StructuredFieldError) as ctx:
            state.fail("message")
        self.assertEqual(ctx.exception.args[0], "message")
        self.assertEqual(ctx.exception.position, 1)
        self.assertEqual(ctx.exception.offending_char, ord("b"))
        self.assertIsNone(ctx.exception.context)

    def test_explicit_position(self):
        state = ParserState(b"abc")
        state.cursor = 3
        with self.assertRaises(StructuredFieldError) as ctx:
            state.fail("message", state.cursor - 1)
        self.assertEqual(ctx.exception.position, 2)
        self.assertEqual(ctx.exception.offending_char, ord("c"))

    def test_zero_position_is_not_the_default(self):
        state = ParserState(b"abc")
        state.cursor = 2
        with self.assertRaises(StructuredFieldError) as ctx:
            state.fail("message", 0)
        self.assertEqual(ctx.exception.position, 0)
        self.assertEqual(ctx.exception.offending_char, ord("a"))

    def test_end_of_input(self):
        for data, position in [(b"abc", 3), (b"abc", 4), (b"", 0)]:
            with self.subTest(data=data, position=position):
                state = ParserState(data)
                with self.assertRaises(StructuredFieldError) as ctx:
                    state.fail("message", position)
                self.assertEqual(ctx.exception.position, position)
                self.assertIsNone(ctx.exception.offending_char)

    def test_cause(self):
        state = ParserState(b"abc")
        why = IndexError("x")
        with self.assertRaises(StructuredFieldError) as ctx:
            state.fail("message", cause=why)
        self.assertIs(ctx.exception.__cause__, why)

        with self.assertRaises(StructuredFieldError) as ctx:
            state.fail("message")
        self.assertIsNone(ctx.exception.__cause__)
        self.assertFalse(ctx.exception.__suppress_context__)


if __name__ == "__main__":
    unittest.main()
