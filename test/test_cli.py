"""The command line interface passes its input through as bytes."""

import json
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(*argv: bytes | str, stdin: bytes = b"") -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [ROOT] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])
    )
    return subprocess.run(
        [sys.executable, "-m", "http_sf", *argv],
        input=stdin,
        capture_output=True,
        check=False,
        cwd=ROOT,
        env=env,
        timeout=30,
    )


class TestCli(unittest.TestCase):
    def test_stdin_valid(self):
        result = run("-d", "--stdin", stdin=b"a=1, b")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"a": [1, {}], "b": [True, {}]})

    def test_stdin_invalid_utf8_is_a_parse_failure(self):
        result = run("-d", "--stdin", stdin=b"a=\xff\xfe")
        self.assertEqual(result.returncode, 1)
        stderr = result.stderr.decode("utf-8")
        self.assertNotIn("Traceback", stderr)
        self.assertTrue(stderr.startswith("VALUE: a=\\xff\\xfe\nFAIL: "), stderr)

    def test_argument(self):
        result = run("-i", "42")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [42, {}])

    @unittest.skipIf(sys.platform == "win32", "argv bytes aren't recoverable")
    def test_argument_invalid_utf8_is_a_parse_failure(self):
        result = run("-i", b"a=\xff")
        self.assertEqual(result.returncode, 1)
        stderr = result.stderr.decode("utf-8")
        self.assertNotIn("Traceback", stderr)
        self.assertTrue(stderr.startswith("VALUE: a=\\xff\nFAIL: "), stderr)


if __name__ == "__main__":
    unittest.main()
