---
name: ck3-debug
description: Debug a Crusader Kings III mod that does not work - content not appearing in game, localization showing raw keys, events not firing, game failing to load. Use when CK3 mod behaviour is wrong and the cause is unknown.
---

# Debug a CK3 mod

CK3 fails silently far more often than it errors. Work down this list in order;
most problems are caught in step 1 without launching the game.

## 1. Static checks first

    python D:/ck3/tools/ck3.py validate <slug> --strict

This catches the majority of real causes:
- **Unbalanced braces** — CK3 truncates the file from the bad brace onward and
  everything after it silently vanishes.
- **Missing UTF-8 BOM on a `.yml`** — the entire loc file is ignored, so every
  key renders as its raw name.
- **Malformed loc entries** — must be one leading space then `KEY:0 "text"`.
- **Language mismatch** between filename, folder and `l_<lang>:` header.
- **Duplicate definitions** inside the mod.

## 2. Is the mod actually loading?

    python D:/ck3/tools/ck3.py playset list

The mod must appear in the list. If missing:

    python D:/ck3/tools/ck3.py deploy <slug>
    python D:/ck3/tools/ck3.py playset add <slug>

Check the pointer file `<user dir>/mod/<slug>.mod` has an absolute `path=` with
forward slashes only.

## 3. Is something else overwriting it?

    python D:/ck3/tools/ck3.py where <relative/path.txt>

If a mod below yours provides the same path, your file never loads. Move yours
later in the playset, or merge (see the `ck3-compat` skill).

## 4. Does every key you referenced exist?

    python D:/ck3/tools/ck3.py find <key>
    python D:/ck3/tools/ck3.py loc <key>

An invented trigger, effect, trait or modifier name does not error — it is
simply ignored. This is the classic cause of "my event never fires" and "my
trait does nothing". Verify each one and read the vanilla definition.

## 5. Run it

    python D:/ck3/tools/ck3.py launch --clear-logs
    # play, reproduce, then quit from the in-game menu
    python D:/ck3/tools/ck3.py errors

- Steam must already be running.
- A large AGOT stack takes minutes to load and settles near 15 GB RAM. Flat high
  memory means loading finished.
- **Empty output is a clean run.** CK3 only creates `error.log` when something
  failed; do not wait for a log that will never appear.
- The full stdout capture is in `D:/ck3/logs/run-*.log` if you need more than
  the flagged lines.

## 6. In-game, with `-debug_mode`

- Console `effect <script>` / `trigger <script>` runs script against the selected
  character — the fastest way to test a scripted effect without an event.
- `reload loc`, `reload gui`, `reload texture` avoid a restart for those assets.
  Script logic changes still need a restart.
- Debug tooltips show raw script keys, which identifies the key behind any
  in-game string.

Reference: `D:/ck3/docs/reference/gotchas.md`.
