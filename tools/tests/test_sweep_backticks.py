"""Regression tests for the wrapped-grep-target sweep in tools/sweep_backticks.py.

WHY THIS FILE EXISTS. The sweep was a throwaway shell one-liner retyped from
memory in every review round, and every retyping was wrong in a new way: one
was vacuous because a citation matches itself, one was case-blind in prose and
case-sensitive in fact, one read a blockquoted fence delimiter as prose, one
counted escaped backticks. f74e420 turned it into a file, and 8a71ce1
corrected that file, so the mistakes stop being invisible. That only helps if
the behaviour is pinned, because the file is small enough to look obviously
correct while being wrong - which is exactly what happened to each one-liner,
and then happened to the file: 8a71ce1's message says it recorded the
unterminated-fence limit and it recorded an invented mismatched-marker one
instead.

Run it with `python tools/tests/test_sweep_backticks.py`. Stdlib unittest, no
pytest, for the reason test_citations.py gives in its own header.

THE DOCUMENTED LIMITS ARE TESTED AS LIMITS, not as bugs. Every bullet of the
KNOWN LIMITS block in sweep_backticks.py has a test here, including the
unterminated fence, which is the only one whose failure mode is to report
nothing at all. If someone later makes one of them report, its test fails and
the block has to be updated with the change. That is the intent - a limit
nobody has written down is indistinguishable from a defect nobody has noticed,
and a limit written down that the code does not actually have is worse than
either, because it sends the reader looking for the wrong hazard.

A SHA IS UNLABELLED ONLY WHEN IT BELONGS TO THE REPOSITORY THIS FILE LIVES IN.
Two checkouts are in play - this one, and the mod's own history nested at
mods/battle_chronicles - and a SHA from one does not resolve in the other, so
`git show` on it reports an unknown revision rather than the wrong commit.
Anything cited below out of the mod's history is marked "(mod repo)" at the
point of citation; everything else resolves from the tooling root.

WHAT PINS WHAT IS STATED PER TEST, NOT IN AGGREGATE. "Every test is killed by
at least one mutant" is true of this suite and it is weak: it is a property of
the SUITE, and it says nothing about whether a given test pins the behaviour
its name claims. Where a test is weaker than its name suggests, its own
docstring says so.
"""

from __future__ import annotations

import contextlib
import io
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import sweep_backticks as S  # noqa: E402

