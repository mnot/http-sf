"""InnerList copy, +, and * keep the list's parameters."""

import copy
import pickle
import unittest
from typing import Dict

from http_sf.compat import InnerList, Item, Parameters


def make() -> InnerList:
    il = InnerList([1, 2])
    il.params["a"] = 1
    return il


class TestInnerListParams(unittest.TestCase):
    def check_params(self, result: InnerList, expected: Dict[str, int]) -> None:
        self.assertIsInstance(result, InnerList)
        self.assertEqual(dict(result.params), expected)
        self.assertIsInstance(result.params, Parameters)

    def test_copy_keeps_params(self):
        self.check_params(make().copy(), {"a": 1})

    def test_copy_agrees_with_copy_copy(self):
        il = make()
        self.assertEqual(str(il.copy()), str(copy.copy(il)))
        self.assertEqual(str(il.copy()), "(1 2);a=1")

    def test_add_list_keeps_params(self):
        result = make() + [3]
        self.check_params(result, {"a": 1})
        self.assertEqual(str(result), "(1 2 3);a=1")

    def test_add_innerlist_keeps_left_params(self):
        right = InnerList([3])
        right.params["b"] = 2
        self.check_params(make() + right, {"a": 1})
        self.check_params(right + make(), {"b": 2})

    def test_radd_takes_params_from_innerlist(self):
        result = [3] + make()
        self.check_params(result, {"a": 1})
        self.assertEqual(str(result), "(3 1 2);a=1")

    def test_mul_and_rmul_keep_params(self):
        self.assertEqual(str(make() * 2), "(1 2 1 2);a=1")
        self.assertEqual(str(2 * make()), "(1 2 1 2);a=1")

    def test_imul_keeps_params(self):
        il = make()
        il *= 2
        self.assertEqual(str(il), "(1 2 1 2);a=1")

    def test_results_are_itemised(self):
        for result in (make() + [3], [3] + make(), make() * 2, make().copy()):
            for member in result:
                self.assertIsInstance(member, Item)

    def test_params_mapping_not_shared_but_members_are(self):
        """The copy is shallow: members are shared, the params mapping isn't."""
        il = make()
        results = [
            il.copy(),
            il + [3],
            [3] + il,
            il * 2,
            2 * il,
            copy.copy(il),
        ]
        for result in results:
            self.assertIsNot(result.params, il.params)
            result.params["z"] = 9
            self.assertTrue(any(member is il[0] for member in result))
        self.assertEqual(dict(il.params), {"a": 1})

    def test_slices_drop_params(self):
        # Deliberate: a slice is a different list, not a copy of this one.
        il = make()
        for sliced in (il[0:2], il[:], il[::-1]):
            self.assertIsInstance(sliced, InnerList)
            self.assertEqual(dict(sliced.params), {})

    def test_deepcopy_keeps_params(self):
        il = make()
        result = copy.deepcopy(il)
        self.assertEqual(str(result), "(1 2);a=1")
        self.assertIsNot(result.params, il.params)

    def test_pickle_keeps_params(self):
        result = pickle.loads(pickle.dumps(make()))
        self.assertEqual(str(result), "(1 2);a=1")

    def test_subclass_extra_attribute_agrees_with_copy_copy(self):
        class Extra(InnerList):
            def __init__(self, values=None, extra="default"):
                super().__init__(values)
                self.extra = extra

        il = Extra([1], extra="original")
        il.params["a"] = 1
        for result in (il.copy(), copy.copy(il)):
            self.assertIsInstance(result, Extra)
            self.assertEqual(result.extra, "original")
            self.assertEqual(dict(result.params), {"a": 1})

    def test_subclass_with_required_arguments_copies(self):
        class Required(InnerList):
            def __init__(self, first, second):
                super().__init__([first, second])

        il = Required(1, 2)
        il.params["a"] = 1
        for result in (il.copy(), copy.copy(il)):
            self.assertIsInstance(result, Required)
            self.assertEqual(str(result), "(1 2);a=1")

    def test_original_unchanged(self):
        il = make()
        _ = il + [3]
        _ = il * 3
        _ = il.copy()
        self.assertEqual(str(il), "(1 2);a=1")

    def test_plain_dict_params_stay_plain(self):
        il = InnerList([1, 2])
        il.params = {"a": 1}  # type: ignore[assignment]
        result = il.copy()
        self.assertEqual(result.params, {"a": 1})
        self.assertIsNot(result.params, il.params)

    def test_subclass_preserved(self):
        class Sub(InnerList):
            pass

        il = Sub([1])
        il.params["a"] = 1
        for result in (il.copy(), il + [2], [2] + il, il * 2):
            self.assertIsInstance(result, Sub)
            self.assertEqual(dict(result.params), {"a": 1})


if __name__ == "__main__":
    unittest.main()
