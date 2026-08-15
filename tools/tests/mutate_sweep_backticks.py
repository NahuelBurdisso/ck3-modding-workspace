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
entry below breaks one line of sweep_backticks.py and the run records which
tests go red. A SURVIVING MUTANT NAMES A VACUOUS TEST, or a behaviour nothing
pins at all.

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

NOT PART OF THE ACCEPTANCE SET. It edits a tracked file in place, so it is run
deliberately and never as part of a batch. It restores the file in a `finally`,
and it writes BYTES so that the restore is byte-identical: `write_text` on
Windows translates every `\\n` to `\\r\\n`, which rewrote the whole of
sweep_backticks.py to CRLF the first time this harness ran. The working copy is
LF, so that is a real corruption of a file the harness is supposed to leave
alone.

Run it with `python tools/tests/mutate_sweep_backticks.py`. Exit 0 means every
mutant was killed.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

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
        "if path.suffix.lower() not in EXTS or not path.is_file():",
        "if path.suffix not in EXTS or not path.is_file():",
    ),
    (
        "walk: accept every extension",
        "if path.suffix.lower() not in EXTS or not path.is_file():",
        "if not path.is_file():",
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
        "walk: leave filenames in filesystem order",
        "        filenames.sort()",
        "        filenames.reverse()",
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
        "if path.suffix.lower() not in EXTS or not path.is_file():",
        "if path.suffix.lower() not in EXTS:",
    ),
    (
        "decode: stop stripping the BOM",
        'lines = path.read_text(encoding="utf-8-sig").splitlines()',
        'lines = path.read_text(encoding="utf-8").splitlines()',
    ),
    (
        "walk: stop reading Python",
        '".md", ".mod", ".py"}',
        '".md", ".mod"}',
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
    # ONE MUTANT PER EXTENSION, dropped singly. "walk: stop reading Python"
    # above is not enough on its own: the test it kills used to derive both its
    # fixtures and its expectation from S.EXTS, so shrinking EXTS shrank the
    # fixture set with it and four of these five survived the whole suite.
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
    # ONE MUTANT PER TOP-LEVEL TREE, pruned singly. The three-at-once mutant
    # above dies too easily: pruning only `docs` left the suite green, because
    # markdown still reaches the scanner through CLAUDE.md and templates/, and
    # that is exactly the regression round 16 found by hand.
    (
        "walk: prune the docs tree",
        'PRUNE = {".git", "__pycache__"}',
        'PRUNE = {".git", "__pycache__", "docs"}',
    ),
    (
        "walk: prune the mods tree",
        'PRUNE = {".git", "__pycache__"}',
        'PRUNE = {".git", "__pycache__", "mods"}',
    ),
    (
        "walk: prune the tools tree",
        'PRUNE = {".git", "__pycache__"}',
        'PRUNE = {".git", "__pycache__", "tools"}',
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

FAIL_RE = re.compile(r"^(test_\w+) \(.*\) \.\.\. (?:FAIL|ERROR)", re.M)


def run() -> tuple[bool, set[str]]:
    """Run the suite once. Returns (passed, names of the tests that did not)."""
    # PYTHONDONTWRITEBYTECODE IS NOT OPTIONAL. Two mutants of the same byte
    # length written inside one filesystem timestamp resolution reuse the first
    # one's cached .pyc, and the second reports a false OK.
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    proc = subprocess.run(
        [sys.executable, str(SUITE)], capture_output=True, text=True, env=env
    )
    return proc.returncode == 0, set(FAIL_RE.findall(proc.stdout + proc.stderr))


def main() -> int:
    original = TARGET.read_bytes()

    passed, red = run()
    if not passed:
        print("BASELINE IS RED - fix that before mutating:", sorted(red))
        return 1
    print("baseline: green\n")

    survivors = []
    for name, old, new in MUTANTS:
        text = original.decode("utf-8")
        if text.count(old) != 1:
            print(f"!! ANCHOR MATCHED {text.count(old)}x, expected 1: {name}")
            survivors.append(name)
            continue
        TARGET.write_bytes(text.replace(old, new, 1).encode("utf-8"))
        try:
            passed, red = run()
        finally:
            TARGET.write_bytes(original)
        if passed:
            print(f"SURVIVED  {name}")
            survivors.append(name)
        elif not red:
            # A NON-ZERO EXIT IS NOT A KILL BY ITSELF. A mutant that stops the
            # suite importing also exits non-zero, and counting it teaches the
            # harness to accept a mutation no test ever saw. Round 18 found
            # this reading only the code, before it had cost anything.
            print(f"CRASHED   {name} - the suite failed without naming a test")
            survivors.append(name)
        else:
            print(f"killed    {name}")
            for test in sorted(red):
                print(f"            {test}")

    print()
    if survivors:
        print(f"{len(survivors)} SURVIVING MUTANT(S):")
        for name in survivors:
            print(f"  {name}")
        return 1
    print("every mutant killed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
