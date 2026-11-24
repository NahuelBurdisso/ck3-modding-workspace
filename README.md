# CK3 modding workspace

Tooling for developing Crusader Kings III mods against vanilla CK3 and the A Game of Thrones (AGOT)
submod stack. It exists because CK3 script fails silently: a wrong key, a missing localization entry
or a file another mod fully replaces produces no error, only a mod that does nothing. The tools here
make those failures visible before the game is launched.

The mods built with it are in [ck3-mods](https://github.com/NahuelBurdisso/ck3-mods) and
[battle-chronicles](https://github.com/NahuelBurdisso/battle-chronicles).

## What is here

| Path | What |
|---|---|
| `tools/ck3.py` | The CLI |
| `tools/ck3lib/` | Library behind it: a Paradox-script parser, a SQLite index of the game and every installed mod, validator, scaffolder, playset editor, launcher |
| `tools/_*.py` | Single-purpose analysis scripts (file-collision merges, localization ledgers, trigger and trait scans) |
| `tools/tests/` | Tests for the library |
| `_*.py` | Save-game queries: characters, houses, titles, straight from a `.ck3` save |
| `docs/reference/` | Folder map, script cheatsheet, gotchas, workflow, playbook |
| `docs/api/<version>/` | The engine's own `script_docs` dump: effects, triggers, scopes, on_actions, modifiers |
| `docs/specs`, `docs/plans`, `docs/battle-chronicles` | Design docs, implementation plans and run ledgers for Battle Chronicles |
| `.claude/` | Agent and skill definitions used to drive the workflow with Claude Code |

## CLI

```
python tools/ck3.py doctor | index | stats
python tools/ck3.py where <relpath> | find <key> [--partial] | loc <key>
python tools/ck3.py conflicts
python tools/ck3.py new "Name" [--agot] [--deploy] | deploy <slug> | validate <slug> [--strict]
python tools/ck3.py playset list|add|remove|move|audit
python tools/ck3.py api <key> [--kind effects|triggers|...] [--partial]
python tools/ck3.py launch [--clear-logs] | errors | probe <regex>
```

- `index` builds a SQLite database of every script key and localization key in the game and in each
  installed mod, so `find`, `where` and `loc` answer "who defines this, and who wins" instantly.
- `conflicts` lists files that more than one enabled mod fully replaces.
- `validate` checks a mod against the index and the engine API dump before it is deployed.
- `launch`, `errors` and `probe` start the game, then read its error log for a mod's own lines.

## Setup

Python 3. All machine-specific paths (game, user data, workshop) live in `ck3.config.json`; edit that
file for your install. The index, logs and mod sources (`mods/`, one repository each) are not tracked.
