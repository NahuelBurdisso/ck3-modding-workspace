"""Mutation harness for tools/tests/test_sweep_backticks.py.

WHY THIS IS A FILE AND NOT A SHELL LOOP. The thing it checks - that a test
actually fails when the behaviour it names is broken - is worth nothing if the
harness itself is retyped from memory each time it is wanted. That is the exact
history of the sweep this harness points at: it was a `grep` one-liner, it was
retyped in every review round, and every retyping was wrong in a new way.
f74e420 made the sweep a file for that reason and 8a71ce1 corrected it; this is
the same move one level up.

WHAT IT PROVES. Rounds 15 and 16 both found tests in test_citations.py that
passed against a build with the checked behaviour deleted. A test that cannot
fail is not a test, and reading one does not tell you which kind it is. Each
entry below anchors on ONE line of sweep_backticks.py and the run records which
tests go red. AN ENTRY IS ONE ANCHOR AND NOT ONE LINE OF OUTPUT: the entry named
`report: at most one line per file` puts a second line back in place of the one
it matched, and the anchor is what has to be unique, not the replacement. A
SURVIVING MUTANT NAMES A VACUOUS TEST, or a behaviour nothing pins at all.

WHAT IT DOES NOT PROVE, and what its first version was read as proving: that
every test pins the behaviour ITS NAME CLAIMS. "Every test is killed by at
least one mutant" is a property of the SUITE. Round 18 held that property while
behaviours of the sweep had no mutant here at all - the fence exit, the
`is_file()` guard, BOM handling, most of the extension list, and the whole of
`main()` - and while two tests were weaker than their names. Round 19 held it
again, over a longer list, while dropping any one of four extensions and while
pruning the docs tree alone both went undetected, and while the paragraph named
`AN UNREADABLE FILE IS NOT SKIPPED` had nothing behind it at all.

THE LIST BELOW IS THE CLAIM. It is only as good as its coverage of the file it
points at, so a behaviour added to sweep_backticks.py without an entry here is
unpinned no matter what this run prints. TWO SHAPES OF ENTRY ARE WORTH DRAFTING
FOR THAT REASON: break each element of a collection SINGLY as well as wholesale
- a mutant that empties EXTS or that prunes three directories at once dies to
almost anything, and it is the single drop that finds a test deriving its
expectation from the thing it is checking.

THE MECHANISM IS NOT HERE. Apply, run, restore and report live in `mutate.py`
beside this file, and so does the reasoning for them - the byte-level restore,
the mandatory `PYTHONDONTWRITEBYTECODE`, why a non-zero exit is not a kill, and
why this is never run as part of a batch. It was moved there when a second
harness needed it: a copy of a mechanism that has already been got wrong twice
is a copy of both mistakes, and it drifts silently besides.

SOME MUTATIONS ARE DELIBERATELY ABSENT, and they are written down here so that
their absence is a decision rather than an oversight. NO COUNT IS GIVEN FOR
THEM: round 20's draft said TWO and was short the same round it was written.
Dropping `.resolve()` from `main()` survives because every path a test hands it
is already absolute. A `sub(..., count=N)` at or above the width of the suite's
escape ramp survives because no fixture is wide enough to see it, and no finite
fixture ever closes that. Adding either would put a permanent survivor in this
list and train the reader to skim the result, which is the failure the whole
file is arranged against.

WHAT WAS ABSENT ON A FALSE PREMISE, and is now present: deleting `filenames.sort()`.
That one was recorded as a decision, on the grounds that NTFS returns entries in
name order anyway. NTFS collates uppercased and case-insensitively, which is not
Python's order, so it was observable all along and was not observed. A premise
nobody checked is how a coverage gap gets written down as a choice.

THE dirnames SORT WAS A DIFFERENT AND PLAINER GAP: nothing recorded it, it was
simply missing, and both are present now. 1af8901 described the two as one thing
- "deleting either sort ... was recorded as a decision" - in this file, in the
suite and in two commit messages, which is a misdescription of a past commit
inside the commit that exists to correct one.

THE SAME COMMIT MISCOUNTED THIS LIST. 1af8901's message says "44 entries"; the
list it shipped holds 43. NO CORRECTED NUMBER IS WRITTEN HERE, and that is the
point rather than an evasion: a number in prose beside a list that grows is
wrong at the next commit, and this file already refuses to count its own
deliberate absences for that reason. `len(MUTANTS)` is the only place the answer
should be read from, and `mutate.py` prints it on the baseline line.

Run it with `python tools/tests/mutate_sweep_backticks.py`. Exit 0 means every
mutant was killed.
"""

