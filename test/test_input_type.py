"""parse() accepts bytes, bytearray and memoryview; anything else is a TypeError."""

import unittest

from http_sf import StructuredFieldError, parse

CASES = [
    ("item", b"foo"),
    ("item", b":aGk=:"),
    ("list", b"1, 2"),
    ("dictionary", b"a=1"),
]


class TestInputType(unittest.TestCase):
    def test_accepted_types(self):
        for tltype, raw in CASES:
            expected = parse(raw, tltype=tltype)
            for wrap in (bytes, bytearray, memoryview):
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
