"""Regression tests for the citation checker in ck3lib.validate.

WHY THIS FILE EXISTS. `_check_citations` and `_citation_files` have carried a
real defect in every review round since they were written, and each one was
found by hand-probing in a throwaway script that was then thrown away. Rounds
10 through 14 found, in order: bare citations resolved against the last full
citation on the line rather than the preceding one; a shadowed basename never
scanned as a citer; `.md` invisible because the walk fell back to SCRIPT_EXTS;
`tests/` invisible because the walk used SCAN_DIRS; a hyphenated `bc_` name
escaping the missing-file error; a mis-cased extension doing the same; and a
dropped `is_file()` guard turning a broken symlink into a traceback. Every one
of those is pinned below by the SHA that fixed it. The point is not coverage,
it is that the next round has to break a named test to reintroduce a defect
this project has already paid for once.

Run it with `python tools/tests/test_citations.py`. There is no pytest in this
environment on purpose - stdlib unittest keeps the test runnable from a clean
checkout with nothing installed.

WHAT THESE TESTS DO NOT COVER, and cannot: a citation that lands on a real,
non-blank line of the right file which is nonetheless the WRONG line. That is
the failure round 8 lost its headline to and no positional check can see it.
The countermeasure for that class is the naming rule in bc_flavour.txt, not
this file.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ck3lib import validate as V  # noqa: E402
from ck3lib.paths import load_config  # noqa: E402


class CitationTestCase(unittest.TestCase):
    """Builds a throwaway mod tree per test and runs the real checker on it."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="ck3_cite_"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def write(self, relpath: str, text: str) -> Path:
        path = self.root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def check(self) -> list[str]:
        """Every issue as `LEVEL path:line: message`, in report order."""
        issues: list[V.Issue] = []
        V._check_citations(self.root, issues)
        return [issue.format() for issue in issues]

    def citer_paths(self) -> list[str]:
        """Every file the walk offered to the scanner, in walk order.

        `_citation_files` returns three things and this is the third; naming it
        once here keeps `[2]` out of the tests, where it is unreadable and where
        reordering the tuple would silently change what they assert about.
        """
        return [relpath for relpath, _ in V._citation_files(self.root)[2]]

    def assertNoIssues(self) -> None:
        found = self.check()
        self.assertEqual(found, [], f"expected a clean tree, got {found}")

    def assertIssueMatching(self, needle: str) -> str:
        found = self.check()
        hits = [line for line in found if needle in line]
        self.assertEqual(len(hits), 1, f"expected exactly one issue containing {needle!r}, got {found}")
        return hits[0]


