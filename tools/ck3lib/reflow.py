"""Reflow ONE comment paragraph to a column budget.

WHY THIS EXISTS. The battle_chronicles mod's comments are its only design record
- nothing in this workspace may be proven by running the game - and they are
held to an 84-column budget. Four consecutive review rounds found the same
defect, and every one of them was made by the same act: rewrapping a paragraph by
hand. The artifacts were a 45-character line under an 84-column budget, a
five-character widow reading `# is.`, and a 54-character line welded between two
77s. Two of the three were produced by a fix commit whose entire purpose was
correcting the previous one. Reviewing harder did not converge, because a
reviewer sees the result and the defect is in the mechanism.

WHAT IT REFUSES IS THE INTERESTING HALF. This rewrites prose in place, so every
ambiguity it cannot resolve is raised rather than guessed:

  - a line in the range that is not a comment. A range is typed by hand and a
    range off by one reaches script, where rewrapping `set_variable = { ... }`
    as prose destroys it silently.
  - a bare `#` inside the range. That is the separator these comment blocks use,
    so a range spanning one spans TWO paragraphs, and merging them is exactly
    the round 3 defect: two sentences welded into one, with the causality
    inverted in the joining.
  - mixed leading whitespace, which means two blocks.
  - a continuation line left of the continuation column, which means the range
    ran into the next entry of a labelled table.
  - a first line whose label region carries no two-space separator, because
    then a label cannot be told from the opening words of the prose.

A QUOTED RUN IS ONE TOKEN, and this is the feature the tool is least able to do
without. The rule these comments are held to is that a QUOTED RUN MAY WRAP but a
GREP TARGET MAY NEVER, and a grep target is spelled as a quoted run. The first
draft of this module filled greedily by word and broke `"man commanding here"`
across two lines on its very first real paragraph - reintroducing, automatically
and everywhere, the exact defect it was written to stop. So a backtick-delimited
or double-quote-delimited run, with whatever punctuation is welded to either end,
is placed whole.

WHOLE ONLY WHERE WHOLE FITS. A quoted run too long to sit on a line of its own is
split back into words rather than overflowing the budget, because the alternative
is a tool that manufactures new over-width lines - and the over-width check is a
count of KNOWN ones, so every new one has to be argued for by hand. A single
unbroken TOKEN longer than the budget still overflows, since there is nothing to
split: bc_flavour.txt carries an engine message 82 characters long which must
appear intact, and breaking it is the one unrecoverable failure available here.

AN UNQUOTED GREP TARGET IS NOT PROTECTED, and this is the limitation to know
before pointing the tool at existing prose. The rule is that a grep target is
spelled as a quoted run, and where it is, the paragraph above keeps it whole.
Where it is not, the tool cannot see it. Running this over the `"the man"` entry
of bc_l_english.yml splits the bare all-caps verdict naming that entry's
collision - a name the same entry says "sits on one unbroken line because a name
is cited on one line or it is not cited at all". So a reflow whose range covers
an unquoted name is a reflow to check by eye, and the corpus as it stands is
hand-wrapped and correct: this exists for edits made from here on, not to be
swept over what is already there.

THE CONTINUATION COLUMN COMES FROM THE SECOND LINE, not from a guess. The
collision table in bc_l_english.yml is a term in a left column and prose in a
right one, with every continuation aligned under the prose. Reading the column
off the second line keeps that table a table; the first line's label is copied
verbatim and padded out to the same column.
"""

from __future__ import annotations

import re

DEFAULT_WIDTH = 84

# THE QUOTED ALTERNATIVES COME FIRST and that ordering is the whole regex. A
# leading `\S+` would match `"man` and never look for the closing quote, which is
# how the first draft split a grep target. Each alternative also carries `\S*` on
# both ends so the comma after a closing quote travels with it rather than
# becoming a token that can start a line.
#
# THE BACKTICK IS SPELLED `\x60`, for the reason sweep_backticks.py spells its own
# FENCE_RE that way. Written literally this line carries three backticks, so it is
# odd, so the sweep reports it as a possible split name on every run - a permanent
# entry in a report whose only value is being short enough to read.
ATOM_RE = re.compile(r"\S*\x60[^\x60]*\x60\S*|\S*\"[^\"]*\"\S*|\S+")


