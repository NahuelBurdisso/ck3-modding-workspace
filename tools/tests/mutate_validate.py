"""Mutation harness for tools/tests/test_validate.py.

WHY IT EXISTS AT ALL, given that test_citations.py has had one for rounds. The
suite it points at was written in a single sitting, against an implementation
that already worked, and every test in it passed the first time it ran. THAT IS
THE WORST CASE FOR A TEST FILE, not the best: a suite written to describe code
that already does the right thing cannot tell you whether it would notice the
code doing the wrong one. Rounds 15 and 16 both found tests in test_citations.py
that passed against a build with the checked behaviour deleted, and those were
written the same way.

WHAT EACH ENTRY IS. A name, an exact anchor in tools/ck3lib/validate.py, and
what to put in its place. `mutate.py` beside this file owns the mechanism and
the reasoning for it. A SURVIVING MUTANT NAMES A VACUOUS TEST, or a behaviour
nothing pins at all.

BOTH DIRECTIONS ARE MUTATED WHERE A CHECK HAS TWO. Turning a check off finds a
test that never fires; widening a check finds a test that would pass against a
check firing on everything, which is the failure mode a suite of one-sided
assertions cannot see. The version check, the two customizable-localization
resolvers and the strict gate are all mutated both ways for that reason.

WHAT IS DELIBERATELY NOT MUTATED. Anything whose break stops the module
importing or raises inside a check: `mutate.py` counts a crash as a survivor,
correctly, because a suite that failed without naming a test saw nothing. Two
guards are in that class - `if not mod_root.is_dir()` and the early `return []`
after a bad loc filename - and both are reached instead through the value they
return, which is observable and which a test can assert on.

Run it with `python tools/tests/mutate_validate.py`. Exit 0 means every mutant
was killed.
"""

from __future__ import annotations

from pathlib import Path

from mutate import run_mutants

TOOLS = Path(__file__).resolve().parents[1]
TARGET = TOOLS / "ck3lib" / "validate.py"
SUITE = TOOLS / "tests" / "test_validate.py"

