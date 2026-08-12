# CK3 modding workspace

Crusader Kings III mod development. Targets vanilla CK3 and the AGOT submod
stack. Everything about paths lives in `ck3.config.json` — never hardcode a path.

## Layout

    ck3.config.json        game/user/workshop paths, base mod id, game version
    tools/ck3.py           CLI (see below)
    tools/ck3lib/          paths, pdxscript parser, index, validate, scaffold,
                           playset, launch
    mods/<slug>/           mod sources, one git repo each
    index/ck3.sqlite3      generated index, rebuildable, not tracked
    docs/reference/        folder-map, script-cheatsheet, gotchas, workflow,
                           playbook, sources
    logs/                  captured ck3.exe stdout

## CLI

    python tools/ck3.py doctor | index | stats
    python tools/ck3.py where <relpath> | find <key> [--partial] | loc <key>
    python tools/ck3.py conflicts
    python tools/ck3.py new "Name" [--agot] [--deploy] | deploy <slug> | validate <slug> [--strict]
    python tools/ck3.py playset list|add|remove|move|audit
    python tools/ck3.py launch [--clear-logs] | errors | probe <regex>
    python tools/ck3.py sync-workshop <id>

## Rules

- **Look it up, do not guess.** Before writing any effect, trigger, trait,
  on_action or loc key, run `ck3.py find` / `ck3.py loc` and read the vanilla
  definition the index points at. The index covers vanilla plus all 60+ enabled
  mods; a hallucinated key fails silently in-game.
- **Add files, do not replace them.** A file at a vanilla relative path replaces
  the vanilla file entirely. Prefer a new uniquely-named file. Check with
  `ck3.py where` before touching an existing path.
- **Prefix every invented key** with the mod slug. Collisions resolve silently in
  favour of whoever loads last.
- **Localization is UTF-8 with BOM**, entry format ` KEY:0 "text"`. No BOM = the
  whole file is ignored.
- **Run `ck3.py validate` before claiming anything works.** Braces, BOM and loc
  syntax fail silently in CK3.
- **Results come from `<user dir>/logs/`, never from stdout.** `debug_log` writes
  to `debug.log`; `[Checksum Builder]` stdout spam is not a file manifest. Read a
  run with `ck3.py probe <marker>`. Empty `logs/` after a session means a clean
  run, not a missing log.
- **Spike before you build.** A restart costs ~7 minutes, so one probe mod must
  answer every open question in one run. See `docs/reference/playbook.md`.
- **Script runs more often than it looks.** Never nest an unbounded iterator in a
  per-character pulse; use `trigger_if` rather than relying on early-out, because
  tooltip rendering evaluates every branch. See `docs/reference/playbook.md`.
- Never edit files under `SteamLibrary/` — workshop content is overwritten on
  update. Write a patch mod in `mods/` that loads last instead.
- Playset edits (`playset add/remove/move`) change what the user's game loads.
  Back-ups are automatic, but confirm with the user before reordering an
  existing playset.
- Claude cannot subscribe to Steam Workshop items. Ask the user to do it.

## Reference

Read `docs/reference/` before non-trivial work — `script-cheatsheet.md` for
syntax, `folder-map.md` for where things go, `gotchas.md` for silent failures,
`workflow.md` for the loop, `playbook.md` for how to test a mod without losing a
day to loading screens, `sources.md` for where a trustworthy answer comes from.

The best available reference is one the game generates itself: `script_docs` in
the in-game console (`-debug_mode -develop`) dumps every effect, trigger, scope
link, modifier and on_action to `<user dir>/logs/`. It has never been run here,
and Claude cannot run it — the console is an in-game overlay. Ask the user.
