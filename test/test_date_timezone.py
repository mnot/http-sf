"""Date serialisation must not depend on the host's timezone: naive values are rejected."""

import unittest
from datetime import datetime, timedelta, timezone

from http_sf import StructuredFieldError, parse, ser
from http_sf.util import json_load


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


class TestDateRange(unittest.TestCase):
    """Timestamp conversion is platform-independent; the range edges are exact."""

    def test_negative_timestamp(self):
        self.assertEqual(
            parse(b"@-1", tltype="item")[0],
            datetime(1969, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
        )

    def test_epoch(self):
        self.assertEqual(
            parse(b"@0", tltype="item")[0], datetime(1970, 1, 1, tzinfo=timezone.utc)
        )

    def test_result_is_utc(self):
        value = parse(b"@-1", tltype="item")[0]
        self.assertEqual(value.utcoffset(), timedelta(0))

    def test_max_date(self):
        value = parse(b"@253402300799", tltype="item")[0]
        self.assertEqual(value, datetime(9999, 12, 31, 23, 59, 59, tzinfo=timezone.utc))
        self.assertEqual(ser(value), "@253402300799")

    def test_min_date(self):
        value = parse(b"@-62135596800", tltype="item")[0]
        self.assertEqual(value, datetime(1, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(ser(value), "@-62135596800")

    def test_past_max_date(self):
        with self.assertRaises(StructuredFieldError) as ctx:
            parse(b"@253402300800", tltype="item")
        self.assertEqual(ctx.exception.args[0], "Date value out of range")

    def test_before_min_date(self):
        with self.assertRaises(StructuredFieldError) as ctx:
            parse(b"@-62135596801", tltype="item")
        self.assertEqual(ctx.exception.args[0], "Date value out of range")

    def test_json_load_negative(self):
        self.assertEqual(
            json_load({"__type": "date", "value": -1}),
            datetime(1969, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
        )

    def test_json_load_edges(self):
        self.assertEqual(
            json_load({"__type": "date", "value": 253402300799}),
            datetime(9999, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
        )
        self.assertEqual(
            json_load({"__type": "date", "value": -62135596800}),
            datetime(1, 1, 1, tzinfo=timezone.utc),
        )

    def test_json_load_out_of_range_is_int(self):
        for value in (253402300800, -62135596801, 999999999999999, -999999999999999):
            self.assertEqual(json_load({"__type": "date", "value": value}), value)


if __name__ == "__main__":
    unittest.main()
