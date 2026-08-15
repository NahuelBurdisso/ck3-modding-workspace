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

KNOWN LIMITS, the first two also written down in that same paragraph:
  - a span wrapped across three or more lines leaves the middle lines with no
    backtick at all, so it is caught at its two ends and not in its middle;
  - two independent unbalanced spans on one line sum to even and hide each
    other;
  - a fence opened inside a blockquote is handled, but a fence whose opener and
    closer use different markers is not;
  - an escaped backtick is stripped before counting. Without that, a balanced
    line containing one flips to odd, which is a FALSE POSITIVE - but a line
    that is genuinely unbalanced AND carries one escaped backtick flips to
    even, which is a FALSE NEGATIVE and is the dangerous direction. Neither has
    been observed; the stripping trades the common noise for the rare miss.

THIS FILE SPELLS ITS OWN BACKTICKS AS `\\x60`. A detector that matches on a
character will contain that character, and writing it literally made the sweep
report three lines of its own source on every run. Excluding this file by name
would be a carve-out of exactly the kind the rule exists to prevent, so the
character is escaped instead and the count stays even.
"""

import re
import sys
from pathlib import Path

# Every extension that can carry a comment or prose. The mod's script, its loc,
# its gui, the tooling's Python, and the docs.
EXTS = {".txt", ".yml", ".gui", ".info", ".md", ".py"}

# A fence may be indented, and may sit inside one or more blockquote markers.
# `> ` followed by a fence is a real line of
# docs/plans/2026-08-13-battle-chronicles-expansion-plan-3-reputation.md, and
# reading it as prose put two fenced lines into the report.
FENCE_RE = re.compile(r"^\s*(?:>\s*)*(?:\x60{3}|~{3})")

ESCAPED_BACKTICK_RE = re.compile(r"\\\x60")

BACKTICK = "\x60"

PRUNE = {".git", "__pycache__"}


def sweep(root: Path) -> list[tuple[str, int, str]]:
    hits = []
    for path in sorted(root.rglob("*")):
        if any(part in PRUNE for part in path.parts):
            continue
        if path.suffix not in EXTS or not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8-sig").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        fenced = False
        for lineno, line in enumerate(lines, 1):
            if FENCE_RE.match(line):
                fenced = not fenced
                continue
            if fenced:
                continue
            if ESCAPED_BACKTICK_RE.sub("", line).count(BACKTICK) % 2:
                hits.append((path.relative_to(root).as_posix(), lineno, line.strip()))
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