class TestPositionChecks(CitationTestCase):
    """Every kind of report the checker can emit, and the silences around them.

    The kinds are enumerated in validate.py under the paragraph named
    `WHAT THIS CHECKS IS POSITION, NOT MEANING`. There are more tests here than
    kinds, and deliberately: `}` alone needs two, one for a citation that STARTS
    on it and one for a range that ENDS on it, and the boundary cases each need
    a silent partner or the test cannot tell a working check from a check that
    fires on everything. If a new kind is added, add a test; if one of these
    stops firing, the checker regressed.
    """

    def setUp(self) -> None:
        super().setUp()
        self.write("common/bc_target.txt", "one\n\n#\n}\nfive\n")

    def test_blank_line(self) -> None:
        self.write("common/bc_citer.txt", "# see bc_target.txt:2\n")
        self.assertIssueMatching("bc_target.txt:2, which is ``")

    def test_bare_hash(self) -> None:
        self.write("common/bc_citer.txt", "# see bc_target.txt:3\n")
        self.assertIssueMatching("bc_target.txt:3, which is `#`")

    def test_closing_brace_as_range_start(self) -> None:
        self.write("common/bc_citer.txt", "# see bc_target.txt:4-5\n")
        self.assertIssueMatching("bc_target.txt:4, which is `}`")

    def test_closing_brace_as_range_end_is_allowed(self) -> None:
        # A range may legitimately END on the `}` that closes the block it
        # spans. Only a range STARTING there names nothing.
        self.write("common/bc_citer.txt", "# see bc_target.txt:1-4\n")
        self.assertNoIssues()

    def test_past_end_of_file(self) -> None:
        self.write("common/bc_citer.txt", "# see bc_target.txt:9\n")
        self.assertIssueMatching("bc_target.txt:9, past the end of that file (5 lines)")

    def test_below_line_one(self) -> None:
        self.write("common/bc_citer.txt", "# see bc_target.txt:0\n")
        self.assertIssueMatching("bc_target.txt:0, and there is no line 0")

    def test_backwards_range(self) -> None:
        self.write("common/bc_citer.txt", "# see bc_target.txt:5-1\n")
        self.assertIssueMatching("bc_target.txt:5-1, which runs backwards")

    def test_range_ending_in_zero_is_backwards_not_absent(self) -> None:
        # THE SPELLING THIS PINS IS THE GUARD, NOT THE LOOP. `resolve` has two
        # `end is not None` tests. The one that matters is the backwards guard
        # above the loop: under `if end:` a `-0` range is read as a range with
        # no end and falls through silently, which is what shipped. The loop's
        # copy is defensive only - by the time control reaches it end >= start
        # >= 1, so the two spellings cannot differ there, and mutating the loop
        # alone leaves this test green. Mutating the guard turns it red.
        self.write("common/bc_citer.txt", "# see bc_target.txt:1-0\n")
        self.assertIssueMatching("bc_target.txt:1-0, which runs backwards")

    def test_missing_mod_file(self) -> None:
        self.write("common/bc_citer.txt", "# see bc_absent.txt:1\n")
        self.assertIssueMatching("cites `bc_absent.txt`, which this mod does not contain")

    def test_ambiguous_basename_warns_once(self) -> None:
        self.write("common/bc_dup.txt", "a\n")
        self.write("events/bc_dup.txt", "a\n")
        self.write("common/bc_citer.txt", "# see bc_dup.txt:1\n# and bc_dup.txt:1\n")
        line = self.assertIssueMatching("a basename more than one file in this mod has")
        self.assertTrue(line.startswith("WARN "), line)

    def test_ambiguous_basename_suppresses_the_range_check(self) -> None:
        # Which of the colliding files wins the `texts` slot is deliberately
        # not observable: the ambiguity branch returns before `texts` is read.
        # This is why the walk sorts only for issue-order stability.
        self.write("common/bc_dup.txt", "a\n")
        self.write("events/bc_dup.txt", "a\nb\nc\nd\n")
        self.write("common/bc_citer.txt", "# see bc_dup.txt:4\n")
        found = self.check()
        self.assertEqual(len(found), 1, found)
        self.assertIn("a basename more than one file", found[0])

    def test_a_valid_citation_is_silent(self) -> None:
        self.write("common/bc_citer.txt", "# see bc_target.txt:1 and bc_target.txt:5\n")
        self.assertNoIssues()


