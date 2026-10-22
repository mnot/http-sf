"""str() of a StructuredFieldError carries the position and context."""

import unittest

from http_sf import StructuredFieldError, parse


class TestErrorStr(unittest.TestCase):
    def test_position_and_context(self):
        with self.assertRaises(StructuredFieldError) as ctx:
            parse(b"foo; bar=", tltype="item")
        self.assertEqual(str(ctx.exception), "Empty item at position 9 (in 'bar')")

    def test_position_only(self):
        with self.assertRaises(StructuredFieldError) as ctx:
            parse(b"foo bar", tltype="item")
        self.assertEqual(
            str(ctx.exception),
            "Trailing characters after value (missing comma?) at position 4",
        )

    def test_position_zero(self):
        with self.assertRaises(StructuredFieldError) as ctx:
            parse(b"", tltype="item")
        self.assertEqual(ctx.exception.position, 0)
        self.assertTrue(str(ctx.exception).endswith(" at position 0"))

    def test_dictionary_context(self):
        with self.assertRaises(StructuredFieldError) as ctx:
            parse(b"a=1, b=", tltype="dictionary")
        self.assertEqual(ctx.exception.context, "b")
        self.assertTrue(str(ctx.exception).endswith(" (in 'b')"), str(ctx.exception))
        self.assertIn(f"at position {ctx.exception.position}", str(ctx.exception))

    def test_innermost_context_wins(self):
        with self.assertRaises(StructuredFieldError) as ctx:
            parse(b"a=1;b=, c=2", tltype="dictionary")
        self.assertEqual(ctx.exception.context, "b")
        self.assertTrue(str(ctx.exception).endswith(" (in 'b')"), str(ctx.exception))

    def test_attributes_unchanged(self):
        with self.assertRaises(StructuredFieldError) as ctx:
            parse(b"foo; bar=", tltype="item")
        self.assertEqual(ctx.exception.args, ("Empty item",))
        self.assertEqual(ctx.exception.position, 9)
        self.assertEqual(ctx.exception.context, "bar")

    def test_bare(self):
        self.assertEqual(str(StructuredFieldError("oops")), "oops")
        self.assertEqual(
            str(StructuredFieldError("oops", position=3, context="k")),
            "oops at position 3 (in 'k')",
        )
        self.assertEqual(
            str(StructuredFieldError("oops", context="k")), "oops (in 'k')"
        )

    def test_no_message(self):
        self.assertEqual(str(StructuredFieldError(position=2)), "at position 2")
        self.assertEqual(str(StructuredFieldError()), "")


if __name__ == "__main__":
    unittest.main()
