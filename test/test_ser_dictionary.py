"""ser() follows RFC 9651 section 4.1.2 for Boolean true dictionary members."""

import unittest

from http_sf import parse, ser


class TestSerDictionary(unittest.TestCase):
    def test_bare_true(self):
        self.assertEqual(ser({"a": True}), "a")

    def test_true_with_empty_params(self):
        self.assertEqual(ser({"a": (True, {})}), "a")

    def test_true_with_params(self):
        self.assertEqual(ser({"a": (True, {"b": 1})}), "a;b=1")

    def test_false(self):
        self.assertEqual(ser({"a": False}), "a=?0")

    def test_one_is_not_true(self):
        self.assertEqual(ser({"a": 1}), "a=1")

    def test_mixed(self):
        self.assertEqual(
            ser({"a": True, "b": 2, "c": (True, {"d": True}), "e": ([1, 2], {})}),
            "a, b=2, c;d, e=(1 2)",
        )

    def test_round_trip(self):
        self.assertEqual(
            parse(ser({"a": True}).encode(), tltype="dictionary"), {"a": (True, {})}
        )


if __name__ == "__main__":
    unittest.main()
