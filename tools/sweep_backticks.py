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

KNOWN LIMITS. The first two are also written down in that same paragraph:

  - a span wrapped across three or more lines leaves the middle lines with no
    backtick at all, so it is caught at its two ends and not in its middle;
  - two independent unbalanced spans on one line sum to even and hide each
    other;
  - a fence whose opener and closer use different markers is not recognised as
    a pair, and the state machine then treats the rest of the file as fenced,
    which is a silent MISS of everything below. No such fence exists today;
  - a backslash immediately before a real backtick is read as an escape and
    stripped, which flips a balanced line to odd. That is a false positive, the
    harmless direction, and no line in the tree does it.

EXTENSIONS ARE MATCHED CASE-INSENSITIVELY, because the rule the sweep enforces
is casing-blind and a `README.MD` would otherwise be skipped in silence.

AN UNREADABLE FILE IS NOT SKIPPED. Only `UnicodeDecodeError` is caught, so a
file this process cannot open raises out of the sweep. `validate.py` takes the
same stance for the same reason - its
`test_an_unopenable_entry_is_skipped_rather_than_crashing` records it - and a
sweep that quietly drops what it could not read is the exact defect this tool
exists to catch, one level up.

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
            if path.suffix.lower() not in EXTS or not path.is_file():
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
