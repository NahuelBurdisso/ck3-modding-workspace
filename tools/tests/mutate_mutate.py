"""Mutation harness for tools/tests/test_mutate.py - the driver grading itself.

WHY THE GRADER IS GRADED. `mutate.py` decides, for every other harness in this
directory, whether a mutation was killed. A defect in it is silent by
construction: a driver that scores a survivor as a kill certifies a vacuous
test as a good one, and no other file in the tree can see that. test_mutate.py
was written to pin it; THIS file is what says whether test_mutate.py would
notice the pins being pulled.

IT IS NOT CIRCULAR, and the reason is worth stating because it looks it. The
copy of `run_mutants` doing the grading is the one imported into THIS process
before any mutation is applied. The broken copy only ever exists on disk, where
the subprocess reads it. The two never mix.

EVERY ENTRY UNDOES SOMETHING A COMMENT IN `mutate.py` CLAIMS. That is the
selection rule: each mutant reverts one documented decision - reading the
summary instead of the progress line, listing ERROR beside FAIL, setting
PYTHONDONTWRITEBYTECODE, restoring in bytes, refusing to count an import
failure - and names the test that must object.

WHAT IS DELIBERATELY NOT MUTATED. `text = original.decode("utf-8")` inside the
loop, against re-reading the target from disk. The two are EQUIVALENT while the
restore in `finally` stands - disk and `original` agree at the top of every
iteration - so a mutant swapping them can only survive, and it did before it
was removed. Telling them apart needs both faults at once, and the restore has
a mutant of its own. No test in test_mutate.py claims to pin the difference.

NEITHER IS THE `timeout=timeout` PASSED TO `subprocess.run`, and that one is a
mutant this file cannot afford rather than one it does not want. Removing it is
the whole defect the timeout was added for, so the suite would hang - and the
run grading it would then sit on its OWN timeout, which is the same default,
for a verdict of TIMED OUT: a survivor either way, bought with two minutes. The
question it would ask is asked cheaply instead by the DEFAULT_TIMEOUT mutant
below, which proves the budget is read, and by the TimeoutExpired mutant, which
proves what is done when it fires.

Run it with `python tools/tests/mutate_mutate.py`. Exit 0 means every mutant
was killed. It is slower than its siblings because every mutant runs a suite
that itself spawns a subprocess per case.
"""

from __future__ import annotations

from pathlib import Path

from mutate import run_mutants

TOOLS = Path(__file__).resolve().parents[1]
TARGET = TOOLS / "tests" / "mutate.py"
SUITE = TOOLS / "tests" / "test_mutate.py"

MUTANTS = [
    # --- what counts as a named failure ----------------------------------
    # THE PATTERN THIS FILE'S TARGET USED TO CARRY. It matches only while no
    # test method has a docstring, which was true of every suite here and is
    # what made the defect invisible.
    (
        "verdict: go back to reading the progress line",
        r'FAIL_RE = re.compile(r"^(?:FAIL|ERROR): (test_\w+) \(", re.M)',
        r'FAIL_RE = re.compile(r"^(test_\w+) \(.*\) \.\.\. (?:FAIL|ERROR)", re.M)',
    ),
    (
        "verdict: stop treating an errored test as a named failure",
        r'FAIL_RE = re.compile(r"^(?:FAIL|ERROR): (test_\w+) \(", re.M)',
        r'FAIL_RE = re.compile(r"^(?:FAIL): (test_\w+) \(", re.M)',
    ),
    (
        "verdict: read stdout only, where unittest writes nothing",
        "set(FAIL_RE.findall(proc.stdout + proc.stderr))",
        "set(FAIL_RE.findall(proc.stdout))",
    ),
    (
        "verdict: call every run green",
        "    return proc.returncode == 0, set(",
        "    return True, set(",
    ),
    (
        "verdict: count an import failure as a kill",
        "        elif not red:",
        "        elif False:",
    ),
    (
        "verdict: never report a survivor",
        "        elif passed:",
        "        elif False:",
    ),
    (
        "verdict: exit 0 with survivors on the list",
        "        for name in survivors:\n            print(f\"  {name}\")\n        return 1",
        "        for name in survivors:\n            print(f\"  {name}\")\n        return 0",
    ),
    # --- the two hazards the docstring is mostly about --------------------
    (
        "hazard: let the subprocess cache bytecode",
        'env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")',
        "env = dict(os.environ)",
    ),
    # RESTORED THROUGH `write_text`, which is the exact bug that put CRLF into
    # a tracked LF file the first time. Only a byte comparison sees it.
    (
        "hazard: restore the target as text",
        "            target.write_bytes(original)",
        '            target.write_text(original.decode("utf-8"))',
    ),
    (
        "hazard: leave the last mutant on disk",
        "        try:\n            passed, red, timed_out = run_suite(suite, timeout)\n        finally:\n            target.write_bytes(original)",
        "        try:\n            passed, red, timed_out = run_suite(suite, timeout)\n        finally:\n            pass",
    ),
    # --- the third hazard: a mutant that never finishes --------------------
    (
        "hazard: read a timed-out suite as an ordinary failure",
        "        return False, set(), True",
        "        return False, set(), False",
    ),
    (
        "hazard: score a suite that never finished as a kill",
        '            print(f"TIMED OUT {name} - the suite did not finish in {timeout}s")\n            survivors.append(name)',
        '            print(f"TIMED OUT {name} - the suite did not finish in {timeout}s")',
    ),
    (
        "hazard: start mutating over a baseline that never finished",
        '    if timed_out:\n        print(f"BASELINE TIMED OUT',
        '    if False:\n        print(f"BASELINE TIMED OUT',
    ),
    # A BUDGET TOO SMALL DOES NOT FAIL SAFE. It reports a suite that was
    # merely slow as one that will never finish, which is a false survivor -
    # the same wrong answer as having no timeout at all, arrived at from the
    # other side.
    (
        "hazard: set a budget no real suite can finish inside",
        "DEFAULT_TIMEOUT = 120",
        "DEFAULT_TIMEOUT = 0.001",
    ),
    # --- anchors ----------------------------------------------------------
    (
        "anchor: accept an anchor that matches more than once",
        "        if text.count(old) != 1:",
        "        if text.count(old) < 1:",
    ),
    # --- the baseline and the count --------------------------------------
    (
        "baseline: mutate over a red suite anyway",
        "    if not passed:\n        print(\"BASELINE IS RED",
        "    if False:\n        print(\"BASELINE IS RED",
    ),
    (
        "count: stop printing the size of the list",
        'print(f"baseline: green - {len(mutants)} mutants\\n")',
        'print("baseline: green\\n")',
    ),
]


if __name__ == "__main__":
    raise SystemExit(run_mutants(TARGET, SUITE, MUTANTS))
