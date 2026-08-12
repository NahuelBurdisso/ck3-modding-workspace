# Gotchas

Things that fail silently or waste an hour. Most were learned the hard way on
this machine.

## Encoding

- Localization `.yml` **must** be UTF-8 **with BOM**. Without it CK3 drops the
  entire file and every key renders as its raw name. `ck3.py validate` checks it.
- Script `.txt` should be UTF-8. A BOM there is tolerated.
- Loc entry syntax is exact: one leading space, `KEY:0 "text"`. The number is a
  version counter, not a variable. Missing quotes or a missing space kills the line.
- The filename language, the folder language and the `l_<lang>:` header must all
  agree, or the file is ignored.

## Structure

- Unbalanced braces do not raise a clear error — CK3 truncates the file from the
  bad brace onward and everything after it silently disappears.
- A file at a vanilla relative path **replaces** the vanilla file entirely.
  Nothing merges. Adding `common/traits/my_traits.txt` is almost always right;
  editing `common/traits/00_traits.txt` is almost always wrong.
- `common/defines/` is the exception: defines are read per key, so a small
  override file with only the keys you change works.
- Prefix every key you invent with your mod slug. Two mods defining the same
  scripted effect name = the later one silently wins.

## Load order and playsets

- Last mod in `dlc_load.json` wins. Compat patches go *after* their targets.
- The Paradox launcher is optional. The game reads `dlc_load.json` directly, and
  the order of `enabled_mods` **is** the load order.
- **Opening the launcher regenerates `dlc_load.json` from its own SQLite DB and
  discards edits made outside it.** After editing the playset with
  `ck3.py playset`, launch `binaries/ck3.exe` directly.
- Each workshop mod needs a pointer file `<user dir>/mod/ugc_<id>.mod`: the
  workshop `descriptor.mod` contents plus an absolute `path=`.
- `path=` must use forward slashes only. Mixed separators can be rejected.

## Running the game

- Steam must be running first; `ck3.exe` will not start it.
- `-debug_mode` enables the console, error reporting to stdout, and reload
  commands.
- **Do not pipe the launch through `tail`** — you lose everything except
  trailing `[Checksum Builder]` spam. Redirect the whole stream to a file.
- `logs/` stays empty while the game runs *and* after a clean exit. CK3 only
  creates `error.log` when something actually failed. Empty `logs/`, `crashes/`,
  `dumps/` and `exceptions/` after a full session means a clean run — do not sit
  waiting for a log that will never appear.
- A large AGOT stack takes several minutes to load and settles around 15 GB RAM.
  High-but-flat memory means loading finished, not a leak.
- The process ignores `WM_CLOSE`, so `Process.CloseMainWindow()` does nothing.
  Quit from the in-game menu.

## Iteration speed

- In `-debug_mode` the console `reload` family avoids full restarts:
  `reload texture`, `reload gui`, `reload loc`. Script logic changes generally
  still need a restart.
- `effect`/`trigger` console commands run arbitrary script on the selected
  character — fastest way to test a scripted effect without an event.
- `debug_mode` also surfaces tooltips with raw script names, which is the
  quickest way to find the key behind an in-game string.

## Steam Workshop

- Claude cannot subscribe to workshop items — that is an authenticated write on
  the user's account. Only the user can, and only from inside the Steam client.
  Browser subscribe clicks while logged out silently no-op.
- Source of truth for what is installed:
  `D:/SteamLibrary/steamapps/workshop/appworkshop_1158310.acf`
  (`WorkshopItemsInstalled` plus `NeedsDownload`/`NeedsUpdate`).
  An id absent from the acf after a client restart means *not subscribed*, not
  *downloading*.
- Check whether an item is live/delisted without auth:

      curl -s -X POST https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/ \
        -d itemcount=1 -d "publishedfileids[0]=<id>"

  `result=1`, `banned=0`, `visibility=0` = live and public.
- `WebFetch` on `steamcommunity.com` item pages is unreliable: it rate-limits,
  renders current-year "Last Updated" dates with the wrong year, and spuriously
  reports items as removed. Confirm against the API before repeating any claim.

## Merging two mods that replaced the same file

Works well, reuse it:

1. `ck3.py conflicts` to find every path claimed by 2+ mods.
2. Use the *base* mod's copy of the file as the merge base — submods usually copy
   a file wholesale and then edit different regions, so a 3-way merge is clean:
   `git merge-file -p <ours> <base> <theirs>`
3. Verify by brace balance and by confirming each input's unique lines survived.
4. Put the merge patch last in the playset.

Caveat: some mods legitimately comment out `{`-opening lines, so their files are
genuinely brace-imbalanced relative to the base. A merge that inherits the same
offset is correct, not broken. Check *why* before "fixing" it.
