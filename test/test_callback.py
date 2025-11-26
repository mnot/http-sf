
import unittest
from http_sf import parse

class TestCallback(unittest.TestCase):
    def test_dictionary_duplicate_key(self):
        duplicates = []
        def callback(key, context):
            duplicates.append((key, context))
        
        parse(b"a=1, a=2", tltype="dictionary", on_duplicate_key=callback)
        self.assertEqual(duplicates, [("a", "dictionary")])

    def test_parameter_duplicate_key(self):
        duplicates = []
        def callback(key, context):
            duplicates.append((key, context))
        
        parse(b"a;b=1;b=2", tltype="item", on_duplicate_key=callback)
        self.assertEqual(duplicates, [("b", "parameter")])

    def test_nested_duplicate_key(self):
        duplicates = []
        def callback(key, context):
            duplicates.append((key, context))
        
        parse(b"a;b=1;b=2, a=3", tltype="dictionary", on_duplicate_key=callback)
        self.assertEqual(duplicates, [("b", "parameter"), ("a", "dictionary")])

if __name__ == "__main__":
    unittest.main()
