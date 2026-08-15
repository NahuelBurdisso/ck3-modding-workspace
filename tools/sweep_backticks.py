"""Unbalanced-backtick sweep: find grep targets broken across a line wrap.

WHY THIS AND NOT A NAME LIST. The rule it enforces is written down in
mods/battle_chronicles/common/customizable_localization/bc_flavour.txt, under
the paragraph named `THE DETECTOR IS AN UNBALANCED BACKTICK`. A name list has
to be maintained and goes stale silently; an unbalanced backtick is the literal
signature of the defect and is casing-blind, so it needs neither.

NOT A `validate` CHECK, deliberately. The tree has legitimate multi-line
quotations - of loc text, of script, of command lines, of engine output - and
those wrap on purpose, so a hard error would fire on a clean tree. Read the
output and judge each line; do not gate on the count.

KNOWN LIMITS. The three-line span and the two-spans-on-one-line pair are also
written down in that same paragraph. NO ORDINAL AND NO COUNT IS USED TO REFER TO
ANY OF THEM, here or anywhere else, because a position in this list goes false
without anyone touching the sentence that cites it. 8a71ce1 opened this block
with "The first two are also written down in that same paragraph"; 1af8901
replaced that clause with the two subjects it meant and recorded the swap
nowhere, which is written here instead. For the ordinal that actually drifted see
the paragraph named `WHAT IS NOT A LIMIT: A MISMATCHED FENCE PAIR`. An earlier
draft of this sentence cited that paragraph as charging 8a71ce1 with a positional
citation, which it does not: what it charges 8a71ce1 with is a false limit and a
commit message that misdescribes it.

  - a span wrapped across three or more lines leaves the middle lines with no
    backtick at all, so it is caught at its two ends and not in its middle;
  - two independent unbalanced spans on one line sum to even and hide each
    other;
  - AN UNTERMINATED FENCE SWALLOWS THE REST OF ITS FILE: the sweep does not
    report less confidently below an unclosed opener, it reports nothing at
    all. WHAT IS UNIQUE ABOUT IT IS THE BLAST RADIUS, NOT THE SILENCE. An
    earlier draft called it the only limit here whose failure mode is silence,
    which the two-spans-on-one-line bullet disproves: that one is a silent miss
    too, and its own test asserts the silence. The difference is that a hidden
    pair costs the line it sits on and an unclosed opener costs every line below
    it. The state machine is one boolean with no stack, so it cannot tell an
    unclosed fence from a very long one. Pinned by
    `test_an_unterminated_fence_swallows_the_rest` in
    tools/tests/test_sweep_backticks.py;
  - a backslash immediately before a real backtick is read as an escape and
    stripped, which flips a balanced line to odd. That is a false positive, the
    harmless direction, and it is pinned by
    `test_a_backslash_before_a_backtick_is_read_as_an_escape`.
    WHERE THE ESCAPES ACTUALLY SIT has taken two drafts to get right. The docs
    tree carries them - in the rivalry plan and in the before-and-after plan,
    quoting comments that themselves contain backticks - and none of THOSE
    flips, because they come two to a line and an even strip changes no parity.
    An earlier draft said no line in the tree did it at all, which one grep
    disproves; the draft after it said none of them flips full stop, which is
    also wrong. The only lines in either checkout where the strip does flip one
    are two fixtures of the suite that pins this bullet, at one escape each, and
    `test_the_sweep_does_not_report_its_own_source` leans on the flip.
    `sub` IS CALLED WITHOUT A COUNT, so every escape on a line is stripped and
    not some prefix of them. BE PRECISE ABOUT WHAT PINS THAT: a fixture of N
    escapes catches a truncation at count k ONLY WHEN N-k IS ODD, because at an
    even difference the leftover escapes cancel in pairs and the report comes
    out byte-identical. One width is therefore blind to half the counts below it
    as well as to every count at or above it, and no finite fixture closes the
    second half. The claim that a fixture of N catches any count below N was
    generalised from N=2, one of only two widths where it happens to hold. What
    closes the odd half is the RAMP, whose consecutive steps alternate parity.
    Pinned by `test_a_truncated_strip_is_caught_below_the_ramps_width`;
  - THE REPORT DIES ON A CHARACTER THE OUTPUT STREAM CANNOT ENCODE, and takes
    the summary line with it. On Windows a redirected stdout - a pipe or a
    file, which is how the acceptance count is read - falls back to cp1252,
    and `print` then raises out of `main()` before the total is written. THE
    FAILURE IS LOUD WHERE ANYONE LOOKS AT IT: the traceback goes to stderr and
    the exit status is non-zero. What it is not is loud IN BAND - the redirected
    file is a short, well-formed run of hit lines whose only sign of trouble is
    a missing summary. An earlier draft of this bullet said the run "looks
    TRUNCATED rather than failed", which reads as a silent failure and is wrong.
    A console stdout is UTF-8 since PEP 528 and does not have this fault, which
    is why the hazard is stated as redirection and not as a terminal. What keeps
    it quiet today is not that the trees are ASCII - they are not - but that the
    characters on the lines that actually report are inside cp1252, AND THAT THE
    LINE IS CUT AT 110, which is a coupling and not a defence: a character the
    stream cannot encode sitting past that column is never handed to `print` at
    all, so the same file raises or does not depending on where in its line the
    character falls. Pinned by
    `test_a_non_ascii_quotation_is_lost_to_a_redirected_stdout`;
  - THE REPORTED LINE NUMBER IS NOT ALWAYS GREP'S, and TWO SEPARATE MECHANISMS
    make it so. `read_text` opens in universal-newline mode, so a lone \\r is
    already a break before anything else runs; and `splitlines` then breaks on
    \\v, \\f, \\x1c, \\x1d, \\x1e, \\x85, U+2028 and U+2029 as well as on \\n.
    grep counts \\n alone, so a file carrying any of them reports a number
    nobody can navigate to, which is the one thing the report exists to give.
    An earlier draft named `splitlines` alone and left \\r off the list. \\r IS
    a splitlines boundary; it is simply consumed a layer earlier and never
    reaches it, which is a distinction worth the sentence rather than the
    omission. No line of either tree carries any of them, lone \\r included,
    which is why this is recorded rather than fixed. Pinned by
    `test_a_form_feed_is_a_line_break_here_and_not_to_grep`.

WHAT IS NOT A LIMIT: A MISMATCHED FENCE PAIR. 8a71ce1 shipped a KNOWN LIMITS
bullet claiming that a block opened with three backticks and closed with three
tildes is not recognised as a pair, and that the rest of the file is then
swallowed. NO ORDINAL IS GIVEN FOR IT HERE, and the reason is narrower than an
earlier draft of this paragraph said. 94c4c31 wrote "Until this paragraph was
written the third bullet above claimed", and that WAS true of the file it scoped
itself to: in 94c4c31's parent the third bullet is the mismatched-fence one. The
round-20 draft quoted only "the third bullet above", read the ordinal against
the post-diff file, and accused the citation of being wrong on arrival rather
than by drift. It was not wrong on arrival. A quotation cut short enough to
change its meaning is a worse defect than the one it was alleging, and it is
recorded here rather than quietly deleted.

What IS wrong with that ordinal is narrower and still enough: it addresses a
file the reader does not have open. Following it needs `git show 94c4c31^`, and
it went false for anyone reading the shipped file the moment the diff landed.
Citing a position in a list is the same defect as citing a line number, and it
was written into the file that exists to prevent it - which is why every bullet
above is referred to by its subject.

The claim itself is false, and it hid the real hazard behind an invented one
for two commits. `FENCE_RE` matches either marker and the toggle is
marker-agnostic, so a mismatched pair closes exactly like a matched one -
`test_a_fence_closed_by_the_other_marker_is_still_a_pair` is the proof.
8a71ce1's own message says it recorded the unterminated-fence limit; it did
not, it recorded this instead, which is the failure this file exists to make
harder.

EXTENSIONS ARE MATCHED CASE-INSENSITIVELY, because the rule the sweep enforces
is casing-blind and a `README.MD` would otherwise be skipped in silence. THE
DOTFILE NAMES BESIDE THEM ARE NOT, and the asymmetry is deliberate: a mis-cased
extension is something a person types, while a dotfile name is fixed by git,
which does not read a `.GITIGNORE` either. That list exists at all because a
name with no second dot has NO SUFFIX for `EXTS` to match - which is how
`mods/battle_chronicles/.gitattributes` came to hold two paragraphs of prose
that this tool could not see.

AN UNREADABLE FILE IS NOT SKIPPED. Only `UnicodeDecodeError` is caught, so a
file this process cannot open raises out of the sweep, and a sweep that quietly
drops what it could not read is the exact defect this tool exists to catch, one
level up. `validate.py` takes the same stance for the same reason, but BE
PRECISE ABOUT WHERE THAT IS WRITTEN: it is a comment inside
`test_an_unopenable_entry_is_skipped_rather_than_crashing`, which says in as
many words that it does NOT cover an unreadable file. Reading that name as a
pin is a mistake this docstring made until it was corrected. What is pinned
either side is the `is_file()` guard, which is a different case - an entry that
os.walk offered and that is not a file.

The pin for `AN UNREADABLE FILE IS NOT SKIPPED` is
`test_a_file_that_cannot_be_opened_raises_out_of_the_sweep`, and it did not
exist until round 19: widening the clause to `(UnicodeDecodeError, OSError)`,
or to a bare `Exception`, left every test green, so the fix that paragraph
describes could have been reverted without a red anywhere.

THIS FILE SPELLS ITS OWN BACKTICKS AS `\\x60`. A detector that matches on a
character will contain that character, and writing it literally made the sweep
report lines of its own source on every run. Excluding this file by name would
be a carve-out of exactly the kind the rule exists to prevent, so the character
is escaped instead and the count stays even.
"""