class TestBareContinuations(CitationTestCase):
    """`effects.log:9770 (grudge), :9810 (nemesis)` is a real line in this mod.

    A bare `:N` belongs to whatever file was named BEFORE it on the line.
    Round 10 (ec8eced) found the checker matching full citations and bare ones
    in two separate passes, so a bare `:N` resolved against the LAST full
    citation on the line rather than the preceding one - wrong in both
    directions, and live on README.md at the time.
    """

    def setUp(self) -> None:
        super().setUp()
        self.write("common/bc_short.txt", "one\n")
        self.write("common/bc_long.txt", "\n".join(str(n) for n in range(1, 21)) + "\n")

    def test_bare_resolves_against_the_preceding_file(self) -> None:
        # `:15` follows bc_long.txt and precedes bc_short.txt. It is valid in
        # bc_long.txt. A two-pass implementation resolves it against
        # bc_short.txt and reports a false "past the end".
        self.write("common/bc_citer.txt", "# bc_long.txt:1, :15 then bc_short.txt:1\n")
        self.assertNoIssues()

    def test_bare_after_the_last_file_is_still_caught(self) -> None:
        self.write("common/bc_citer.txt", "# bc_long.txt:1 then bc_short.txt:1, :15\n")
        self.assertIssueMatching("bc_short.txt:15, past the end of that file (1 lines)")

    def test_an_unresolvable_target_clears_the_running_file(self) -> None:
        # Clearing is POSITIONAL. `00_vanilla.txt` is not in this mod, so the
        # bare `:99` after it belongs to nothing and must not be resolved
        # against bc_long.txt. THE NUMBER IS 99 AND NOT 15 ON PURPOSE: 15 is a
        # real line of bc_long.txt, so a build that failed to clear would
        # resolve it happily and the test would pass without testing anything.
        # 99 is off the end of that 20-line file, so failing to clear reports.
        self.write("common/bc_citer.txt", "# bc_long.txt:1 then 00_vanilla.txt:47, :99\n")
        self.assertNoIssues()

    def test_a_target_outside_cite_exts_clears_the_running_file(self) -> None:
        # THE BROAD PATTERN EXISTS FOR THIS. `effects.log:9770 (grudge), :9810
        # (nemesis)` is a real line of bc_rivalry_effects.txt. `.log` is not in
        # CITE_EXTS, so ANY_CITE_RE matches it and RESOLVABLE_CITE_RE does not;
        # the match still has to clear `current`, or the bare `:9810` would
        # resolve against whatever mod file was named earlier on the line.
        # Narrowing ANY_CITE_RE to CITE_EXTS makes this fail: the `.log` match
        # disappears, and `:99` attaches to bc_long.txt.
        self.write("common/bc_citer.txt", "# bc_long.txt:1 then effects.log:9770, :99\n")
        self.assertNoIssues()

    def test_an_ambiguous_target_clears_the_running_file(self) -> None:
        # THE THIRD CLEARING SITE, and it was the one no test reached. Mutating
        # `current = None` out of the ambiguous branch left the whole suite
        # green until this was written; the other two branches each had a test
        # already. An ambiguous basename is deliberately left unresolved, so a
        # bare `:99` behind one has no file and must resolve against nothing -
        # not against bc_long.txt, which is merely the last file that DID
        # resolve. The warning about the basename is expected and asserted; the
        # `:99` error is the regression.
        self.write("common/bc_dup.txt", "a\n")
        self.write("events/bc_dup.txt", "a\n")
        self.write("common/bc_citer.txt", "# bc_long.txt:1 then bc_dup.txt:1, :99\n")
        self.assertIssueMatching("cites `bc_dup.txt`, a basename more than one file in this mod has")
        self.assertEqual(len(self.check()), 1, self.check())

    def test_a_loc_key_is_not_read_as_a_bare_citation(self) -> None:
        # `(?<![\w.])` on BARE_CITE_RE: without it `bc_frag_x:0` matched as a
        # bare `:0` and resolved against the file named before it.
        #
        # THE KEY IS ON A COMMENT LINE, and it has to be. A `.yml` line that
        # does not start with `#` is skipped whole before any regex runs, so
        # the first draft of this test - which put the key on a real loc line,
        # where it naturally lives - passed against a build with the lookbehind
        # deleted. Putting a key-shaped token in a comment is artificial; the
        # thing under test is the regex, and this is the only way to reach it.
        self.write("common/bc_citer.txt", "# bc_long.txt:1, and the key bc_frag_x:0 renders it\n")
        self.assertNoIssues()


