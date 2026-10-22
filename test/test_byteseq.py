"""Byte Sequence parsing: behaviour at the edges, and linear cost."""

import unittest

from http_sf import StructuredFieldError, parse


class TestByteSeq(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(parse(b":aGVsbG8=:", tltype="item")[0], b"hello")
        self.assertEqual(parse(b"::", tltype="item")[0], b"")

    def test_padding_is_optional(self):
        # RFC 9651 section 4.2.7: parsers SHOULD NOT fail on missing padding.
        for value, expected in (
            (b":aGVsbG8:", b"hello"),  # unpadded
            (b":uuueGVsbG8=:", b"\xba\xeb\x9e\x19[\x1b\x1b"),  # partially padded
            (b":aGVsbG8==:", b"hello"),  # extra padding
            (b":aGVsbG8=:", b"hello"),
            (b":AA:", b"\x00"),
            (b":AA=:", b"\x00"),
            (b":AA==:", b"\x00"),
            (b":AAA:", b"\x00\x00"),
            (b":AAAA:", b"\x00\x00\x00"),
            (b":iZ==:", b"\x89"),  # non-zero pad bits
            (b":iZ:", b"\x89"),  # non-zero pad bits, unpadded
        ):
            with self.subTest(value=value):
                self.assertEqual(parse(value, tltype="item")[0], expected)

    def test_padding_elsewhere_still_fails(self):
        for value in (
            b":=aGVsbG8=:",  # padding at beginning
            b":a=GVsbG8=:",  # padding in middle
            b":aGVs=bG8=:",
            b":a:",  # one leftover character can't encode a byte
            b":aGVsbG8aa:",  # likewise, after full groups
        ):
            with self.subTest(value=value), self.assertRaises(StructuredFieldError):
                parse(value, tltype="item")

    def test_padding_run_limits(self):
        # Padding is at most two characters, and needs data in front of it.
        for value in (
            b":AA===:",
            b":AAAA====:",
            b":aGVsbG8===:",
            b":=:",
            b":==:",
            b":===:",
            b":====:",
        ):
            with self.subTest(value=value), self.assertRaises(StructuredFieldError):
                parse(value, tltype="item")

    def test_alphabet_still_enforced(self):
        for value in (
            b":aGVsbG8=!:",
            b":aGVsbG8.:",
            b":aGVsb G8=:",
            b":aGVs\nbG8=:",  # line feed
            b":aGVs\r\nbG8=:",
            b":_-Ah:",  # base64url alphabet
        ):
            with self.subTest(value=value), self.assertRaises(StructuredFieldError):
                parse(value, tltype="item")

    def test_unterminated(self):
        for value in (b":aGVsbG8=", b":", b"a=:aGVsbG8="):
            with self.subTest(value=value), self.assertRaises(StructuredFieldError) as ctx:
                parse(value, tltype="dictionary" if value[:2] == b"a=" else "item")
            self.assertEqual(ctx.exception.position, len(value))

    def test_not_at_start(self):
        self.assertEqual(
            parse(b"a=:AA==:, b=:BB==:", tltype="dictionary"),
            {"a": (b"\x00", {}), "b": (b"\x04", {})},
        )

    def test_disallowed_character_position(self):
        with self.assertRaises(StructuredFieldError) as ctx:
            parse(b"x, :aG.s:", tltype="list")
        self.assertEqual(ctx.exception.position, 6)
        self.assertEqual(ctx.exception.offending_char, ord("."))

    def test_does_not_copy_remaining_input(self):
        # Slicing the rest of the input for every Byte Sequence makes parsing
        # quadratic; count the bytes sliced rather than timing it.
        class CountingBytes(bytes):
            sliced = 0

            def __getitem__(self, key):  # type: ignore[no-untyped-def]
                result = super().__getitem__(key)
                if isinstance(key, slice):
                    CountingBytes.sliced += len(result)
                return result

        data = CountingBytes(b",".join([b":AA==:"] * 4000))
        parse(data, tltype="list")
        # Linear: about half the input is copied (the base64 content). The
        # quadratic version copies about 2000 times the input.
        self.assertLess(CountingBytes.sliced, 2 * len(data))


if __name__ == "__main__":
    unittest.main()
