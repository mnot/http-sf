"""Errors that report the fault itself: Non-integer Date, Invalid UTF-8 and
Binary Sequence padding."""

import binascii
import itertools
import unittest

from http_sf import StructuredFieldError, parse
from http_sf.byteseq import parse_byteseq
from http_sf.date import parse_date
from http_sf.display_string import parse_display_string
from http_sf.state import ParserState


def failure(value: bytes, tltype: str) -> StructuredFieldError:
    try:
        parse(value, tltype=tltype)
    except StructuredFieldError as why:
        return why
    raise AssertionError(f"{value!r} parsed")


class PositionTestCase(unittest.TestCase):
    def check(self, cases):
        for value, tltype, message, position in cases:
            with self.subTest(value=value, tltype=tltype):
                why = failure(value, tltype)
                self.assertEqual(why.args[0], message)
                self.assertEqual(why.position, position)
                if position < len(value):
                    self.assertEqual(why.offending_char, value[position])
                else:
                    self.assertIsNone(why.offending_char)


class TestNonIntegerDate(PositionTestCase):
    MESSAGE = "Non-integer Date"

    def test_period_is_the_fault(self):
        self.check(
            [
                (b"@1.5,", "list", self.MESSAGE, 2),
                (b"@1.5", "item", self.MESSAGE, 2),
                (b"@1.5 ", "item", self.MESSAGE, 2),
                (b"@1.567", "item", self.MESSAGE, 2),
                (b"@0.0", "item", self.MESSAGE, 2),
                (b"@12.5", "item", self.MESSAGE, 3),
            ]
        )

    def test_negative(self):
        self.check(
            [
                (b"@-1.5", "item", self.MESSAGE, 3),
                (b"@-0.0", "item", self.MESSAGE, 3),
                (b"@-123.456", "item", self.MESSAGE, 5),
            ]
        )

    def test_long_integer_part(self):
        # 12 digits is as long as a Decimal's integer part gets.
        self.check(
            [
                (b"@123456789012.5", "item", self.MESSAGE, 13),
                (b"@-123456789012.5", "item", self.MESSAGE, 14),
            ]
        )

    def test_after_the_number(self):
        # A second period, or an exponent, is not part of the number.
        self.check(
            [
                (b"@1.5.", "item", self.MESSAGE, 2),
                (b"@1.5e3", "item", self.MESSAGE, 2),
                (b"@1.5.5", "item", self.MESSAGE, 2),
            ]
        )

    def test_contexts(self):
        self.check(
            [
                (b"a, @1.5", "list", self.MESSAGE, 5),
                (b"(@1.5)", "list", self.MESSAGE, 3),
                (b"(1 @2.5)", "list", self.MESSAGE, 5),
                (b"a=@1.5", "dictionary", self.MESSAGE, 4),
                (b"a=1, b=@1.5", "dictionary", self.MESSAGE, 9),
                (b"a=(1 @2.5)", "dictionary", self.MESSAGE, 7),
                (b"a;b=@1.5", "item", self.MESSAGE, 6),
                (b"a;b=1;c=@1.5, d", "list", self.MESSAGE, 10),
                (b"a=1;b=@1.5", "dictionary", self.MESSAGE, 8),
                (b"(a;b=@1.5)", "list", self.MESSAGE, 7),
            ]
        )

    def test_period_before_the_date(self):
        # Keys and Tokens can contain a ".", which isn't the one to report.
        self.check(
            [
                (b"a.b=@1.5", "dictionary", self.MESSAGE, 6),
                (b"*.a=@1.5", "dictionary", self.MESSAGE, 6),
                (b"a.b=1, c.d=@12.5", "dictionary", self.MESSAGE, 14),
                (b"a.b=1;c.d=@12.5", "dictionary", self.MESSAGE, 13),
                (b"x.y;k.l=@12.5", "item", self.MESSAGE, 11),
                (b"z, x.y;k.l=@12.5", "list", self.MESSAGE, 14),
                (b"(x.y;k.l=@12.5)", "list", self.MESSAGE, 12),
                (b"t.k, @1.5", "list", self.MESSAGE, 7),
                (b"a.b, c.d;e.f=@-1.5", "list", self.MESSAGE, 16),
            ]
        )

    def test_context_is_kept(self):
        self.assertEqual(failure(b"a=1, b=@1.5", "dictionary").context, "b")
        self.assertEqual(failure(b"a;b=@1.5", "item").context, "b")

    def test_same_position_as_number_errors(self):
        # Number errors are reported at the byte that causes them, and so is
        # this one.
        self.check(
            [
                (b"@1.", "item", "Decimal ends in '.'", 2),
                (b"1.", "item", "Decimal ends in '.'", 1),
                (b"@1234567890123.5", "item", "Decimal too long.", 14),
                (b"1234567890123.5", "item", "Decimal too long.", 13),
            ]
        )

    def test_direct_call(self):
        state = ParserState(b"xx@1.5")
        state.cursor = 2
        with self.assertRaises(StructuredFieldError) as ctx:
            parse_date(state)
        self.assertEqual(ctx.exception.position, 4)
        self.assertEqual(ctx.exception.offending_char, ord("."))
        self.assertEqual(state.cursor, 6)

    def test_cursor_is_after_the_number(self):
        state = ParserState(b"@1.5,")
        with self.assertRaises(StructuredFieldError):
            parse_date(state)
        self.assertEqual(state.cursor, 4)

    def test_no_cause(self):
        why = failure(b"@1.5", "item")
        self.assertIsNone(why.__cause__)
        self.assertFalse(why.__suppress_context__)

    def test_unchanged(self):
        # Not Non-integer Date errors; these stay where they were.
        self.check(
            [
                (b"@1e5", "item", "Trailing characters after value (missing comma?)", 2),
                (b"@+1", "item", "Number doesn't start with a DIGIT", 1),
                (b"@.5", "item", "Number doesn't start with a DIGIT", 1),
                (b"@", "item", "Number input lacked a number", 1),
                (b"@999999999999999", "item", "Date value out of range", 16),
                (b"@-999999999999999", "item", "Date value out of range", 17),
                (b"@253402300800", "item", "Date value out of range", 13),
            ]
        )

    def test_integers_parse(self):
        for value in (b"@1", b"@-1", b"@0", b"@-0", b"@253402300799", b"@-62135596800"):
            with self.subTest(value=value):
                parse(value, tltype="item")
        parse(b"a=@1, b;c=@-2", tltype="dictionary")
        parse(b"@1, (@2 @3;a=@4)", tltype="list")


