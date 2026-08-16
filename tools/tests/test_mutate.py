"""What `mutate.py` must get right, pinned against synthetic targets.

WHY THE DRIVER NEEDS ITS OWN SUITE. Every other test file in this directory
decides whether some behaviour is correct. This one decides whether the thing
that grades those files is telling the truth, and it had no tests at all while
two harnesses depended on it. A driver that misreads a kill as a survivor cries
wolf, which is survivable; one that misreads a survivor as a KILL certifies a
vacuous test as a good one, which is the failure the harnesses exist to prevent
and which nothing else in the tree can see.

WHAT IS ACTUALLY SYNTHETIC HERE. Every test below builds a throwaway target
module and a throwaway suite in a temp directory and runs the real driver over
them. Nothing is stubbed and nothing is monkeypatched, because both hazards the
driver was written for - the CRLF rewrite and the stale .pyc - live in the
subprocess and the filesystem, not in Python objects.

NO TEST METHOD IN THIS FILE MAY GAIN A DOCSTRING WITHOUT ONE BEING ADDED TO
THE SYNTHETIC SUITES TOO. The docstring case is exactly what
`test_a_red_test_with_a_docstring_is_still_named` exists to hold, and it holds
it by writing a docstring into the generated suite, not by relying on the
conventions of this file.
"""

from __future__ import annotations

import io
import contextlib
import os
import tempfile
import unittest
from pathlib import Path

import mutate

# A target with two independent behaviours, so a mutant can turn one off
# without disturbing the other.
TARGET_SRC = (
    "def double(n):\n"
    "    return n * 2\n"
    "\n"
    "\n"
    "def triple(n):\n"
    "    return n * 3\n"
)

SUITE_HEAD = (
    "import unittest\n"
    "\n"
    "import subject\n"
    "\n"
    "\n"
    "class T(unittest.TestCase):\n"
)

SUITE_TAIL = '\n\nif __name__ == "__main__":\n    unittest.main(verbosity=2)\n'


class MutateTestCase(unittest.TestCase):
    def setUp(self) -> None:
        # os.environ is restored wholesale because one test below edits it:
        # the driver reads the environment it was started in, so the only way
        # to test what the driver adds is to take it away first.
        env = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(env)))
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.target = self.root / "subject.py"
        self.suite = self.root / "suite_subject.py"
        self.target.write_bytes(TARGET_SRC.encode("utf-8"))

    def write_suite(self, *bodies: str) -> None:
        self.suite.write_bytes(
            (SUITE_HEAD + "".join(bodies) + SUITE_TAIL).encode("utf-8")
        )

    def run_mutants(
        self, mutants: list[tuple[str, str, str]], timeout: float = mutate.DEFAULT_TIMEOUT
    ) -> tuple[int, str]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = mutate.run_mutants(self.target, self.suite, mutants, timeout)
        return code, buf.getvalue()


BOTH_CHECKED = (
    "    def test_double(self):\n"
    "        self.assertEqual(subject.double(2), 4)\n"
    "\n"
    "    def test_triple(self):\n"
    "        self.assertEqual(subject.triple(2), 6)\n"
)

KILL_DOUBLE = ("kill double", "    return n * 2", "    return n * 99")
KILL_TRIPLE = ("kill triple", "    return n * 3", "    return n * 99")


class TestVerdicts(MutateTestCase):
    """Which outcomes count as a kill, and which do not."""

    def test_a_killed_mutant_returns_zero_and_names_the_red_test(self) -> None:
        self.write_suite(BOTH_CHECKED)
        code, out = self.run_mutants([KILL_DOUBLE])
        self.assertEqual(code, 0)
        self.assertIn("killed    kill double", out)
        self.assertIn("test_double", out)
        self.assertIn("every mutant killed", out)

    def test_a_surviving_mutant_returns_nonzero_and_is_listed(self) -> None:
        # Only `triple` is checked, so breaking `double` changes nothing the
        # suite looks at. That is the whole point of a mutation run.
        self.write_suite(
            "    def test_triple(self):\n"
            "        self.assertEqual(subject.triple(2), 6)\n"
        )
        code, out = self.run_mutants([KILL_DOUBLE])
        self.assertEqual(code, 1)
        self.assertIn("SURVIVED  kill double", out)
        self.assertIn("1 SURVIVING MUTANT(S):", out)

    def test_a_red_test_with_a_docstring_is_still_named(self) -> None:
        # THE REGRESSION THIS FILE WAS OPENED FOR. At verbosity 2 unittest puts
        # the verdict on a second line when the method has a docstring, so a
        # pattern anchored on the progress line matches nothing and the driver
        # reports CRASHED - a survivor - for a mutation the suite caught. No
        # method in this directory has a docstring, so nothing would have found
        # this until the day someone wrote one.
        self.write_suite(
            "    def test_double(self):\n"
            '        """This docstring is the fixture."""\n'
            "        self.assertEqual(subject.double(2), 4)\n"
        )
        code, out = self.run_mutants([KILL_DOUBLE])
        self.assertEqual(code, 0)
        self.assertIn("killed    kill double", out)
        self.assertIn("test_double", out)
        self.assertNotIn("CRASHED", out)

    def test_a_mutation_that_raises_inside_a_test_is_a_kill(self) -> None:
        # An errored test is a named test: the suite noticed. mutate_validate.py
        # keeps two mutants that work this way, so this is the behaviour they
        # are standing on.
        self.write_suite(BOTH_CHECKED)
        code, out = self.run_mutants(
            [("raise instead", "    return n * 2", "    raise ValueError(n)")]
        )
        self.assertEqual(code, 0)
        self.assertIn("killed    raise instead", out)
        self.assertIn("test_double", out)

    def test_a_mutation_that_stops_the_suite_importing_is_not_a_kill(self) -> None:
        # No test ran, so no test proved anything. Counting the non-zero exit
        # would teach the harness to accept a mutation nothing ever saw.
        self.write_suite(BOTH_CHECKED)
        code, out = self.run_mutants(
            [("break the syntax", "    return n * 2", "    return n * (")]
        )
        self.assertEqual(code, 1)
        self.assertIn("CRASHED   break the syntax", out)
        self.assertIn("1 SURVIVING MUTANT(S):", out)


