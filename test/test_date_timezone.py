"""Date serialisation must not depend on the host's timezone: naive values are rejected."""

import unittest
from datetime import datetime, timedelta, timezone

from http_sf import parse, ser


class TestDateTimezone(unittest.TestCase):
    def test_naive_rejected(self):
        with self.assertRaises(ValueError):
            ser(datetime(2020, 1, 1))

    def test_error_suggests_fix(self):
        with self.assertRaises(ValueError) as ctx:
            ser(datetime(2020, 1, 1))
        self.assertIn("timezone", str(ctx.exception))

    def test_naive_rejected_in_structures(self):
        with self.assertRaises(ValueError):
            ser({"a": (datetime(2020, 1, 1), {})})

    def test_utc(self):
        self.assertEqual(ser(datetime(2020, 1, 1, tzinfo=timezone.utc)), "@1577836800")

    def test_offset_is_honoured(self):
        zone = timezone(timedelta(hours=10))
        self.assertEqual(ser(datetime(2020, 1, 1, 10, tzinfo=zone)), "@1577836800")

    def test_roundtrip(self):
        value = parse(b"@1577836800", tltype="item")[0]
        self.assertEqual(ser(value), "@1577836800")


if __name__ == "__main__":
    unittest.main()
