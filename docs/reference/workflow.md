# Workflow

## One-time setup

    python tools/ck3.py doctor     # verify paths, exe, playset
    python tools/ck3.py index      # ~2-3 min, builds index/ck3.sqlite3

Rebuild the index after subscribing to mods, changing the playset, or a game
patch. It is a full rebuild, not incremental.

## Making a mod

    python tools/ck3.py new "My Mod" --agot --deploy
    #  -> D:/ck3/mods/my_mod/                      source, git-initialised
    #  -> <user dir>/mod/my_mod.mod                pointer with absolute path=
    python tools/ck3.py playset add my_mod         # append = loads last = wins

`--agot` adds `dependencies={"A Game of Thrones"}` so the launcher enforces
ordering. Drop it for a pure-vanilla mod.

Then edit files under `D:/ck3/mods/my_mod/` directly. Nothing is copied — the
game reads the source folder, so there is no build step and no sync step.

## Loop

    python tools/ck3.py validate my_mod --strict
    python tools/ck3.py launch --clear-logs
    # ... play, reproduce, quit from the in-game menu ...
    python tools/ck3.py errors

`validate` before every launch: it catches missing BOMs, brace imbalance and
malformed loc lines in a second, which the game would otherwise swallow silently
or report five minutes into a load.

## Research before writing

Never guess at a key. Ask the index:

    python tools/ck3.py find <key>              # exact definition sites
    python tools/ck3.py find <part> --partial
    python tools/ck3.py loc <loc_key>
    python tools/ck3.py where <relative/path.txt>

`find` returns every source in load order, so the last row is the definition the
game actually uses. Read that file for working syntax.

## Compatibility work

    python tools/ck3.py conflicts               # paths claimed by 2+ mods

Each line lists the chain in load order; the last mod wins outright. If two mods
each rewrote the same file for different reasons, merge them into a patch mod
that loads last — see `gotchas.md` for the 3-way merge recipe.

    python tools/ck3.py playset list
    python tools/ck3.py playset audit           # missing content, version drift
    python tools/ck3.py playset move my_patch --position 99

Every playset write backs up `dlc_load.json` to `index/playset-backups/` first.
Remember that opening the Paradox launcher will overwrite these edits.

## Workshop pointers

    python tools/ck3.py sync-workshop 3664900993

Regenerates `<user dir>/mod/ugc_<id>.mod` from the installed workshop
descriptor. Use it after a mod updates and its metadata changed, or to rebuild
pointer files the launcher never created.