class TestAnchors(MutateTestCase):
    """An anchor must match exactly once, and a miss is a failure."""

    def test_an_anchor_matching_twice_is_a_survivor_and_is_not_applied(self) -> None:
        self.write_suite(BOTH_CHECKED)
        before = self.target.read_bytes()
        code, out = self.run_mutants([("ambiguous", "    return n *", "    return 0 *")])
        self.assertEqual(code, 1)
        self.assertIn("ANCHOR MATCHED 2x, expected 1: ambiguous", out)
        self.assertEqual(self.target.read_bytes(), before)

    def test_an_anchor_matching_nothing_is_a_survivor(self) -> None:
        # A stale anchor and a killed mutant look identical if only the exit
        # status is watched, which is why this is loud rather than skipped.
        self.write_suite(BOTH_CHECKED)
        code, out = self.run_mutants([("stale", "    return n * 7", "    pass")])
        self.assertEqual(code, 1)
        self.assertIn("ANCHOR MATCHED 0x, expected 1: stale", out)

    def test_a_replacement_may_be_longer_than_what_it_replaces(self) -> None:
        # At least one live entry puts two lines where it matched one, so this
        # is pinned rather than assumed.
        self.write_suite(BOTH_CHECKED)
        code, out = self.run_mutants(
            [("two for one", "    return n * 2", "    n = n + 1\n    return n * 2")]
        )
        self.assertEqual(code, 0)
        self.assertIn("killed    two for one", out)


class TestRestore(MutateTestCase):
    """The target must come back exactly as it was found."""

    def test_the_target_is_restored_byte_for_byte(self) -> None:
        # LF IS THE POINT. `Path.write_text` translates \n to \r\n on Windows,
        # and the first harness written here restored its target with it and
        # rewrote a tracked LF file to CRLF. A byte comparison is the only
        # assertion that sees that.
        self.write_suite(BOTH_CHECKED)
        before = self.target.read_bytes()
        self.assertNotIn(b"\r\n", before)
        self.run_mutants([KILL_DOUBLE, KILL_TRIPLE])
        self.assertEqual(self.target.read_bytes(), before)

    def test_the_target_is_restored_even_when_a_mutant_breaks_the_suite(self) -> None:
        self.write_suite(BOTH_CHECKED)
        before = self.target.read_bytes()
        self.run_mutants([("break the syntax", "    return n * 2", "    return n * (")])
        self.assertEqual(self.target.read_bytes(), before)

    def test_a_run_of_several_mutants_grades_each_one(self) -> None:
        self.write_suite(BOTH_CHECKED)
        code, out = self.run_mutants([KILL_DOUBLE, KILL_TRIPLE])
        self.assertEqual(code, 0)
        self.assertIn("killed    kill double", out)
        self.assertIn("killed    kill triple", out)
        self.assertNotIn("ANCHOR MATCHED", out)


class TestBaseline(MutateTestCase):
    """Nothing is mutated over a suite that is already red."""

    def test_a_red_baseline_returns_nonzero_without_mutating(self) -> None:
        self.write_suite(
            "    def test_double(self):\n"
            "        self.assertEqual(subject.double(2), 5)\n"
        )
        before = self.target.read_bytes()
        code, out = self.run_mutants([KILL_DOUBLE])
        self.assertEqual(code, 1)
        self.assertIn("BASELINE IS RED", out)
        self.assertIn("test_double", out)
        self.assertNotIn("killed", out)
        self.assertNotIn("SURVIVED", out)
        self.assertEqual(self.target.read_bytes(), before)

    def test_the_mutant_count_is_printed_from_the_list(self) -> None:
        # The harness docstrings say the run prints this, and for one round
        # they said so while it did not. It is printed rather than written down
        # because 1af8901's message said 44 over a list of 43.
        self.write_suite(BOTH_CHECKED)
        _, out = self.run_mutants([KILL_DOUBLE, KILL_TRIPLE])
        self.assertIn("baseline: green - 2 mutants", out)


