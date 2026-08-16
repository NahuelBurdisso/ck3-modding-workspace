"""Mutation harness for tools/tests/test_pdxscript.py.

WHY A CHARACTERIZATION SUITE NEEDS THIS MORE THAN A TDD ONE DOES. test_pdxscript
was written against code that already worked, and every one of its 46 tests
passed on the first run. A suite written that way has no evidence behind it: a
test that asserts what the code already does passes whether it pins the
behaviour or merely restates it, and the difference is invisible until the
behaviour changes. Breaking the module on purpose is the only way to tell.

THE SELECTION RULE IS THE CALLER, NOT THE LINE. This module is deliberately
shallow, so most of it could be written several ways and be equally correct.
What is not negotiable is the handful of decisions some caller depends on:
`_OPERATORS` ordered longest-first, the string and comment states reset at the
newline, `expect_value` in `top_level_defs`, the `op` requirement in
`keys_matching`, the three-byte read in `has_bom`. Each mutant undoes one of
those and names the caller that would be wrong.

THE `if j == i` GUARD IS NOT ON THE LIST, and it is the one line here that most
deserves to be. Its only job is to advance the scanner past a character that can
neither start a word nor an operator; break it and `tokenize` loops forever. No
unittest assertion can grade that - a suite that never returns names no test -
so the mutant is a survivor whichever way it is scored, and scoring it costs the
harness its whole timeout budget. It was on the list once. Applying it hung the
run, and because a hung run is killed from outside, the `finally` that restores
the target never fired and pdxscript.py was left mutated on disk: the timeout in
mutate.py exists because of this entry, and removing the entry is what the
timeout's own report - "a mutant no test can grade" - recommends.

WHAT IS DELIBERATELY NOT MUTATED. The `for encoding in ("utf-8-sig", "utf-8")`
loop in `read_text` is not reduced to `("utf-8",)`: `utf-8` decodes a BOM to
`\\ufeff` rather than failing, so the mutant produces a different string but no
exception, and the only test that would see it is the BOM one - which is already
pinned by a mutant on the loop's presence as a whole. Two mutants for one
behaviour is noise in a list whose value is that every entry means something.

THREE MORE WERE TRIED AND WITHDRAWN AS EQUIVALENT, which is worth recording so
they are not proposed again. The `expect_value = False` and `pending = None`
that `top_level_defs` runs on `close` are DEAD DEFENSIVE CODE: `pending` is only
ever assigned at depth 0, a `close` at depth 0 drives the depth negative, and
every token after that is skipped until an `open` brings it back - and `open`
clears both fields itself. There is no input on which removing either changes an
answer. The mutant on that branch now takes the `depth -= 1`, which is the line
that does the work. Dropping `\\r` from the whitespace class in
`tokenize` changes nothing: `\\r` is also in the terminator set a word stops at,
so the scanner reaches it, matches no word, and skips it by the lone-character
guard - one branch later, same token stream. And rewriting `has_bom` as
`fh.read().startswith(...)` returns the same answer for every input including
the empty file; the difference is that it reads ten megabytes to look at three,
which is a cost, not a behaviour. `test_has_bom_does_not_read_the_whole_file`
states the intent and no assertion can catch the violation.

Run it with `python tools/tests/mutate_pdxscript.py`. Exit 0 means every mutant
was killed.
"""

from __future__ import annotations

from pathlib import Path

from mutate import run_mutants

TOOLS = Path(__file__).resolve().parents[1]
TARGET = TOOLS / "ck3lib" / "pdxscript.py"
SUITE = TOOLS / "tests" / "test_pdxscript.py"

