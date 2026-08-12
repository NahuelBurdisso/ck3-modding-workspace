# Battle Chronicles — design

Status: draft
Mod slug: `battle_chronicles`
Target: CK3 1.19.0.6 + A Game of Thrones 0.4.40

## Problem

Battles in the current playset resolve as arithmetic. The engine rolls a phase
event for every commander and every knight in a combat once every five days
(`COMBAT_EVENT_DAYS = 5` in `common/defines/00_defines.txt:581`), which is a lot
of narrative opportunity — and almost all of it is spent on casualties.

Measured across the whole install:

| Source | Phase event defs |
|---|---|
| Crusader Kings III | 13 |
| A Game of Thrones | 19 |
| AGOT - Battlefield Duel + | 1 (retired, `always = no`) |
| all other 62 mods | 0 |

Effect verbs used by every phase event in vanilla + AGOT combined:
`death` 36, `maimed` 22, `add_prestige` 19, `add_trait` 6, `trigger_event` 4,
`send_interface_toast` 13, `set_variable` 38. There is **not one**
`add_character_modifier` and **not one** `add_opinion`.

So a battle can kill your commander, cripple him, or do nothing. It can never
swing, never turn, and never produce a story or a grudge. Meanwhile
`commander_none` carries `base = 1000` chance weight, so "nothing happens" is
overwhelmingly the common outcome.

## What this mod does

Adds a **momentum** layer on top of the existing casualty layer. New phase
events read the tactical situation — terrain, numbers, supply, commander
quality — and apply short-lived `advantage` modifiers that make a battle's
course visible and swingy, without touching how lethal it is.

The two ideas previously scoped as "Battle Chronicles" and "Tides of Battle"
ship as one mod. They are the same system: Chronicles is the narration, Tides is
the situational gating that decides which narration is possible.

## Corrected assumption

An earlier proposal was to implement Tides through `common/combat_effects`.
**That is not possible.** Per `_combat_effects.info` the schema is only:

    name = loc_key
    advantage = int
    adjacency = yes/no
    visible = yes/no
    image = key

There is no `is_valid`, no `trigger`, no `chance`. Every key in
`00_combat_effects.txt` (`defender_river`, `supply_state_starving_advantage`,
`combat_debt_level_0..9`, `recently_disembarked_advantage`) is applied by
hardcoded engine conditions. New keys would never fire. The numbers can be
retuned, nothing more. This mod does not touch that folder.

The situational logic lives in phase-event `is_valid` blocks instead, which are
fully scriptable.

## Non-goals

- No new men-at-arms. That space is saturated (AGOT 908, Brightboar 185,
  Armies of Westeros 138) and any addition would collide.
- No new deaths or maimings. AGOT owns casualty rates; this mod stays out.
- No duel content. Battlefield Duel+ owns duels with 131 events and 131 scripted
  effects. This mod hooks alongside it, never replaces it.
- No replacement of any vanilla or AGOT file.

## Decisions taken

| Decision | Choice |
|---|---|
| Tides delivery | Phase events gating on situation, applying `advantage` modifiers |
| Lethality | Non-lethal. No new `death` or `maimed` effects anywhere |
| Interruption | Toasts by default; a small player-only subset becomes pop-up events |
| Tuning | Game rules for frequency and for whether momentum swings are large |

## Architecture

    mods/battle_chronicles/
      descriptor.mod                       dependencies = A Game of Thrones
      common/
        combat_phase_events/
          bc_commander_phase_events.txt    new file, additive
          bc_knight_phase_events.txt       new file, additive
        modifiers/
          bc_momentum_modifiers.txt        the advantage modifiers
        game_rules/
          bc_game_rules.txt                frequency + swing size
        scripted_triggers/
          bc_scripted_triggers.txt         shared situation tests
        scripted_effects/
          bc_scripted_effects.txt          shared momentum application
        on_action/
          bc_on_actions.txt                cleanup on combat end
      events/
        bc_events.txt                      the player-facing pop-ups
      localization/english/
        bc_l_english.yml                   UTF-8 with BOM

Every filename is prefixed `bc_`, so nothing collides with vanilla, AGOT, or the
62 other mods. All definitions are additive: CK3 reads every file in
`common/combat_phase_events/` and merges the keys.