class TestWalkCoverage(CitationTestCase):
    """Three rounds running found a file the walk could not see.

    fc6792f a root-level file, ec8eced a basename shadowed by another file's,
    d904308 any `.md` at all. Then 58fbc23 found `tests/`, allowed by
    `_check_structure` and absent from SCAN_DIRS, and stopped enumerating the
    exceptions: the extension is now the only filter, and these pin that it
    stays that way. 6c17af4 added the `.git` prune on top; ddd1ac9 restored the
    `is_file()` guard that the switch to os.walk had dropped.
    """

    def test_a_directory_outside_scan_dirs_is_visible_both_ways(self) -> None:
        self.write("tests/bc_helper.txt", "a\nb\n")
        self.write("common/bc_citer.txt", "# see bc_helper.txt:2\n")
        self.assertNoIssues()
        citers = self.citer_paths()
        self.assertIn("tests/bc_helper.txt", citers)

    def test_a_root_level_file_is_visible_both_ways(self) -> None:
        self.write("README.md", "cites bc_target.txt:1\n")
        self.write("common/bc_target.txt", "a\n")
        self.assertNoIssues()
        citers = self.citer_paths()
        self.assertIn("README.md", citers)

    def test_markdown_below_a_scan_dir_is_visible(self) -> None:
        self.write("common/notes.md", "cites bc_absent.txt:1\n")
        self.assertIssueMatching("cites `bc_absent.txt`, which this mod does not contain")

    def test_a_shadowed_basename_is_still_scanned_as_a_citer(self) -> None:
        # Keying the citer side by basename meant the second file to claim a
        # shared basename was never scanned for its OWN outgoing citations.
        self.write("common/bc_dup.txt", "a\n")
        self.write("events/bc_dup.txt", "# see bc_elsewhere.txt:1\n")
        self.assertIssueMatching("cites `bc_elsewhere.txt`, which this mod does not contain")

    def test_git_is_pruned_at_any_depth(self) -> None:
        self.write(".git/bc_target.txt", "a\n")
        self.write("common/.git/bc_target.txt", "a\n")
        self.write("common/bc_citer.txt", "# see bc_target.txt:1\n")
        # Neither copy registers, so the citation reports missing rather than
        # ambiguous.
        self.assertIssueMatching("cites `bc_target.txt`, which this mod does not contain")
        # And the pruning is what does it, not a per-path filter afterwards:
        # nothing under a `.git` appears on the citer side either. Without the
        # first assertion this one passes against a build that opens every git
        # object and then discards it, which is the slow shape 58fbc23 replaced.
        citers = self.citer_paths()
        self.assertEqual([p for p in citers if ".git/" in p], [])

    def test_an_unopenable_entry_is_skipped_rather_than_crashing(self) -> None:
        # os.walk puts anything that is not a directory into `filenames`,
        # including a broken symlink, and `read_text` calls `read_bytes` with
        # no handler. Dropping the `is_file()` guard turned a skipped entry
        # into a FileNotFoundError out of `validate`.
        #
        # The name is injected rather than symlinked because creating a
        # symlink on Windows needs a privilege this account does not have, and
        # a test that skips on the only platform anyone runs it on pins
        # nothing. Injection covers exactly one other case besides the broken
        # symlink: the file being deleted between the scandir and the read,
        # which raises ENOENT and which `Path.is_file()` swallows. It does NOT
        # cover an unreadable file. `Path.is_file()` ignores only ENOENT,
        # ENOTDIR, EBADF and ELOOP, so EACCES propagates out of the guard and
        # out of `validate`. That case is unhandled, deliberately: a mod folder
        # this process cannot read is a broken checkout, not a file to skip.
        self.write("common/bc_citer.txt", "# see bc_citer.txt:1\n")
        real_walk = V.os.walk

        def walk_with_a_ghost(top, *args, **kwargs):
            for dirpath, dirnames, filenames in real_walk(top, *args, **kwargs):
                if Path(dirpath).name == "common":
                    filenames = list(filenames) + ["bc_ghost.txt"]
                yield dirpath, dirnames, filenames

        with mock.patch.object(V.os, "walk", walk_with_a_ghost):
            self.assertNoIssues()

    def test_a_broken_symlink_is_skipped_rather_than_crashing(self) -> None:
        # The real-world version of the test above, run only where the OS
        # allows it. Kept because injection proves the guard, not the premise
        # that os.walk really does list a broken link as a file.
        link = self.root / "common" / "bc_ghost.txt"
        link.parent.mkdir(parents=True, exist_ok=True)
        try:
            link.symlink_to(self.root / "common" / "does_not_exist.txt")
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlinks unavailable here: {exc}")
        self.write("common/bc_citer.txt", "# nothing to see\n")
        self.assertNoIssues()

    def test_the_walk_order_is_sorted_and_parents_lead(self) -> None:
        # ASSERTS THE ORDER, NOT MERELY THAT IT REPEATS. The first version of
        # this test called `_citation_files` five times and compared the results
        # to each other, which passes on an unsorted walk too - os.walk hands
        # back the same directory in the same order twice running on one
        # filesystem, so repetition proves nothing. What the sorting buys is a
        # report order that is the same across MACHINES, and only a literal
        # pins that.
        #
        # A directory's own files come before its subdirectories, because
        # os.walk yields the directory before it descends. That is why
        # root-level README.md leads rather than trails, and it is a different
        # order from the `sorted(rglob("*"))` this replaced.
        for name in ("zz", "aa"):
            self.write(f"common/sub/bc_{name}.txt", "a\n")
        self.write("common/bc_mid.txt", "a\n")
        self.write("events/bc_ev.txt", "a\n")
        self.write("README.md", "a\n")
        # TWO SIBLING DIRECTORIES, because one cannot show a directory ordering.
        # With only `common/` present, reversing the `dirnames` sort changed
        # nothing and the mutation survived.
        self.assertEqual(
            self.citer_paths(),
            [
                "README.md",
                "common/bc_mid.txt",
                "common/sub/bc_aa.txt",
                "common/sub/bc_zz.txt",
                "events/bc_ev.txt",
            ],
        )