MUTANTS = [
    # --- tokenize ---------------------------------------------------------
    # LONGEST FIRST. Reversed, `=` matches the `=` of `>=` and the `>` is left
    # to be skipped as an unexpected character, so `count >= 3` tokenizes as a
    # plain assignment and reads as a definition of `count`.
    (
        "tokenize: order the operators shortest first",
        '_OPERATORS = ("?=", ">=", "<=", "!=", "==", "=", ">", "<")',
        '_OPERATORS = ("=", ">", "<", "?=", ">=", "<=", "!=", "==")',
    ),
    (
        "tokenize: let an unterminated string run past its line",
        "        while j < n and text[j] != '\"' and text[j] != \"\\n\":",
        "        while j < n and text[j] != '\"':",
    ),
    (
        "tokenize: keep the quotes on a string token",
        'yield Token("str", text[i + 1 : j], line)',
        'yield Token("str", text[i : j + 1], line)',
    ),
    # THE ANCHOR CARRIES THE `i += 1` BELOW IT because `brace_report` counts
    # lines with the identical two lines and the shorter anchor matched both.
    (
        "tokenize: stop counting lines",
        "        if c == \"\\n\":\n            line += 1\n            i += 1",
        '        if c == "\\n":\n            line += 0\n            i += 1',
    ),
    (
        "tokenize: let a comment eat the newline that ends it",
        '        if c == "#":\n            while i < n and text[i] != "\\n":\n                i += 1\n            continue',
        '        if c == "#":\n            while i < n and text[i] != "\\n":\n                i += 1\n            i += 1\n            continue',
    ),
    # The terminator set is what ends a word. Drop `=` from it and `a=b` is one
    # word, which is the shape vanilla writes most of its script in.
    (
        "tokenize: stop ending a word at an operator character",
        "            while j < n and text[j] not in ' \\t\\r\\n{}=\"#<>!':",
        "            while j < n and text[j] not in ' \\t\\r\\n':",
    ),
    # --- strip_comments ---------------------------------------------------
    (
        "strip: carry the comment state across the newline",
        '        if c == "\\n":\n            in_comment = False\n            in_str = False',
        '        if c == "\\n":\n            in_comment = in_comment\n            in_str = False',
    ),
    (
        "strip: carry the string state across the newline",
        '        if c == "\\n":\n            in_comment = False\n            in_str = False',
        '        if c == "\\n":\n            in_comment = False\n            in_str = in_str',
    ),
    (
        "strip: keep the body of a string, braces and all",
        "        if in_str:\n            if c == '\"':\n                in_str = False\n            continue",
        "        if in_str:\n            if c == '\"':\n                in_str = False\n            out.append(c)\n            continue",
    ),
    (
        "strip: drop the newline along with the comment",
        '            out.append(c)\n            continue\n        if in_comment:',
        "            continue\n        if in_comment:",
    ),
    # --- brace_report -----------------------------------------------------
    (
        "braces: report the last negative line instead of the first",
        "            if depth < 0 and first_bad is None:",
        "            if depth < 0:",
    ),
    (
        "braces: stop counting lines, so the bad line is always the first",
        '        if c == "\\n":\n            line += 1\n        elif c == "{":',
        '        if c == "\\n":\n            line += 0\n        elif c == "{":',
    ),
    (
        "braces: count braces without stripping comments and strings",
        "    for c in strip_comments(text):",
        "    for c in text:",
    ),
    (
        "braces: stop tracking depth, so an unmatched close is never seen",
        "        elif c == \"}\":\n            depth -= 1",
        '        elif c == "}":\n            depth += 1',
    ),
    (
        "braces: report one count for both directions",
        "    return opens, closes, first_bad",
        "    return opens, opens, first_bad",
    ),
    # --- top_level_defs ---------------------------------------------------
    (
        "defs: report keys at every depth",
        "        if depth != 0:\n            continue",
        "        if False:\n            continue",
    ),
    (
        "defs: read the value of a scalar as another key",
        "        if expect_value:\n            expect_value = False\n            pending = None\n            continue",
        "        if False:\n            expect_value = False\n            pending = None\n            continue",
    ),
    (
        "defs: leave the depth raised after a block, hiding every later key",
        "        if tok.kind == \"close\":\n            depth -= 1",
        '        if tok.kind == "close":\n            depth += 0',
    ),
    (
        "defs: report a bare word that no operator follows",
        "        if tok.kind == \"op\":\n            if pending is not None:",
        '        if tok.kind == "word":\n            if pending is not None:',
    ),
    # --- keys_matching ----------------------------------------------------
    (
        "keys: match a word whether or not an operator follows it",
        '        if tok.kind == "op" and prev is not None and prev.kind == "word" and rx.match(prev.value):',
        "        if prev is not None and prev.kind == \"word\" and rx.match(prev.value):",
    ),
    (
        "keys: return only the first match",
        "            found.append((prev.value, prev.line))",
        "            found[:] = found or [(prev.value, prev.line)]",
    ),
    # --- parse_descriptor -------------------------------------------------
    (
        "descriptor: read a braced value as its first item rather than a list",
        "            if toks[i].kind == \"open\":",
        "            if False:",
    ),
    (
        "descriptor: run off the end of a truncated file",
        "            if i >= len(toks):\n                break",
        "            if False:\n                break",
    ),
    (
        "descriptor: collect only words from a braced value, not quoted strings",
        '                    if toks[i].kind in ("str", "word"):',
        '                    if toks[i].kind in ("word",):',
    ),
    # --- parse_loc --------------------------------------------------------
    (
        "loc: accept an entry that is not indented",
        "LOC_ENTRY = re.compile(r'^(\\s+)([A-Za-z0-9_.\\-]+):(\\d*)\\s+\"(.*)\"\\s*(?:#.*)?$')",
        "LOC_ENTRY = re.compile(r'^(\\s*)([A-Za-z0-9_.\\-]+):(\\d*)\\s+\"(.*)\"\\s*(?:#.*)?$')",
    ),
    (
        "loc: require the closing quote to end the line, rejecting a comment",
        "LOC_ENTRY = re.compile(r'^(\\s+)([A-Za-z0-9_.\\-]+):(\\d*)\\s+\"(.*)\"\\s*(?:#.*)?$')",
        "LOC_ENTRY = re.compile(r'^(\\s+)([A-Za-z0-9_.\\-]+):(\\d*)\\s+\"(.*)\"$')",
    ),
    (
        "loc: require a version number on every entry",
        "LOC_ENTRY = re.compile(r'^(\\s+)([A-Za-z0-9_.\\-]+):(\\d*)\\s+\"(.*)\"\\s*(?:#.*)?$')",
        "LOC_ENTRY = re.compile(r'^(\\s+)([A-Za-z0-9_.\\-]+):(\\d+)\\s+\"(.*)\"\\s*(?:#.*)?$')",
    ),
    (
        "loc: report a blank line as malformed",
        '        if not line or line.lstrip().startswith("#"):',
        '        if line.lstrip().startswith("#"):',
    ),
    (
        "loc: report a comment line as malformed",
        '        if not line or line.lstrip().startswith("#"):',
        "        if not line:",
    ),
    (
        "loc: leave the BOM on, so the language header never matches",
        "    for lineno, raw in enumerate(text.lstrip(BOM).splitlines(), start=1):",
        "    for lineno, raw in enumerate(text.splitlines(), start=1):",
    ),
    (
        "loc: number the lines from zero",
        "    for lineno, raw in enumerate(text.lstrip(BOM).splitlines(), start=1):",
        "    for lineno, raw in enumerate(text.lstrip(BOM).splitlines(), start=0):",
    ),
    (
        "loc: silently drop a malformed line instead of reporting it",
        "            bad.append((lineno, line.strip()))",
        "            pass",
    ),
    # --- read_text and has_bom --------------------------------------------
    (
        "read: raise on bytes that are not utf-8 instead of falling back",
        '    return data.decode("latin-1")',
        '    return data.decode("utf-8")',
    ),
    (
        "read: stop stripping the BOM",
        '    for encoding in ("utf-8-sig", "utf-8"):',
        '    for encoding in ("utf-8",):',
    ),
]


if __name__ == "__main__":
    raise SystemExit(run_mutants(TARGET, SUITE, MUTANTS))