## Core mechanic: momentum

A phase event that "goes well" applies a temporary `advantage` character
modifier to the commander. `advantage` is confirmed valid on characters — it is
used on traits in `00_traits.txt` and on modifiers in
`common/modifiers/00_event_modifiers.txt`.

Proposed modifiers in `bc_momentum_modifiers.txt`:

| Key | advantage | Duration | Granted by |
|---|---|---|---|
| `bc_momentum_minor` | +3 | 20 days | small successes |
| `bc_momentum_major` | +6 | 20 days | decisive moments |
| `bc_faltering_minor` | -3 | 20 days | small setbacks |
| `bc_faltering_major` | -6 | 20 days | banner falls, line breaks |

Durations are shorter than a typical battle so momentum decays rather than
locking in. Under the "large swings" game rule the values double.

Momentum is applied through one scripted effect, `bc_apply_momentum_effect`,
parameterised by magnitude and direction, so tuning happens in exactly one place.

Modifier names must read as battlefield causes, not as game mechanics: the
combat advantage tooltip lists them verbatim next to `Commander Martial Skill`
and `Leading Own Soldiers`. Confirmed in game — see risk 1.

## Event catalogue — shipping set

Chapter 1 is deliberately small. Ship it, play it, then extend; the whole point
of the file layout is that adding event 11 costs nothing structurally.

### Commander events (`type = commander`)

| Key | Gate (`is_valid`) | Outcome |
|---|---|---|
| `bc_banner_falls` | commander leading, side losing on strength | `bc_faltering_major`, small stress |
| `bc_rally_the_line` | has `bc_faltering_*` active | clears faltering, applies `bc_momentum_minor` |
| `bc_horse_killed_under_him` | prowess-gated | `bc_faltering_minor`, prestige on survival |
| `bc_flank_collapses` | outnumbered | `bc_faltering_major` |
| `bc_van_breaks_through` | outnumbering, commander martial high | `bc_momentum_major` |
| `bc_ground_favours_us` | terrain gate (see risks) | `bc_momentum_minor` |
| `bc_lines_bogged_down` | terrain gate | both sides `bc_faltering_minor` |

### Knight events (`type = knight`)

| Key | Gate | Outcome |
|---|---|---|
| `bc_knight_holds_the_breach` | knight alive, side losing | side momentum, knight prestige |
| `bc_knight_shames_himself` | low prowess, side losing | knight stress + liege opinion hit |
| `bc_shieldbrother_forged` | two knights same side survive together | mutual opinion, memory |

`bc_shieldbrother_forged` is the seed of the "Shieldbrothers" idea from the
ranked list — it is included here because the hook is free once we are already
iterating knights.

## Chance weighting

The competition is `commander_none` at `base = 1000`, plus AGOT's casualty
events. Vanilla's `chance` blocks use `base` plus `modifier = { add = N ... }`
or `modifier = { factor = N ... }`, as seen in `00_commander_phase_events.txt`.

Budget: the entire Chronicles set should win roughly **15-20% of commander
rolls** at default frequency. At one roll per 5 days that is a notable moment
roughly every 25-30 days of battle — frequent enough to feel alive, rare enough
not to drown AGOT's own events.

Starting weights: `base = 60` per commander event, scaled by the frequency game
rule (`0.5x / 1x / 2x`). These are guesses and **must** be tuned against
observed play; the game rule exists precisely so tuning needs no script edits.

## Game rules

Format confirmed against `common/game_rules/00_game_rules.txt`, read in script
via `has_game_rule = <option>` exactly as vanilla's `commander_none` reads
`has_game_rule = easy_difficulty`.

    bc_frequency   = bc_frequency_low | bc_frequency_default | bc_frequency_high
    bc_swing       = bc_swing_subtle  | bc_swing_default     | bc_swing_dramatic

No option sets `blocks_achievements`.

## Player interaction

Default path is `send_interface_toast`, matching vanilla and AGOT so the mod
reads as native. A subset — `bc_banner_falls`, `bc_rally_the_line`,
`bc_van_breaks_through` — additionally fires a real event from `bc_events.txt`
when `is_ai = no` and the commander is the player's own character, offering a
choice such as spend prestige to rally, or hold and preserve strength.