# A FIXTURE THAT CARRIES A LONE BACKTICK SPELLS IT `\x60`, for the reason
# sweep_backticks.py gives for spelling its own that way: a detector whose
# source turns up in its own report on every run teaches the reader to skim the
# report. Twelve fixture lines here did exactly that. The escape is the same
# character at run time, so nothing under test changes, and it is preferred over
# excluding this file by name because a carve-out is the shape the rule exists
# to prevent. BALANCED FIXTURES ARE LEFT LITERAL - they never reported, and a
# fence delimiter written out as three escapes is unreadable, so it gets a name
# instead.
ODD_LINE = "an \x60 unbalanced line\n"
FENCE = "\x60" * 3 + "\n"


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
    """One test per bullet of sweep_backticks.py's KNOWN LIMITS block.

    These assert the CURRENT behaviour so that changing it is a deliberate act
    with a failing test attached, not a silent widening nobody records.

    An earlier version of this docstring said the block admitted to TWO misses.
    It admitted to more than that, and the bullet the miscount dropped was the
    unterminated fence - the only one of them whose failure mode is to report
    nothing at all. A test class that undercounts the limits it covers is
    hiding a defect behind the word "limit", which is the accusation the whole
    of this file exists to answer.
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

    def test_an_unterminated_fence_swallows_the_rest(self) -> None:
        # THE WORST OF THE FOUR, and the one no test covered until this one.
        # `fenced` is a single boolean with no stack, so an opener that is
        # never closed leaves the flag set to the end of the file and the sweep
        # reports NOTHING below it. The silent partner is the same file with
        # the fence closed, without which this passes against a sweep that
        # reports nothing at all.
        self.write("open.md", FENCE + ODD_LINE)
        self.write("shut.md", "```\n```\n" + ODD_LINE)
        self.assertEqual(self.hits(), [("shut.md", 3)])

    def test_a_backslash_before_a_backtick_is_read_as_an_escape(self) -> None:
        # The fourth bullet, and the only limit in the FALSE-POSITIVE
        # direction. The fixture below ends a code span with a literal
        # backslash, which is not an escape, so the line is genuinely balanced
        # and the sweep is wrong to report it. Nothing in the tree trips it; it
        # is pinned so that a later attempt to be cleverer about escapes has to
        # face it.
        self.write("a.md", "A span ending in a backslash: \x60x\\\x60 and done.\n")
        self.assertEqual(self.hits(), [("a.md", 1)])


class TestFences(SweepTestCase):
    """Fenced blocks are skipped, including fences inside a blockquote.

    f74e420 shipped the blockquote fix with the wrong reason attached: it said
    the defect put fenced BODY lines into the report. It does not. A fence
    delimiter is three backticks, so an unrecognised delimiter is odd and
    reports ITSELF; the body only reports if the body is itself unbalanced.
    Both halves are pinned below - the second by a fixture whose body IS
    unbalanced, because with the blockquoted body the reputation plan actually
    has, which carries no backtick, the assertion cannot tell "the body is
    exempt" from "the body had nothing to say".

    The class also pins what is NOT a limit. 8a71ce1 shipped a KNOWN LIMITS
    bullet claiming a fence opened with one marker and closed with the other is
    not paired, and that the rest of the file is then swallowed. FENCE_RE
    matches either marker and the toggle is marker-agnostic, so that is false
    and it stood for two commits in place of the real hazard.
    """

    def test_an_unbalanced_line_inside_a_fence_is_skipped(self) -> None:
        self.write("a.md", FENCE + ODD_LINE + FENCE)
        self.assertClean()

    def test_a_blockquoted_fence_is_recognised_and_reports_nothing(self) -> None:
        self.write("a.md", "> ```bash\n> grep -n 'x' file\n> ```\n")
        self.assertClean()

    def test_an_unrecognised_fence_delimiter_reports_itself(self) -> None:
        # THE PROOF FOR THE PARAGRAPH ABOVE. With the `>` allowance removed
        # from FENCE_RE, these are the lines that report - the delimiters, at 1
        # and 3, not the body at 2, which carries no backtick.
        self.write("a.md", "> ```bash\n> grep -n 'x' file\n> ```\n")
        no_blockquote = re.compile(r"^\s*(?:\x60{3}|~{3})")
        with mock.patch.object(S, "FENCE_RE", no_blockquote):
            self.assertEqual(self.hits(), [("a.md", 1), ("a.md", 3)])

    def test_an_unrecognised_delimiter_does_not_exempt_an_odd_body(self) -> None:
        # THE OTHER HALF, and the one f74e420's message actually claimed. The
        # fixture above cannot show it: its body carries no backtick, so
        # "the body did not report" and "the body is exempt" look identical.
        # Give the body something to say and it says it, at line 2.
        self.write("a.md", "> ```bash\n> " + ODD_LINE + "> ```\n")
        no_blockquote = re.compile(r"^\s*(?:\x60{3}|~{3})")
        with mock.patch.object(S, "FENCE_RE", no_blockquote):
            self.assertEqual(self.hits(), [("a.md", 1), ("a.md", 2), ("a.md", 3)])

    def test_a_fence_closed_by_the_other_marker_is_still_a_pair(self) -> None:
        # THE REFUTATION OF 8a71ce1'S THIRD BULLET. Opened with backticks,
        # closed with tildes, and the odd line after the close still reports -
        # so the pair closed and the rest of the file was not swallowed. The
        # matched-pair partner is written beside it because a sweep that never
        # entered the fenced state at all would also report line 4 of the
        # first file, and the fenced ODD_LINE inside each proves it did.
        self.write("mixed.md", FENCE + ODD_LINE + "~~~\n" + ODD_LINE)
        self.write("same.md", FENCE + ODD_LINE + FENCE + ODD_LINE)
        self.assertEqual(self.hits(), [("mixed.md", 4), ("same.md", 4)])

    def test_a_tilde_fence_is_recognised(self) -> None:
        self.write("a.md", "~~~\n" + ODD_LINE + "~~~\n")
        self.assertClean()

    def test_an_indented_fence_is_recognised(self) -> None:
        # `^\s*` in FENCE_RE. A fence nested under a list item is indented, and
        # a delimiter read as prose is odd and reports itself - the same defect
        # the blockquote form had.
        self.write("a.md", "  " + FENCE + ODD_LINE + "  " + FENCE)
        self.assertClean()

    def test_a_fence_inside_two_blockquote_markers_is_recognised(self) -> None:
        # `(?:>\s*)*` repeats. With `?` in its place one marker is allowed and
        # two are not, which is the shape a quoted reply carries.
        self.write("a.md", "> > ```bash\n> > x\n> > ```\n")
        self.assertClean()


class TestEscapedBackticks(SweepTestCase):
    """Stripping removes BOTH failure modes; it does not trade one for the other.

    Counted raw, an escaped backtick flips a balanced line to odd - noise - and
    flips an unbalanced line to even, which is a MISS. The second test here is
    the one that matters, because it is the miss: delete the strip and THE
    SWEEP goes green on a file with a real wrapped marker in it, so the test
    goes RED. Both tests here go red under that mutation, which is the point of
    them; an earlier draft of this docstring, and 2bc0257's message, said the
    test goes green, which would make it the vacuous kind this file exists to
    rule out.

    f74e420's header did get the direction backwards - "the stripping trades
    the common noise for the rare miss". 8a0d33e's prose (mod repo) did NOT: it
    named both failure modes correctly and only implied a trade with the word
    "but", which is the distinction 6145832 (mod repo) drew and which an earlier
    draft here flattened back out.
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

    # THE SEVEN ARE WRITTEN OUT HERE, NOT READ BACK OUT OF S.EXTS. The first
    # version of the test below derived its fixtures AND its expectation from
    # `sorted(S.EXTS)`, which puts the same set on both sides: dropping `.mod`
    # from EXTS also dropped the fixture that would have caught it, and the
    # test stayed green. Four mutants survived the whole suite that way until
    # round 19 wrote them. A literal is the only form in which anything here
    # says "these seven", which is what bc_flavour.txt claims of the sweep.
    LISTED_EXTS = (".gui", ".info", ".md", ".mod", ".py", ".txt", ".yml")

    def test_every_listed_extension_is_actually_scanned(self) -> None:
        # One fixture per listed extension, each of which must report. Until
        # this test existed only `.txt` and `.md` were covered, so dropping
        # `.yml`, `.gui`, `.info`, `.mod` or `.py` from EXTS was a silent
        # narrowing - which flatly contradicts bc_flavour.txt's claim that the
        # sweep checks every commentable file.
        for i, ext in enumerate(self.LISTED_EXTS):
            self.write(f"f{i}{ext}", ODD_LINE)
        self.assertEqual(
            self.hits(),
            [(f"f{i}{ext}", 1) for i, ext in enumerate(self.LISTED_EXTS)],
        )

    def test_the_literal_list_above_is_the_one_the_sweep_declares(self) -> None:
        # On its own this restates a declaration and pins nothing about the
        # walk, which is why it is not the whole of the coverage. What it buys
        # is that the literal cannot drift out of step with EXTS in either
        # direction: an extension added to the sweep without a fixture beside
        # it fails HERE, naming the line to edit, instead of being scanned by
        # no test at all.
        self.assertEqual(S.EXTS, set(self.LISTED_EXTS))

    def test_a_bom_is_not_reported_as_part_of_the_line(self) -> None:
        # Every mod script file carries a UTF-8 BOM, so `utf-8-sig` is not
        # decoration. THE ASSERTION IS ON THE REPORTED TEXT, not on the line
        # number, because a BOM shifts neither the numbering nor the backtick
        # count - read as plain `utf-8` it survives into line 1 as U+FEFF,
        # which `str.strip()` does not remove, and the sweep then prints a line
        # that does not match what a grep for it would find.
        (self.root / "bom.txt").write_bytes(b"\xef\xbb\xbf" + ODD_LINE.encode("utf-8"))
        self.assertEqual(
            S.sweep(self.root), [("bom.txt", 1, ODD_LINE.strip())]
        )

    def test_a_file_that_is_not_utf8_is_skipped_rather_than_crashing(self) -> None:
        (self.root / "bad.txt").write_bytes(b"\xff\xfe an \x60 unbalanced line\n")
        self.assertClean()

    def test_a_file_that_cannot_be_opened_raises_out_of_the_sweep(self) -> None:
        # THE OTHER HALF OF THE `except` CLAUSE, and the half nothing pinned
        # until round 19: widening it to `(UnicodeDecodeError, OSError)` or to
        # `Exception` left the whole suite green, so 8a71ce1's headline fix
        # could be reverted without a red test. A sweep that quietly drops what
        # it could not read is the exact defect this tool exists to catch, one
        # level up, so the failure is loud on purpose. Injected through
        # `read_text` because making a real file unopenable needs an ACL this
        # account cannot set, and a test that skips where it is run pins
        # nothing.
        self.write("a.md", ODD_LINE)

        real_read = Path.read_text

        def read_text_that_is_denied(self_, *args, **kwargs):
            if self_.name == "a.md":
                raise PermissionError(13, "Permission denied")
            return real_read(self_, *args, **kwargs)

        with mock.patch.object(Path, "read_text", read_text_that_is_denied):
            with self.assertRaises(PermissionError):
                S.sweep(self.root)

    def test_an_entry_that_is_not_a_file_is_skipped(self) -> None:
        # os.walk puts anything that is not a directory into `filenames`,
        # including a broken symlink and a name deleted between the scandir and
        # the read. `read_text` on one raises FileNotFoundError, which the
        # sweep does not catch, so the `is_file()` guard is what stands between
        # that and a crash. Injected rather than symlinked for the reason
        # test_citations.py gives: creating a symlink on Windows needs a
        # privilege this account does not have, and a test that skips on the
        # only platform anyone runs it on pins nothing. PATCHED THROUGH A
        # CONTEXT MANAGER, not by assignment plus addCleanup: `S.os` is the
        # real os module, so a failure between the two statements leaves every
        # later test in the process walking the patched version.
        self.write("real.md", ODD_LINE)
        real_walk = S.os.walk

        def walk_with_a_ghost(top, *args, **kwargs):
            for dirpath, dirnames, filenames in real_walk(top, *args, **kwargs):
                if Path(dirpath) == self.root:
                    filenames = filenames + ["ghost.md"]
                yield dirpath, dirnames, filenames

        with mock.patch.object(S.os, "walk", walk_with_a_ghost):
            self.assertEqual(self.hits(), [("real.md", 1)])

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
    `validate` check.

    EVERY ASSERTION HERE IS POSITIVE OR PAIRED WITH ONE. An earlier version of
    this class held only shape checks over the hits and one `assertNotIn`, and
    it passed against a sweep that returned an empty list on this checkout and
    against one that had stopped reading Python at all - a pure negative is
    satisfied by any narrowing, including narrowing to nothing.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = Path(__file__).resolve().parents[2]
        cls.hits = S.sweep(cls.repo)

    def test_the_sweep_reports_something_over_the_real_checkout(self) -> None:
        # THE SILENT PARTNER FOR EVERY OTHER TEST IN THIS CLASS. The tree is
        # not clean, so a sweep that finds nothing here has broken, and no
        # tmpdir test above would notice: they all build the tree they read.
        # No count is asserted - the number drifts with every commit, and this
        # file's own rule is that a drifting count is not a fact.
        self.assertTrue(self.hits, "the sweep found nothing in a tree that is not clean")

    def test_the_hits_are_well_formed(self) -> None:
        for rel, lineno, line in self.hits:
            self.assertFalse(Path(rel).is_absolute(), rel)
            self.assertGreaterEqual(lineno, 1, rel)
            self.assertEqual(line, line.strip(), rel)
            self.assertEqual(
                (self.repo / rel).read_text(encoding="utf-8-sig").splitlines()[
                    lineno - 1
                ].strip(),
                line,
                f"{rel}:{lineno} does not hold the text reported for it",
            )

    def test_the_sweep_reads_python_and_markdown_alike(self) -> None:
        # Both extensions are in EXTS and both carry comment prose the rule
        # covers. Asserting that the sweep OPENED them, not that they are
        # clean: a narrowing of EXTS is invisible to a report that happens to
        # be empty for the narrowed type anyway.
        opened = set()
        real_read = Path.read_text

        def read_text_recording(self_, *args, **kwargs):
            opened.add(self_.suffix.lower())
            return real_read(self_, *args, **kwargs)

        with mock.patch.object(Path, "read_text", read_text_recording):
            S.sweep(self.repo)
        self.assertLessEqual({".py", ".md", ".txt"}, opened)

    def test_all_three_top_level_trees_are_swept(self) -> None:
        # ROUND 16'S REGRESSION, PINNED DIRECTLY. Adding just "docs" to PRUNE
        # left the whole suite green: `.md` still reaches the scanner through
        # CLAUDE.md at the root and through templates/, so "the sweep reads
        # markdown" does not cover it, and the harness's own PRUNE mutant only
        # dies because it prunes three directories at once. These are the three
        # the prose the rule governs actually lives in - docs/ the plans and
        # specs, mods/ the script comments, tools/ the Python.
        tops = {rel.split("/", 1)[0] for rel, _, _ in self.hits}
        for top in ("docs", "mods", "tools"):
            self.assertIn(top, tops, f"nothing reported anywhere under {top}/")

    def test_the_sweep_does_not_report_its_own_source(self) -> None:
        # sweep_backticks.py spells its backticks as escapes so that it does not
        # name itself on every run. Excluding it by name would be a carve-out of
        # the kind the rule exists to prevent, so this pins the escaping instead.
        # Paired with the test above, which is what stops a narrowed EXTS from
        # satisfying this one by never reading the file.
        reported = {rel for rel, _, _ in self.hits}
        self.assertNotIn("tools/sweep_backticks.py", reported)
        self.assertNotIn("tools/tests/test_sweep_backticks.py", reported)
        self.assertNotIn("tools/tests/mutate_sweep_backticks.py", reported)


