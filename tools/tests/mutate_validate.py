"""Mutation harness for tools/tests/test_validate.py.

WHY IT EXISTS AT ALL. Only one suite in this directory had a harness before this
one: `mutate_sweep_backticks.py`, added in 2bc0257. `test_citations.py` still
has none. The suite THIS file points at was written in a single sitting, against
an implementation that already worked, and every test in it passed the first
time it ran. THAT IS THE WORST CASE FOR A TEST FILE, not the best: a suite
written to describe code that already does the right thing cannot tell you
whether it would notice the code doing the wrong one. 444716d - "close the
vacuous tests round 15 found" - is what that costs when nothing checks, and
test_citations.py was written the same way this one was.

WHAT EACH ENTRY IS. A name, an exact anchor in tools/ck3lib/validate.py, and
what to put in its place. `mutate.py` beside this file owns the mechanism and
the reasoning for it. A SURVIVING MUTANT NAMES A VACUOUS TEST, or a behaviour
nothing pins at all.

BOTH DIRECTIONS ARE MUTATED WHERE A CHECK HAS TWO. Turning a check off finds a
test that never fires; widening a check finds a test that would pass against a
check firing on everything, which is the failure mode a suite of one-sided
assertions cannot see. The version check, the two customizable-localization
resolvers and the strict gate are all mutated both ways for that reason.

A CRASH IS NOT AUTOMATICALLY A SURVIVOR, and an earlier draft of this docstring
said it was. `mutate.py` reads a kill off `FAIL_RE`, which matches `... FAIL`
AND `... ERROR`, so a mutation that makes a check RAISE is reported by unittest
as an errored test, is named, and is a kill. Only a break that stops the suite
importing - no test ever runs, none is named - reaches the CRASHED branch. Two
mutants below are kept precisely because they raise: the early `return []` after
a bad loc filename, and the ground guard.

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
    (
        "structure: drop thumbnail.png from the allowlist",
        '        "thumbnail.png",\n',
        "",
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
    # ONE MUTANT PER PREFIX, DROPPED SINGLY. The widening entry above dies to
    # almost anything; it is the single drop that finds a test covering
    # `common/` and calling that the tuple.
    (
        "script: stop collecting definitions under common/",
        'startswith(("common/", ',
        "startswith((",
    ),
    (
        "script: stop collecting definitions under events/",
        '"events/", "history/"',
        '"history/"',
    ),
    (
        "script: stop collecting definitions under history/",
        ', "history/"))',
        "))",
    ),
    # RAISES NOTHING AND REPORTS NOTHING - the file is simply gone from the
    # run, which is the failure mode this whole module exists to end.
    (
        "script: swallow a file that cannot be read",
        '        issues.append(Issue(ERROR, relpath, None, f"unreadable: {exc}"))\n        return []',
        "        return []",
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
    # THE OTHER SIDE OF THAT BOUNDARY. At `> 1` a file sitting directly under
    # localization/ takes its own FILENAME as the folder language, which never
    # matches and false-errors on a legal layout.
    (
        "loc: read the filename as the folder it sits in",
        '    folder_lang = parts[1] if len(parts) > 2 else None',
        "    folder_lang = parts[1] if len(parts) > 1 else None",
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
    # RAISES RATHER THAN REPORTS, AND IS STILL A KILL. Without the early return
    # `name_match.group(2)` runs on None; the AttributeError is reported as an
    # errored test, which `FAIL_RE` matches by name.
    (
        "loc: keep checking a file whose name CK3 will not open",
        '        return []\n    file_lang = name_match.group(2)',
        "    file_lang = name_match.group(2)",
    ),
    # --- the ground partition -------------------------------------------
    # INVERTED RATHER THAN DELETED, and not for the reason an earlier draft
    # gave. Inverting is STRICTLY STRONGER than deleting: a mod without the file
    # falls through to `read_text` and raises exactly as deletion would, AND
    # every mod that has the file now returns before a single band is read, so
    # the whole check goes silent as well. One entry therefore covers both the
    # guard and the body it guards.
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
        "run: report the folder that does exist and scan the one that does not",
        "    if not mod_root.is_dir():",
        "    if mod_root.is_dir():",
    ),
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
    # --- what the file loop opens ----------------------------------------
    # ONE PER EXTENSION, DROPPED SINGLY, then the widening. A dropped extension
    # is silent: the file stops being braced-checked and its definitions stop
    # being collected, and nothing anywhere says so.
    (
        "run: stop opening .txt",
        '(".txt", ".gui"',
        '(".gui"',
    ),
    (
        "run: stop opening .gui",
        '".gui", ".gfx"',
        '".gfx"',
    ),
    (
        "run: stop opening .gfx",
        '".gfx", ".asset"',
        '".asset"',
    ),
    (
        "run: stop opening .asset",
        '".asset", ".info")',
        '".info")',
    ),
    (
        "run: stop opening .info",
        ', ".info"):',
        "):",
    ),
    (
        "run: open everything that is not localization",
        'if ext in (".txt", ".gui", ".gfx", ".asset", ".info"):',
        'if ext != ".yml":',
    ),
    # --- the two resolvers' patterns -------------------------------------
    (
        "run: stop recognising the two-scope Custom2 form",
        'CUSTOM_CALL_RE = re.compile(r"\\.Custom2?\\(\\s*\'([^\']+)\'")',
        'CUSTOM_CALL_RE = re.compile(r"\\.Custom\\(\\s*\'([^\']+)\'")',
    ),
    (
        "run: read a trailing comment as part of the arm key",
        'LOC_ARM_RE = re.compile(r"^\\s*localization_key\\s*=\\s*([^\\s#]+)", re.M)',
        'LOC_ARM_RE = re.compile(r"^\\s*localization_key\\s*=\\s*(\\S+)", re.M)',
    ),
    # --- the categories that expect localization -------------------------
    (
        "run: stop expecting localization for traits",
        '{"common/traits", ',
        "{",
    ),
    (
        "run: stop expecting localization for decisions",
        '"common/decisions", ',
        "",
    ),
    (
        "run: stop expecting localization for character interactions",
        ', "common/character_interactions"}',
        "}",
    ),
    (
        "run: expect localization for scripted effects as well",
        'LOC_EXPECTED = {"common/traits", "common/decisions", "common/character_interactions"}',
        'LOC_EXPECTED = {"common/traits", "common/decisions", "common/character_interactions", "common/scripted_effects"}',
    ),
    # --- the vanilla override notice -------------------------------------
    (
        "run: stop noticing that a file overrides vanilla",
        "        if (cfg.game_root / relpath).is_file():",
        "        if False:",
    ),
    (
        "run: collect the overrides and never report them",
        "    if vanilla_overrides:",
        "    if False:",
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
