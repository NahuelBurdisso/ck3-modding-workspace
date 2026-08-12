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

## The user directory

- **There are two CK3 user dirs on this machine and only one is live.**
  Live: `D:/Documents/Paradox Interactive/Crusader Kings III/`.
  Dead decoy: `C:/Users/nahue/Documentos/Paradox Interactive/Crusader Kings III/`.
  The decoy has a full `mod/` folder and a plausible `dlc_load.json`, so deploying
  into it looks correct and simply never loads. This burned an entire session.
- Resolve it from the registry instead of guessing at the Spanish folder name:
  `reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders" | grep -i personal`
  → `Personal REG_EXPAND_SZ D:\Documents`. CK3 uses the Windows known-folder API,
  so it follows `Personal`.
- Tells that a dir is the dead one: `launcher-v2.sqlite` is 0 bytes (live is
  ~180 KB), no `last_save.ck3` / `continue_game.json` / `dlc_signature`, and
  `dlc_load.json` mtime only ever matches your own edits.
- Local (non-workshop) `.mod` pointers in the live dir use an absolute `path=`,
  same as workshop pointers — not a relative `mod/<name>`.
- **A mod source folder does not have to live under the user dir.** A pointer at
  `path="D:/ck3/mods/<slug>"` mounts fine — confirmed by
  `Mounted Data: D:/ck3/mods/battle_chronicles` in `debug.log`. So `ck3.py deploy`
  needs no copy step, and there is only ever one copy of the source to edit.

## Saves

- **A modded game rule is baked into the save.** Disabling the mod afterwards
  makes the save fail to load that key:
  `[E] Failed to read key reference: <rule_option> ... in file: "save games/<x>.ck3"`.
  Bisect by disabling a mod only on a save made *before* the mod was added, or
  expect this noise.
- **`autosave_exit.ck3` can be written truncated** if the game is quit while
  heavily loaded, and `last_save.ck3` + `continue_game.json` both get pointed at
  it. A save that is much smaller than the previous autosaves is the tell
  (101 MB vs 124/155 MB here). Symptom is a hard, reproducible
  `EXCEPTION_ACCESS_VIOLATION` a few minutes into loading, at the same fault
  address every time and with no script error near it. Use **Load** and pick an
  older autosave rather than **Continue**.
- A crash that reproduces at the *identical* fault address both with and without
  your mod is not your mod. Check the address in `crashes/*/exception.txt`
  before spending runs on a bisect. Fault addresses are only comparable within
  one Windows boot (ASLR fixes the image base per boot).

## on_actions do NOT fully merge

- `events = { }`, `random_events = { }` and `on_actions = { }` are additive lists
  and merge across files. **`effect = { }` does not.** If two files give the same
  on_action an `effect`, the engine keeps exactly one and logs
  `[E][jomini_onaction.cpp:161]: There is more than one 'effect' defined using most recent: file: ...`
- "Most recent" is **file read order inside `common/on_action`, which is
  alphabetical — not playset load order.** A mod loading dead last still loses if
  its filename sorts early: `bc_spike_on_actions.txt` was discarded in favour of
  `combat_on_actions.txt`. Naming a file `zz_*` is the usual workaround, but it
  only wins a race you should not be running.
- **Always hook via `events = { your.event }`** and put the logic in a
  `hidden = yes` event with the right `scope = ...`. That is what vanilla does
  (`on_combat_end_winner` → `combat_event.0001`, `hidden = yes`,
  `scope = combat_side`) and it composes with every other mod.

- `common/on_action` is **singular**. A folder named `common/on_actions/` is
  silently ignored — no error, no entries, nothing.
- An on_action's `effect = { }` runs *concurrently with*, not before, its
  `events = { }`. Scopes and variables set in the effect do **not** reach the
  events. Save what the event needs inside the event.
- `on_game_start` fires exactly once per save. A mod enabled mid-save therefore
  never initialises. If setup matters, guard it on a version variable checked
  from a pulse on_action instead.

## Scope and syntax traps that produce no error

- **`prev` cannot be chained.** There is no `prevprev`. Save a scope instead.
- **`save_scope_as` does nothing inside a trigger block.** Use
  `save_temporary_scope_as` there.
- Saved scopes survive an unbroken effect chain, including across
  `trigger_event`. They do not survive a delayed event across a different chain.
- **`NOT` with more than one child is NAND, not NOR** — it is true when *any*
  child is false. For "none of these", use `NOR`.
- **`add_character_modifier` with no `days`/`years` is permanent.** Easy way to
  ship a modifier that never comes off.
- `show_as_tooltip = { }` displays without executing; `hidden_effect = { }`
  executes without displaying. Mixing them up looks like a broken effect.
- Event ids above `9999` in a namespace are unreliable — keep four digits.
- The `:0` in a loc entry is a version counter with no meaning to the engine.
  It is not an index and not a variable.

## Combat phase events

