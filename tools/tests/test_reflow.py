"""Regression tests for the comment reflow in tools/ck3lib/reflow.py.

WHY THIS FILE EXISTS. Four consecutive review rounds on the battle_chronicles
mod found the same defect class, and every one of them was produced by the same
act: reflowing a comment paragraph by hand. Round 2 spliced a paragraph instead
of reflowing it and left a 45-character line under an 84-character budget. Round
3's fix severed an antecedent by inserting lines mid-sentence. Round 4 found two
fresh artifacts - a five-character widow reading `# is.`, and a 54-character line
welded between two 77s - both produced by a reflow that stopped at the edge of
the hunk it was editing. Reviewing harder did not converge, because the reviewer
sees the result and the defect is in the mechanism. reflow.py removes the
mechanism.

THE TOOL IS ONLY WORTH HAVING IF IT CANNOT EAT PROSE. It rewrites comments in
place, so a bug here is a bug that silently deletes design record - which in this
workspace is the only design record there is, since nothing may be tested in the
game. Every test below is therefore a safety property first and a formatting
property second, and the two content-preservation tests are the ones to keep
green at any cost.

Run it with `python tools/tests/test_reflow.py`. Stdlib unittest, no pytest, for
the reason test_citations.py gives in its own header.

WHAT PINS WHAT IS STATED PER TEST, NOT IN AGGREGATE, for the reason
test_sweep_backticks.py's header gives.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ck3lib import reflow as R  # noqa: E402


class TestReflow(unittest.TestCase):
    def test_a_short_line_pulls_words_up_from_the_line_below(self) -> None:
        # THE ROUND 4 DEFECT, REDUCED. `# is.` was a five-character line under an
        # 84-column budget with a full line above it. Greedy fill cannot produce
        # that shape, which is the whole reason to fill greedily rather than by
        # hand.
        got = R.reflow(["# alpha beta", "# gamma delta"], width=20)
        self.assertEqual(got, ["# alpha beta gamma", "# delta"])

    def test_an_over_wide_line_is_split(self) -> None:
        # The other direction, and the one the 84-column rule needs: a line over
        # budget is broken rather than left standing.
        got = R.reflow(["# alpha beta gamma delta"], width=14)
        self.assertEqual(got, ["# alpha beta", "# gamma delta"])

    def test_every_word_survives_in_order(self) -> None:
        # THE SAFETY PROPERTY. Formatting may change; the prose may not. A reflow
        # that drops or reorders a word is worse than no reflow at all, because
        # the diff looks like whitespace churn and nobody reads it.
        words = [f"w{n}" for n in range(40)]
        got = R.reflow(["# " + " ".join(words)], width=24)
        self.assertEqual(" ".join(l[2:] for l in got).split(), words)

    def test_the_budget_is_the_whole_line_including_the_prefix(self) -> None:
        # `#` and its space are part of the line the 84-column rule measures, so
        # they are part of the budget. Measuring only the prose would let every
        # line run two characters over.
        got = R.reflow(["# aaaa bbbb"], width=6)
        self.assertEqual(got, ["# aaaa", "# bbbb"])

    def test_a_word_at_exactly_the_budget_stays_on_the_line(self) -> None:
        # The off-by-one. `<=` not `<`: a line that lands exactly on the budget
        # is legal, and rejecting it silently narrows every paragraph by one
        # character.
        got = R.reflow(["# aaa bbb"], width=9)
        self.assertEqual(got, ["# aaa bbb"])

    def test_a_word_longer_than_the_budget_gets_its_own_line_and_overflows(self) -> None:
        # THE ATOMIC RUN. bc_flavour.txt carries an engine message 82 characters
        # long that must not be broken, and this workspace's rules say a grep
        # target may never wrap. Breaking it would be the one unrecoverable
        # failure, so the tool overflows the budget instead and lets the
        # over-width check report it.
        got = R.reflow(["# a `an-enormous-unbreakable-token` b"], width=12)
        self.assertEqual(got, ["# a", "# `an-enormous-unbreakable-token`", "# b"])

    def test_a_backticked_run_is_never_split(self) -> None:
        # THE RULE THIS WORKSPACE ENFORCES BY HAND EVERYWHERE ELSE: a quoted run
        # may wrap, a GREP TARGET may never, and a grep target is spelled as a
        # backticked run. A filler that breaks one makes the name uncitable and
        # the break is invisible in review.
        # THE LEADING WORD IS LONG ON PURPOSE. With a short one the run ends a
        # line either way, and a filler that had never heard of quoting would
        # pass by luck - which is what the mutation harness caught it doing.
        got = R.reflow(["# aaaaaaaaaa `bee cee dee` ff"], width=20)
        self.assertEqual(got, ["# aaaaaaaaaa", "# `bee cee dee` ff"])

    def test_a_double_quoted_run_is_never_split(self) -> None:
        # The defect that was actually shipped by this module's first draft, on
        # its first real paragraph: `"man commanding here"` broken after `"man`.
        # Double quotes carry grep targets here as often as backticks do.
        got = R.reflow(['# aa "bee cee dee" ff'], width=20)
        self.assertEqual(got, ['# aa "bee cee dee"', "# ff"])

    def test_punctuation_welded_to_a_closing_quote_travels_with_it(self) -> None:
        # A comma left behind becomes a token that can open a line, which is
        # both ugly and a lie about where the quote ended.
        # WIDTH 16 FORCES THE BREAK. At a width the whole thing fits on, the
        # comma's placement is not being tested at all - it would pass over a
        # tokenizer that dropped the comma into its own token.
        got = R.reflow(['# aaaa "bee cee", dd'], width=16)
        self.assertEqual(got, ["# aaaa", '# "bee cee", dd'])

    def test_a_quoted_run_too_long_to_fit_alone_is_split_after_all(self) -> None:
        # WHOLE ONLY WHERE WHOLE FITS. Keeping an over-long run intact would
        # manufacture a new over-width line, and the over-width check is a count
        # of KNOWN ones - so every new one costs a human argument. Splitting is
        # the lesser failure and the one the budget already tolerates for prose.
        got = R.reflow(['# aa "bee cee dee" ff'], width=12)
        self.assertEqual(got, ['# aa "bee', '# cee dee"', "# ff"])

    def test_the_leading_whitespace_of_the_comment_is_preserved(self) -> None:
        # Comments inside an event block are tab-indented. Reflowing one to
        # column zero would move it out of its block visually and produce a diff
        # touching every line.
        # WIDTH 14, NOT 12: a tab counts as ONE character here, which is the same
        # convention the 84-column check uses, so `\t# alpha beta` is 13 and a
        # budget of 12 would break after the first word and pin nothing about the
        # indent.
        got = R.reflow(["\t# alpha beta gamma"], width=14)
        self.assertEqual(got, ["\t# alpha beta", "\t# gamma"])

    def test_a_hanging_indent_is_taken_from_the_second_line(self) -> None:
        # THE LABELLED ENTRY, which is the shape of the collision table in
        # bc_l_english.yml - a term in the left column, prose in the right, and
        # every continuation aligned under the prose. Deriving the continuation
        # column from the second line rather than guessing keeps the table a
        # table.
        got = R.reflow(
            ['#   "the man"   alpha beta gamma', "#               delta"],
            width=30,
        )
        self.assertEqual(
            got,
            ['#   "the man"   alpha beta', "#               gamma delta"],
        )

    def test_a_label_shorter_than_the_column_keeps_its_padding(self) -> None:
        # The label is copied verbatim and padded out to the continuation
        # column, so a short term does not drag the prose left on line one only.
        got = R.reflow(['#   "x"         alpha beta', "#               gamma"], width=40)
        self.assertEqual(got, ['#   "x"         alpha beta gamma'])

    def test_a_first_line_carrying_only_a_label_is_padded_out_to_the_column(self) -> None:
        # A term too wide for its column is written on a line of its own in
        # these tables, so the first line stops short of the column and carries
        # no prose at all. That is the one shape where the padding is load
        # bearing: without it the prose pulled up from line two lands against
        # the term instead of under the column, and the table stops lining up.
        # It is also the one shape where the two-space separator is absent and
        # must not be demanded, since with no prose there is nothing to separate.
        got = R.reflow(['#   "x"', "#          alpha beta"], width=40)
        self.assertEqual(got, ['#   "x"    alpha beta'])

    def test_reflowing_twice_changes_nothing(self) -> None:
        # IDEMPOTENCE IS THE ACCEPTANCE CHECK. `reflow` then `git diff --exit-code`
        # is how a paragraph is proven already correct, and that only works if a
        # second pass is a no-op.
        once = R.reflow(["# alpha beta gamma delta epsilon zeta"], width=20)
        self.assertEqual(R.reflow(once, width=20), once)

    def test_no_output_line_carries_trailing_whitespace(self) -> None:
        # Trailing whitespace is invisible in review and shows up as a diff in
        # the next commit that touches the line, which is how an unrelated
        # paragraph ends up in a hunk.
        got = R.reflow(["#    alpha    ", "#  beta  "], width=40)
        self.assertTrue(all(line == line.rstrip() for line in got))

    def test_a_line_that_is_not_a_comment_is_refused(self) -> None:
        # A BOUNDARY, and the reason it is loud: the caller passes a line RANGE,
        # a range is typed by hand, and a range off by one reaches code. Rewrapping
        # `set_variable = { name = x value = y }` as prose destroys it silently.
        # THE MESSAGE IS PART OF THE ASSERTION. Every refusal in this module
        # raises ValueError, so a bare assertRaises passes on the wrong refusal
        # and lets the boundary itself be deleted.
        with self.assertRaisesRegex(ValueError, "not a comment line"):
            R.reflow(["# alpha", "set_variable = { name = x }"], width=40)

    def test_a_bare_hash_separator_inside_the_range_is_refused(self) -> None:
        # TWO PARAGRAPHS, NOT ONE. A `#` on its own is the separator this
        # workspace's comment blocks use, and merging across it is exactly the
        # round 3 defect - two sentences welded together, one of them inverted in
        # meaning. The tool declines rather than guessing which side wins.
        with self.assertRaises(ValueError):
            R.reflow(["# alpha", "#", "# beta"], width=40)

    def test_an_empty_range_is_refused(self) -> None:
        # Nothing to reflow is a caller error, not an empty result: it means the
        # range resolved to no lines and the caller is about to write that back.
        with self.assertRaises(ValueError):
            R.reflow([], width=40)

    def test_mixed_leading_whitespace_is_refused(self) -> None:
        # A range that spans two indent levels spans two blocks. Picking either
        # indent silently re-parents half the prose.
        with self.assertRaises(ValueError):
            R.reflow(["# alpha", "\t# beta"], width=40)

    def test_a_continuation_indented_less_than_the_second_line_is_refused(self) -> None:
        # The continuation column comes from the second line, so a later line
        # that starts left of it is not part of the same hanging-indent
        # paragraph. Reflowing anyway would pull a new entry's label into the
        # previous entry's prose - the collision table's failure mode.
        with self.assertRaises(ValueError):
            R.reflow(
                ['#   "a"     alpha', "#           beta", '#   "b"     gamma'],
                width=40,
            )

    def test_a_first_line_whose_label_region_has_no_separator_is_refused(self) -> None:
        # Without a two-space separator the tool cannot tell a label from the
        # first words of the prose, and guessing would either duplicate those
        # words or delete them. `#  alpha beta` under a continuation column of 8
        # is that ambiguity.
        with self.assertRaises(ValueError):
            R.reflow(["#  alpha beta", "#        gamma"], width=40)


class TestFindParagraph(unittest.TestCase):
    def test_the_paragraph_around_a_line_stops_at_a_bare_hash(self) -> None:
        # THE POINT OF THE HELPER. Round 4's two artifacts were both produced by
        # a reflow that stopped where the edit stopped rather than where the
        # paragraph stopped. Given one line inside it, this returns the whole
        # paragraph, so the tool cannot repeat that.
        lines = ["# a", "#", "# b", "# c", "# d", "#", "# e"]
        self.assertEqual(R.find_paragraph(lines, 4), (2, 5))

    def test_the_paragraph_stops_at_a_non_comment_line(self) -> None:
        # Script below a header block ends it just as firmly as a separator does.
        lines = ["# a", "# b", "bc_x = {", "}"]
        self.assertEqual(R.find_paragraph(lines, 2), (0, 2))

    def test_a_labelled_table_is_cut_into_one_paragraph_per_entry(self) -> None:
        # THE DEFECT THIS HELPER WAS REWRITTEN FOR. The collision table in
        # bc_l_english.yml is 53 consecutive comment lines with no `#` between
        # any two entries. Reading the whole run as one paragraph and reflowing
        # it flattens the table into prose and destroys every left-column term.
        # The entries are told apart by INDENT: a label sits left of its own
        # continuations, so the next label ends the previous entry.
        lines = [
            '#   "a"     alpha',
            "#           beta",
            '#   "b"     gamma',
            "#           delta",
        ]
        self.assertEqual(R.find_paragraph(lines, 1), (0, 2))
        self.assertEqual(R.find_paragraph(lines, 2), (0, 2))
        self.assertEqual(R.find_paragraph(lines, 3), (2, 4))

    def test_a_plain_paragraph_runs_to_the_end_of_its_block(self) -> None:
        # The other half of the same rule: one indent throughout means one
        # paragraph, so the indent cut must not fire on ordinary prose.
        lines = ["# a", "# b", "# c"]
        self.assertEqual(R.find_paragraph(lines, 2), (0, 3))

    def test_a_plain_paragraph_stops_where_a_table_starts(self) -> None:
        # A header sentence directly above a table, with no `#` between them,
        # is the shape bc_l_english.yml actually uses. The prose must not absorb
        # the first entry's label.
        lines = ["# a", "# b", '#   "x"     alpha', "#           beta"]
        self.assertEqual(R.find_paragraph(lines, 1), (0, 2))
        self.assertEqual(R.find_paragraph(lines, 3), (2, 4))

    def test_a_line_that_is_not_a_comment_has_no_paragraph(self) -> None:
        # ASSERTED ON THE MESSAGE for the reason the reflow refusals give: drop
        # the guard and the very next line still raises ValueError, from _head,
        # so a bare assertRaises cannot tell the guard from its absence.
        lines = ["# a", "bc_x = {"]
        with self.assertRaisesRegex(ValueError, "not inside a comment paragraph"):
            R.find_paragraph(lines, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