import os
import re
import sys
from pathlib import Path

# Every extension that can carry a comment or prose. The mod's script, its loc,
# its gui, its descriptor, the tooling's Python, and the docs.
EXTS = {".txt", ".yml", ".gui", ".info", ".md", ".mod", ".py"}

# EXTENSIONS ARE NOT ENOUGH, because a dotfile with no second dot has no
# suffix at all: `Path(".gitattributes").suffix` is the empty string, so no
# entry in EXTS can ever reach one. mods/battle_chronicles/.gitattributes
# carries two paragraphs of prose naming `has_bom` and `_check_loc_file` in
# backticks, which is exactly the kind of line the sweep exists to catch
# wrapping, and it was invisible to this tool while that was true. Matched on
# the WHOLE NAME and case-sensitively: unlike an extension, a dotfile name is
# fixed by git and by convention, and `.GITATTRIBUTES` is not a thing.
NAMES = {".gitattributes", ".gitignore"}

# A fence may be indented, and may sit inside one or more blockquote markers.
# `> ` followed by three backticks is a real line of
# docs/plans/2026-08-13-battle-chronicles-expansion-plan-3-reputation.md. What
# it costs to miss is the DELIMITER, not the fenced body: a delimiter is three
# backticks, so an unrecognised one is odd and reports itself. The body is
# scanned too, and would report if it held an odd count - in that file it holds
# no backtick at all, so the delimiters were the whole of the noise.
FENCE_RE = re.compile(r"^\s*(?:>\s*)*(?:\x60{3}|~{3})")

