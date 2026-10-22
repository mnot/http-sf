"""parse() accepts any bytes-like object; anything else is a TypeError."""

import array
import mmap
import unittest

from http_sf import StructuredFieldError, parse

CASES = [
    ("item", b"foo"),
    ("item", b":aGk=:"),
    ("list", b"1, 2"),
    ("dictionary", b"a=1"),
]


def _mmap(raw: bytes) -> mmap.mmap:
    m = mmap.mmap(-1, len(raw))
    m.write(raw)
    return m


def _array(raw: bytes) -> "array.array[int]":
    return array.array("B", raw)


class TestInputType(unittest.TestCase):
    def test_accepted_types(self):
        for tltype, raw in CASES:
            expected = parse(raw, tltype=tltype)
            for wrap in (bytes, bytearray, memoryview, _mmap, _array):
                with self.subTest(tltype=tltype, raw=raw, wrap=wrap.__name__):
                    self.assertEqual(parse(wrap(raw), tltype=tltype), expected)

    def test_str_rejected(self):
        for tltype, raw in CASES:
            with self.subTest(tltype=tltype, raw=raw):
                with self.assertRaises(TypeError) as ctx:
                    parse(raw.decode("ascii"), tltype=tltype)  # type: ignore[arg-type]
                self.assertIn(".encode()", str(ctx.exception))
                self.assertIn("str", str(ctx.exception))

    def test_other_types_rejected(self):
        for value in (None, 1, ["a"], object()):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    parse(value, tltype="item")  # type: ignore[arg-type]

    def test_encode_hint_only_for_str(self):
        with self.assertRaises(TypeError) as ctx:
            parse(None, tltype="item")  # type: ignore[arg-type]
        self.assertNotIn(".encode()", str(ctx.exception))
        self.assertIn("NoneType", str(ctx.exception))

    def test_bytes_subclass(self):
        class MyBytes(bytes):
            pass

        self.assertEqual(
            parse(MyBytes(b"a=1"), tltype="dictionary"),
            parse(b"a=1", tltype="dictionary"),
        )

    def test_str_with_name(self):
        with self.assertRaises(TypeError):
            parse("gzip, br", name="Accept-Encoding")  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            parse("a", name="zzz-unknown")  # type: ignore[arg-type]
        self.assertEqual(
            parse(memoryview(b"gzip, br"), name="Accept-Encoding"),
            parse(b"gzip, br", name="Accept-Encoding"),
        )

    def test_checked_before_tltype(self):
        with self.assertRaises(TypeError):
            parse("a", tltype="bogus")  # type: ignore[arg-type]

    def test_not_a_structured_field_error(self):
        # Type misuse is a caller bug, not a malformed field value.
        with self.assertRaises(TypeError) as ctx:
            parse("foo", tltype="item")  # type: ignore[arg-type]
        self.assertNotIsInstance(ctx.exception, StructuredFieldError)

    def test_memoryview_error_position(self):
        with self.assertRaises(StructuredFieldError) as ctx:
            parse(memoryview(b"a, ,"), tltype="list")
        self.assertIsNotNone(ctx.exception.position)


if __name__ == "__main__":
    unittest.main()
