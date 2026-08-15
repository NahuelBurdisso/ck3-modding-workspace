"""Mutation harness for tools/tests/test_sweep_backticks.py.

WHY THIS IS A FILE AND NOT A SHELL LOOP. The thing it checks - that a test
actually fails when the behaviour it names is broken - is worth nothing if the
harness itself is retyped from memory each time it is wanted. That is the exact
history of the sweep this harness points at: it was a `grep` one-liner, it was
retyped in every review round, and every retyping was wrong in a new way.
8a71ce1 made the sweep a file for that reason; this is the same move one level
up.

WHAT IT PROVES. Rounds 15 and 16 both found tests in test_citations.py that
passed against a build with the checked behaviour deleted. A test that cannot
fail is not a test, and reading one does not tell you which kind it is. Each
entry below breaks one line of sweep_backticks.py and the run records which
tests go red. A SURVIVING MUTANT NAMES A VACUOUS TEST, or a behaviour nothing
pins at all.

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
