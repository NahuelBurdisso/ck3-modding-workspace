"""Regression tests for the wrapped-grep-target sweep in tools/sweep_backticks.py.

WHY THIS FILE EXISTS. The sweep was a throwaway shell one-liner retyped from
memory in every review round, and every retyping was wrong in a new way: one
was vacuous because a citation matches itself, one was case-blind in prose and
case-sensitive in fact, one read a blockquoted fence delimiter as prose, one
counted escaped backticks. 8a71ce1 turned it into a file so the mistakes stop
being invisible. That only helps if the behaviour is pinned, because the file
is small enough to look obviously correct while being wrong - which is exactly
what happened to each one-liner.

Run it with `python tools/tests/test_sweep_backticks.py`. Stdlib unittest, no
pytest, for the reason test_citations.py gives in its own header.

THE DOCUMENTED LIMITS ARE TESTED AS LIMITS, not as bugs. A span broken across
three or more lines and two unbalanced spans sharing one line both escape this
detector on purpose; if someone later makes them report, these tests fail and
the KNOWN LIMITS block in sweep_backticks.py has to be updated with them. That
is the intent - a limit nobody has written down is indistinguishable from a
defect nobody has noticed.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import sweep_backticks as S  # noqa: E402

# A FIXTURE THAT CARRIES A LONE BACKTICK SPELLS IT `\x60`, for the reason
# sweep_backticks.py gives for spelling its own that way: a detector whose
# source turns up in its own report on every run teaches the reader to skim the
# report. Twelve fixture lines here did exactly that. The escape is the same
# character at run time, so nothing under test changes, and it is preferred over
# excluding this file by name because a carve-out is the shape the rule exists
# to prevent. BALANCED FIXTURES ARE LEFT LITERAL - they never reported, and
# `\x60{3}` for a fence delimiter is unreadable.
ODD_LINE = "an \x60 unbalanced line\n"


class SweepTestCase(unittest.TestCase):
    """Builds a throwaway tree per test and runs the real sweep on it."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="ck3_sweep_"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def write(self, relpath: str, text: str) -> Path:
        path = self.root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def hits(self) -> list[tuple[str, int]]:
        """Every reported line as `(relpath, lineno)`, in sweep order."""
        return [(rel, lineno) for rel, lineno, _ in S.sweep(self.root)]

    def assertClean(self) -> None:
        found = S.sweep(self.root)
        self.assertEqual(found, [], f"expected a clean tree, got {found}")


class TestTheSignature(SweepTestCase):
    """A wrapped span is odd at both ends; a balanced line is silent.

    The silent partners are not padding. Without them every test here passes
    against a detector that reports every line it reads, which is the shape a
    `grep -c` one-liner degenerates into.
    """

    def test_a_balanced_line_is_not_reported(self) -> None:
        self.write("a.md", "See `BC: floor admitted` for the marker.\n")
        self.assertClean()

    def test_a_line_with_no_backtick_at_all_is_not_reported(self) -> None:
        self.write("a.md", "Nothing quoted on this line.\n")
        self.assertClean()

    def test_a_span_wrapped_once_reports_both_of_its_ends(self) -> None:
        self.write("a.md", "See `BC: floor\nadmitted` for the marker.\n")
        self.assertEqual(self.hits(), [("a.md", 1), ("a.md", 2)])

    def test_two_balanced_spans_on_one_line_are_not_reported(self) -> None:
        # Four backticks is even for the right reason, not by luck; the pairing
        # is what the detector actually relies on.
        self.write("a.md", "Both `BC: one` and `BC: two` are fine.\n")
        self.assertClean()


class TestDocumentedLimits(SweepTestCase):
    """The two misses that sweep_backticks.py's KNOWN LIMITS block admits to.

    These assert the CURRENT behaviour so that changing it is a deliberate act
    with a failing test attached, not a silent widening nobody records.
    """

    def test_the_middle_of_a_span_broken_twice_is_not_reported(self) -> None:
        # Line 2 lies wholly inside the span and carries no backtick, so it is
        # invisible. The two ends still report, which is why the span is caught
        # at all.
        self.write("a.md", "See `BC: a very\nlong marker\nname` here.\n")
        self.assertEqual(self.hits(), [("a.md", 1), ("a.md", 3)])

    def test_two_unbalanced_spans_on_one_line_hide_each_other(self) -> None:
        # `one` opens on line 2 and `two` closes on it; the counts sum to even
        # and the line is silent even though two spans straddle it.
        self.write("a.md", "close` and open `x\n")
        self.assertClean()