class TestNameMatching(CitationTestCase):
    """Two escapes, both from a narrow pattern the broad one did not match.

    A `bc_` file that does not exist must produce the error whatever its name
    looks like. It escaped once for a hyphen (58fbc23 fixed the stem) and once
    for its case (6c17af4 fixed the extension group and the prefix test).

    EVERY SHA IN THIS FILE IS A TOOLING-REPO SHA. The mod is a second git repo
    under `mods/`, and a SHA that resolves there does not resolve here - this
    paragraph named `a283d54`, a mod commit, for exactly that reason.
    """

    def test_a_hyphenated_missing_name_still_errors(self) -> None:
        self.write("common/bc_citer.txt", "# see bc_missing-2.txt:1\n")
        self.assertIssueMatching("cites `bc_missing-2.txt`, which this mod does not contain")

    def test_a_mis_cased_extension_still_errors(self) -> None:
        self.write("common/bc_citer.txt", "# see BC_T.TXT:1\n")
        self.assertIssueMatching("cites `BC_T.TXT`, which this mod does not contain")

    def test_a_mis_cased_stem_still_errors(self) -> None:
        # CK3 is case-sensitive on Linux, so a mis-cased citation of a file
        # that DOES exist is a real defect, not a Windows-only nicety.
        self.write("common/bc_target.txt", "a\n")
        self.write("common/bc_citer.txt", "# see BC_TARGET.txt:1\n")
        self.assertIssueMatching("cites `BC_TARGET.txt`, which this mod does not contain")

    def test_a_non_mod_missing_file_is_silent(self) -> None:
        # The checker only claims to know about this mod's own files.
        self.write("common/bc_citer.txt", "# see 00_court_poet_tasks.txt:47\n")
        self.assertNoIssues()

    def test_a_time_is_not_a_citation(self) -> None:
        self.write("common/bc_citer.txt", "# ran at 12:30 and took 4:05\n")
        self.assertNoIssues()


