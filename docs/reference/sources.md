# Sources

Where to get an answer that is *true for this install* rather than true for some
patch three years ago. Ordered by trust.

## 1. `script_docs` — the authoritative dump

The game documents itself. **Already captured, in `docs/api/1.19.0.6/`.**

    python tools/ck3.py api side_strength
    python tools/ck3.py api add_gold --kind effects
    python tools/ck3.py api knight --partial

Ask this before writing any effect, trigger or scope link. It is the only source
that is true for *this* binary.

Caveat worth knowing: it is authoritative about **existence and scope**, but its
usage strings are hand-written and occasionally incomplete — `add_opinion` omits
the `opinion = N` parameter that every vanilla call site passes. Existence: trust
the dump. Exact syntax: confirm against a vanilla call site.

| File | Entries | Contents |
|---|---:|---|
| `effects.log` | 1945 | every effect, supported scopes, call syntax |
| `triggers.log` | 1954 | every trigger, supported scopes, comparison traits |
| `event_targets.log` | 286 | every scope link, with input→output scope |
| `event_scopes.log` | — | scope types: can they hold variables, evaluate triggers, save |
| `modifiers.log` | — | every modifier key, and its use areas (character / province / county) |
| `on_actions.log` | 1748 | every on_action and the scope it fires in |

Two things to know about it:

- **It reflects the loaded playset, not just vanilla.** `on_actions.log` contains
  AGOT's own entries (`agot_administrative_setup`). So "not in the dump" means
  "not in the engine *and* not in any enabled mod" — a strong negative.
- **Regenerate it after a game patch.** Commit under a new `docs/api/<version>/`;
  `ck3.py api` reads the highest-numbered folder.

To regenerate: in-game console with `-debug_mode -develop`, type `script_docs`
(lowercase, no arguments). It writes into `<user dir>/logs/`. There is no launch
argument for it, and the console is an in-game overlay rather than an OS window,
so Claude cannot drive it — ask the user.

## 2. The game's own `.info` files

The install ships **166 `.info` files**, one per `common/` subfolder plus GUI,
shader and data-format specs. They are the format documentation for the folder
they sit in, written by the developers, and they answer questions the wiki does
not. `common/combat_phase_events/_combat_phase_events.info` is nine lines and
states that `chance` is weighted against all other *valid* events, and that an
empty `effect` is skipped internally — both load-bearing facts.

**Always read the `_<folder>.info` before writing a new kind of file.**

## 3. Vanilla script

Still the best answer to "what does the engine actually accept", because it is
guaranteed to parse on this version. `ck3.py find <key>` → read the file. When
vanilla and the wiki disagree, vanilla wins.

## 4. ck3-tiger

`amtep/tiger` (v1.19.0) — a static validator for CK3 mods, written against typed
tables of every scope, effect and trigger. Two uses:

- run it over a mod to catch what `ck3.py validate` cannot (wrong scope for an
  effect, misspelled trigger, unused loc key)
- **read its tables as documentation** — they are version-tagged and machine
  generated, so they are a decent stand-in until `script_docs` has been run

## 5. The wiki, via a proxy

`ck3.paradoxwikis.com` is behind Cloudflare and blocks fetches. Two ways through:

- `jesec/ck3-modding-wiki` — a static GitHub mirror; fetch the raw markdown
- `https://r.jina.ai/<url>` — a rendering proxy that returns the page as text

Treat wiki content as *dated*. Confirm anything load-bearing against vanilla
script before writing it down here.

## 6. CWTools config

`DragonKnightOfBreeze/cwtools-ck3-config` is the maintained fork of the CWTools
rule set. Same role as the tiger tables — typed definitions of the script API —
useful for cross-checking, and nothing is cached locally right now.

## Rule

Anything recorded in `docs/reference/` should be traceable to a run on this
machine, to vanilla script, or to `script_docs`. Web-sourced claims get written
down only after they survive one of those three.

Worked example of why. Web research reported
`scope:combat_side.enemy_side.vastly_outnumbered_combat_side_threshold` as a
built-in scope link for testing whether a side is outnumbered. It is not in
`event_targets.log` at all. `ck3.py find` located the real thing: a vanilla
*script value* in `common/script_values/00_combat_values.txt`, `side_strength`
multiplied by **5**. Plausible name, wrong construct, wrong magnitude, and it
would have silently replaced a working 1.5x threshold with one that almost never
fires. Thirty seconds of checking against the dump.
