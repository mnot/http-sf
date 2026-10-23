"""
String, Display String, Token and Key parsing, checked byte by byte against a
small reference written straight from RFC 9651 (sections 4.2.5, 4.2.6, 4.2.10
and 3.1.2).

The parsers copy runs of ordinary characters with compiled patterns, so what
matters is where a run starts and stops, and which bytes are in each pattern.
Every byte value is substituted and inserted at every offset of short
templates, with runs of 0 to 5 characters.

A parser that fails to make progress would hang the suite, so every call to a
parser is under a short timer (where SIGALRM exists) and fails instead.
"""

import contextlib
import signal
import unittest

import http_sf.util
from http_sf import StructuredFieldError, Token, parse
from http_sf.display_string import parse_display_string
from http_sf.state import ParserState
from http_sf.string import parse_string
from http_sf.token import parse_token
from http_sf.util import parse_key

DQUOTE, BACKSLASH, PERCENT = 0x22, 0x5C, 0x25
TCHARS = set(
    b"!#$%&'*+-.^_`|~:/"
    + bytes(c for c in range(128) if chr(c).isascii() and chr(c).isalnum())
)
ALPHA = set(bytes(c for c in range(128) if chr(c).isascii() and chr(c).isalpha()))
LCALPHA = set(bytes(range(ord("a"), ord("z") + 1)))
UCALPHA = set(bytes(range(ord("A"), ord("Z") + 1)))
HEX = set(b"0123456789abcdef")


class Err:
    """The reference says: fail parsing. position is None where it isn't pinned."""

    def __init__(self, position):
        self.position = position


# --- reference parsers: (value, end) on success, or Err


def ref_string(data, i):  # 4.2.5, starting at the DQUOTE
    out = bytearray()
    i += 1
    while True:
        if i >= len(data):
            return Err(len(data))
        c = data[i]
        i += 1
        if c == BACKSLASH:
            if i >= len(data):
                return Err(len(data))
            n = data[i]
            i += 1
            if n not in (DQUOTE, BACKSLASH):
                return Err(i - 1)
            out.append(n)
        elif c == DQUOTE:
            return out.decode("ascii"), i
        elif c <= 0x1F or c >= 0x7F:
            return Err(i - 1)
        else:
            out.append(c)


def ref_display_string(data, i):  # 4.2.10, starting at the PERCENT
    if data[i : i + 2] != b'%"':
        return Err(i)
    i += 2
    out = bytearray()
    while True:
        if i >= len(data):
            return Err(len(data))
        c = data[i]
        i += 1
        if c <= 0x1F or c >= 0x7F:
            return Err(i - 1)
        if c == DQUOTE:
            try:
                return out.decode("utf-8"), i
            except UnicodeDecodeError:
                return Err(None)
        if c == PERCENT:
            pair = data[i : i + 2]
            if len(pair) < 2:
                return Err(None)
            if not all(h in HEX for h in pair):
                return Err(i)
            out.append(int(pair, 16))
            i += 2
        else:
            out.append(c)


def ref_token(data, i):  # 4.2.6, starting at a start character
    j = i + 1
    while j < len(data) and data[j] in TCHARS:
        j += 1
    return data[i:j].decode("ascii"), j


def ref_key(data, i, compat):  # 3.1.2
    first = LCALPHA | {ord("*")} | (UCALPHA if compat else set())
    rest = LCALPHA | set(b"0123456789_-.*") | (UCALPHA if compat else set())
    if i >= len(data) or data[i] not in first:
        return Err(i)
    j = i + 1
    while j < len(data) and data[j] in rest:
        j += 1
    return data[i:j].decode("ascii").lower(), j


# ---


class TimedOut(Exception):
    pass


def _alarm(signum, frame):
    raise TimedOut("parser did not return")


@contextlib.contextmanager
def guarded(seconds=0.5):
    if not hasattr(signal, "setitimer"):
        yield
        return
    old = signal.signal(signal.SIGALRM, _alarm)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


@contextlib.contextmanager
def compat(value):
    old = http_sf.util.COMPAT
    http_sf.util.COMPAT = value
    try:
        yield
    finally:
        http_sf.util.COMPAT = old


def guarded_parse(data, tltype):
    with guarded():
        return parse(data, tltype=tltype)


def mutations(template):
    """Every byte value substituted at, and inserted before, every offset."""
    for off in range(len(template) + 1):
        for byte in range(256):
            b = bytes([byte])
            yield template[:off] + b + template[off:]
            if off < len(template):
                yield template[:off] + b + template[off + 1 :]


def templates_string():
    for n in range(6):
        yield b'"' + b"a" * n + b'"'
        yield b'"' + b"a" * n + b'\\"' + b"b" * n + b'"'
        yield b'"' + b"a" * n + b'\\\\"'
    yield b'"ab\\'
    yield b'"ab'


def templates_display_string():
    for n in range(6):
        yield b'%"' + b"a" * n + b'"'
        yield b'%"' + b"a" * n + b"%c3%a9" + b"b" * n + b'"'
        yield b'%"' + b"%41" * n + b'"'
    yield b'%"a%4'
    yield b'%"ab'


def templates_token():
    for n in range(6):
        yield b"a" * (n + 1) + b","
        yield b"*" + b"b/c:d" * n


def templates_key():
    for n in range(6):
        yield b"a" * (n + 1) + b"=1"
        yield b"*" + b"b_-.*" * n + b";c"


