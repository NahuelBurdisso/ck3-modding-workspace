"""Mutation harness for tools/tests/test_paths.py.

WHY A MODULE THIS SMALL IS WORTH GRADING. Nothing in paths.py is hard, and that
is exactly the problem: a test suite over a file of one-line properties passes
whether it pins the layout or merely restates it, and a wrong path here does not
raise. It yields an empty directory listing, which reads downstream as a clean
mod, an empty index, or a playset with nothing in it. The suite has to be shown
to notice a wrong path, not just to name one.

THE SELECTION RULE IS THE SILENT FAILURE. Every mutant below produces a path
that is well-formed, plausible, and points somewhere that does not exist -
`game_dir` without its `game/` folder, `mods_src` under the user directory
rather than the workspace - because that is the shape this module's real bugs
have. The two that are not path swaps are the two type conversions in
`load_config`, where the damage surfaces as a TypeError in some other file.

WHAT IS DELIBERATELY NOT MUTATED. `dlc_load`, `game_logs` and `run_logs` are
left alone. They are the same one-line join as the four properties that are
mutated, tested by the same assertions, and adding them would grade nothing the
list does not already grade - it would only make the list longer, and the value
of this list is that every entry means something.

Run it with `python tools/tests/mutate_paths.py`. Exit 0 means every mutant was
killed.
"""

from __future__ import annotations

from pathlib import Path

from mutate import run_mutants

TOOLS = Path(__file__).resolve().parents[1]
TARGET = TOOLS / "ck3lib" / "paths.py"
SUITE = TOOLS / "tests" / "test_paths.py"

MUTANTS = [
    # --- the derived paths ------------------------------------------------
    # THE INSTALL FOLDER AND THE `game/` FOLDER ARE NOT INTERCHANGEABLE. Only
    # the inner one mirrors a mod's own layout, so every vanilla lookup made
    # against the outer one resolves to nothing and reports nothing.
    (
        "root: point game_root at the install folder",
        '        return self.game_dir / "game"',
        "        return self.game_dir",
    ),
    (
        "exe: look for the binary beside the game data",
        '        return self.game_dir / "binaries" / "ck3.exe"',
        '        return self.game_root / "binaries" / "ck3.exe"',
    ),
    (
        "mods: put the deploy target in the workspace",
        '        return self.user_dir / "mod"',
        '        return self.workspace_dir / "mod"',
    ),
    (
        "mods: read our own sources from the user directory",
        '        return self.workspace_dir / "mods"',
        '        return self.user_dir / "mods"',
    ),
    (
        "index: keep the database at the workspace root",
        '        return self.workspace_dir / "index" / "ck3.sqlite3"',
        '        return self.workspace_dir / "ck3.sqlite3"',
    ),
    (
        "loc: default to english alone",
        'loc_languages: tuple[str, ...] = ("english", "spanish")',
        'loc_languages: tuple[str, ...] = ("english",)',
    ),
    # --- check ------------------------------------------------------------
    (
        "check: accept an install folder with no game folder in it",
        "        if not self.game_root.is_dir():",
        "        if not self.game_dir.is_dir():",
    ),
    (
        "check: stop looking after the first problem",
        "            problems.append(f\"game_dir invalid: {self.game_root} not found\")\n        if not self.user_dir.is_dir():",
        "            problems.append(f\"game_dir invalid: {self.game_root} not found\")\n            return problems\n        if not self.user_dir.is_dir():",
    ),
    (
        "check: never report a missing workshop directory",
        "        if not self.workshop_dir.is_dir():",
        "        if False:",
    ),
    (
        "check: say a directory is wrong without saying which one was tried",
        'problems.append(f"game_dir invalid: {self.game_root} not found")',
        'problems.append("game_dir invalid")',
    ),
    # --- load_config ------------------------------------------------------
    (
        "load: leave the directory keys as strings",
        "        raw[key] = Path(os.path.expandvars(raw[key]))",
        "        raw[key] = os.path.expandvars(raw[key])",
    ),
    (
        "load: stop expanding environment variables in a path",
        "        raw[key] = Path(os.path.expandvars(raw[key]))",
        "        raw[key] = Path(raw[key])",
    ),
    # A LIST INSIDE A FROZEN DATACLASS IS STILL MUTABLE, and this object is
    # handed to every tool in the tree.
    (
        "load: keep loc_languages as the list it was in the json",
        '        raw["loc_languages"] = tuple(raw["loc_languages"])',
        '        raw["loc_languages"] = list(raw["loc_languages"])',
    ),
    (
        "load: demand a loc_languages key the default exists to make optional",
        '    if "loc_languages" in raw:',
        "    if True:",
    ),
    # --- version_matches --------------------------------------------------
    (
        "version: compare the segments only one side has",
        "    for a, b in zip(left, right):",
        "    for a, b in zip(left, right, strict=True):",
    ),
    (
        "version: honour a wildcard only in the declaration",
        '        if a == "*" or b == "*":',
        '        if a == "*":',
    ),
    (
        "version: never report a mismatch",
        "        if a != b:\n            return False",
        "        if a != b:\n            continue",
    ),
    (
        "version: treat an undeclared version as a mismatch",
        "    if not supported or not game:\n        return True",
        "    if False:\n        return True",
    ),
    # --- to_pdx_path ------------------------------------------------------
    (
        "pdx: emit the separator the launcher rejects",
        '    return str(path).replace("\\\\", "/")',
        '    return str(path).replace("/", "\\\\")',
    ),
]


if __name__ == "__main__":
    raise SystemExit(run_mutants(TARGET, SUITE, MUTANTS))