MUTANTS = [
    # --- descriptor.mod -------------------------------------------------
    (
        "descriptor: stop reporting a missing descriptor",
        'issues.append(Issue(ERROR, "descriptor.mod", None, "missing descriptor.mod at mod root"))',
        "pass",
    ),
    (
        "descriptor: skip the first required key",
        "    for key in REQUIRED_DESCRIPTOR_KEYS:",
        "    for key in REQUIRED_DESCRIPTOR_KEYS[1:]:",
    ),
    # THE VERSION CHECK, BOTH WAYS. Inverted, the mismatch goes silent and the
    # wildcard warns; a suite that only tested one of those passes one of these.
    (
        "descriptor: invert the version comparison",
        "if isinstance(supported, str) and not version_matches(supported, cfg.supported_version):",
        "if isinstance(supported, str) and version_matches(supported, cfg.supported_version):",
    ),
    (
        "descriptor: never warn about the version",
        "if isinstance(supported, str) and not version_matches(supported, cfg.supported_version):",
        "if False and isinstance(supported, str):",
    ),
    (
        "descriptor: report forward slashes instead of backslashes",
        'if "path" in data and "\\\\" in str(data["path"]):',
        'if "path" in data and "/" in str(data["path"]):',
    ),
    # --- the mod root ---------------------------------------------------
    (
        "structure: drop .gitattributes from the allowlist",
        '        ".gitattributes",\n',
        "",
    ),
    (
        "structure: stop allowing the directories CK3 loads",
        "    allowed = set(SCAN_DIRS) | {",
        "    allowed = set() | {",
    ),
    (
        "structure: warn about nothing",
        "        if entry.name not in allowed:",
        "        if False:",
    ),
    # --- braces ---------------------------------------------------------
    (
        "script: stop reporting an unbalanced count",
        "    if opens != closes:",
        "    if False:",
    ),
    (
        "script: stop reporting a stray closing brace",
        "    if first_bad is not None:",
        "    if False:",
    ),
    (
        "script: collect top-level definitions out of gui files too",
        'if relpath.startswith(("common/", "events/", "history/")) and path.suffix.lower() == ".txt":',
        'if relpath.startswith(("common/", "events/", "history/", "gui/")):',
    ),
    # --- localization ---------------------------------------------------
    (
        "loc: stop checking for the BOM",
        "    if not has_bom(path):",
        "    if False:",
    ),
    (
        "loc: forget which folder the file is in",
        '    folder_lang = parts[1] if len(parts) > 2 else None',
        "    folder_lang = None",
    ),
    (
        "loc: accept any language in the filename",
        "    if file_lang not in KNOWN_LANGS:",
        "    if False:",
    ),
    (
        "loc: stop comparing the folder to the filename",
        "    if folder_lang and folder_lang != file_lang:",
        "    if False:",
    ),
    (
        "loc: stop requiring the header line",
        "    if header_lang is None:",
        "    if False:",
    ),
    (
        "loc: stop comparing the header to the filename",
        "    elif header_lang != file_lang:",
        "    elif False:",
    ),
    (
        "loc: stop reporting malformed entries",
        "    for lineno, content in malformed:",
        "    for lineno, content in []:",
    ),
    (
        "loc: stop reporting duplicate keys",
        "        if entry.key in seen:",
        "        if False:",
    ),
    (
        "loc: return no keys at all",
        "    return list(seen)",
        "    return []",
    ),
    # --- the ground partition -------------------------------------------
    # INVERTED RATHER THAN DELETED. Deleting the guard makes `read_text` raise
    # on a mod that has no ground file, which `mutate.py` counts as a survivor
    # and which would say nothing about the suite either way.
    (
        "ground: skip every mod, not just the ones without bands",
        "    if not path.is_file():\n        return",
        "    if path.is_file():\n        return",
    ),
    (
        "ground: stop noticing a base in no band",
        "        if name not in found:",
        "        if False:",
    ),
    (
        "ground: stop noticing a helper that is not a base",
        "        if name not in BC_GROUND_BASES:",
        "        if False:",
    ),
    (
        "ground: stop noticing a base in two bands",
        "    for name in sorted({n for n in found if found.count(n) > 1}):",
        "    for name in sorted({n for n in found if found.count(n) > 2}):",
    ),
    (
        "ground: skip the AGOT-side check in silence",
        "        issues.append(\n            Issue(WARN, BC_GROUND_FILE, None, f\"SKIPPED the AGOT-side check: no enabled source provides {AGOT_TERRAIN_FILE}\")\n        )\n        return",
        "        return",
    ),
    (
        "ground: read the road helpers as terrain bands",
        "    shipped = {n for n in TERRAIN_DEF_RE.findall(read_text(agot))} - BC_GROUND_NON_BASES",
        "    shipped = {n for n in TERRAIN_DEF_RE.findall(read_text(agot))}",
    ),
    (
        "ground: stop noticing a terrain AGOT added",
        "    for name in sorted(shipped - set(BC_GROUND_BASES)):",
        "    for name in sorted(set()):",
    ),
    (
        "ground: stop noticing a terrain AGOT dropped",
        "    for name in sorted(set(BC_GROUND_BASES) - shipped):",
        "    for name in sorted(set()):",
    ),
    # --- the whole run ---------------------------------------------------
    (
        "run: return nothing for a mod folder that does not exist",
        'return [Issue(ERROR, str(mod_root), None, "mod folder does not exist")]',
        "return []",
    ),
    (
        "run: stop reporting a key defined twice",
        "                if key in defs_by_key:",
        "                if False:",
    ),
    (
        "run: stop resolving localization_key arms",
        "if key.startswith(MOD_KEY_PREFIX) and key not in loc_keys:",
        "if False:",
    ),
    # BOTH WAYS AGAIN. Dropping the prefix test makes the resolver fire on an
    # AGOT or vanilla name it cannot possibly resolve, which is a false error on
    # a correct mod and is the direction a one-sided suite misses.
    (
        "run: resolve every Custom() call, not just this mod's",
        "if key.startswith(MOD_KEY_PREFIX) and key not in custom_loc_defs:",
        "if key not in custom_loc_defs:",
    ),
    (
        "run: stop resolving Custom() calls",
        "if key.startswith(MOD_KEY_PREFIX) and key not in custom_loc_defs:",
        "if False:",
    ),
    (
        "run: make the localization warning unconditional",
        "    if strict:",
        "    if True:",
    ),
    (
        "run: expect localization for script-value macros too",
        '            if category in LOC_EXPECTED and key not in loc_keys and not key.startswith("@"):',
        "            if category in LOC_EXPECTED and key not in loc_keys:",
    ),
    (
        "run: expect localization in no category at all",
        '            if category in LOC_EXPECTED and key not in loc_keys and not key.startswith("@"):',
        '            if category in set() and key not in loc_keys and not key.startswith("@"):',
    ),
    # --- the counts every commit message quotes --------------------------
    (
        "summarize: start from an empty dict",
        "    out = {ERROR: 0, WARN: 0, INFO: 0}",
        "    out = {}",
    ),
    (
        "summarize: stop accumulating",
        "        out[issue.level] = out.get(issue.level, 0) + 1",
        "        out[issue.level] = 1",
    ),
]


if __name__ == "__main__":
    raise SystemExit(run_mutants(TARGET, SUITE, MUTANTS))
