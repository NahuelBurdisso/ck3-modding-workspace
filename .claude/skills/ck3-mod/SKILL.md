---
name: ck3-mod
description: Create a new Crusader Kings III mod or add content to an existing one. Use when the user asks to build a CK3 mod, add a trait/event/decision/on_action, or write CK3 script. Handles scaffolding, research, implementation, validation and deployment.
---

# Build CK3 mod content

## 1. Locate or create the mod

    python D:/ck3/tools/ck3.py doctor

Existing mods live in `D:/ck3/mods/`. If the user needs a new one:

    python D:/ck3/tools/ck3.py new "<Display Name>" [--agot] --deploy

Use `--agot` when the content depends on the A Game of Thrones total conversion
(it writes `dependencies=`). Omit it for vanilla mods. Ask which, if unclear.

## 2. Confirm the index is current

    python D:/ck3/tools/ck3.py stats

If missing or stale (mods added/removed since), rebuild — it takes two to three
minutes:

    python D:/ck3/tools/ck3.py index

## 3. Research before writing

Delegate to the `ck3-researcher` subagent, or run directly:

    python D:/ck3/tools/ck3.py find <key>
    python D:/ck3/tools/ck3.py loc <key>
    python D:/ck3/tools/ck3.py where <relative/path.txt>

Read the vanilla (or winning mod) definition and copy its real syntax. Never
invent a trigger, effect, trait or scope link — unknown keys fail silently at
runtime.

## 4. Implement

Delegate to the `ck3-modder` subagent for anything beyond a couple of lines.

Requirements:
- New files with unique names; do not replace vanilla files unless there is no
  alternative. Check `where` first.
- Prefix every invented key with the mod slug.
- Event ids must match the file's `namespace`.
- Localization at `localization/english/<slug>_l_english.yml`, UTF-8 **with
  BOM**, entries as ` KEY:0 "text"`.

## 5. Validate — required before claiming success

    python D:/ck3/tools/ck3.py validate <slug> --strict

Zero errors. Show the output. Fix and re-run rather than explaining away.

## 6. Enable and test

    python D:/ck3/tools/ck3.py playset add <slug>     # confirm with the user first
    python D:/ck3/tools/ck3.py launch --clear-logs
    # user plays and quits from the in-game menu
    python D:/ck3/tools/ck3.py errors

Empty output means a clean run — CK3 only writes logs when something failed.

Reference: `D:/ck3/docs/reference/script-cheatsheet.md`, `folder-map.md`,
`gotchas.md`.
