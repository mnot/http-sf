"""Error reporting for unterminated Inner Lists, reprs, and the command line."""

import os
import subprocess
import sys
import unittest
from pathlib import Path

from http_sf import DisplayString, StructuredFieldError, Token, parse


class TestUnterminatedInnerList(unittest.TestCase):
    def test_messages_and_positions(self):
        cases = [
            (b"(", "list"),
            (b"( ", "list"),
            (b"(a ", "list"),
            (b"a, (", "list"),
            (b"a=(", "dictionary"),
            (b"a=( ", "dictionary"),
        ]
        for value, tltype in cases:
            with self.subTest(value=value):
                try:
                    parse(value, tltype=tltype)
                except StructuredFieldError as why:
                    self.assertEqual(why.args[0], "End of inner list not found")
                    self.assertEqual(why.position, len(value))
                else:
                    self.fail("parsed")

    def test_unchanged_error(self):
        with self.assertRaises(StructuredFieldError) as ctx:
            parse(b"(a", tltype="list")
        self.assertEqual(ctx.exception.args[0], "End of inner list not found")

    def test_valid_inner_lists(self):
        self.assertEqual(parse(b"()", tltype="list"), [([], {})])
        self.assertEqual(parse(b"( a )", tltype="list")[0][0], [(Token("a"), {})])


class TestRepr(unittest.TestCase):
    def test_display_string(self):
        self.assertEqual(repr(DisplayString("x")), 'DisplayString("x")')

    def test_token(self):
        self.assertEqual(repr(Token("x")), 'Token("x")')


class TestCommandLine(unittest.TestCase):
    def run_cli(self, *args):
        # Always exercise this checkout, not whatever http_sf is installed.
        root = Path(__file__).resolve().parent.parent
        env = dict(os.environ, PYTHONPATH=str(root))
        return subprocess.run(
            [sys.executable, "-m", "http_sf", *args],
            capture_output=True,
            text=True,
            check=False,
            cwd=root,
            env=env,
        )

    def test_unknown_field_name(self):
        result = self.run_cli("-n", "x-not-a-known-field", "a")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("x-not-a-known-field", result.stderr)

    def test_known_field_name(self):
        result = self.run_cli("-n", "Cache-Control", "max-age=60")
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
