"""Error messages must not carry raw input bytes."""

import unittest

from http_sf import StructuredFieldError, parse


class TestErrorEscaping(unittest.TestCase):
    def check(self, value: bytes, tltype: str, char: int) -> None:
        with self.assertRaises(StructuredFieldError) as ctx:
            parse(value, tltype=tltype)
        message = ctx.exception.args[0]
        self.assertTrue(message.isprintable(), message)
        self.assertEqual(ctx.exception.offending_char, char)

    def test_bare_item(self):
        for char in (0x1B, 0x0A, 0x85, 0xFF):
            with self.subTest(char=char):
                self.check(bytes([char]) + b"foo", "item", char)

    def test_dictionary_after_key(self):
        for char in (0x1B, 0x0A, 0x85, 0xFF):
            with self.subTest(char=char):
                self.check(b"a " + bytes([char]), "dictionary", char)

    def test_string_backslash(self):
        for char in (0x1B, 0x0A, 0x85, 0xFF):
            with self.subTest(char=char):
                self.check(b'"\\' + bytes([char]) + b'"', "item", char)

    def test_message_shows_escape(self):
        with self.assertRaises(StructuredFieldError) as ctx:
            parse(b"\x1b[31mfoo", tltype="item")
        self.assertEqual(
            ctx.exception.args[0],
            "There is no Structured Field item starting with '\\x1b'",
        )


if __name__ == "__main__":
    unittest.main()