def esc(data: bytes) -> bytes:
    "Percent-encode every byte, as a Display String escape."
    return b"".join(b"%%%02x" % byte for byte in data)


def display_string(*parts: bytes) -> bytes:
    return b'%"' + b"".join(parts) + b'"'


def first_rejected_byte(data: bytes):
    """
    Index of the first byte of data that UTF-8 rejects, or None if it's valid:
    a byte that can't begin a sequence, or the byte after the valid part of a
    sequence that can't continue it. len(data) if data ends in the middle of a
    sequence. Hand-written from Unicode Table 3-7.
    """
    i = 0
    while i < len(data):
        lead = data[i]
        if lead < 0x80:
            i += 1
            continue
        if 0xC2 <= lead <= 0xDF:
            ranges = [(0x80, 0xBF)]
        elif lead == 0xE0:
            ranges = [(0xA0, 0xBF), (0x80, 0xBF)]
        elif 0xE1 <= lead <= 0xEC or lead in (0xEE, 0xEF):
            ranges = [(0x80, 0xBF)] * 2
        elif lead == 0xED:
            ranges = [(0x80, 0x9F), (0x80, 0xBF)]
        elif lead == 0xF0:
            ranges = [(0x90, 0xBF), (0x80, 0xBF), (0x80, 0xBF)]
        elif 0xF1 <= lead <= 0xF3:
            ranges = [(0x80, 0xBF)] * 3
        elif lead == 0xF4:
            ranges = [(0x80, 0x8F), (0x80, 0xBF), (0x80, 0xBF)]
        else:
            return i
        for offset, (low, high) in enumerate(ranges, 1):
            if i + offset >= len(data):
                return len(data)
            if not low <= data[i + offset] <= high:
                return i + offset
        i += len(ranges) + 1
    return None


