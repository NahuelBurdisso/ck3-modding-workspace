"""Static checks for a mod folder.

Catches the failure modes that CK3 reports badly or not at all: unbalanced
braces (silently truncates the rest of the file), missing UTF-8 BOM on
localization (whole file ignored), malformed loc lines, duplicate definitions,
and descriptor mistakes.

Also checks: (a) `localization_key` arms in common/customizable_localization/
resolve to a loc key owned by this mod; (b) `[scope.Custom('...')]` calls in
the mod's localization resolve to a customizable_localization definition in
this mod; (c) [mod-specific] the Battle Chronicles six ground bands partition
every AGOT base terrain helper exactly once.
"""

from __future__ import annotations

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
    allowed = set(SCAN_DIRS) | {
        "descriptor.mod",
        "thumbnail.png",
        ".git",
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


def validate_mod(cfg: Config, mod_root: Path, strict: bool = False) -> list[Issue]:
    issues: list[Issue] = []
    if not mod_root.is_dir():
        return [Issue(ERROR, str(mod_root), None, "mod folder does not exist")]

    _check_descriptor(mod_root, cfg, issues)
    _check_structure(mod_root, issues)
    _check_ground_partition(cfg, mod_root, issues)

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