class TestProseScanning(CitationTestCase):
    """In markdown every line is prose; in script only `#` lines are.

    Restricting `.md` to `#`-prefixed lines reduces README.md to heading text,
    which is how round 9 shipped a citation checker that could not read the
    largest body of prose in the mod. A blank line ends a paragraph there.
    """

    def test_markdown_body_text_is_scanned(self) -> None:
        self.write("README.md", "Some prose citing bc_absent.txt:1 inline.\n")
        self.assertIssueMatching("cites `bc_absent.txt`, which this mod does not contain")

    def setUp(self) -> None:
        super().setUp()
        # 20 lines, so `:99` is off the end of it and `:15` is not. EVERY
        # PARAGRAPH-RESET TEST BELOW USES 99. With 15 the bare citation resolves
        # cleanly whether or not the reset happened, and the test passes against
        # a build with the reset deleted - which is how the markdown one shipped.
        self.write("common/bc_long.txt", "\n".join(str(n) for n in range(1, 21)) + "\n")

    def test_a_blank_line_ends_the_running_file_in_markdown(self) -> None:
        self.write("README.md", "See bc_long.txt:1\n\n:99\n")
        self.assertNoIssues()

    def test_a_bare_hash_ends_the_running_file_in_script(self) -> None:
        # The house style separates comment paragraphs with a bare `#`, and a
        # running target must not cross one - the marker differs from
        # markdown's blank line, the rule does not.
        self.write("common/bc_citer.txt", "# See bc_long.txt:1\n#\n# and :99\n")
        self.assertNoIssues()

    def test_a_code_line_ends_the_running_file_in_script(self) -> None:
        self.write("common/bc_citer.txt", "# See bc_long.txt:1\nfoo = { }\n# and :99\n")
        self.assertNoIssues()

    def test_a_running_target_does_carry_across_comment_lines(self) -> None:
        # The partner to the two above. Without it they pass against a build
        # that resets `current` on every line, which would disable bare
        # continuations entirely rather than scope them.
        self.write("common/bc_citer.txt", "# See bc_long.txt:1\n# and :99\n")
        self.assertIssueMatching("bc_long.txt:99, past the end of that file (20 lines)")

    def test_non_comment_script_lines_are_not_scanned(self) -> None:
        # A loc value or an effect body may contain anything; only comments
        # carry citations in script files.
        self.write("common/bc_citer.txt", 'desc = "bc_absent.txt:1"\n')
        self.assertNoIssues()

    def test_gui_and_info_files_are_scanned_as_script(self) -> None:
        # `.gui` and `.info` are in CITE_EXTS and nothing else here touches
        # them. They are script, not prose: comment lines only.
        self.write("gui/bc_widget.gui", "# see bc_absent_a.txt:1\n")
        self.write("bc_notes.info", "# see bc_absent_b.txt:1\n")
        found = self.check()
        self.assertEqual(len(found), 2, found)
        self.assertIssueMatching("cites `bc_absent_a.txt`, which this mod does not contain")
        self.assertIssueMatching("cites `bc_absent_b.txt`, which this mod does not contain")


class TestAgainstTheRealMod(unittest.TestCase):
    """The mod itself must stay clean, and the checker must see all of it.

    A checker that reports nothing because it walked nothing looks identical
    to a clean mod from the validator's output alone. This asserts it opened
    a plausible number of files and found the ones that matter.
    """

    mod_root = Path(__file__).resolve().parents[2] / "mods" / "battle_chronicles"

    def setUp(self) -> None:
        if not self.mod_root.is_dir():
            self.skipTest(f"{self.mod_root} not present")

    def test_the_mod_has_no_citation_issues(self) -> None:
        issues: list[V.Issue] = []
        V._check_citations(self.mod_root, issues)
        self.assertEqual([issue.format() for issue in issues], [])

    def test_the_walk_reaches_the_files_that_matter(self) -> None:
        texts, ambiguous, citers = V._citation_files(self.mod_root)
        relpaths = {relpath for relpath, _ in citers}
        self.assertIn("README.md", relpaths)
        self.assertIn("common/customizable_localization/bc_flavour.txt", relpaths)
        self.assertIn("localization/english/bc_l_english.yml", relpaths)
        self.assertEqual(ambiguous, set())
        self.assertGreater(len(texts), 10)
        self.assertFalse([relpath for relpath in relpaths if ".git/" in relpath])

    def test_validate_mod_actually_calls_the_citation_check(self) -> None:
        # EVERY OTHER TEST HERE CALLS `_check_citations` DIRECTLY, so all of
        # them pass against a `validate_mod` that never calls it - the check
        # would be dead code and the suite would be green. This is the one
        # assertion that the wiring exists.
        #
        # Asserting the call rather than an error string, because producing a
        # citation error from the real mod means writing a broken citation into
        # it, and the mod is the thing under `test_the_mod_has_no_citation_issues`
        # two methods up. `--strict` is not passed: the citation check runs on
        # every validate, and pinning that is half the point.
        cfg = load_config()
        with mock.patch.object(V, "_check_citations", wraps=V._check_citations) as spy:
            V.validate_mod(cfg, self.mod_root)
        self.assertEqual(spy.call_count, 1)
        self.assertIs(spy.call_args.args[0], self.mod_root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