# Stripping this removes BOTH failure modes rather than trading one for the
# other. Counted raw, an escaped backtick flips a balanced line to odd - noise -
# and flips a genuinely unbalanced line to even, which is a miss. Stripped,
# neither happens.
ESCAPED_BACKTICK_RE = re.compile(r"\\\x60")

BACKTICK = "\x60"

PRUNE = {".git", "__pycache__"}


def sweep(root: Path) -> list[tuple[str, int, str]]:
    hits = []
    for dirpath, dirnames, filenames in os.walk(root):
        # In place, so os.walk does not descend. Filtering the paths afterwards
        # is correct but walks every git object to do it.
        dirnames[:] = sorted(d for d in dirnames if d not in PRUNE)
        filenames.sort()
        for name in filenames:
            path = Path(dirpath) / name
            if (path.suffix.lower() not in EXTS and name not in NAMES) or not path.is_file():
                continue
            try:
                lines = path.read_text(encoding="utf-8-sig").splitlines()
            except UnicodeDecodeError:
                continue
            fenced = False
            for lineno, line in enumerate(lines, 1):
                if FENCE_RE.match(line):
                    fenced = not fenced
                    continue
                if fenced:
                    continue
                if ESCAPED_BACKTICK_RE.sub("", line).count(BACKTICK) % 2:
                    rel = path.relative_to(root).as_posix()
                    hits.append((rel, lineno, line.strip()))
    return hits


def main() -> int:
    root = (Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")).resolve()
    hits = sweep(root)
    for rel, lineno, line in hits:
        print(f"{rel}:{lineno}: {line[:110]}")
    print(f"--- unbalanced backtick lines: {len(hits)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