Guard: the pop-up path carries a character flag with a cooldown so a single long
siege cannot produce a stream of prompts.

## Compatibility

- Load order: **after AGOT and after Battlefield Duel+**. Append to the playset
  and it lands before `agot_conflict_merge`; move it before the merge patch if
  ordering ever matters.
- Zero file collisions by construction — verify with
  `python tools/ck3.py conflicts` after deploying.
- Battlefield Duel+ retired its own `battleduel_phase` (`always = no`) and moved
  to manual/opportunity entry routes, so there is no contention for the phase
  slot. Its duel events remain untouched.
- Seasons of Ice and Fire owns `agot_seasons`. If terrain/weather gating proves
  workable, prefer plain vanilla terrain checks over any Seasons-specific key so
  the mod does not hard-depend on it.

## Risks and unknowns

1. ~~**Does a commander's `advantage` character modifier actually apply to the
   combat?**~~ **Resolved — yes. Proven in game 2026-08-12.** Applying vanilla
   `ai_extreme_conqueror_modifier` (`advantage = 25`, `00_basic_modifiers.txt:686`)
   to a commander mid-battle moved the breakdown from

       Our Advantage: +35        ->    Our Advantage: +60
         Commander Martial Skill: +30    Commander Martial Skill: +30
         Leading Own Soldiers: +5        Leading Own Soldiers: +5
                                         Scourge of the Gods: +25

   Two things follow. The mechanic works, so momentum is viable. And the
   breakdown lists each modifier **by its localized name**, so every Chronicles
   momentum modifier becomes a legible cause in the battle UI for free — the
   player sees *why* the tide moved without any extra UI work.
2. ~~**Can `is_valid` read the combat's terrain?**~~ **Resolved — yes.** Vanilla
   itself uses `scope:combat_side.combat.location`
   (`00_commander_phase_events.txt:346`, `00_knight_phase_events.txt:1241,1396`).
   `location` is a province scope, so `terrain = forest` applies directly:

       scope:combat_side.combat.location = { terrain = forest }

   The terrain-gated events stay in scope.
3. Chance weights are unvalidated guesses. Expect two or three tuning passes.
4. AGOT's `set_variable` usage (38 occurrences) suggests it tracks combat state
   on characters. Confirm no variable-name overlap; the `bc_` prefix should
   cover it.

## Phase 0 spike — RESULTS (2026-08-12)

`mods/bc_spike` ran its full 13-probe suite in game. **All 13 pass. Every
mechanic the Chronicles design depends on works.** Read out from
`<user dir>/logs/debug.log`, not stdout — see the note at the end of this section.

| Probe | Question | Result |
|-------|----------|--------|
| P1 | mod loads at all | PASS — `BC Spike\|mod/bc_spike.mod\|Enabled` in `debug.log` |
| P2 | commander phase event fires from a new additive file | PASS — fired once |
| P3 | knight phase event fires from a new additive file | PASS — 6 firings |
| P4 | terrain readable via `scope:combat_side.combat.location` | PASS — location reachable, `terrain` evaluated cleanly |
| P5 | side-strength comparison usable as a gate | PASS — reported `LOSING` correctly |
| P6 | modded `advantage` modifier renders in the battle breakdown | PASS (vanilla control, risk 1) |
| P7 | parameterised scripted effect | PASS — `$MODIFIER$` substituted |
| P8 | modded game rule readable via `has_game_rule` | PASS — `default` |
| P9 | toast with modded loc renders | PASS |
| P10 | pop-up event fires for the player from a phase event | PASS — fired, option A taken |
| P11 | `add_opinion` from a knight event | PASS — 6 firings |
| P12 | modifiers cleaned up when the battle ends | PASS — hook fired 6×, 27 cleanups (see the on_action note below) |
| P13 | `has_character_modifier` gates re-firing | PASS — explicit: `gated event fired while winning`, and with `base = 100000` the commander probe still fired exactly once per battle |
| P14 | knights on a side are enumerable | PASS — enumerated |

Notes worth keeping:

- **`combat_phase_events` fire every `COMBAT_EVENT_DAYS = 5`.** Nothing happens
  while the battle screen is open and the game is paused. Let time run.
- P4 reported `terrain = other but readable`. The battle was fought at a coastal
  province, so it simply fell through the `forest`/`hills`/`mountains`/`plains`
  chain. The probe's actual question — is the province scope reachable and is
  `terrain` evaluable — is answered yes. Enumerate the full terrain list when
  writing the real terrain-gated events.
- `$PARAM$` substitution inside a quoted string **swallows the space before it**:
  `"applied $MODIFIER$"` logs as `appliedbc_spike_momentum_major`. Cosmetic, but
  do not build strings that rely on that space.
- **P12 initially FAILED, and the failure corrected the design.** The cleanup hook
  was written as `on_combat_end_winner = { effect = { ... } }`. on_action
  `effect` blocks **do not merge across files** — the engine keeps one and logs
  `[E][jomini_onaction.cpp:161]: There is more than one 'effect' defined using most recent`.
  Worse, "most recent" is decided by **alphabetical file order inside
  `common/on_action`, not playset load order**, so `bc_spike_on_actions.txt` lost
  to `combat_on_actions.txt` despite the mod loading last.

  This invalidates the earlier note that "Grand Remembrance and Battlefield Duel+
  both append to these same two keys" — they cannot both own an `effect` there.

  Fixed by using the additive `events = { }` list, which is the hook vanilla
  itself uses, with the logic in a `hidden = yes`, `scope = combat_side` event:

      on_combat_end_winner = { events = { bc_spike.0002 } }

  **Every Chronicles on_action hook must use `events`, never `effect`.**
  Re-verified after the rewrite: hook fired on both sides of three combats and
  stripped 27 knight modifiers. The commander branch (`side_commander ?=`) logged
  no removal only because the commander held no momentum at that moment — the
  cleanup effect itself is proven by the knight path.

  Because cleanup runs at combat end, a knight locked out by
  `NOT = { has_character_modifier = ... }` becomes eligible again in the *next*
  battle. That is the desired behaviour for momentum, but it means the lockout is
  per-battle, not per-character-per-campaign.

Re-run it:

    python tools/ck3.py playset add bc_spike
    python tools/ck3.py launch --clear-logs
    # fight a battle you personally command, let several days pass
    grep BC_SPIKE "<user dir>/logs/debug.log"

### Fast path — answers risk 1 in ~30 seconds

Waiting for the phase event to fire naturally costs a full battle. Risk 1 does
not need it. In `-debug_mode`, with any battle in progress that you command,
open the console and run:

    effect add_character_modifier = { modifier = bc_spike_advantage_modifier days = 30 }

(The console `effect` command takes the effect inline; it is not wrapped in
`effect = { }` the way script files are. Append a character id to target
someone other than the selected character.)

then open the battle and read the advantage breakdown. If it moves by +50, the
momentum design holds. The phase event below only additionally proves the
event plumbing and terrain probe.

### Reading results — do not use stdout

`debug_log` writes to `<user dir>/logs/debug.log`. Piping `ck3.exe -debug_mode`
to a file captures only `[Checksum Builder]` spam and will make a perfectly
healthy mod look dead. `logs/error.log` names the file behind every complaint
and is the fastest proof a mod parsed. `debug.log` also contains a literal
enabled-mod manifest (`<Name>|mod/<file>.mod|Enabled`) plus a
`Mounted Data: <path>` line per mod — that is the authoritative load check.
`[Checksum Builder]` is not.

The live user dir on this machine is `D:/Documents/Paradox Interactive/Crusader
Kings III`, resolved from `HKCU\...\User Shell Folders\Personal`. There is a
convincing but dead second copy under `C:/Users/nahue/Documentos`; deploying
there fails silently and looks exactly like a broken mod.

Remove the spike before shipping: `python tools/ck3.py playset remove bc_spike`.

## Validation

    python tools/ck3.py validate battle_chronicles --strict
    python tools/ck3.py conflicts
    python tools/ck3.py launch --clear-logs
    python tools/ck3.py errors

Zero errors required before play. Empty `errors` output after a session is a
clean run.