from __future__ import annotations

from pathlib import Path

from mutate import run_mutants

TOOLS = Path(__file__).resolve().parents[1]
TARGET = TOOLS / "sweep_backticks.py"
SUITE = TOOLS / "tests" / "test_sweep_backticks.py"

# Each entry is (name, exact text to find, text to put in its place). The anchor
# is matched literally and exactly once; a miss is reported rather than skipped,
# because a mutation that was never applied looks identical to one that was
# killed if you only watch the exit status.
MUTANTS = [
    (
        "fence: drop the blockquote allowance",
        r'FENCE_RE = re.compile(r"^\s*(?:>\s*)*(?:\x60{3}|~{3})")',
        r'FENCE_RE = re.compile(r"^\s*(?:\x60{3}|~{3})")',
    ),
    (
        "fence: drop the tilde form",
        r'FENCE_RE = re.compile(r"^\s*(?:>\s*)*(?:\x60{3}|~{3})")',
        r'FENCE_RE = re.compile(r"^\s*(?:>\s*)*(?:\x60{3})")',
    ),
    (
        "fence: never enter the fenced state",
        "                    fenced = not fenced",
        "                    fenced = False",
    ),
    (
        "escape: count escaped backticks raw",
        'if ESCAPED_BACKTICK_RE.sub("", line).count(BACKTICK) % 2:',
        "if line.count(BACKTICK) % 2:",
    ),
    # THE TRUNCATED STRIP, AT THREE DEPTHS. One entry is not enough here and
    # round 20 shipped one: `count=1` died against a two-escape fixture while
    # `count=2` sailed through it, and `count=2` was the worse mutant, because
    # at two the real trees cannot see it either - no line of either carries
    # more than two escapes, so the report is byte-identical and so is the
    # acceptance total. What kills these is the RAMP of escape counts in the
    # suite, and a count at or above the ramp's width would survive; 7 is here
    # because it is the largest the ramp still beats, and adding an 8 would put
    # a permanent survivor in this list.
    (
        "escape: strip only the FIRST escaped backtick on a line",
        'if ESCAPED_BACKTICK_RE.sub("", line).count(BACKTICK) % 2:',
        'if ESCAPED_BACKTICK_RE.sub("", line, count=1).count(BACKTICK) % 2:',
    ),
    (
        "escape: strip only the first TWO escaped backticks on a line",
        'if ESCAPED_BACKTICK_RE.sub("", line).count(BACKTICK) % 2:',
        'if ESCAPED_BACKTICK_RE.sub("", line, count=2).count(BACKTICK) % 2:',
    ),
    (
        "escape: strip only the first SEVEN escaped backticks on a line",
        'if ESCAPED_BACKTICK_RE.sub("", line).count(BACKTICK) % 2:',
        'if ESCAPED_BACKTICK_RE.sub("", line, count=7).count(BACKTICK) % 2:',
    ),
    (
        "parity: report every line that carries a backtick",
        'if ESCAPED_BACKTICK_RE.sub("", line).count(BACKTICK) % 2:',
        'if ESCAPED_BACKTICK_RE.sub("", line).count(BACKTICK):',
    ),
    (
        "parity: report every line, backtick or not",
        'if ESCAPED_BACKTICK_RE.sub("", line).count(BACKTICK) % 2:',
        "if True:",
    ),
    (
        "walk: match extensions case-sensitively",
        "if (path.suffix.lower() not in EXTS and name not in NAMES) or not path.is_file():",
        "if (path.suffix not in EXTS and name not in NAMES) or not path.is_file():",
    ),
    (
        "walk: accept every extension",
        "if (path.suffix.lower() not in EXTS and name not in NAMES) or not path.is_file():",
        "if not path.is_file():",
    ),
    # THE NAMES ARM, BOTH WAYS. Dropping it puts the extensionless dotfiles
    # back out of reach - `Path(".gitattributes").suffix` is "", so no spelling
    # of EXTS substitutes for it - and lowercasing it widens an allowlist whose
    # members are fixed by git and never appear mis-cased.
    (
        "walk: stop reading the dotfiles no extension can reach",
        "if (path.suffix.lower() not in EXTS and name not in NAMES) or not path.is_file():",
        "if path.suffix.lower() not in EXTS or not path.is_file():",
    ),
    (
        "walk: match a dotfile name case-insensitively",
        "and name not in NAMES) or not path.is_file():",
        "and name.lower() not in NAMES) or not path.is_file():",
    ),
    (
        "walk: filter nothing, prune nothing",
        "dirnames[:] = sorted(d for d in dirnames if d not in PRUNE)",
        "dirnames[:] = sorted(dirnames)",
    ),
    (
        "walk: reverse the directory order",
        "dirnames[:] = sorted(d for d in dirnames if d not in PRUNE)",
        "dirnames[:] = sorted((d for d in dirnames if d not in PRUNE), reverse=True)",
    ),
    (
        "walk: reverse the file order",
        "        filenames.sort()",
        "        filenames.reverse()",
    ),
    # THE TWO SORTS DELETED OUTRIGHT. Round 20 wrote the filenames one down as
    # deliberately absent on the grounds that NTFS hands entries back in name
    # order anyway; it never mentioned the dirnames one at all. NTFS does not
    # hand them back in PYTHON's name order: it collates uppercased and
    # case-insensitively, so os.walk offers ["a.md", "B.md"] where `sorted`
    # gives ["B.md", "a.md"]. Both die against the mixed-case fixture in the
    # suite; the single-case fixtures beside it cannot see either.
    (
        "walk: stop sorting filenames",
        "        filenames.sort()",
        "        pass",
    ),
    (
        "walk: stop sorting directories",
        "dirnames[:] = sorted(d for d in dirnames if d not in PRUNE)",
        "dirnames[:] = [d for d in dirnames if d not in PRUNE]",
    ),
    (
        "decode: let a non-utf8 file raise",
        "            except UnicodeDecodeError:",
        "            except ZeroDivisionError:",
    ),
    (
        "report: an absolute path instead of a relative one",
        "rel = path.relative_to(root).as_posix()",
        "rel = path.as_posix()",
    ),
    (
        "report: at most one line per file",
        "                    hits.append((rel, lineno, line.strip()))",
        "                    hits.append((rel, lineno, line.strip()))\n                    break",
    ),
    (
        "report: drop the line number",
        "                    hits.append((rel, lineno, line.strip()))",
        "                    hits.append((rel, 1, line.strip()))",
    ),
    (
        "report: keep the leading whitespace",
        "                    hits.append((rel, lineno, line.strip()))",
        "                    hits.append((rel, lineno, line))",
    ),
    # From here down are the gaps rounds 18 and 19 found: behaviours of the
    # sweep that no test and no mutant touched, so that "every test is killed"
    # was true of the suite while separate behaviours were unpinned. NO COUNT
    # IS GIVEN. The first version of this comment said "the nine below" when
    # there were ten, which is the drifting-count defect this project's own
    # rules forbid and which round 19 caught in the file that polices it.
    (
        "fence: enter but never leave the fenced state",
        "                    fenced = not fenced",
        "                    fenced = True",
    ),
    (
        "fence: require the delimiter at column zero",
        r'FENCE_RE = re.compile(r"^\s*(?:>\s*)*(?:\x60{3}|~{3})")',
        r'FENCE_RE = re.compile(r"^(?:>\s*)*(?:\x60{3}|~{3})")',
    ),
    (
        "fence: allow at most one blockquote marker",
        r'FENCE_RE = re.compile(r"^\s*(?:>\s*)*(?:\x60{3}|~{3})")',
        r'FENCE_RE = re.compile(r"^\s*(?:>\s*)?(?:\x60{3}|~{3})")',
    ),
    (
        "walk: drop the is_file guard",
        "if (path.suffix.lower() not in EXTS and name not in NAMES) or not path.is_file():",
        "if (path.suffix.lower() not in EXTS and name not in NAMES):",
    ),
    (
        "decode: stop stripping the BOM",
        'lines = path.read_text(encoding="utf-8-sig").splitlines()',
        'lines = path.read_text(encoding="utf-8").splitlines()',
    ),
    (
        # `splitlines` also breaks on \v, \f, \x1c, \x1d, \x1e, \x85, U+2028
        # and U+2029, which is why the reported number is not always grep's.
        # Nothing pinned that until round 21 and this mutant survived.
        "decode: break lines on the newline alone",
        'lines = path.read_text(encoding="utf-8-sig").splitlines()',
        'lines = path.read_text(encoding="utf-8-sig").split("\\n")',
    ),
    (
        "walk: stop reading Python",
        '".md", ".mod", ".py"}',
        '".md", ".mod"}',
    ),
    # ONE MUTANT PER LISTED NAME, dropped singly, for the reason the extension
    # block above records: a wholesale empty set dies to almost anything, and
    # it is the single drop that finds a test taking its fixtures from the set
    # it is checking. The widening is here too, because an allowlist has no
    # other way to go wrong.
    (
        "walk: stop reading .gitattributes",
        '{".gitattributes", ',
        "{",
    ),
    (
        "walk: stop reading .gitignore",
        ', ".gitignore"}',
        "}",
    ),
    (
        "walk: read any dotfile git happens to own",
        'NAMES = {".gitattributes", ".gitignore"}',
        'NAMES = {".gitattributes", ".gitignore", ".gitmodules"}',
    ),
    (
        "walk: prune the three directories the real tree keeps its prose in",
        'PRUNE = {".git", "__pycache__"}',
        'PRUNE = {".git", "__pycache__", "docs", "mods", "tools"}',
    ),
    (
        "main: reword the summary line",
        'print(f"--- unbalanced backtick lines: {len(hits)}")',
        'print(f"--- total: {len(hits)}")',
    ),
    (
        "main: stop truncating a long quotation",
        'print(f"{rel}:{lineno}: {line[:110]}")',
        'print(f"{rel}:{lineno}: {line}")',
    ),
    (
        "main: ignore the path argument",
        'root = (Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")).resolve()',
        'root = Path(".").resolve()',
    ),
    # ONE MUTANT PER LISTED EXTENSION, dropped singly - and the header means
    # every one of them, which the first version did not: it said "one per
    # extension" over a block that left `.txt` and `.md` out. "walk: stop
    # reading Python" above is not enough on its own, because the test it kills
    # used to derive both its fixtures and its expectation from S.EXTS, so
    # shrinking EXTS shrank the fixture set with it and every single drop but
    # that one survived the whole suite.
    (
        "walk: stop reading script",
        'EXTS = {".txt",',
        'EXTS = {',
    ),
    (
        "walk: stop reading markdown",
        '".info", ".md",',
        '".info",',
    ),
    (
        "walk: stop reading loc",
        '{".txt", ".yml",',
        '{".txt",',
    ),
    (
        "walk: stop reading gui",
        '".yml", ".gui",',
        '".yml",',
    ),
    (
        "walk: stop reading the descriptor",
        '".gui", ".info",',
        '".gui",',
    ),
    (
        "walk: stop reading the mod file",
        '".md", ".mod",',
        '".md",',
    ),
    # PRUNE, BROKEN IN BOTH DIRECTIONS AND ONE MEMBER AT A TIME. The
    # three-at-once mutant above dies too easily. Round 19 found that adding
    # just `docs` left the suite green, and that is exactly the regression
    # round 16 found by hand. WHY IT LEFT THE SUITE GREEN IS BEST STATED AS A
    # RULE, not as a list: docs/ is not pruned in the fixtures the suite
    # builds, and it is not the only markdown in the shipping tree either -
    # every mod README, every file under .claude/, and CLAUDE.md at the root
    # are all outside docs/ and all swept. NO COUNT OF THEM IS GIVEN, for the
    # reason this file gives for its absent mutants. 1af8901 named a subset and
    # read as exhaustive, which is the same partial-survey shape as the
    # templates/ claim it replaced.
    #
    # THE WIDENING MUTANT NAMES A DIRECTORY THAT DOES NOT EXIST, deliberately.
    # What kills it is the suite pinning the SET, so the name is arbitrary, and
    # a real one invites the reader to think the entry is about that tree.
    # Round 20 wrote that claim as already true while an entry named `docs` -
    # the largest single contributor to the acceptance count - and argued for
    # it from templates/ carrying commentable mod script, which holds no files
    # at all.
    (
        "walk: prune one directory more",
        'PRUNE = {".git", "__pycache__"}',
        'PRUNE = {".git", "__pycache__", "nowhere"}',
    ),
    (
        "walk: stop pruning .git",
        'PRUNE = {".git", "__pycache__"}',
        'PRUNE = {"__pycache__"}',
    ),
    (
        "walk: stop pruning __pycache__",
        'PRUNE = {".git", "__pycache__"}',
        'PRUNE = {".git"}',
    ),
    # THE WIDENED `except`, which is 8a71ce1's headline fix run backwards. Both
    # of these left the suite green until round 19, so the paragraph named
    # `AN UNREADABLE FILE IS NOT SKIPPED` was prose with nothing behind it.
    (
        "decode: swallow every OSError too",
        "            except UnicodeDecodeError:",
        "            except (UnicodeDecodeError, OSError):",
    ),
    (
        "decode: swallow every exception",
        "            except UnicodeDecodeError:",
        "            except Exception:",
    ),
]


if __name__ == "__main__":
    raise SystemExit(run_mutants(TARGET, SUITE, MUTANTS))
