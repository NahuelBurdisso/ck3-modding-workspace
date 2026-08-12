"""Minimal tokenizer/reader for Paradox (Clausewitz/Jomini) script and .yml loc.

Not a full evaluator - it is deliberately shallow. Everything here only needs to
be correct enough to answer "what is defined where" and "is this file
structurally sane", which is what the index and the validator ask for.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

BOM = "\ufeff"

_OPERATORS = ("?=", ">=", "<=", "!=", "==", "=", ">", "<")


@dataclass(frozen=True)
class Token:
    kind: str  # word | str | op | open | close
    value: str
    line: int


def tokenize(text: str):
    """Yield Tokens. Comments are dropped; unterminated strings stop at EOL."""
    line = 1
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == "\n":
            line += 1
            i += 1
            continue
        if c in " \t\r":
            i += 1
            continue
        if c == "#":
            while i < n and text[i] != "\n":
                i += 1
            continue
        if c == "{":
            yield Token("open", "{", line)
            i += 1
            continue
        if c == "}":
            yield Token("close", "}", line)
            i += 1
            continue
        if c == '"':
            j = i + 1
            while j < n and text[j] != '"' and text[j] != "\n":
                j += 1
            yield Token("str", text[i + 1 : j], line)
            i = j + 1 if j < n and text[j] == '"' else j
            continue
        for op in _OPERATORS:
            if text.startswith(op, i):
                yield Token("op", op, line)
                i += len(op)
                break
        else:
            j = i
            while j < n and text[j] not in ' \t\r\n{}="#<>!':
                j += 1
            if j == i:  # lone unexpected char, skip it rather than spin
                i += 1
                continue
            yield Token("word", text[i:j], line)
            i = j


def strip_comments(text: str) -> str:
    """Remove comments and string bodies - used for brace counting only."""
    out = []
    in_str = False
    in_comment = False
    for c in text:
        if c == "\n":
            in_comment = False
            in_str = False
            out.append(c)
            continue
        if in_comment:
            continue
        if in_str:
            if c == '"':
                in_str = False
            continue
        if c == "#":
            in_comment = True
            continue
        if c == '"':
            in_str = True
            continue
        out.append(c)
    return "".join(out)


def brace_report(text: str) -> tuple[int, int, int | None]:
    """Return (open_count, close_count, line_of_first_negative_depth)."""
    depth = 0
    line = 1
    first_bad = None
    opens = closes = 0
    for c in strip_comments(text):
        if c == "\n":
            line += 1
        elif c == "{":
            depth += 1
            opens += 1
        elif c == "}":
            depth -= 1
            closes += 1
            if depth < 0 and first_bad is None:
                first_bad = line
    return opens, closes, first_bad


def top_level_defs(text: str) -> list[tuple[str, int]]:
    """Every `key = ...` assignment at depth 0, as (key, line)."""
    defs: list[tuple[str, int]] = []
    depth = 0
    pending: Token | None = None
    expect_value = False
    for tok in tokenize(text):
        if tok.kind == "open":
            depth += 1
            expect_value = False
            pending = None
            continue
        if tok.kind == "close":
            depth -= 1
            expect_value = False
            pending = None
            continue
        if depth != 0:
            continue
        if tok.kind == "op":
            if pending is not None:
                defs.append((pending.value, pending.line))
                pending = None
            expect_value = True
            continue
        if expect_value:
            expect_value = False
            pending = None
            continue
        pending = tok
    return defs


def keys_matching(text: str, pattern: str) -> list[tuple[str, int]]:
    """Every `key = ...` at ANY depth whose key matches `pattern`.

    Needed for nested definition files such as common/landed_titles, where the
    meaningful keys (k_*, c_*, b_*) live several levels down.
    """
    rx = re.compile(pattern)
    found: list[tuple[str, int]] = []
    prev: Token | None = None
    for tok in tokenize(text):
        if tok.kind == "op" and prev is not None and prev.kind == "word" and rx.match(prev.value):
            found.append((prev.value, prev.line))
        prev = tok
    return found


def parse_descriptor(text: str) -> dict[str, object]:
    """Read a .mod / descriptor.mod into {key: str | list[str]}."""
    result: dict[str, object] = {}
    toks = list(tokenize(text))
    i = 0
    while i < len(toks):
        tok = toks[i]
        if tok.kind == "word" and i + 1 < len(toks) and toks[i + 1].kind == "op":
            key = tok.value
            i += 2
            if i >= len(toks):
                break
            if toks[i].kind == "open":
                items: list[str] = []
                i += 1
                while i < len(toks) and toks[i].kind != "close":
                    if toks[i].kind in ("str", "word"):
                        items.append(toks[i].value)
                    i += 1
                result[key] = items
            else:
                result[key] = toks[i].value
        i += 1
    return result


# --- localization -------------------------------------------------------

LOC_HEADER = re.compile(r"^l_([a-z_]+):\s*$")
LOC_ENTRY = re.compile(r'^(\s+)([A-Za-z0-9_.\-]+):(\d*)\s+"(.*)"\s*(?:#.*)?$')


@dataclass(frozen=True)
class LocEntry:
    key: str
    version: str
    value: str
    line: int


def parse_loc(text: str) -> tuple[str | None, list[LocEntry], list[tuple[int, str]]]:
    """Return (language, entries, malformed_lines)."""
    lang = None
    entries: list[LocEntry] = []
    bad: list[tuple[int, str]] = []
    for lineno, raw in enumerate(text.lstrip(BOM).splitlines(), start=1):
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        header = LOC_HEADER.match(line)
        if header:
            lang = header.group(1)
            continue
        entry = LOC_ENTRY.match(line)
        if entry:
            entries.append(LocEntry(entry.group(2), entry.group(3), entry.group(4), lineno))
        else:
            bad.append((lineno, line.strip()))
    return lang, entries, bad


def read_text(path: Path) -> str:
    """Decode a game file. UTF-8 with or without BOM; latin-1 as last resort."""
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


def has_bom(path: Path) -> bool:
    with path.open("rb") as fh:
        return fh.read(3) == b"\xef\xbb\xbf"
