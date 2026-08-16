"""Regression tests for tools/ck3lib/pdxscript.py.

WHY THIS FILE WAS WRITTEN LAST AND SHOULD HAVE BEEN WRITTEN FIRST. Every other
tested module in this tree stands on this one. `validate.py` asks it what is
defined where, whether a file's braces balance, whether a loc file parses; the
index asks it the same questions across forty-eight sources. It had no tests at
all until a validator check was built directly on `tokenize` - the custom-loc arm
shape, which decides whether an arm is guarded by asking what DEPTH a `trigger`
sits at. Depth is a tokenizer output. A check that careful resting on a substrate
that unchecked is the wrong way round.

WHAT MAKES A SHALLOW PARSER'S BUGS EXPENSIVE. The module's own header calls it
deliberately shallow, and that is the right design: it only has to answer "what
is defined where" and "is this structurally sane". But shallow does not mean
forgiving. A tokenizer that reads `>=` as `>` then `=` reports a key that is not
there. One that lets an unterminated string run past its line eats the rest of
the file and reports NOTHING wrong with it - the same silent-truncation failure
that `brace_report` exists to catch, arriving through the tool that was supposed
to catch it.

EVERY TEST NAMES THE CALLER IT PROTECTS where the behaviour is not obvious on its
own, because a tokenizer test reads as arbitrary otherwise: there is no way to
tell a deliberate rule from an accident of implementation by looking at the token
stream alone.

Run it with `python tools/tests/test_pdxscript.py`. Stdlib unittest, no pytest,
for the reason test_citations.py gives in its own header.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ck3lib import pdxscript as P  # noqa: E402


def kinds(text: str) -> list[tuple[str, str]]:
    return [(t.kind, t.value) for t in P.tokenize(text)]


class TestTokenize(unittest.TestCase):
    def test_a_simple_assignment_is_word_op_word(self) -> None:
        self.assertEqual(kinds("a = b"), [("word", "a"), ("op", "="), ("word", "b")])

    def test_braces_are_their_own_tokens(self) -> None:
        self.assertEqual(
            kinds("a = { }"), [("word", "a"), ("op", "="), ("open", "{"), ("close", "}")]
        )

    def test_a_comment_is_dropped_and_its_newline_is_not(self) -> None:
        # The newline has to survive or every line number below the comment is
        # wrong, and a line number is what a validator issue IS.
        self.assertEqual(kinds("# note\na = b"), [("word", "a"), ("op", "="), ("word", "b")])
        self.assertEqual([t.line for t in P.tokenize("# note\na = b")], [2, 2, 2])

    def test_a_quoted_string_becomes_one_token_without_its_quotes(self) -> None:
        self.assertEqual(kinds('name = "The Mod"'), [("word", "name"), ("op", "="), ("str", "The Mod")])

    def test_an_unterminated_string_stops_at_the_end_of_its_line(self) -> None:
        # THE FAILURE THIS FORBIDS IS SILENT AND TOTAL. Let the string run on and
        # every brace, key and definition below it disappears into the token
        # stream's one string token, and the file reports as clean - which is
        # exactly the truncation `brace_report` exists to detect.
        self.assertEqual(
            kinds('a = "oops\nb = c'),
            [("word", "a"), ("op", "="), ("str", "oops"), ("word", "b"), ("op", "="), ("word", "c")],
        )

    def test_a_two_character_operator_is_not_split_into_two(self) -> None:
        # `_OPERATORS` IS ORDERED, LONGEST FIRST, AND THAT ORDERING IS LOAD
        # BEARING. Split `>=` into `>` and `=` and `top_level_defs` sees an `op`
        # where it expected one anyway - but `count >= 3` then reads as a
        # definition of `count`, and a scripted trigger becomes a top-level key.
        for op in ("?=", ">=", "<=", "!=", "=="):
            self.assertEqual(kinds(f"a {op} b")[1], ("op", op), op)

    def test_a_word_ends_at_punctuation_with_no_space_before_it(self) -> None:
        # `a={b=c}` with no spaces is legal script and common in vanilla.
        self.assertEqual(
            kinds("a={b=c}"),
            [
                ("word", "a"),
                ("op", "="),
                ("open", "{"),
                ("word", "b"),
                ("op", "="),
                ("word", "c"),
                ("close", "}"),
            ],
        )

    def test_a_comment_with_no_space_after_a_value_still_ends_the_value(self) -> None:
        self.assertEqual(kinds("a = b# note"), [("word", "a"), ("op", "="), ("word", "b")])

    def test_a_lone_unexpected_character_is_skipped_rather_than_spun_on(self) -> None:
        # `!` alone matches no operator and cannot start a word, so the scanner
        # would make no progress on it. This is the guard that makes the module
        # terminate on hostile input rather than hang the whole run.
        self.assertEqual(kinds("!a = b"), [("word", "a"), ("op", "="), ("word", "b")])

    def test_carriage_returns_are_whitespace_so_crlf_files_tokenize_the_same(self) -> None:
        self.assertEqual(kinds("a = b\r\nc = d"), kinds("a = b\nc = d"))
        self.assertEqual([t.line for t in P.tokenize("a = b\r\nc = d")], [1, 1, 1, 2, 2, 2])


class TestStripComments(unittest.TestCase):
    def test_a_comment_goes_and_its_newline_stays(self) -> None:
        self.assertEqual(P.strip_comments("a # note\nb"), "a \nb")

    def test_a_string_body_goes_so_braces_inside_it_are_not_counted(self) -> None:
        self.assertEqual(P.strip_comments('a = "{{{"'), "a = ")

    def test_an_unterminated_string_ends_at_the_newline(self) -> None:
        # Without the reset a stray quote swallows the rest of the file and
        # `brace_report` returns 0, 0, None on a file with a hundred braces.
        self.assertEqual(P.strip_comments('a = "oops\n{ }'), "a = \n{ }")


class TestBraceReport(unittest.TestCase):
    def test_a_balanced_file_reports_equal_counts_and_no_bad_line(self) -> None:
        self.assertEqual(P.brace_report("a = { b = { } }"), (2, 2, None))

    def test_a_missing_close_shows_in_the_counts_and_not_as_a_bad_line(self) -> None:
        # THE TWO HALVES ARE DIFFERENT FAULTS. An unclosed brace is only visible
        # in the totals, because depth never goes negative; an unmatched close is
        # visible at the exact line. Reporting only one of them was the original
        # bug this function was written for.
        self.assertEqual(P.brace_report("a = { b = {"), (2, 0, None))

    def test_an_unmatched_close_names_the_line_it_is_on(self) -> None:
        self.assertEqual(P.brace_report("a = { }\n\n}\n"), (1, 2, 3))

    def test_only_the_first_negative_line_is_reported(self) -> None:
        self.assertEqual(P.brace_report("}\n}\n"), (0, 2, 1))

    def test_braces_in_comments_and_strings_are_not_counted(self) -> None:
        self.assertEqual(P.brace_report('# { { {\na = "}"\n'), (0, 0, None))


class TestTopLevelDefs(unittest.TestCase):
    def test_a_block_definition_is_returned_with_its_line(self) -> None:
        self.assertEqual(P.top_level_defs("\na = {\n}\n"), [("a", 2)])

    def test_keys_inside_a_block_are_not_top_level(self) -> None:
        # This is the whole point of the function: `common/traits/*.txt` defines
        # traits at depth 0 and their fields at depth 1, and a duplicate-key
        # check that cannot tell them apart reports every field of every trait.
        self.assertEqual(P.top_level_defs("a = {\n\tb = c\n\td = { e = f }\n}\n"), [("a", 1)])

    def test_two_definitions_in_a_row_are_both_found(self) -> None:
        self.assertEqual(P.top_level_defs("a = {\n}\nb = {\n}\n"), [("a", 1), ("b", 3)])

    def test_a_scalar_assignment_is_a_definition_too(self) -> None:
        # descriptor.mod and the loc-adjacent files are all scalars, and
        # `namespace = bc_battle` is what the duplicate-namespace warning reads.
        self.assertEqual(P.top_level_defs("namespace = bc_battle\n"), [("namespace", 1)])

    def test_the_value_of_a_scalar_is_not_itself_read_as_a_key(self) -> None:
        # `expect_value` exists for exactly this: `a = b\nc = d` has four words
        # at depth 0 and only two of them are keys.
        self.assertEqual(P.top_level_defs("a = b\nc = d\n"), [("a", 1), ("c", 2)])

    def test_a_bare_list_of_values_at_depth_zero_defines_nothing(self) -> None:
        self.assertEqual(P.top_level_defs("a b c\n"), [])

    def test_a_value_followed_by_another_operator_is_still_not_a_key(self) -> None:
        # THE CASE THAT SEPARATES `expect_value` FROM PENDING-OVERWRITING. On
        # `a = b\nc = d` the two agree by luck: `b` is replaced as pending by
        # `c` before any operator arrives, so dropping the flag costs nothing.
        # Put an operator straight after the value and only the flag knows that
        # `b` was spoken for.
        self.assertEqual(P.top_level_defs("a = b = c\n"), [("a", 1)])

    def test_a_stray_close_hides_everything_below_it(self) -> None:
        # NOT A NICE PROPERTY, PINNED BECAUSE IT IS THE ONE WE HAVE. A stray `}`
        # takes the depth negative and it never returns, so the rest of the file
        # defines nothing as far as this function is concerned. What makes that
        # survivable is that `brace_report` reads the same text and reports the
        # unmatched close as an error, so the file is never silently thin - the
        # caller is told the braces are wrong before it trusts the key list.
        self.assertEqual(P.top_level_defs("a = b\n}\nc = d\n"), [("a", 1)])

    def test_a_definition_after_a_block_valued_one_is_still_found(self) -> None:
        # The reset on `close` is what makes this work; without it the first word
        # after `}` is treated as the pending value of the block above.
        self.assertEqual(P.top_level_defs("a = { x = y }\nb = z\n"), [("a", 1), ("b", 2)])


class TestKeysMatching(unittest.TestCase):
    def test_a_nested_key_matching_the_pattern_is_found(self) -> None:
        # common/landed_titles nests k_ inside e_ inside nothing, so the keys
        # that matter are never at depth 0 and `top_level_defs` cannot see them.
        text = "e_empire = {\n\tk_kingdom = {\n\t\tc_county = {\n\t\t}\n\t}\n}\n"
        self.assertEqual(P.keys_matching(text, r"k_"), [("k_kingdom", 2)])

    def test_a_value_that_matches_the_pattern_is_not_a_key(self) -> None:
        # THE `op` HAS TO FOLLOW THE WORD. Match on the word alone and
        # `culture = k_thing` reports `k_thing` as a definition of itself.
        self.assertEqual(P.keys_matching("culture = k_thing\n", r"k_"), [])

    def test_a_matching_word_that_no_operator_follows_is_not_a_key(self) -> None:
        # THE VALUE CASE ABOVE IS NOT THE ONLY ONE. A matching word can also sit
        # in a bare list - `can_create` blocks and title lists in landed_titles
        # both spell one - where nothing follows it but the closing brace. Match
        # on the word and every member of every such list becomes a definition.
        self.assertEqual(P.keys_matching("e_empire = {\n\tk_listed\n}\n", r"k_"), [])

    def test_every_match_is_returned_and_not_just_the_first(self) -> None:
        self.assertEqual(
            P.keys_matching("k_a = {\n}\nk_b = {\n}\n", r"k_"), [("k_a", 1), ("k_b", 3)]
        )


class TestParseDescriptor(unittest.TestCase):
    def test_a_quoted_scalar_loses_its_quotes(self) -> None:
        self.assertEqual(P.parse_descriptor('name = "Battle Chronicles"'), {"name": "Battle Chronicles"})

    def test_a_braced_value_becomes_a_list(self) -> None:
        self.assertEqual(P.parse_descriptor('tags = { "Flavor" "Events" }'), {"tags": ["Flavor", "Events"]})

    def test_an_empty_braced_value_is_an_empty_list_and_not_a_missing_key(self) -> None:
        # `_check_descriptor` tests presence before it tests contents, so the two
        # have to stay distinguishable: a mod with `tags = { }` declared it and a
        # mod with no `tags` line did not.
        self.assertEqual(P.parse_descriptor("tags = { }"), {"tags": []})

    def test_several_keys_are_all_read(self) -> None:
        parsed = P.parse_descriptor('name = "M"\nversion = "1.0"\ntags = { "A" }\n')
        self.assertEqual(parsed, {"name": "M", "version": "1.0", "tags": ["A"]})

    def test_a_trailing_key_with_no_value_is_dropped_rather_than_crashing(self) -> None:
        # A truncated descriptor is a real thing to be handed, and a traceback
        # out of `validate` reports nothing about the sixty files behind it.
        self.assertEqual(P.parse_descriptor('name = "M"\nversion ='), {"name": "M"})


class TestParseLoc(unittest.TestCase):
    def test_the_language_header_is_read(self) -> None:
        lang, entries, bad = P.parse_loc('l_english:\n key:0 "v"\n')
        self.assertEqual((lang, [(e.key, e.version, e.value, e.line) for e in entries], bad),
                         ("english", [("key", "0", "v", 2)], []))

    def test_an_entry_must_be_indented(self) -> None:
        # THE LEADING WHITESPACE IS REQUIRED BY THE GAME, and an unindented entry
        # is ignored by it. Reporting it as malformed is the whole value here:
        # the key looks present in the file and is absent in play.
        _, entries, bad = P.parse_loc('l_english:\nkey:0 "v"\n')
        self.assertEqual((entries, bad), ([], [(2, 'key:0 "v"')]))

    def test_a_missing_version_number_is_allowed_and_comes_back_empty(self) -> None:
        _, entries, _ = P.parse_loc('l_english:\n key: "v"\n')
        self.assertEqual([(e.key, e.version) for e in entries], [("key", "")])

    def test_a_trailing_comment_after_the_value_is_allowed(self) -> None:
        _, entries, bad = P.parse_loc('l_english:\n key:0 "v" # note\n')
        self.assertEqual(([(e.key, e.value) for e in entries], bad), ([("key", "v")], []))

    def test_a_line_with_no_closing_quote_is_malformed(self) -> None:
        # In game this swallows the following lines into one entry, so it is the
        # loc-side twin of the unterminated string in the tokenizer.
        _, entries, bad = P.parse_loc('l_english:\n key:0 "v\n')
        self.assertEqual((entries, bad), ([], [(2, 'key:0 "v')]))

    def test_blank_lines_and_comments_are_neither_entries_nor_malformed(self) -> None:
        _, entries, bad = P.parse_loc("l_english:\n\n # note\n")
        self.assertEqual((entries, bad), ([], []))

    def test_a_bom_does_not_hide_the_language_header(self) -> None:
        # A loc file without a BOM is ignored wholesale by CK3, so every real
        # file has one, so the header is never the first character of the text.
        lang, _, _ = P.parse_loc("\ufeffl_english:\n")
        self.assertEqual(lang, "english")

    def test_the_reported_line_number_counts_from_the_top_of_the_file(self) -> None:
        _, entries, _ = P.parse_loc('l_english:\n\n\n key:0 "v"\n')
        self.assertEqual([e.line for e in entries], [4])


class TestReadText(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "f.txt"

    def test_a_bom_is_stripped(self) -> None:
        self.path.write_bytes("\ufeffa = b".encode("utf-8"))
        self.assertEqual(P.read_text(self.path), "a = b")

    def test_plain_utf8_is_read_unchanged(self) -> None:
        self.path.write_bytes("a = é".encode("utf-8"))
        self.assertEqual(P.read_text(self.path), "a = é")

    def test_bytes_that_are_not_utf8_fall_back_rather_than_raising(self) -> None:
        # Vanilla ships latin-1 in a few places. The fallback is what stops one
        # such file aborting a whole-playset scan.
        self.path.write_bytes(b"a = \xe9")
        self.assertEqual(P.read_text(self.path), "a = é")

    def test_has_bom_is_true_only_for_the_utf8_bom(self) -> None:
        self.path.write_bytes(b"\xef\xbb\xbfl_english:\n")
        self.assertTrue(P.has_bom(self.path))
        self.path.write_bytes(b"l_english:\n")
        self.assertFalse(P.has_bom(self.path))

    def test_has_bom_does_not_read_the_whole_file(self) -> None:
        # It is called on every loc file of every enabled source. Reading three
        # bytes rather than the file is the difference between a scan that runs
        # and one nobody waits for.
        self.path.write_bytes(b"\xef\xbb\xbf" + b"x" * 10_000_000)
        self.assertTrue(P.has_bom(self.path))


if __name__ == "__main__":
    unittest.main(verbosity=2)
