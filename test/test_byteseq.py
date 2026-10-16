"""Byte Sequence parsing: behaviour at the edges, and linear scaling."""

import time
import unittest

from http_sf import StructuredFieldError, parse


class TestByteSeq(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(parse(b":aGVsbG8=:", tltype="item")[0], b"hello")
        self.assertEqual(parse(b"::", tltype="item")[0], b"")

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
        self.assertEqual(ctx.exception.position, 8)

    def test_scales_linearly(self):
        def timed(count: int) -> float:
            data = b",".join([b":AA==:"] * count)
            start = time.perf_counter()
            parse(data, tltype="list")
            return time.perf_counter() - start

        timed(1000)  # warm up
        small = min(timed(25000) for _ in range(3))
        large = min(timed(100000) for _ in range(3))
        # Linear is about 4x; copying the remaining input per item is about 16x.
        self.assertLess(large / small, 9)


if __name__ == "__main__":
    unittest.main()
