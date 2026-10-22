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


class TestBulkMutation(unittest.TestCase):
    """extend and += must itemise values the way append and insert do."""

    def test_list_extend(self):
        my_list = List(["a"])
        my_list.extend([1, Token("b"), ["x", "y"]])
        self.assertTrue(all(isinstance(i, (Item, InnerList)) for i in my_list))
        self.assertIsInstance(my_list[-1], InnerList)
        self.assertEqual(str(my_list), '"a", 1, b, ("x" "y")')

    def test_list_extend_generator(self):
        my_list = List()
        my_list.extend(i for i in [1, 2])
        self.assertEqual(str(my_list), "1, 2")

    def test_list_iadd(self):
        my_list = List([1])
        alias = my_list
        my_list += [2, "c"]
        self.assertIs(my_list, alias)
        self.assertEqual(str(my_list), '1, 2, "c"')

    def test_list_extend_keeps_items(self):
        item = Item(5)
        item.params["a"] = True
        my_list = List()
        my_list.extend([item])
        self.assertIs(my_list[0], item)
        self.assertEqual(str(my_list), "5;a")

    def test_list_add(self):
        self.assertEqual(str(List([1]) + [2]), "1, 2")
        self.assertEqual(str([0] + List([1])), "0, 1")

    def test_inner_list_extend(self):
        inner = InnerList([1])
        inner.params["z"] = True
        inner.extend([2, Token("t")])
        self.assertEqual(str(inner), "(1 2 t);z")

    def test_inner_list_iadd(self):
        inner = InnerList([1])
        inner.params["z"] = True
        inner += [2, "s"]
        self.assertIsInstance(inner, InnerList)
        self.assertEqual(str(inner), '(1 2 "s");z')

    def test_list_extend_self(self):
        my_list = List([1, 2])
        my_list.extend(my_list)
        self.assertEqual(str(my_list), "1, 2, 1, 2")
        my_list += my_list
        self.assertEqual(len(my_list), 8)

    def test_inner_list_extend_self(self):
        inner = InnerList([1, 2])
        inner.extend(inner)
        self.assertEqual(str(inner), "(1 2 1 2)")
        inner += inner
        self.assertEqual(len(inner), 8)

    def test_inner_list_add(self):
        self.assertEqual(str(InnerList([1]) + [2]), "(1 2)")

    def test_inner_list_copy(self):
        self.assertEqual(str(InnerList([1, 2]).copy()), "(1 2)")


class TestTokenAndDisplayString(unittest.TestCase):
    def test_token_constructor(self):
        token = Token("abc")
        self.assertEqual(str(token), "abc")

    def test_display_string_roundtrip(self):
        item = Item(DisplayString("hello"))
        self.assertEqual(str(item), '%"hello"')


if __name__ == "__main__":
    unittest.main()