def _head(line: str) -> str:
    """The leading whitespace and the `#`, without the space after it."""
    stripped = line.lstrip(" \t")
    if not stripped.startswith("#"):
        raise ValueError(f"not a comment line: {line!r}")
    return line[: len(line) - len(stripped)] + "#"


def find_paragraph(lines: list[str], lineno: int) -> tuple[int, int]:
    """The half-open index range of the paragraph containing 1-based `lineno`.

    A BLOCK ends at a bare `#`, at a non-comment line, or at the file edge. A
    block is not a paragraph: the collision table in bc_l_english.yml is 53
    consecutive comment lines carrying a dozen separate entries with no `#`
    between them, and merging those into one run would flatten the table into
    prose and lose every left-column term. So a block is then cut by INDENT.

    A paragraph is a first line, followed by every consecutive line sharing the
    continuation column - which is the second line's indent. An entry of a
    labelled table indents its label less than its own continuations, so the
    next entry's label ends the previous entry. A plain paragraph has one indent
    throughout and runs to the end of its block.

    This is what stops a reflow at the paragraph boundary rather than at the edge
    of whatever hunk the caller happened to be editing - the mistake that
    produced both of round 4's artifacts.
    """
    index = lineno - 1
    if index < 0 or index >= len(lines):
        raise ValueError(f"line {lineno} is outside the file")

    def is_body(i: int) -> bool:
        return lines[i].lstrip(" \t").startswith("#") and lines[i].strip() != "#"

    if not is_body(index):
        raise ValueError(f"line {lineno} is not inside a comment paragraph")
    block_start = index
    while block_start > 0 and is_body(block_start - 1):
        block_start -= 1
    block_end = index + 1
    while block_end < len(lines) and is_body(block_end):
        block_end += 1

    def indent(i: int) -> int:
        return _indent_of(lines[i][len(_head(lines[i])) :])

    start = block_start
    while start < block_end:
        nxt = start + 1
        column = indent(nxt) if nxt < block_end and indent(nxt) >= indent(start) else indent(start)
        end = start + 1
        while end < block_end and indent(end) == column:
            end += 1
        if start <= index < end:
            return start, end
        start = end
    raise AssertionError("the anchor line is inside the block it was found in")


def reflow(lines: list[str], width: int = DEFAULT_WIDTH) -> list[str]:
    """Rewrap one comment paragraph, preserving every word and its order."""
    if not lines:
        raise ValueError("nothing to reflow: the range resolved to no lines")

    head = _head(lines[0])
    for line in lines[1:]:
        if _head(line) != head:
            raise ValueError(f"the range spans two indent levels: {line!r}")
    for line in lines:
        if line.strip() == "#":
            raise ValueError("the range spans a `#` separator, so two paragraphs")

    # `after` is what follows the `#`, indent included.
    afters = [line[len(head) :] for line in lines]
    column = _indent_of(afters[1] if len(afters) > 1 else afters[0])

    first = afters[0]
    label = first[:column]
    # A FIRST LINE THAT DOES NOT REACH THE COLUMN CARRIES NO PROSE, so there is
    # nothing there a label could be confused with and the two-space separator
    # is not needed to tell them apart. A term long enough to fill its own line
    # is written that way in these tables; the padding below is what puts the
    # continuation prose under the column rather than against the term.
    if len(first) > column and label.strip() and not label.endswith("  "):
        raise ValueError(f"cannot tell a label from prose in {lines[0]!r}")
    body = [first[column:]]
    for after, line in zip(afters[1:], lines[1:]):
        if _indent_of(after) < column:
            raise ValueError(f"line is left of the continuation column: {line!r}")
        body.append(after[column:])

    atoms = ATOM_RE.findall(" ".join(body))
    if not atoms:
        raise ValueError("the range carries no prose")

    lead = head + label.ljust(column)
    cont = head + " " * column
    # A quoted run that cannot fit even alone on a continuation line is split
    # back into its words HERE, before filling, so the filler itself never has
    # to decide whether an atom is really atomic.
    words: list[str] = []
    for atom in atoms:
        if len(cont) + len(atom) > width:
            words.extend(atom.split())
        else:
            words.append(atom)

    out: list[str] = []
    current = lead + words[0]
    for word in words[1:]:
        if len(current) + 1 + len(word) <= width:
            current += " " + word
        else:
            out.append(current)
            current = cont + word
    out.append(current)
    return out


def _indent_of(after: str) -> int:
    return len(after) - len(after.lstrip(" "))
