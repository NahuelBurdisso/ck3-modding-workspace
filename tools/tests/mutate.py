"""The driver every mutation harness in this directory runs on.

WHAT A HARNESS OWNS AND WHAT THIS OWNS. A harness names a target module, a test
suite, and a list of (name, anchor, replacement) triples; the reasoning for each
triple belongs beside it, in the harness. Everything below is the mechanism -
apply, run, restore, report - and it lives here because it has already been got
wrong twice and a copy of it would have to be got right again.

THE TWO HAZARDS IT EXISTS TO CONTAIN, both found the hard way:

  - `Path.write_text` ON WINDOWS TRANSLATES EVERY `\\n` TO `\\r\\n`. The first
    harness restored its target with it and rewrote the whole file to CRLF. The
    working copy is LF, so that is a real corruption of a file the harness is
    supposed to leave exactly as it found it. Everything here reads and writes
    BYTES, and the restore is therefore byte-identical.
  - `PYTHONDONTWRITEBYTECODE` IS NOT OPTIONAL. Two mutants of the same byte
    length written inside one filesystem timestamp resolution reuse the first
    one's cached `.pyc`, and the second reports a false OK - a survivor read as
    a kill, which is the one error a mutation run must not make quietly.

A NON-ZERO EXIT IS NOT A KILL BY ITSELF. A mutant that stops the suite importing
also exits non-zero, and counting it teaches the harness to accept a mutation no
test ever saw. A kill requires a NAMED test to have gone red.

AN ANCHOR THAT DOES NOT MATCH EXACTLY ONCE IS A FAILURE, not a skip. A mutation
that was never applied looks identical to one that was killed if the only thing
watched is the exit status, and anchors go stale every time their target is
edited. THE ANCHOR IS WHAT MUST BE UNIQUE - a replacement is free to be longer
or shorter than what it replaces, and at least one entry in this directory puts
two lines where it matched one.

NONE OF THIS IS PART OF THE ACCEPTANCE SET. A harness edits a tracked file in
place, so it is run deliberately, alone, and never alongside anything that
imports the file it is mutating: while it runs, what is on disk is the broken
version.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

Mutant = tuple[str, str, str]

# unittest writes progress to stderr at verbosity 2; both streams are searched
# so a harness cannot be defeated by a suite that reports on the other one.
FAIL_RE = re.compile(r"^(test_\w+) \(.*\) \.\.\. (?:FAIL|ERROR)", re.M)


def run_suite(suite: Path) -> tuple[bool, set[str]]:
    """Run one suite. Returns (passed, names of the tests that did not)."""
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    proc = subprocess.run(
        [sys.executable, str(suite)], capture_output=True, text=True, env=env
    )
    return proc.returncode == 0, set(FAIL_RE.findall(proc.stdout + proc.stderr))


def run_mutants(target: Path, suite: Path, mutants: list[Mutant]) -> int:
    """Break `target` one anchor at a time and report what `suite` noticed."""
    original = target.read_bytes()

    passed, red = run_suite(suite)
    if not passed:
        print("BASELINE IS RED - fix that before mutating:", sorted(red))
        return 1
    # The count is PRINTED AND NOT WRITTEN DOWN in any docstring. A number in
    # prose beside a list that grows is wrong at the next commit: 1af8901's
    # message said 44 over a list of 43.
    print(f"baseline: green - {len(mutants)} mutants\n")

    survivors = []
    for name, old, new in mutants:
        text = original.decode("utf-8")
        if text.count(old) != 1:
            print(f"!! ANCHOR MATCHED {text.count(old)}x, expected 1: {name}")
            survivors.append(name)
            continue
        target.write_bytes(text.replace(old, new, 1).encode("utf-8"))
        try:
            passed, red = run_suite(suite)
        finally:
            target.write_bytes(original)
        if passed:
            print(f"SURVIVED  {name}")
            survivors.append(name)
        elif not red:
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