class Checker(unittest.TestCase):
    def direct(self, parser, ref, data, start, what):
        want = ref(data, start)
        state = ParserState(data)
        state.cursor = start
        try:
            with guarded():
                got = parser(state)
        except StructuredFieldError as why:
            self.assertIsInstance(want, Err, (what, data))
            if want.position is not None:
                self.assertEqual(why.position, want.position, (what, data))
            return want
        self.assertNotIsInstance(want, Err, (what, data))
        self.assertEqual(str(got), want[0], (what, data))
        self.assertEqual(state.cursor, want[1], (what, data))
        return want

    def through_parse(self, data, want, what):
        """parse() as an item: it must reject what the reference rejects, and
        return the reference's value where nothing but spaces follows."""
        try:
            with guarded():
                got = parse(data, tltype="item")
        except StructuredFieldError:
            if isinstance(want, Err):
                return
            self.assertNotEqual(data[want[1] :].strip(b" "), b"", (what, data))
            return
        if isinstance(want, Err):
            self.fail(f"{what}: accepted {data!r}")
        if data[want[1] :].strip(b" ") == b"":
            self.assertEqual(str(got[0]), want[0], (what, data))
        # otherwise a parameter or other tail follows; not this test's concern


class TestScanRuns(Checker):
    def run_group(self, templates, parser, ref, first_ok, what):
        seen = set()
        for template in templates:
            for data in mutations(template):
                if data in seen:
                    continue
                seen.add(data)
                if data and first_ok(data[0]):
                    want = self.direct(parser, ref, data, 0, what)
                    self.through_parse(data, want, what)

    def test_string(self):
        self.run_group(
            templates_string(),
            parse_string,
            ref_string,
            lambda c: c == DQUOTE,
            "String",
        )

    def test_display_string(self):
        self.run_group(
            templates_display_string(),
            parse_display_string,
            ref_display_string,
            lambda c: c == PERCENT,
            "Display String",
        )

    def test_token(self):
        self.run_group(
            templates_token(),
            parse_token,
            ref_token,
            lambda c: c in ALPHA or c == ord("*"),
            "Token",
        )

    def test_key(self):
        for value in (False, True):
            with compat(value):
                seen = set()
                for template in templates_key():
                    for data in mutations(template):
                        if data in seen:
                            continue
                        seen.add(data)
                        want = ref_key(data, 0, value)
                        state = ParserState(data)
                        try:
                            with guarded():
                                got = parse_key(state)
                        except StructuredFieldError as why:
                            self.assertIsInstance(want, Err, (value, data))
                            self.assertEqual(why.position, want.position, data)
                            continue
                        self.assertNotIsInstance(want, Err, (value, data))
                        self.assertEqual((got, state.cursor), want, (value, data))
                        # as a dictionary member, when the key is all there is
                        if want[1] == len(data):
                            self.assertEqual(
                                guarded_parse(data, "dictionary"),
                                {want[0]: (True, {})},
                            )

    def test_key_after_other_input(self):
        # The key scan starts wherever the cursor is, not at 0
        for value in (False, True):
            with compat(value):
                for data in (b"x;ab", b"x, Ab", b"x;aB;c", b"x;a-B.c_d*e"):
                    for start in range(len(data) + 1):
                        want = ref_key(data, start, value)
                        state = ParserState(data)
                        state.cursor = start
                        try:
                            with guarded():
                                got = parse_key(state)
                        except StructuredFieldError:
                            self.assertIsInstance(want, Err, (value, data, start))
                            continue
                        self.assertEqual((got, state.cursor), want)


class TestDirectCases(Checker):
    def test_del_in_display_string(self):
        for data in (b'%"\x7f"', b'%"a\x7f"', b'%"abc\x7fdef"', b'%"ab%41\x7f"'):
            with self.assertRaises(StructuredFieldError) as ctx:
                guarded_parse(data, "item")
            self.assertEqual(ctx.exception.offending_char, 0x7F)
            self.assertEqual(ctx.exception.position, data.index(b"\x7f"))

    def test_del_in_string(self):
        for data in (b'"\x7f"', b'"abc\x7fdef"'):
            with self.assertRaises(StructuredFieldError) as ctx:
                guarded_parse(data, "item")
            self.assertEqual(ctx.exception.position, data.index(b"\x7f"))

    def test_backslash_is_ordinary_in_display_string(self):
        self.assertEqual(str(guarded_parse(b'%"a\\b"', "item")[0]), "a\\b")

    def test_percent_ends_a_run_in_display_string(self):
        self.assertEqual(str(guarded_parse(b'%"ab%c3%a9cd"', "item")[0]), "abécd")

    def test_compat_keys(self):
        with compat(False):
            for data in (b"Ab=1", b"aB=1"):
                with self.assertRaises(StructuredFieldError):
                    guarded_parse(data, "dictionary")
            self.assertEqual(guarded_parse(b"ab", "dictionary"), {"ab": (True, {})})
        with compat(True):
            self.assertEqual(guarded_parse(b"Ab=1", "dictionary"), {"ab": (1, {})})
            self.assertEqual(guarded_parse(b"aB=1", "dictionary"), {"ab": (1, {})})
            self.assertEqual(
                guarded_parse(b"x;aBc=1", "list"), [(Token("x"), {"abc": 1})]
            )
        # and the flag is back to what it was
        self.assertFalse(http_sf.util.COMPAT)
        with self.assertRaises(StructuredFieldError):
            guarded_parse(b"aB=1", "dictionary")

    def test_runs_end_at_the_right_byte(self):
        self.assertEqual(guarded_parse(b'"ab\\"cd\\\\ef"', "item")[0], 'ab"cd\\ef')
        self.assertEqual(guarded_parse(b"a1:/*, b", "list")[0][0], Token("a1:/*"))
        self.assertEqual(
            guarded_parse(b"ab-c.d_e*f9;x", "dictionary"),
            {"ab-c.d_e*f9": (True, {"x": True})},
        )


if __name__ == "__main__":
    unittest.main()
