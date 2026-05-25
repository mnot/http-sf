"""Tests for the http_sfv-compatible API exposed by http_sf.compat."""

import unittest

from http_sf.compat import (
    Dictionary,
    DisplayString,
    InnerList,
    Item,
    List,
    Token,
)


class TestItem(unittest.TestCase):
    def test_parse_value_and_params(self):
        item = Item()
        item.parse(b"foo;a=1")
        self.assertEqual(item.value, Token("foo"))
        self.assertEqual(dict(item.params), {"a": 1})

    def test_serialise_roundtrip(self):
        item = Item()
        item.parse(b"foo;a=1")
        self.assertEqual(str(item), "foo;a=1")

    def test_eq_ignores_params(self):
        item_a = Item("foo")
        item_a.params["x"] = 1
        item_b = Item("foo")
        self.assertEqual(item_a, item_b)

    def test_eq_to_bare_value(self):
        item = Item(Token("foo"))
        item.params["x"] = 1
        self.assertEqual(item, Token("foo"))

    def test_parse_error_is_valueerror(self):
        with self.assertRaises(ValueError):
            Item().parse(b"!!!")


class TestList(unittest.TestCase):
    def test_parse(self):
        my_list = List()
        my_list.parse(b"foo; a=1, bar; b=2")
        self.assertEqual(len(my_list), 2)
        self.assertEqual(my_list[0].value, Token("foo"))
        self.assertEqual(my_list[0].params["a"], 1)

    def test_contains_uses_item_equality(self):
        my_list = List()
        my_list.parse(b"foo;a=1, bar;b=2")
        self.assertIn(Token("foo"), my_list)
        self.assertEqual(my_list.count(Token("foo")), 1)

    def test_append_bare_value(self):
        my_list = List()
        my_list.parse(b"foo;a=1")
        my_list.append(Token("bar"))
        self.assertEqual(my_list[-1].value, Token("bar"))

    def test_append_inner_list(self):
        my_list = List()
        my_list.append(["x", "y"])
        self.assertIsInstance(my_list[-1], InnerList)
        self.assertEqual(my_list[-1][0].value, "x")

    def test_serialise(self):
        my_list = List()
        my_list.parse(b"a, b;q=5, c")
        self.assertEqual(str(my_list), "a, b;q=5, c")

    def test_inner_list_with_params(self):
        my_list = List()
        my_list.append(["x", "y"])
        my_list[-1][-1].params["a"] = True
        self.assertEqual(str(my_list), '("x" "y";a)')


class TestDictionary(unittest.TestCase):
    def test_init_with_dict(self):
        my_dict = Dictionary({"a": "1", "b": 2, "c": Token("foo")})
        self.assertEqual(my_dict["a"].value, "1")
        self.assertEqual(my_dict["b"].value, 2)
        self.assertEqual(my_dict["c"].value, Token("foo"))

    def test_serialise_after_param_set(self):
        my_dict = Dictionary({"a": "1", "b": 2, "c": Token("foo")})
        my_dict["b"].params["b1"] = 2.0
        self.assertEqual(str(my_dict), 'a="1", b=2;b1=2.0, c=foo')

    def test_parse_bare_member_is_true(self):
        my_dict = Dictionary()
        my_dict.parse(b"a=1, b, c;x=2")
        self.assertEqual(my_dict["b"].value, True)
        self.assertEqual(str(my_dict), "a=1, b, c;x=2")

    def test_empty_serialisation_raises(self):
        with self.assertRaises(ValueError):
            str(Dictionary())


class TestInnerList(unittest.TestCase):
    def test_parse_via_list(self):
        my_list = List()
        my_list.parse(b"(1 2);a, 3")
        self.assertIsInstance(my_list[0], InnerList)
        self.assertEqual(my_list[0][0].value, 1)
        self.assertEqual(my_list[0].params["a"], True)

    def test_inner_list_str(self):
        inner = InnerList(["x", Token("y")])
        inner.params["z"] = True
        self.assertEqual(str(inner), '("x" y);z')


class TestTokenAndDisplayString(unittest.TestCase):
    def test_token_constructor(self):
        token = Token("abc")
        self.assertEqual(str(token), "abc")

    def test_display_string_roundtrip(self):
        item = Item(DisplayString("hello"))
        self.assertEqual(str(item), '%"hello"')


if __name__ == "__main__":
    unittest.main()
