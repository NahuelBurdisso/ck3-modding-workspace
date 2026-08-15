"""Static checks for a mod folder.

Catches the failure modes that CK3 reports badly or not at all: unbalanced
braces (silently truncates the rest of the file), missing UTF-8 BOM on
localization (whole file ignored), malformed loc lines, duplicate definitions,
and descriptor mistakes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .paths import Config, version_matches
from .pdxscript import brace_report, has_bom, parse_descriptor, parse_loc, read_text, top_level_defs
from .sources import SCAN_DIRS, iter_files

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


def validate_mod(cfg: Config, mod_root: Path, strict: bool = False) -> list[Issue]:
    issues: list[Issue] = []
    if not mod_root.is_dir():
        return [Issue(ERROR, str(mod_root), None, "mod folder does not exist")]

    _check_descriptor(mod_root, cfg, issues)
    _check_structure(mod_root, issues)

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

    for relpath, line, key in custom_loc_arms:
        if key not in loc_keys:
            issues.append(
                Issue(ERROR, relpath, line, f"`localization_key = {key}` has no loc entry in this mod")
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