class TestBytecodeIsNotCached(MutateTestCase):
    """Two same-length mutants inside one timestamp must not share a .pyc."""

    def test_two_mutants_of_equal_length_are_graded_separately(self) -> None:
        # THE HAZARD IN ONE SENTENCE: without PYTHONDONTWRITEBYTECODE the
        # second mutant reuses the first one's cached bytecode and is reported
        # OK - a survivor read as a kill, which is the one error a mutation run
        # must not make quietly. Both replacements below are the same byte
        # length as what they replace and as each other, and the run is fast
        # enough that both land inside one filesystem timestamp.
        #
        # THE VARIABLE IS SCRUBBED FIRST, and without that this test cannot
        # fail. The driver sets it for the suites IT launches, so the whole
        # acceptance set - and mutate_mutate.py above all - runs with it
        # already in the environment, where `dict(os.environ)` alone would
        # inherit it and the mutant that deletes the setting survives. It did.
        os.environ.pop("PYTHONDONTWRITEBYTECODE", None)
        self.write_suite(
            "    def test_double(self):\n"
            "        self.assertEqual(subject.double(2), 4)\n"
        )
        code, out = self.run_mutants(
            [
                ("first", "    return n * 2", "    return n * 8"),
                ("second", "    return n * 3", "    return n * 9"),
            ]
        )
        # `double` is checked and `triple` is not, so the correct grading is
        # one kill and one survivor. A shared .pyc reports two kills.
        self.assertEqual(code, 1)
        self.assertIn("killed    first", out)
        self.assertIn("SURVIVED  second", out)
        self.assertFalse((self.root / "__pycache__").exists())


class TestTimeout(MutateTestCase):
    """A suite that will never finish must not take the run down with it."""

    # THREE SECONDS, NOT THE DEFAULT TWO MINUTES. Every test in this class waits
    # out its own timeout, so the budget is the runtime; it only has to be long
    # enough that a green synthetic suite - one file, one test, no imports beyond
    # the target - finishes inside it on a loaded machine.
    SHORT = 3.0

    # `double` is called by every suite below, so the loop is entered by the test
    # and not by the import: the driver must distinguish "no test finished" from
    # "no test ran", and only the first of those is what a timeout means.
    HANG = ("hang", "    return n * 2", "    while True:\n        pass")

    def test_a_mutant_that_hangs_is_reported_and_counted_as_a_survivor(self) -> None:
        # NOT A KILL, deliberately. Nothing named a test, so nothing objected -
        # what the suite did was fail to finish. Reporting it as a kill would
        # certify a mutation no test can grade.
        self.write_suite(BOTH_CHECKED)
        code, out = self.run_mutants([self.HANG], timeout=self.SHORT)
        self.assertEqual(code, 1)
        self.assertIn("TIMED OUT hang", out)
        self.assertIn("1 SURVIVING MUTANT(S):", out)
        self.assertNotIn("killed", out)

    def test_the_target_is_restored_after_a_mutant_hangs(self) -> None:
        # THE REGRESSION THIS CLASS WAS OPENED FOR. Before the timeout the run
        # blocked forever, so the `finally` that puts the file back never ran,
        # and the only way out was killing the process - which is exactly the
        # thing that skips the restore. A tracked file was left mutated on disk.
        self.write_suite(BOTH_CHECKED)
        before = self.target.read_bytes()
        self.run_mutants([self.HANG], timeout=self.SHORT)
        self.assertEqual(self.target.read_bytes(), before)

    def test_a_run_continues_grading_after_one_mutant_times_out(self) -> None:
        self.write_suite(BOTH_CHECKED)
        code, out = self.run_mutants([self.HANG, KILL_TRIPLE], timeout=self.SHORT)
        self.assertEqual(code, 1)
        self.assertIn("TIMED OUT hang", out)
        self.assertIn("killed    kill triple", out)

    def test_a_baseline_that_never_finishes_mutates_nothing(self) -> None:
        # A red baseline and a hung baseline are both "do not start", but they
        # print differently because the operator's next move differs: one is a
        # broken test to fix, the other is a suite that has to be interrupted
        # before anything here can be believed.
        self.write_suite(
            "    def test_double(self):\n"
            "        while True:\n"
            "            pass\n"
        )
        before = self.target.read_bytes()
        code, out = self.run_mutants([KILL_DOUBLE], timeout=self.SHORT)
        self.assertEqual(code, 1)
        self.assertIn("BASELINE TIMED OUT", out)
        self.assertNotIn("BASELINE IS RED", out)
        self.assertNotIn("baseline: green", out)
        self.assertEqual(self.target.read_bytes(), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
