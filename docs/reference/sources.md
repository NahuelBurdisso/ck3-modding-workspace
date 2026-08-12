# Sources

Where to get an answer that is *true for this install* rather than true for some
patch three years ago. Ordered by trust.

## 1. `script_docs` — the authoritative dump

The game can document itself. In-game console, `-debug_mode -develop`:

    script_docs

Lowercase, no arguments. It writes to `<user dir>/logs/`:

| File | Contents |
|---|---|
| `effects.log` | every effect, its required scope, its parameters |
| `triggers.log` | every trigger, supported scopes, value types |
| `event_targets.log` | every scope link (`liege`, `side_commander`, ...) with input→output scope |
| `event_scopes.log` | the scope type list |
| `modifiers.log` | every modifier key the engine knows |
| `on_actions.log` | every on_action and the scope it fires in |

There is **no launch-argument equivalent** — it must be typed in the console, and
CK3's console is an in-game overlay, so Claude cannot drive it (see gotchas,
"Reading results out of a run"). Ask the user.

This has never been run on this install. Doing it once per game version and
committing the output is the single highest-value thing available: it turns every
"does this effect exist in 1.19?" question from a web search into a grep.

## 2. The game's own `.info` files

The install ships **166 `.info` files** describing GUI types, shaders and data
formats. `ck3.py find` indexes the script; these are the layer under it.

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