class TestInvalidUTF8(PositionTestCase):
    """The position is the first byte that UTF-8 rejects, as an input offset."""

    MESSAGE = "Invalid UTF-8"

    def fault(self, content: bytes, position: int):
        "content is already escaped; it follows the opening %\" at 2."
        value = display_string(content)
        self.check([(value, "item", self.MESSAGE, position)])
        self.assertIsInstance(failure(value, "item").__cause__, UnicodeDecodeError)

    def cut_off(self, content: bytes):
        "The string ends in the middle of a sequence: the closing DQUOTE."
        value = display_string(content)
        self.check([(value, "item", self.MESSAGE, len(value) - 1)])
        self.assertEqual(failure(value, "item").offending_char, ord('"'))

    def test_bytes_that_cannot_begin_a_sequence(self):
        self.fault(b"%ff", 2)
        self.fault(b"%fe", 2)
        self.fault(b"%80", 2)  # continuation byte
        self.fault(b"%bf", 2)
        self.fault(b"%c0", 2)
        self.fault(b"%c1%bf", 2)
        self.fault(b"%f5%80%80%80", 2)
        self.fault(b"%f8%88%80%80%80", 2)
        self.fault(b"a%bf", 3)
        self.fault(b"abc%f5", 5)

    def test_bad_byte_at_each_offset(self):
        for n in range(8):
            with self.subTest(plain=n):
                self.fault(b"a" * n + b"%ff", 2 + n)
            with self.subTest(escaped=n):
                self.fault(esc(b"a" * n) + b"%ff", 2 + 3 * n)
            with self.subTest(mixed=n):
                self.fault(b"a%61" * n + b"%ff", 2 + 4 * n)

    def test_valid_multibyte_before(self):
        # Each escape is three input bytes, however many bytes the character has.
        self.fault(esc("é".encode()) + b"%ff", 8)
        self.fault(esc("€".encode()) + b"%ff", 11)
        self.fault(esc("\U0001f600".encode()) + b"%ff", 14)
        self.fault(esc("é€\U0001f600".encode()) + b"%ff", 2 + 3 * 9)
        self.fault(b"ab" + esc("é".encode()) + b"cd%e2%82a", 18)

    def test_lead_byte_followed_by_ascii(self):
        # The byte that can't continue the sequence is the one reported.
        self.fault(b"%c3a", 5)
        self.fault(b"%c3%61", 5)
        self.fault(b"%e2a%ff", 5)
        self.fault(b"%e2%82a", 8)
        self.fault(b"%f0%9f%98a", 11)
        self.fault(b"xy%c3a", 7)
        self.fault(b"x%e2%82%61", 9)

    def test_cut_off_by_the_closing_quote(self):
        # Valid so far; the closing DQUOTE is the byte that can't continue it.
        for content in (
            b"%c2",
            b"%e2",
            b"%e2%82",
            b"%f0",
            b"%f0%9f",
            b"%f0%9f%98",
            b"abc%f0%9f%98",
            esc("é".encode()) + b"%e2%82",
            b"ab" + esc("é".encode()) + b"cd%e2%82",
        ):
            with self.subTest(content=content):
                self.cut_off(content)

    def test_impossible_sequences_at_the_end(self):
        # The second byte is already wrong, so it, not the quote, is rejected.
        for content in (b"%ed%a0", b"%e0%80", b"%f0%80", b"%f4%90"):
            with self.subTest(content=content):
                self.fault(content, 5)
                self.fault(b"ab" + content, 7)

    def test_two_byte_sequences(self):
        self.fault(b"%c3%28", 5)  # bad continuation
        self.fault(b"%c3%c3", 5)
        self.fault(b"%c3%ff", 5)
        self.fault(b"%c3%28%ff", 5)

    def test_three_byte_sequences(self):
        self.fault(b"%e2%28%a1", 5)  # bad second byte
        self.fault(b"%e2%82%28", 8)  # bad third byte
        self.fault(b"%e2%82%e2", 8)
        self.fault(b"%e0%80%80", 5)  # overlong
        self.fault(b"%e0%9f%bf", 5)
        self.fault(b"%ed%a0%80", 5)  # surrogates
        self.fault(b"%ed%bf%bf", 5)
        self.fault(b"ab%ed%a0%80", 7)

    def test_four_byte_sequences(self):
        self.fault(b"%f0%28%8c%bc", 5)  # bad second byte
        self.fault(b"%f0%90%28%bc", 8)  # bad third byte
        self.fault(b"%f0%90%8c%28", 11)  # bad fourth byte
        self.fault(b"%f0%80%80%80", 5)  # overlong
        self.fault(b"%f0%8f%bf%bf", 5)
        self.fault(b"%f4%90%80%80", 5)  # beyond U+10FFFF
        self.fault(b"abc%f4%90%80%80", 8)

    def test_first_fault_wins(self):
        self.fault(b"%ff%fe", 2)
        self.fault(b"a%80%ff", 3)
        self.fault(b"%e2%82a%ff", 8)
        self.fault(b"%c3%a9%c3%28%ff", 11)
        self.fault(b"%ff%e2%82", 2)
        self.fault(b"a%c3%28%e2%82", 6)

    def expect_all(self, prefix, sequences):
        """
        Every sequence follows the prefix (a list of (bytes, escaped) pieces)
        as escapes. The expected position comes from first_rejected_byte and
        from offsets noted while the input is built.
        """
        head = b""
        decoded = b""
        offsets = []
        for piece, escaped in prefix:
            for byte in piece:
                offsets.append(2 + len(head))
                head += b"%%%02x" % byte if escaped else bytes([byte])
                decoded += bytes([byte])
        for sequence in sequences:
            value = display_string(head + esc(sequence))
            rejected = first_rejected_byte(decoded + sequence)
            if rejected is None:
                parse(value, tltype="item")
                continue
            why = failure(value, "item")
            if rejected < len(decoded):
                expected = offsets[rejected]
            else:
                expected = 2 + len(head) + 3 * (rejected - len(decoded))
            self.assertEqual(
                (why.args[0], why.position), (self.MESSAGE, expected), value
            )
            self.assertEqual(why.offending_char, value[expected])

    PREFIXES = (
        [],
        [(b"abc", False)],
        [(b"a", True), (b"bc", False)],
        [("é".encode(), True), (b"x", False), ("€".encode(), True)],
        [(b"ab", False), ("\U0001f600".encode(), True), (b"%", True), (b"c", False)],
    )

    def test_every_two_byte_sequence_after_a_prefix(self):
        pairs = [bytes([a, b]) for a in range(0x80, 0x100) for b in range(0x100)]
        for prefix in self.PREFIXES:
            with self.subTest(prefix=prefix):
                self.expect_all(prefix, pairs)

    def test_longer_sequences_after_a_prefix(self):
        edges = [0x00, 0x41, 0x7F, 0x80, 0x8F, 0x90, 0x9F, 0xA0, 0xBF, 0xC0, 0xC2]
        edges += [0xDF, 0xE0, 0xE1, 0xED, 0xEF, 0xF0, 0xF4, 0xF5, 0xFF]
        sequences = [
            bytes(combination)
            for length in (3, 4)
            for combination in itertools.product(edges, repeat=length)
        ]
        for prefix in self.PREFIXES[:1] + self.PREFIXES[3:4]:
            with self.subTest(prefix=prefix):
                self.expect_all(prefix, sequences)

    def test_contexts(self):
        self.check(
            [
                (b'a, %"%ff"', "list", self.MESSAGE, 5),
                (b'%"x", %"y%ff"', "list", self.MESSAGE, 9),
                (b'(%"%ff")', "list", self.MESSAGE, 3),
                (b'(1 %"%c3a")', "list", self.MESSAGE, 8),
                (b'a=%"x%ff"', "dictionary", self.MESSAGE, 5),
                (b'a=1, b=%"%e2%82x"', "dictionary", self.MESSAGE, 15),
                (b'a=(1 %"%ff")', "dictionary", self.MESSAGE, 7),
                (b'a;b=%"%c3x"', "item", self.MESSAGE, 9),
                (b'a;b=1;c=%"%ed%a0%80", d', "list", self.MESSAGE, 13),
                (b'a=1;b=%"%ff"', "dictionary", self.MESSAGE, 8),
                (b'(a;b=%"%ff")', "list", self.MESSAGE, 7),
            ]
        )

    def test_cut_off_in_contexts(self):
        self.check(
            [
                (b'a, %"%c3", b', "list", self.MESSAGE, 8),
                (b'a=1, b=%"%e2%82"', "dictionary", self.MESSAGE, 15),
                (b'a;b=%"%c3"', "item", self.MESSAGE, 9),
                (b'(%"%f0%9f%98")', "list", self.MESSAGE, 12),
            ]
        )

    def test_context_is_kept(self):
        self.assertEqual(failure(b'a=1, b=%"%ff"', "dictionary").context, "b")
        self.assertEqual(failure(b'a;b=%"%ff"', "item").context, "b")

    def test_direct_call(self):
        state = ParserState(b'xx%"a%e2%82a", y')
        state.cursor = 2
        with self.assertRaises(StructuredFieldError) as ctx:
            parse_display_string(state)
        self.assertEqual(ctx.exception.position, 11)
        self.assertEqual(ctx.exception.offending_char, ord("a"))
        self.assertEqual(state.cursor, 13)  # after the closing DQUOTE

    def test_valid_strings_parse(self):
        for content in (
            esc("é".encode()),
            esc("€".encode()),
            esc("\U0001f600".encode()),
            esc("퟿".encode()),
            esc("".encode()),
            esc("\U0010ffff".encode()),
            b"abc" + esc("é".encode()) + b"def",
        ):
            with self.subTest(content=content):
                parse(display_string(content), tltype="item")

    def test_other_errors_unchanged(self):
        self.check(
            [
                (
                    b'%"%ff',
                    "item",
                    "Reached end of input without finding a closing DQUOTE",
                    5,
                ),
                (b'%"%FF"', "item", "Uppercase percent encoding", 3),
                (b'%"%f"', "item", "Invalid percent encoding", 3),
                (b'%"%ff%g', "item", "Incomplete percent encoding", 6),
                (b'%"%ff\x7f"', "item", "String contains disallowed character", 5),
                (b'%"%ff\xc3\xa9"', "item", "String contains disallowed character", 5),
            ]
        )


