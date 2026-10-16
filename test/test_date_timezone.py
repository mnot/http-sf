"""Date serialisation must not depend on the host's timezone."""

import os
import subprocess
import sys
import time
import unittest
from datetime import datetime, timedelta, timezone

from http_sf import parse, ser


class TestDateTimezone(unittest.TestCase):
    def test_naive_rejected(self):
        with self.assertRaises(ValueError):
            ser(datetime(2020, 1, 1))

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

    @unittest.skipUnless(hasattr(time, "tzset"), "needs time.tzset")
    def test_host_timezone_irrelevant(self):
        code = (
            "from datetime import datetime, timezone;"
            "from http_sf import ser;"
            "print(ser(datetime(2020,1,1,tzinfo=timezone.utc)))"
        )
        outputs = set()
        for tz in ("UTC", "America/New_York", "Australia/Sydney"):
            env = dict(os.environ, TZ=tz)
            outputs.add(
                subprocess.run(
                    [sys.executable, "-c", code],
                    env=env,
                    capture_output=True,
                    text=True,
                    check=True,
                ).stdout
            )
        self.assertEqual(len(outputs), 1)


if __name__ == "__main__":
    unittest.main()