- They fire every `COMBAT_EVENT_DAYS = 5`. Opening the battle screen while the
  game is paused produces nothing, no matter how high `chance = { base = ... }`.
- `type = commander` roots on the commander, so `is_ai = no` means *you* must be
  leading that army. `type = knight` has no such gate and fires for knights on
  any side of any combat in the world.
- Lock a probe out with `NOT = { has_character_modifier = ... }` in `is_valid`;
  verified to work even at `base = 100000`.

## Toasts and messages are not a place to put gameplay

- `send_interface_toast` / `send_interface_message` are documented as *"sends a
  message to the player playing the character in the scope and then executes any
  effects inside"*. Two consequences that are easy to miss:
  - **The recipient is the player playing the scoped character.** Raised on an AI
    courtier, the message reaches nobody. If you want the player to see a thing
    that happened to their knight, re-scope first — vanilla writes
    `liege = { send_interface_message = ... }` for exactly this reason.
  - **Do not rely on effects nested inside them.** Vanilla never does: in
    `00_knight_phase_events.txt` the `set_variable` / `add_prestige` sit in the
    effect block and the message carries only icons and a tooltip. State first,
    presentation second.
- The failure is silent and asymmetric, which is what makes it expensive. One
  Battle Chronicles event penalised the *enemy* commander from outside a toast
  and its own commander from inside one, so the same event was doing two
  different things depending on who was AI.

## `script_docs` is authoritative about existence, not about parameters

The dump is generated from the engine, so if a key is absent it does not exist.
But its usage strings are hand-written and sometimes incomplete. `add_opinion`
documents itself as `{ modifier = X days/months/years = Y target = Z }` and never
mentions `opinion = N` — yet every vanilla call site passes it, and it is the
only way a decaying modifier gets a magnitude. **Existence: trust the dump.
Syntax: confirm against a vanilla call site.**

Similar trap in the dump's own words, worth quoting: `has_trait_rank` notes that
"not having the trait and having rank 0 counts as the same thing", so
`rank < X` **is always true for a character without the trait**.

## Effects that reject what looks obvious

- **`add_gold` refuses a negative value.** `add_gold = -100` logs
  `Script system error! Error: add_gold effect [ Negative value in: {} ]` and the
  option silently does nothing — the player gets the benefit for free. Use
  `remove_short_term_gold = 100`. Vanilla trips over the mirror image of this
  (`Negative value in remove_short_term_gold: -450` in `buy_ruby_crown_events.txt`),
  so neither direction accepts a sign.
- **`monthly_change` on a decaying opinion modifier is a RATE and must be
  positive**, even for a negative opinion. A negative value is rejected with
  `Decaying modifier 'x' should have a duration or monthly_change!` and the
  modifier is dropped. The sign comes from `opinion = -20` at the `add_opinion`
  call site. Every vanilla decaying modifier uses `monthly_change = 0.1`.

## Scripted effect parameters

- `$PARAM$` substitution inside a quoted string **eats the space in front of it**.
  `debug_log = "applied $MODIFIER$"` prints `appliedbc_spike_momentum_major`.
  Harmless for logs, but never build a display string that depends on it.

## Reading results out of a run

- **`debug_log` writes to `<user dir>/logs/debug.log`, never to stdout.** Piping
  `ck3.exe -debug_mode` to a file captures only `[Checksum Builder]` spam. Read
  `logs/debug.log`, `logs/error.log` and `logs/game.log` instead.
- `error.log` is the single best proof a mod loaded and parsed. It names the file
  for every complaint, e.g.
  `Duplicate localization key. Key 'X' is defined in both 'localization/english/<mod>.yml' and ...`
  or `Modifier 'X' was not used by the script or code but exists in the database`.
  A mod that produces such lines is definitively in the load.
- CK3 wants **UTF-8 BOM on script `.txt` too**, not just loc. Without it you get
  `[lexer.cpp:306] File '...' should be in utf8-bom encoding (will try to use it anyways)`.
  It still parses, but it clutters `error.log`.
- **Do not use `PAUSED` as a load canary.** The on-screen pause banner is
  `PAUSED_BY_PLAYER`. `PAUSED` exists in `core_l_english.yml` but nothing draws
  it, so overriding it is a permanent false negative.
- CK3's debug console is an in-game overlay, not a separate OS window. The
  process has exactly one visible top-level window, so `SendKeys` after
  `SetForegroundWindow` types into the *game*, firing hotkeys, unless the
  console overlay already has focus. Prefer driving tests from script.

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
- **`[Checksum Builder]` output is not a file manifest.** Do not use it to prove
  a mod loaded. It lists only checksum-relevant content and omits plenty that is
  definitely loaded — e.g. Battlefield Duel+ ships a uniquely named
  `common/combat_phase_events/00_phase_events.txt`, is enabled, and never appears
  in the log. Absence there means nothing. To confirm a mod is live, check
  in-game (a modifier, a toast, `debug_mode` tooltips) or `dlc_load.json`.
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
