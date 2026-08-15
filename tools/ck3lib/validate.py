"""Static checks for a mod folder.

Catches the failure modes that CK3 reports badly or not at all: unbalanced
braces (silently truncates the rest of the file), missing UTF-8 BOM on
localization (whole file ignored), malformed loc lines, duplicate definitions,
and descriptor mistakes.

Also checks: (a) `localization_key` arms in common/customizable_localization/
resolve to a loc key owned by this mod; (b) `[scope.Custom('...')]` calls in
the mod's localization resolve to a customizable_localization definition in
this mod; (c) [mod-specific] the Battle Chronicles six ground bands partition
every AGOT base terrain helper exactly once; (d) `file.txt:123` citations in
comments land on a line of that file that carries content.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from .paths import Config, version_matches
from .pdxscript import brace_report, has_bom, parse_descriptor, parse_loc, read_text, top_level_defs
from .sources import SCAN_DIRS, iter_files, playset_sources

ERROR = "error"
WARN = "warn"
INFO = "info"

REQUIRED_DESCRIPTOR_KEYS = ("name", "version", "supported_version", "tags")
LOC_FILENAME = re.compile(r"^(.+)_l_([a-z_]+)\.yml$")
KNOWN_LANGS = {
    "english",
    "french",
    "german",
    "japanese",
    "korean",
    "polish",
    "russian",
    "simp_chinese",
    "spanish",
}
# Categories where every definition is expected to have a matching loc key.
LOC_EXPECTED = {"common/traits", "common/decisions", "common/character_interactions"}

# Customizable localization: `localization_key = X` inside an arm names a loc
# key that must exist, and `[scope.Custom('name')]` inside a loc value names a
# customizable_localization definition that must exist. CK3 reports neither.
# A missing loc key renders as the raw key; a missing definition renders as
# nothing at all, which is indistinguishable from an arm that did not match.
CUSTOM_LOC_DIR = "common/customizable_localization/"
# Namespace prefix that identifies keys this mod could plausibly own.
# Battle-Chronicles-specific: a future multi-mod workspace will need to
# generalise this (e.g. read it from the descriptor or a workspace config).
# Used by both the localization_key arm check and the Custom() call check so
# the two agree on what "owned by this mod" means.
# NOT A TOTAL CHECK: a typo that damages the prefix itself (`bcfrag_x` for
# `bc_frag_x`) reads as a foreign key and is skipped silently. Inherent to
# prefix namespacing; the alternative is resolving every arm against the whole
# playset, which is ~770k loc keys across 48 sources per run.
MOD_KEY_PREFIX = "bc_"
# `[^\s#]+` and not `\S+`: `localization_key = bc_x# note` is a legal comment
# with no space before it, and `\S+` would capture `bc_x# note`'s first token
# as the key and false-error on it.
LOC_ARM_RE = re.compile(r"^\s*localization_key\s*=\s*([^\s#]+)", re.M)
CUSTOM_CALL_RE = re.compile(r"\.Custom2?\(\s*'([^']+)'")

# Comments in this workspace cite each other by `file.txt:123` and `file.txt:1-9`,
# and continue with a bare `:456` once the file has been named in the same
# comment paragraph. Nothing enforced them until now, and review rounds on Battle
# Chronicles repeatedly lost time to a citation that was correct when written and
# silently wrong after an unrelated comment ABOVE it grew: every line below a
# comment edit shifts, and a shifted citation still points at a real line, so it
# reads as fine.
#
# WHAT THIS CHECKS IS POSITION, NOT MEANING. The full list of what it will
# report: a citation landing on a blank line, on a bare `#`, on the `}` that
# closes a block (allowed as the END of a range, never as its start), past the
# end of the file, below line 1, a range that runs backwards, a `bc_`-named
# target this mod does not contain, and - as a warning, since it cannot be
# resolved either way without guessing - a target basename that more than one
# file in the mod carries. What it CANNOT report is the case that has
# cost the most: `:270` now names an `exists` guard where it used to name the
# `>=` comparison the sentence is about. Every number in that list is a real
# line. The mitigation for that is not mechanical - cite a named paragraph or a
# definition rather than a line, so the reference moves with the thing it names.
#
# TWO PATTERNS, AND THE BROAD ONE IS NOT AN ACCIDENT. The narrow pattern decides
# what to RESOLVE; the broad one decides what CLEARS the running target. They
# have to differ, because `effects.log:9770 (grudge), :9810 (nemesis)` is a real
# line in this mod (bc_rivalry_effects.txt, the `grudge` note): the log file
# cannot be resolved, but if it did not clear the target then `:9810` would
# resolve against whatever mod file was named earlier in the paragraph. Matching
# only resolvable extensions in one pattern is what made that bug possible in
# the first version of this check. Clearing is POSITIONAL, and the note in
# `_check_citations` on the single ordered pass says why that matters.
#
# CITE_EXTS AND THE NARROW PATTERN ARE ONE DECLARATION ON PURPOSE. The set names
# which files this check will open; the pattern names which citations it will try
# to open one for. Written twice they drift, and the drift is invisible: a
# citation whose extension is in the set but not the pattern silently stops being
# checked, which is exactly the failure mode this whole check exists to end.
# `.md` is in the set so README.md gets the position check at all - it is the
# largest body of prose here and it cites the scripts constantly. Note what that
# does NOT buy: the two README citations round 9 caught had drifted onto real
# lines, which is the case above that no check can see.
CITE_EXTS = {".txt", ".yml", ".gui", ".info", ".md"}
CITE_TAIL = r":(\d+)(?:-(\d+))?"
_CITE_EXT_ALT = "|".join(sorted(ext.lstrip(".") for ext in CITE_EXTS))
# The STEM is shared for the same reason the extension is. When the two stems
# differed, `bc_missing-2.txt:1` matched the broad pattern, failed the narrow
# one, and was dropped as unresolvable - so a `bc_` file that does not exist
# escaped the error, purely because of a hyphen. `(?i:...)` closes the same
# escape in the other direction: CITE_EXTS is lowercase and the target side
# lowercases `suffix`, so without it `BC_T.TXT:1` failed the narrow pattern and
# was dropped for its case alone. The prefix test in `_check_citations` is
# case-folded to match, or a mis-cased `bc_` name would be resolvable and then
# silently skipped for not looking like a mod file.
_CITE_STEM = r"[A-Za-z0-9_.-]+"
RESOLVABLE_CITE_RE = re.compile(r"\b(" + _CITE_STEM + r"\.(?i:" + _CITE_EXT_ALT + "))" + CITE_TAIL)
ANY_CITE_RE = re.compile(r"\b(" + _CITE_STEM + r"\.[A-Za-z0-9]{1,8})" + CITE_TAIL)
# `(?<![\w.])`: without it `bc_frag_x:0 "text"` in a loc file matches as `:0`.
# Only ever applied to comment lines, where a key/value pair cannot appear.
BARE_CITE_RE = re.compile(r"(?<![\w.])" + CITE_TAIL + r"\b")


@dataclass(frozen=True)
class Issue:
    level: str
    path: str
    line: int | None
    message: str

    def format(self) -> str:
        where = self.path if self.line is None else f"{self.path}:{self.line}"
        return f"{self.level.upper():5} {where}: {self.message}"


def _check_descriptor(mod_root: Path, cfg: Config, issues: list[Issue]) -> dict:
    descriptor = mod_root / "descriptor.mod"
    if not descriptor.is_file():
        issues.append(Issue(ERROR, "descriptor.mod", None, "missing descriptor.mod at mod root"))
        return {}
    data = parse_descriptor(read_text(descriptor))
    for key in REQUIRED_DESCRIPTOR_KEYS:
        if key not in data:
            issues.append(Issue(ERROR, "descriptor.mod", None, f"missing required key `{key}`"))
    supported = data.get("supported_version")
    if isinstance(supported, str) and not version_matches(supported, cfg.supported_version):
        issues.append(
            Issue(
                WARN,
                "descriptor.mod",
                None,
                f"supported_version={supported} but installed game is {cfg.supported_version}",
            )
        )
    if "path" in data and "\\" in str(data["path"]):
        issues.append(Issue(ERROR, "descriptor.mod", None, "path= contains backslashes; use forward slashes only"))
    return data


def _check_structure(mod_root: Path, issues: list[Issue]) -> None:
    # THE GIT ENTRIES ARE NAMED ONE AT A TIME ON PURPOSE. A `.git*` glob would
    # also pass a stray `.gitkeep` or a leftover `.git.orig`, and the point of
    # the warning is that the mod root is small enough to enumerate. The cost is
    # that a git file nobody anticipated warns until it is added here, which
    # `.gitattributes` did.
    allowed = set(SCAN_DIRS) | {
        "descriptor.mod",
        "thumbnail.png",
        ".git",
        ".gitattributes",
        ".gitignore",
        ".vscode",
        "README.md",
        "tests",
    }
    for entry in mod_root.iterdir():
        if entry.name not in allowed:
            issues.append(
                Issue(WARN, entry.name, None, "not a directory CK3 loads; it will be ignored by the game")
            )


def _check_script_file(relpath: str, path: Path, issues: list[Issue]) -> list[tuple[str, int]]:
    try:
        text = read_text(path)
    except OSError as exc:
        issues.append(Issue(ERROR, relpath, None, f"unreadable: {exc}"))
        return []
    opens, closes, first_bad = brace_report(text)
    if first_bad is not None:
        issues.append(Issue(ERROR, relpath, first_bad, "closing brace with no matching opening brace"))
    if opens != closes:
        issues.append(
            Issue(ERROR, relpath, None, f"unbalanced braces: {opens} `{{` vs {closes} `}}` (diff {opens - closes})")
        )
    if relpath.startswith(("common/", "events/", "history/")) and path.suffix.lower() == ".txt":
        return top_level_defs(text)
    return []


def _check_loc_file(relpath: str, path: Path, issues: list[Issue]) -> list[str]:
    name_match = LOC_FILENAME.match(path.name)
    parts = relpath.split("/")
    folder_lang = parts[1] if len(parts) > 2 else None

    if not has_bom(path):
        issues.append(Issue(ERROR, relpath, 1, "missing UTF-8 BOM; CK3 will ignore the entire file"))
    if not name_match:
        issues.append(Issue(ERROR, relpath, None, "filename must end with `_l_<language>.yml`"))
        return []
    file_lang = name_match.group(2)
    if file_lang not in KNOWN_LANGS:
        issues.append(Issue(WARN, relpath, None, f"unknown language `{file_lang}` in filename"))
    if folder_lang and folder_lang != file_lang:
        issues.append(
            Issue(ERROR, relpath, None, f"file is `_l_{file_lang}` but sits in localization/{folder_lang}/")
        )

    text = read_text(path)
    header_lang, entries, malformed = parse_loc(text)
    if header_lang is None:
        issues.append(Issue(ERROR, relpath, 1, "missing `l_<language>:` header line"))
    elif header_lang != file_lang:
        issues.append(Issue(ERROR, relpath, 1, f"header is `l_{header_lang}:` but filename says `_l_{file_lang}`"))
    for lineno, content in malformed:
        issues.append(Issue(ERROR, relpath, lineno, f'malformed entry, expected ` KEY:0 "text"` -> {content[:60]}'))

    seen: dict[str, int] = {}
    for entry in entries:
        if entry.key in seen:
            issues.append(
                Issue(WARN, relpath, entry.line, f"duplicate loc key `{entry.key}` (first at line {seen[entry.key]})")
            )
        else:
            seen[entry.key] = entry.line
    return list(seen)


def _scan_matches(path: Path, pattern: re.Pattern[str]) -> list[tuple[int, str]]:
    """Return (line, capture-group-1) for every match in the file."""
    text = read_text(path)
    return [(text.count("\n", 0, m.start()) + 1, m.group(1)) for m in pattern.finditer(text)]


# The 23 AGOT base terrain helpers, in band order. Held as an explicit list and
# not globbed: the `agot_is_*_terrain` glob matches 26 names, because AGOT also
# ships agot_is_majorroad_terrain, agot_is_minorroad_terrain and
# agot_is_location_valid_vanilla_terrain, which are cross-cutting or
# character-scoped and must not be banded.
BC_GROUND_BASES = [
    "drylands", "desert", "desert_mountains", "oasis", "canyon",
    "farmlands", "plains", "steppe", "floodplains", "urban",
    "hills", "mountains", "wetlands", "the_bog", "taiga_bog", "terraced_hills", "highlands",
    "forest", "taiga",
    "jungle", "cloudforest",
    "frozen_flats", "glacier",
]
BC_GROUND_NON_BASES = {"majorroad", "minorroad", "location_valid_vanilla"}
BC_GROUND_FILE = "common/scripted_triggers/bc_ground_triggers.txt"
AGOT_TERRAIN_FILE = "common/scripted_triggers/00_agot_terrain_type_triggers.txt"
TERRAIN_HELPER_RE = re.compile(r"agot_is_(\w+)_terrain")
TERRAIN_DEF_RE = re.compile(r"^agot_is_(\w+)_terrain\s*=\s*\{", re.M)


def _check_ground_partition(cfg: Config, mod_root: Path, issues: list[Issue]) -> None:
    """Mod-specific: the six ground bands must cover every AGOT base exactly once."""
    path = mod_root / BC_GROUND_FILE
    if not path.is_file():
        return

    found = TERRAIN_HELPER_RE.findall(read_text(path))
    for name in BC_GROUND_BASES:
        if name not in found:
            issues.append(Issue(ERROR, BC_GROUND_FILE, None, f"terrain `{name}` is in no ground band"))
    for name in found:
        if name not in BC_GROUND_BASES:
            issues.append(
                Issue(ERROR, BC_GROUND_FILE, None, f"`agot_is_{name}_terrain` is not a base terrain helper")
            )
    for name in sorted({n for n in found if found.count(n) > 1}):
        issues.append(Issue(ERROR, BC_GROUND_FILE, None, f"terrain `{name}` is in more than one ground band"))

    # THE OTHER HALF: has AGOT grown a terrain the bands do not know about?
    # BC_GROUND_BASES above is a frozen literal and can only ever catch drift on
    # the mod's side. Resolved through the playset the way `ck3.py api` and
    # `ck3.py find` do, last source wins.
    #
    # IT SKIPS LOUDLY, NEVER SILENTLY. A validate run on a machine with no
    # playset configured must say that the cross-check did not happen, because a
    # silent skip is indistinguishable from a pass and this check exists
    # precisely for the case nobody is looking.
    agot: Path | None = None
    for source in playset_sources(cfg):
        candidate = source.root / AGOT_TERRAIN_FILE
        if candidate.is_file():
            agot = candidate
    if agot is None:
        issues.append(
            Issue(WARN, BC_GROUND_FILE, None, f"SKIPPED the AGOT-side check: no enabled source provides {AGOT_TERRAIN_FILE}")
        )
        return
    shipped = {n for n in TERRAIN_DEF_RE.findall(read_text(agot))} - BC_GROUND_NON_BASES
    for name in sorted(shipped - set(BC_GROUND_BASES)):
        issues.append(
            Issue(ERROR, BC_GROUND_FILE, None, f"AGOT ships `agot_is_{name}_terrain`, which is in no ground band")
        )
    for name in sorted(set(BC_GROUND_BASES) - shipped):
        issues.append(
            Issue(ERROR, BC_GROUND_FILE, None, f"band uses `agot_is_{name}_terrain`, which AGOT no longer defines")
        )


def _citation_files(
    mod_root: Path,
) -> tuple[dict[str, list[str]], set[str], list[tuple[str, list[str]]]]:
    """Basename -> lines for TARGETS, the colliding basenames, and every CITER.

    THE TARGET SIDE AND THE CITER SIDE ARE DIFFERENT COLLECTIONS ON PURPOSE. A
    citation names a basename, so the target side has to be keyed by one and can
    hold only one file per key. The citer side is a list of paths, so it holds
    every file. Keying both by basename - which the first version did - meant the
    second file to claim a shared basename was never scanned for its own outgoing
    citations, silently, with nothing reported.

    EVERY FILE WITH A CITABLE EXTENSION, WHEREVER IT SITS. This deliberately does
    not use `iter_files`: that walks SCAN_DIRS, and anything outside them - a
    root-level README.md, or a `tests/` directory `_check_structure` explicitly
    allows - would be invisible as a citer AND as a target. The target half is
    the worse one: a citation into a file that IS present then reports the false
    "this mod does not contain it", though only for a `bc_`-prefixed name, since
    that is the only kind `_check_citations` claims to know about. descriptor.mod
    falls out anyway because `.mod` is not in CITE_EXTS, which is fine: nine
    lines, and nothing in the mod cites a line of it.
    """
    texts: dict[str, list[str]] = {}
    ambiguous: set[str] = set()
    citers: list[tuple[str, list[str]]] = []
    # WALK THE WHOLE MOD, NOT SCAN_DIRS. Three rounds running found a file the
    # citation check could not see, each time in a different dimension: fc6792f
    # a root-level file, ec8eced a basename shadowed by another file's, d904308
    # any `.md` at all, because the walk fell back to SCRIPT_EXTS and CITE_EXTS
    # minus SCRIPT_EXTS is exactly `{".md"}`. Each time the file was invisible in
    # BOTH directions. `tests/` was the next one queued up: `_check_structure`
    # allows it at root and SCAN_DIRS does not list it. Rather than enumerate the
    # exceptions a fourth time, the extension is now the only filter.
    #
    # os.walk RATHER THAN rglob SO `.git` CAN BE PRUNED. rglob yields every git
    # object and then discards it per-path; on this mod that was 1074 of 1117
    # entries, and it grows with the object count, not with the mod. Pruning
    # dirnames in place stops the descent instead.
    for dirpath, dirnames, filenames in os.walk(mod_root):
        # Sorted as well as pruned, so issue order is stable across runs and
        # filesystems. Only that: which file of a colliding pair wins the
        # `texts` slot is NOT observable, because `_check_citations` tests
        # `target in ambiguous` before it reads `texts` and returns there.
        # Note the order is stable but NOT the order `sorted(rglob("*"))` gave:
        # os.walk emits a directory's own files before descending, so
        # root-level README.md now leads the report instead of trailing it.
        dirnames[:] = sorted(name for name in dirnames if name != ".git")
        for filename in sorted(filenames):
            path = Path(dirpath) / filename
            # `is_file()` is not redundant with the suffix test. os.walk puts
            # anything that is not a directory into `filenames`, INCLUDING a
            # broken symlink, and `read_text` calls `read_bytes` with no
            # handler - so dropping this guard turned a skipped entry into a
            # FileNotFoundError traceback out of `validate`. Windows junctions
            # happen to land in `dirnames` and are safe either way; a real
            # symlink on a Linux or WSL checkout is not.
            if not path.is_file() or path.suffix.lower() not in CITE_EXTS:
                continue
            relpath = path.relative_to(mod_root).as_posix()
            # splitlines(), not a newline split: the latter leaves a phantom
            # empty last element on any file ending in a newline, which is every
            # file, and a citation one past the last real line would then be
            # reported as landing on a blank line rather than as off the end.
            lines = read_text(path).splitlines()
            citers.append((relpath, lines))
            # No path is walked twice, so a repeated basename is always a second
            # FILE. An earlier version compared the stored path here because it
            # concatenated two candidate lists that could overlap; that guard
            # would now be dead, and dead code implies a case that can occur.
            if filename in texts:
                ambiguous.add(filename)
                continue
            texts[filename] = lines
    return texts, ambiguous, citers


def _check_citations(mod_root: Path, issues: list[Issue]) -> None:
    """Every `file.txt:N` in a comment must land on a line that carries content.

    ONLY FILES THIS MOD OWNS CAN BE RESOLVED. A citation into vanilla, AGOT or a
    game log names a file the checker cannot see, and skipping it is correct -
    but it must also stop a following bare `:N` from resolving against whatever
    mod file was named before it, which is why the clearing decision uses
    ANY_CITE_RE and the resolving decision uses RESOLVABLE_CITE_RE.

    A NAME THAT LOOKS LIKE THIS MOD'S AND RESOLVES TO NOTHING IS AN ERROR, not a
    skip. Renaming or mistyping a script is exactly the visible event this check
    exists to produce; treating it as "some file I cannot see" would hide it.

    A basename two files in the mod share cannot be resolved either way without
    guessing, so a citation naming one is reported once and left unchecked. Both
    files are still scanned for their OWN citations - see the note on the two
    collections in `_citation_files`.

    NOT CHECKED, and none of these are oversights this can close: meaning, per
    the module note on RESOLVABLE_CITE_RE; any target outside CITE_EXTS, which
    is why a `.log` or `.py` citation is skipped; a citation in a comment that
    TRAILS code on the same line, since a script line is taken whole and a line
    that is not entirely a comment ends the paragraph - no such citation exists
    in this mod, and the rule that a comment owns its own line is worth keeping;
    and the D:/ck3 docs repo, which `validate` never sees because it takes one
    mod folder as its argument.
    """
    texts, ambiguous, citers = _citation_files(mod_root)
    reported_ambiguous: set[str] = set()

    def resolve(citing: str, line_no: int, target: str, start: int, end: int | None) -> None:
        lines = texts[target]
        # `end is not None`, not `end`, and THIS is the spelling that matters:
        # `bc_x.txt:1-0` is a reversed range, not a range with no end, and
        # under truthiness it fell through here silently. The same spelling in
        # the loop below is defensive only - by the time control reaches it,
        # end >= start >= 1, where the two spellings cannot differ. Mutating
        # the loop alone leaves every test passing; mutating this line does
        # not. Do not read the loop as the thing that catches `-0`.
        if end is not None and end < start:
            issues.append(
                Issue(ERROR, citing, line_no, f"cites {target}:{start}-{end}, which runs backwards")
            )
            return
        for number, is_range_end in [(start, False)] + ([(end, True)] if end is not None else []):
            if number < 1:
                issues.append(
                    Issue(ERROR, citing, line_no, f"cites {target}:{number}, and there is no line {number}")
                )
                continue
            if number > len(lines):
                issues.append(
                    Issue(ERROR, citing, line_no, f"cites {target}:{number}, past the end of that file ({len(lines)} lines)")
                )
                continue
            body = lines[number - 1].strip()
            # A range may legitimately END on the `}` that closes the block it
            # spans. A citation that STARTS there names nothing.
            if body in ("", "#") or (body == "}" and not is_range_end):
                issues.append(
                    Issue(ERROR, citing, line_no, f"cites {target}:{number}, which is `{lines[number - 1].strip()}`")
                )

    for relpath, lines in citers:
        current: str | None = None
        # IN MARKDOWN EVERY LINE IS PROSE. Restricting to `#` lines the way the
        # script files need would reduce README.md to heading text, i.e. to
        # nothing, and the README is the file whose citations rot fastest. A
        # blank line ends a paragraph there, which is the same rule by a
        # different marker.
        prose_everywhere = relpath.lower().endswith(".md")
        for line_no, line in enumerate(lines, 1):
            stripped = line.strip()
            # A bare `#` ends a paragraph in this house style, and a running
            # target must not survive one: a `:456` three paragraphs below the
            # file that was named would otherwise resolve against it.
            if prose_everywhere:
                if not stripped:
                    current = None
                    continue
            elif not stripped.startswith("#") or stripped == "#":
                current = None
                continue
            # ONE PASS IN DOCUMENT ORDER, and two passes is a bug rather than a
            # tidier spelling. A bare `:N` belongs to whatever file was named
            # BEFORE it on the line, so `00_court_poet_tasks.txt:94-98 ... :47
            # ... bc_commander_phase_events.txt:65` must leave `:47` attached to
            # the vanilla file - i.e. unresolvable - not to the mod file named
            # after it. Collecting the full citations first and then sweeping
            # the bare ones against the survivor attaches every bare citation on
            # the line to the LAST full one, which reports correct citations as
            # broken and lets broken ones through. That was live on
            # README.md:615 the day this was written.
            full = list(ANY_CITE_RE.finditer(line))
            spans = [match.span() for match in full]
            bare = [
                match
                for match in BARE_CITE_RE.finditer(line)
                if not any(lo <= match.start() < hi for lo, hi in spans)
            ]
            for match in sorted(full + bare, key=lambda m: m.start()):
                if match.re is BARE_CITE_RE:
                    if current is not None:
                        resolve(relpath, line_no, current, int(match.group(1)), int(match.group(2)) if match.group(2) else None)
                    continue
                target = match.group(1)
                resolvable = RESOLVABLE_CITE_RE.fullmatch(match.group(0)) is not None
                if target in ambiguous:
                    if target not in reported_ambiguous:
                        reported_ambiguous.add(target)
                        issues.append(
                            Issue(WARN, relpath, line_no, f"cites `{target}`, a basename more than one file in this mod has")
                        )
                    current = None
                    continue
                if not resolvable or target not in texts:
                    if resolvable and target.lower().startswith(MOD_KEY_PREFIX):
                        issues.append(
                            Issue(ERROR, relpath, line_no, f"cites `{target}`, which this mod does not contain")
                        )
                    current = None
                    continue
                current = target
                resolve(relpath, line_no, current, int(match.group(2)), int(match.group(3)) if match.group(3) else None)


def validate_mod(cfg: Config, mod_root: Path, strict: bool = False) -> list[Issue]:
    issues: list[Issue] = []
    if not mod_root.is_dir():
        return [Issue(ERROR, str(mod_root), None, "mod folder does not exist")]

    _check_descriptor(mod_root, cfg, issues)
    _check_structure(mod_root, issues)
    _check_ground_partition(cfg, mod_root, issues)
    _check_citations(mod_root, issues)

    defs_by_key: dict[str, tuple[str, int]] = {}
    def_categories: list[tuple[str, str]] = []
    loc_keys: set[str] = set()
    vanilla_overrides: list[str] = []
    custom_loc_arms: list[tuple[str, int, str]] = []
    custom_calls: list[tuple[str, int, str]] = []

    for relpath, path in iter_files(mod_root):
        ext = path.suffix.lower()
        if (cfg.game_root / relpath).is_file():
            vanilla_overrides.append(relpath)

        if ext in (".txt", ".gui", ".gfx", ".asset", ".info"):
            if relpath.startswith(CUSTOM_LOC_DIR):
                for line, key in _scan_matches(path, LOC_ARM_RE):
                    custom_loc_arms.append((relpath, line, key))
            for key, line in _check_script_file(relpath, path, issues):
                if key in defs_by_key:
                    prev_file, prev_line = defs_by_key[key]
                    issues.append(
                        Issue(WARN, relpath, line, f"`{key}` also defined in {prev_file}:{prev_line}")
                    )
                else:
                    defs_by_key[key] = (relpath, line)
                    parts = relpath.split("/")
                    category = "/".join(parts[:2]) if len(parts) > 2 else parts[0]
                    def_categories.append((category, key))
        elif ext == ".yml" and relpath.startswith("localization/"):
            loc_keys.update(_check_loc_file(relpath, path, issues))
            for line, key in _scan_matches(path, CUSTOM_CALL_RE):
                custom_calls.append((relpath, line, key))

    # Only this mod's own keys. A localization_key arm naming a vanilla or
    # dependency loc key is legitimate and unresolvable from the mod root alone.
    for relpath, line, key in custom_loc_arms:
        if key.startswith(MOD_KEY_PREFIX) and key not in loc_keys:
            issues.append(
                Issue(ERROR, relpath, line, f"`localization_key = {key}` has no loc entry in this mod")
            )

    # Only this mod's own keys. A Custom() call naming a vanilla or AGOT
    # definition is legitimate and unresolvable from the mod root alone.
    custom_loc_defs = {key for category, key in def_categories if category.rstrip("/") == CUSTOM_LOC_DIR.rstrip("/")}
    for relpath, line, key in custom_calls:
        if key.startswith(MOD_KEY_PREFIX) and key not in custom_loc_defs:
            issues.append(
                Issue(ERROR, relpath, line, f"`Custom('{key}')` has no customizable_localization definition in this mod")
            )

    if strict:
        for category, key in def_categories:
            if category in LOC_EXPECTED and key not in loc_keys and not key.startswith("@"):
                issues.append(Issue(WARN, category, None, f"`{key}` has no localization key in this mod"))

    if vanilla_overrides:
        issues.append(
            Issue(INFO, "-", None, f"overrides {len(vanilla_overrides)} vanilla file(s); first: {vanilla_overrides[0]}")
        )
    return issues


def summarize(issues: list[Issue]) -> dict[str, int]:
    out = {ERROR: 0, WARN: 0, INFO: 0}
    for issue in issues:
        out[issue.level] = out.get(issue.level, 0) + 1
    return out
