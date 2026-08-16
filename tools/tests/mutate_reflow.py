"""Mutation harness for tools/tests/test_reflow.py.

WHY THIS ONE MATTERS MORE THAN ITS SIBLINGS. `reflow.py` rewrites prose in place
in the only design record this workspace has. A validator that goes blind reports
a clean file and someone eventually notices; a reflow that goes subtly wrong
edits the comments, is committed, and the damage IS the record. So the question
this file answers is not whether test_reflow.py passes but whether it would
still object once the module stopped doing what its comments say.

THE MUTANT LIST IS THE COMMENT LIST. Every entry undoes one decision that
reflow.py argues for in prose - the quoted alternatives leading the regex, the
punctuation carried by `\\S*`, the split-back for an atom that cannot fit alone,
the continuation column read off the second line, each of the six refusals - and
names the behaviour that has to break. A decision defended in a comment and
pinned by no test is a decision that will be undone by the next edit.

WHAT IS DELIBERATELY NOT MUTATED. `indent(nxt) >= indent(start)` in
`find_paragraph` is not weakened to `>`. On a plain paragraph every line shares
one indent, so both readings pick the same column and the mutant is EQUIVALENT
rather than surviving; telling them apart needs a table whose continuations are
indented less than their own label, which is not a shape these files contain.
`_indent_of` counting only spaces is likewise left alone: a tab inside the
continuation region would already have been refused by the `_head` comparison.

Run it with `python tools/tests/mutate_reflow.py`. Exit 0 means every mutant was
killed.
"""

from __future__ import annotations

from pathlib import Path

from mutate import run_mutants

TOOLS = Path(__file__).resolve().parents[1]
TARGET = TOOLS / "ck3lib" / "reflow.py"
SUITE = TOOLS / "tests" / "test_reflow.py"

MUTANTS = [
    # --- the atom regex, which is the whole defence of a grep target ------
    # THE FIRST DRAFT'S ORDERING. A leading `\S+` matches `"man` and never looks
    # for the closing quote, which is how a grep target got split across two
    # lines on this module's very first real paragraph.
    (
        "atoms: put the bare-word alternative first again",
        r'ATOM_RE = re.compile(r"\S*\x60[^\x60]*\x60\S*|\S*\"[^\"]*\"\S*|\S+")',
        r'ATOM_RE = re.compile(r"\S+|\S*\x60[^\x60]*\x60\S*|\S*\"[^\"]*\"\S*")',
    ),
    (
        "atoms: stop keeping backticked runs whole",
        r'ATOM_RE = re.compile(r"\S*\x60[^\x60]*\x60\S*|\S*\"[^\"]*\"\S*|\S+")',
        r'ATOM_RE = re.compile(r"\S*\"[^\"]*\"\S*|\S+")',
    ),
    (
        "atoms: stop keeping double-quoted runs whole",
        r'ATOM_RE = re.compile(r"\S*\x60[^\x60]*\x60\S*|\S*\"[^\"]*\"\S*|\S+")',
        r'ATOM_RE = re.compile(r"\S*\x60[^\x60]*\x60\S*|\S+")',
    ),
    # The trailing `\S*` is what makes the comma after a closing quote travel
    # with the quote instead of becoming a token that can start a line.
    (
        "atoms: let punctuation break away from a closing quote",
        r'ATOM_RE = re.compile(r"\S*\x60[^\x60]*\x60\S*|\S*\"[^\"]*\"\S*|\S+")',
        r'ATOM_RE = re.compile(r"\S*\x60[^\x60]*\x60|\S*\"[^\"]*\"|\S+")',
    ),
    # --- an atom too long to fit alone ------------------------------------
    # Without the split-back the filler emits a quoted run wider than the
    # budget, and the over-width check is a count of KNOWN lines, so every new
    # one has to be argued for by hand.
    (
        "atoms: overflow rather than splitting a run that cannot fit alone",
        "        if len(cont) + len(atom) > width:",
        "        if False:",
    ),
    (
        "atoms: split every run, whether it fits alone or not",
        "        if len(cont) + len(atom) > width:",
        "        if True:",
    ),
    # --- the fill ---------------------------------------------------------
    (
        "fill: break a word that lands exactly on the budget",
        "        if len(current) + 1 + len(word) <= width:",
        "        if len(current) + 1 + len(word) < width:",
    ),
    (
        "fill: forget the space between two words",
        "        if len(current) + 1 + len(word) <= width:",
        "        if len(current) + len(word) <= width:",
    ),
    (
        "fill: measure the prose without the comment prefix",
        "        if len(current) + 1 + len(word) <= width:",
        "        if len(current) + 1 + len(word) - len(cont) <= width:",
    ),
    # --- the continuation column ------------------------------------------
    (
        "column: guess the column from the first line instead of the second",
        "    column = _indent_of(afters[1] if len(afters) > 1 else afters[0])",
        "    column = _indent_of(afters[0])",
    ),
    (
        "column: drop the hanging indent from continuation lines",
        '    cont = head + " " * column',
        "    cont = head",
    ),
    (
        "column: stop padding a label out to the column",
        "    lead = head + label.ljust(column)",
        "    lead = head + label",
    ),
    # --- the six refusals -------------------------------------------------
    (
        "refuse: rewrap a line that is not a comment",
        '        raise ValueError(f"not a comment line: {line!r}")',
        "        return line",
    ),
    (
        "refuse: merge two paragraphs across a bare `#`",
        '            raise ValueError("the range spans a `#` separator, so two paragraphs")',
        "            pass",
    ),
    (
        "refuse: rewrap two indent levels as one paragraph",
        '            raise ValueError(f"the range spans two indent levels: {line!r}")',
        "            pass",
    ),
    (
        "refuse: swallow a line left of the continuation column",
        '            raise ValueError(f"line is left of the continuation column: {line!r}")',
        "            pass",
    ),
    (
        "refuse: demand a separator from a first line that carries no prose",
        "    if len(first) > column and label.strip() and not label.endswith(\"  \"):",
        '    if label.strip() and not label.endswith("  "):',
    ),
    (
        "refuse: read prose as a label with no separator",
        '        raise ValueError(f"cannot tell a label from prose in {lines[0]!r}")',
        "        pass",
    ),
    (
        "refuse: accept an empty range",
        '        raise ValueError("nothing to reflow: the range resolved to no lines")',
        "        return []",
    ),
    # --- paragraph finding ------------------------------------------------
    # A block is cut at a bare `#` AND THEN by indent. Dropping either cut
    # flattens the collision table in bc_l_english.yml into one run of prose.
    (
        "paragraph: read a bare `#` as part of the block",
        '        return lines[i].lstrip(" \\t").startswith("#") and lines[i].strip() != "#"',
        '        return lines[i].lstrip(" \\t").startswith("#")',
    ),
    (
        "paragraph: stop cutting a block into entries by indent",
        "        column = indent(nxt) if nxt < block_end and indent(nxt) >= indent(start) else indent(start)",
        "        column = indent(start) if False else indent(start)",
    ),
    (
        "paragraph: anchor on a line that is not inside one",
        '        raise ValueError(f"line {lineno} is not inside a comment paragraph")',
        "        pass",
    ),
]


if __name__ == "__main__":
    raise SystemExit(run_mutants(TARGET, SUITE, MUTANTS))
