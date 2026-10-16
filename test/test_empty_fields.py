"""Empty and whitespace-only field values are valid for Lists and Dictionaries."""

import unittest

from http_sf import StructuredFieldError, parse


class TestEmptyFields(unittest.TestCase):
    def test_empty_dictionary(self):
        self.assertEqual(parse(b"", tltype="dictionary"), {})

    def test_space_only_dictionary(self):
        self.assertEqual(parse(b"   ", tltype="dictionary"), {})

    def test_empty_list(self):
        self.assertEqual(parse(b"", tltype="list"), [])

    def test_empty_item_still_fails(self):
        with self.assertRaises(StructuredFieldError):
            parse(b"", tltype="item")

    def test_trailing_comma_still_fails(self):
        with self.assertRaises(StructuredFieldError):
            parse(b"a=1,", tltype="dictionary")

    def test_retrofit_name(self):
        self.assertEqual(parse(b"", name="Cache-Control"), {})


if __name__ == "__main__":
    unittest.main()
