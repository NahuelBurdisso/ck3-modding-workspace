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
    python tools/ck3.py probe 'MY_MOD'

`validate` before every launch: it catches missing BOMs, brace imbalance and
malformed loc lines in a second, which the game would otherwise swallow silently
or report five minutes into a load.

`errors` reads the tail of every log. `probe` is the one to reach for when the
mod under test writes `debug_log` markers: it greps `<user dir>/logs/` for a
pattern and prints counts per distinct message, which is the only workable way to
read a `debug.log` that has grown to tens of megabytes. A restart costs about
seven minutes, so design each run to answer every open question at once —
`playbook.md` covers how.

## Checking the prose

    python tools/sweep_backticks.py . | tail -1

Prints every line of the tree whose backtick count is odd, then a total. An odd
count is the signature of a grep target — a paragraph name, a marker, a filename
— broken across a line wrap, which makes it unfindable by the search it was
written for. It is not a `validate` check and must not be gated on: the tree
carries legitimate multi-line quotations of script, loc and command lines, which
wrap on purpose. Read the lines and judge each one.

`| tail -1` is how the number is taken, because the body is long and only the
total moves between rounds. Two hazards ride along with the pipe, both written
up in `tools/sweep_backticks.py`: on Windows a redirected stdout falls back to
cp1252, so a hit line carrying a character outside it kills the run before the
total prints; and an unterminated fence silences the rest of its own file.

    python tools/tests/test_sweep_backticks.py
    python tools/tests/test_citations.py

Both are stdlib unittest, no pytest, and take about a second each.

    python tools/tests/mutate_sweep_backticks.py

Not part of that set. It edits `tools/sweep_backticks.py` in place, one line at
a time, and records which tests go red for each break — a surviving mutant names
a test that cannot fail. Run it deliberately, never in a batch, and never
alongside anything else that imports the sweep: while it runs, the file on disk
is the broken one.

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