class TestBinarySequencePadding(PositionTestCase):
    """
    "Binary Sequence failed to decode" is reported at the first byte the
    padding rules reject: padding is one or two "=" at the end, after at least
    one data character. A bad length (one data character too many for whole
    groups) isn't a fault in any byte; it stays at the closing ":".
    """

    MESSAGE = "Binary Sequence failed to decode"

    # (content, offset in the content of the first rejected byte). The offsets
    # are counted by hand, not computed from the input.
    THIRD_EQUALS = [
        (b"AA===", 4),
        (b"AAA===", 5),
        (b"AAAA====", 6),
        (b"aGVsbG8===", 9),
        (b"AA======", 4),
        (b"A===", 3),  # a bad length too, but the third "=" comes first
        (b"AA===A", 4),  # ... and it comes before the data character
    ]
    ONLY_EQUALS = [(b"=", 0), (b"==", 0), (b"===", 0), (b"====", 0)]
    DATA_AFTER_EQUALS = [
        (b"AA=A", 3),
        (b"AA=A===", 3),  # the data character comes before the third "="
        (b"AA==A", 4),
        (b"AA=A=", 3),
        (b"AA=A==", 3),
        (b"AA=AA==", 3),
        (b"AAA=AAAA", 4),
        (b"aG=Vs", 3),
        (b"aGVs=bG8=", 5),
        (b"a=GVsbG8=", 2),
        (b"A=A", 2),
        (b"A=AAA", 2),
    ]
    LEADING_EQUALS = [
        (b"=aGVs", 0),
        (b"==aGVs", 0),
        (b"=aGVsbG8=", 0),
        (b"=A=", 0),
    ]
    BAD_LENGTH = [  # the end of the content, where the closing ":" is
        (b"a", 1),
        (b"aGVsb", 5),
        (b"aGVsbG8aa", 9),
        (b"AAAAAAAAA", 9),
        (b"a=", 2),
        (b"a==", 3),
        (b"AAAAA=", 6),
        (b"AAAAA==", 7),
    ]
    CONTEXTS = [  # (before, after, tltype)
        (b"", b"", "item"),
        (b"a, ", b"", "list"),
        (b"a, ", b", b", "list"),
        (b"(a ", b" b)", "list"),
        (b"a=1, b=", b", c", "dictionary"),
        (b"a=", b"", "dictionary"),
        (b"a=1;p=", b"", "dictionary"),
        (b"x;p=", b";q=1", "item"),
    ]

    def check_content(self, cases, is_equals):
        for content, offset in cases:
            self.assertEqual(content[offset] == ord("="), is_equals)
            for before, after, tltype in self.CONTEXTS:
                value = before + b":" + content + b":" + after
                with self.subTest(content=content, before=before, after=after):
                    why = failure(value, tltype)
                    position = len(before) + 1 + offset
                    self.assertEqual(why.args[0], self.MESSAGE)
                    self.assertEqual(why.position, position)
                    self.assertEqual(why.offending_char, value[position])

    def test_third_equals(self):
        self.check_content(self.THIRD_EQUALS, True)

    def test_only_equals(self):
        self.check_content(self.ONLY_EQUALS, True)

    def test_data_after_equals(self):
        self.check_content(self.DATA_AFTER_EQUALS, False)

    def test_leading_equals(self):
        self.check_content(self.LEADING_EQUALS, True)

    def test_bad_length_stays_at_the_closing_colon(self):
        for content, offset in self.BAD_LENGTH:
            self.assertEqual(offset, len(content))
        for content, offset in self.BAD_LENGTH:
            for before, after, tltype in self.CONTEXTS:
                value = before + b":" + content + b":" + after
                with self.subTest(content=content, before=before, after=after):
                    why = failure(value, tltype)
                    position = len(before) + 1 + offset
                    self.assertEqual(why.args[0], self.MESSAGE)
                    self.assertEqual(why.position, position)
                    self.assertEqual(why.offending_char, ord(":"))

    def test_alphabet_error_comes_first(self):
        message = "Binary Sequence contained disallowed character"
        self.check(
            [
                (b":AA===.:", "item", message, 6),
                (b":=.:", "item", message, 2),
                (b":AA=.A:", "item", message, 4),
                (b":AA=A$:", "item", message, 5),
            ]
        )

    def test_first_fault_wins(self):
        self.check(
            [
                (b":=A=A:", "item", self.MESSAGE, 1),
                (b":A=A=A:", "item", self.MESSAGE, 3),
                (b":AA==A==:", "item", self.MESSAGE, 5),
                (b":A==A=:", "item", self.MESSAGE, 4),
                (b":AA===A=A:", "item", self.MESSAGE, 5),
            ]
        )

    def test_cause(self):
        # What the position moved from is unchanged: padding that is wrong
        # before decoding has no cause; the rest is a binascii.Error.
        for content in (b"AA===", b"AAAA====", b"=", b"==", b"AA=A===", b"A==="):
            with self.subTest(content=content):
                why = failure(b":" + content + b":", "item")
                self.assertIsNone(why.__cause__)
                self.assertFalse(why.__suppress_context__)
        for content in (b"AA===A", b"AA=A", b"=aGVs", b"a", b"aGVsb", b"=A=", b"a="):
            with self.subTest(content=content):
                why = failure(b":" + content + b":", "item")
                self.assertIsInstance(why.__cause__, binascii.Error)
                self.assertTrue(why.__suppress_context__)

    def test_context_is_kept(self):
        self.assertEqual(failure(b"a=1, b=:AA=A:", "dictionary").context, "b")
        self.assertEqual(failure(b"a;b=:AA===:", "item").context, "b")

    def test_direct_call(self):
        state = ParserState(b"xx:AA=A:, y")
        state.cursor = 2
        with self.assertRaises(StructuredFieldError) as ctx:
            parse_byteseq(state)
        self.assertEqual(ctx.exception.position, 6)
        self.assertEqual(ctx.exception.offending_char, ord("A"))
        self.assertEqual(state.cursor, 8)  # after the closing ":"

    def test_every_short_content(self):
        # Every content of 0 to 8 characters from a small alphabet, against a
        # left-to-right check of the padding rules.
        for length in range(9):
            for chars in itertools.product(b"A/=", repeat=length):
                content = bytes(chars)
                value = b":" + content + b":"
                offset = self.first_rejected(content)
                with self.subTest(content=content):
                    if offset is None:
                        parse(value, tltype="item")
                        continue
                    why = failure(value, "item")
                    self.assertEqual(why.args[0], self.MESSAGE)
                    self.assertEqual(why.position, 1 + offset)

    @staticmethod
    def first_rejected(content):
        """Offset of the first rejected byte, len(content) if the length is
        wrong, None if the content is valid."""
        data = equals = 0
        for offset, char in enumerate(content):
            if char == ord("="):
                equals += 1
                if data == 0 or equals > 2:
                    return offset
            elif equals:
                return offset
            else:
                data += 1
        return len(content) if data % 4 == 1 else None

    def test_valid_padding_parses(self):
        for value in (
            b":AA==:",
            b":AAA=:",
            b":AAAA==:",
            b":AAAAAA==:",
            b":aGVsbG8=:",
            b":aGVsbG8==:",
            b":aGVsbG8:",
            b"::",
        ):
            with self.subTest(value=value):
                parse(value, tltype="item")


if __name__ == "__main__":
    unittest.main()