class TestFences(SweepTestCase):
    """Fenced blocks are skipped, including fences inside a blockquote.

    f74e420 shipped the blockquote fix with the wrong reason attached: it said
    the defect put fenced BODY lines into the report. It does not. A fence
    delimiter is three backticks, so an unrecognised delimiter is odd and
    reports ITSELF; the body only reports if the body is itself unbalanced.
    Both halves are pinned below because the first is what actually happened
    and the second is what the message claimed.
    """

    def test_an_unbalanced_line_inside_a_fence_is_skipped(self) -> None:
        self.write("a.md", "```\n" + ODD_LINE + "```\n")
        self.assertClean()

    def test_a_blockquoted_fence_is_recognised_and_reports_nothing(self) -> None:
        self.write("a.md", "> ```bash\n> grep -n 'x' file\n> ```\n")
        self.assertClean()

    def test_an_unrecognised_fence_delimiter_reports_itself(self) -> None:
        # THE PROOF FOR THE PARAGRAPH ABOVE. With the `>` allowance removed
        # from FENCE_RE, these are the lines that report - the delimiters, at 1
        # and 3, not the body at 2, which carries no backtick.
        self.write("a.md", "> ```bash\n> grep -n 'x' file\n> ```\n")
        real = S.FENCE_RE
        S.FENCE_RE = __import__("re").compile(r"^\s*(?:\x60{3}|~{3})")
        self.addCleanup(setattr, S, "FENCE_RE", real)
        self.assertEqual(self.hits(), [("a.md", 1), ("a.md", 3)])

    def test_a_tilde_fence_is_recognised(self) -> None:
        self.write("a.md", "~~~\n" + ODD_LINE + "~~~\n")
        self.assertClean()


class TestEscapedBackticks(SweepTestCase):
    """Stripping removes BOTH failure modes; it does not trade one for the other.

    8a0d33e's prose and sweep_backticks.py's own first header both got this
    backwards. Counted raw, an escaped backtick flips a balanced line to odd -
    noise - and flips an unbalanced line to even, which is a MISS. The second
    test here is the one that matters: without stripping it goes green, and a
    real wrapped marker goes unreported.
    """

    def test_a_balanced_line_carrying_an_escape_is_not_reported(self) -> None:
        self.write("a.md", "The `\\`` literal and `BC: x` beside it.\n")
        self.assertClean()

    def test_an_unbalanced_line_carrying_an_escape_is_still_reported(self) -> None:
        self.write("a.md", "A \\` escape and an open `BC: floor\nadmitted` here.\n")
        self.assertEqual(self.hits(), [("a.md", 1), ("a.md", 2)])


class TestWalkCoverage(SweepTestCase):
    """What the walk offers the scanner, and what it must not offer it."""

    def test_git_and_pycache_are_pruned_at_any_depth(self) -> None:
        self.write(".git/a.md", ODD_LINE)
        self.write("sub/.git/b.md", ODD_LINE)
        self.write("sub/__pycache__/c.md", ODD_LINE)
        self.assertClean()

    def test_an_unlisted_extension_is_skipped(self) -> None:
        self.write("a.json", ODD_LINE)
        self.write("a.png", ODD_LINE)
        self.assertClean()

    def test_extensions_match_regardless_of_case(self) -> None:
        # The rule the sweep enforces is casing-blind, so a mis-cased extension
        # must not buy silence. A case-sensitive `path.suffix in EXTS` skips
        # both of these and this test goes green only by accident of the
        # assertion below being on the count.
        self.write("A.MD", ODD_LINE)
        self.write("b.TXT", ODD_LINE)
        self.assertEqual(self.hits(), [("A.MD", 1), ("b.TXT", 1)])

    def test_a_file_that_is_not_utf8_is_skipped_rather_than_crashing(self) -> None:
        (self.root / "bad.txt").write_bytes(b"\xff\xfe an \x60 unbalanced line\n")
        self.assertClean()

    def test_the_walk_order_is_sorted_and_parents_lead(self) -> None:
        # ASSERTS THE ORDER, NOT MERELY THAT IT REPEATS. Comparing several runs
        # to each other passes on an unsorted walk too. TWO SIBLING DIRECTORIES,
        # because with one, reversing the `dirnames` sort changes nothing and
        # the mutation survives.
        for name in ("zz", "aa"):
            self.write(f"sub/{name}.md", ODD_LINE)
        self.write("top.md", ODD_LINE)
        self.write("other/x.md", ODD_LINE)
        self.assertEqual(
            self.hits(),
            [
                ("top.md", 1),
                ("other/x.md", 1),
                ("sub/aa.md", 1),
                ("sub/zz.md", 1),
            ],
        )


class TestAgainstTheRealTree(unittest.TestCase):
    """The sweep over the checkout it ships in.

    NOT AN ASSERTION THAT THE TREE IS CLEAN - it is not, and it is not meant to
    be. The tree carries legitimate multi-line quotations of script, command
    lines, paths and tool output, which is why sweep_backticks.py is not a
    `validate` check. What is pinned is that the sweep RUNS over the real
    checkout and returns well-formed results, which every tmpdir test above
    would pass without.
    """

    def test_the_sweep_runs_over_the_repo_and_returns_well_formed_hits(self) -> None:
        repo = Path(__file__).resolve().parents[2]
        hits = S.sweep(repo)
        for rel, lineno, line in hits:
            self.assertFalse(Path(rel).is_absolute(), rel)
            self.assertGreaterEqual(lineno, 1, rel)
            self.assertIsInstance(line, str)

    def test_the_sweep_does_not_report_its_own_source(self) -> None:
        # sweep_backticks.py spells its backticks as escapes so that it does not
        # name itself on every run. Excluding it by name would be a carve-out of
        # the kind the rule exists to prevent, so this pins the escaping instead.
        repo = Path(__file__).resolve().parents[2]
        reported = {rel for rel, _, _ in S.sweep(repo)}
        self.assertNotIn("tools/sweep_backticks.py", reported)


if __name__ == "__main__":
    unittest.main(verbosity=2)