class TestTheCommandLine(SweepTestCase):
    """`main()`, which nothing pinned until now.

    It matters more than its size suggests. The summary line it prints - whose
    wording is `--- unbalanced backtick lines:` followed by a count - IS the
    acceptance baseline this project quotes at itself between rounds, so a
    change to it invalidates every recorded baseline silently. That prefix is
    kept on one line here for the reason the whole rule exists: a grep target
    broken over a wrap is not a grep target.

    WHAT `run_main` DOES NOT EXERCISE: an encoder. `io.StringIO` accepts every
    character, and the real stdout on the only platform this is run on does
    not. `test_a_non_ascii_quotation_is_lost_to_a_cp1252_console` is the pin
    for that gap, and it pins the limit rather than a fix.
    """

    def run_main(self, argv: list[str]) -> str:
        real_argv = sys.argv
        sys.argv = ["sweep_backticks.py"] + argv
        self.addCleanup(setattr, sys, "argv", real_argv)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(S.main(), 0)
        return buf.getvalue()

    def test_the_summary_line_wording_and_count(self) -> None:
        self.write("a.md", ODD_LINE)
        self.write("b.md", ODD_LINE)
        out = self.run_main([str(self.root)])
        self.assertIn("--- unbalanced backtick lines: 2", out)

    def test_each_hit_prints_as_path_colon_line_colon_text(self) -> None:
        self.write("sub/a.md", ODD_LINE)
        out = self.run_main([str(self.root)])
        self.assertIn("sub/a.md:1: " + ODD_LINE.strip(), out)

    def test_a_long_line_is_truncated_in_the_report(self) -> None:
        # The report is meant to be read, so a 4000-character quotation must
        # not push the next hit off the screen. 110 characters, and the cut is
        # on the STRIPPED text - THE INDENT ON THE FIXTURE IS WHAT PINS THAT
        # HALF. Without it the two orders give the same 110 characters and the
        # sentence above is an unbacked claim; with it, cutting first spends
        # four of the 110 on whitespace and the second assertion names it.
        self.write("a.md", "    " + "x" * 400 + " \x60 open\n")
        out = self.run_main([str(self.root)])
        body = out.splitlines()[0].split(": ", 1)[1]
        self.assertEqual(len(body), 110)
        self.assertTrue(body.startswith("x"), repr(body[:8]))

    def test_a_non_ascii_quotation_is_lost_to_a_cp1252_console(self) -> None:
        # A LIMIT, PINNED AS ONE, NOT A FIX. Every other test in this class
        # writes into io.StringIO, which encodes nothing, so none of them says
        # anything about a real console. The Windows default is cp1252, and
        # `print` on a character it cannot encode raises out of main() - which
        # loses the SUMMARY LINE as well as the hit, so the run looks truncated
        # rather than failed. Nothing in either tree puts a non-ASCII character
        # inside a quoted span today. This is what makes the day one appears a
        # named failure instead of a mystery, and what has to be deleted by
        # whoever decides to reconfigure the stream instead.
        #
        # U+2192 AND NOT AN EM DASH: cp1252 HAS the em dash, at 0x97, so a
        # fixture built on one raises nothing and this test asserts an
        # exception that never comes. That is what the first draft did.
        self.write("a.md", "an \x60 unbalanced \u2192 line\n")
        real_argv = sys.argv
        sys.argv = ["sweep_backticks.py", str(self.root)]
        self.addCleanup(setattr, sys, "argv", real_argv)
        console = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", newline="")
        with contextlib.redirect_stdout(console):
            with self.assertRaises(UnicodeEncodeError):
                S.main()

    def test_with_no_argument_it_sweeps_the_working_directory(self) -> None:
        import os as real_os

        self.write("a.md", ODD_LINE)
        here = real_os.getcwd()
        real_os.chdir(self.root)
        self.addCleanup(real_os.chdir, here)
        out = self.run_main([])
        self.assertIn("a.md:1: ", out)
        self.assertIn("--- unbalanced backtick lines: 1", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
