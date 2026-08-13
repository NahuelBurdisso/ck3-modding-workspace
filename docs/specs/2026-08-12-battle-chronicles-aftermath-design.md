# Battle Chronicles — Aftermath

Date: 2026-08-12
Status: design, not implemented
Mod: `mods/battle_chronicles`
Predecessor: `2026-08-12-battle-chronicles-design.md`

## The problem

Battle Chronicles opens by claiming it produces "a story instead of a casualty
count". Nine of its ten chronicles do not. `bc_chronicles.0090` strips every
momentum modifier at combat end, the opinion modifiers decay within a few years,
and only `bc_shieldbrother_memory` outlives the war. The mod changes how a battle
feels while it runs. It leaves nothing behind.

This design gives `bc_chronicles.0090` a second job. It already fires on both
sides of every combat and currently only deletes.

## What already exists

Everything below was read out of the live playset before designing, and it
removed more of the original design than it kept.

**The commander already gets a battle memory.** `combat_on_actions.txt:117`
creates `battle_won_memory` on `side_commander`, participants `loser` and
`ruler`, and stores the province:

```
combat.location = { save_scope_as = battle_province }
side_commander = {
    create_character_memory = { type = battle_won_memory ... }
    scope:new_memory = { save_scope_as = battle_memory }
    scope:battle_memory = {
        set_variable = { name = battle_location value = scope:battle_province }
    }
}
```

The mirror is at `:552` for the loser. The chance is 10, rising to 100 on a wipe
or against a higher-tier enemy. There is no notability test. **We must not create
a second battle memory for the side commander** — he would carry two memories of
one field.

**The knight gets nothing, but his sword does.** `combat_on_actions.txt:199`
walks `every_side_knight` and increments `artifact_battles_won_var` on his
equipped primary armament. The weapon accumulates a battle count. The man
carries no record that he was there at all.

**Vanilla grades battles twice, and neither grade touches a person.**
`combat_event.3000` writes a map point-of-interest onto the province.
`historical_artifacts.0100` stores `epic_battle_location` / `epic_loser` on the
primary participant to name an artifact later. Both use the same idiom:

```
calc_true_if = {
    amount >= 2
    troops_ratio <= 0.5
    num_enemies_killed >= 10000
    AND = {
        percent_enemies_killed >= 75
        combat = { num_total_troops >= 20000 }
    }
    combat = { OR = { num_total_troops >= 30000 warscore_value >= 25 } }
}
```

`calc_true_if` is the engine's own points system and is the precedent for "was
this battle important enough". This design uses it rather than a bespoke script
value.

**`battle_poi_number_value` is unusable in AGOT.** It multiplies 3000 by a ladder
keyed on `current_year`, topping out at ×6 above 1400. AGOT bookmarks start at
`8082.1.1`, so the ladder is always maxed and the unit is always 18000. AGOT
copied the file verbatim without retuning it, which is why vanilla's battle
point-of-interest is close to unreachable in Westeros. Do not reference it.

**Existing nicknames are career-scale, not battle-scale.** `nick_the_undefeated`
needs 100 victories without a loss, tracked in `combat_event_0001_tracker` and
reset to 0 by any defeat. `nick_the_triumphant` is for beating the man who holds
it. Nothing marks a man for one great day.

## The gap

A notable battle is currently remembered by a province, an artifact and a sword.
It is not remembered by the men who fought it, except for the one commander who
may or may not roll a memory with no regard for whether the battle mattered.

Aftermath fills exactly that and nothing else:

- grade the battle at its end, on its own numbers
- if it clears the bar, every **knight** on the side carries a memory of that field
- the **commander** who won a notable field, and has no name yet, earns one

Knights get the memory because they have none. The commander gets the nickname
because he already has the memory. No overlap with anything above.

## Grading

In `bc_chronicles.0090`, scope `combat_side`, before cleanup.

`bc_battle_is_notable_trigger` in `bc_scripted_triggers.txt`, `calc_true_if`,
reading values directly (`root.percent_enemies_killed` and
`root.enemy_side.side_max_army_size` are read as values in vanilla at
`combat_events.txt:2315` and `combat_on_actions.txt:433`):

| Condition | Meaning |
|---|---|
| `combat = { num_total_troops >= <SIZE_BIG> }` | a large field |
| `combat = { num_total_troops >= <SIZE_HUGE> }` | a famous field |
| `percent_enemies_killed >= <BLOOD>` on either side | a bloody field |
| `side_max_army_size` vs `enemy_side.side_max_army_size` | one side came outnumbered |
| `combat = { warscore_value >= <SCORE> }` | it decided something |

**The bar is symmetric.** Every input is readable from either side — blood via
`enemy_side`, odds via both `side_max_army_size` values — so the winner and the
loser compute the same score and always agree the battle was notable. The
outcome selects which *text* a man carries, never *whether* he carries one. A
field the victors remember and the defeated do not is backwards.

**Starting odds, not ending odds.** `troops_ratio` exists and vanilla uses it,
but at combat *end* it reflects the outcome rather than the odds — a side that
won crushingly reads as though it outnumbered the enemy. `side_max_army_size` on
both sides is the strength each side brought, which is what "against the odds"
means.

**Thresholds are unset on purpose.** Vanilla's numbers (20000 troops, 75% slain)
are calibrated for CK3 army sizes; Westerosi hosts are larger, and a bar copied
across would fire on ordinary battles. See Calibration.

## What a notable battle leaves

**Knights.** `every_side_knight` gets one `bc_battle_memory`, following the
vanilla shape exactly, including the double-scoping vanilla itself comments on
("some kind of dark pact with Code", `00_knight_phase_events.txt:534`):

```
create_character_memory = { type = bc_battle_memory }
scope:new_memory = { save_scope_as = bc_memory }
scope:bc_memory = {
    set_variable = { name = battle_location value = scope:bc_battle_province }
}
```

Localization reads it back with the proven vanilla accessor, per
`memories_l_english.yml:925`:

```
[ROOT.Var('battle_location').GetProvince.GetName]
```

Two memory types, `bc_battle_memory` won and lost, or one type plus a second
variable — decided at implementation, whichever keeps the localization simpler.
Categories follow `battle_lost_memory`: `{ martial war battle }`, `icon =
"battle.dds"`. No `participants` block; the memory is about a field, not a
person, and `became_incapable_due_to_battle_concussion` sets the precedent for a
participant-free memory type.

This also repairs a known dead loop. `bc_chronicles.0090` already walks
`every_side_knight` calling `bc_cleanup_effect`, which is a no-op — knights never
hold momentum, since every knight chronicle applies it to `side_commander`. The
loop now does real work.

**The commander.** On a notable battle he won, `give_nickname` from a new pool,
gated hard:

- `has_any_nickname = no` — never overwrite. `has_nickname` takes a specific key
  and cannot answer "does he have one"; `has_any_nickname` is the trigger.
  Vanilla's `set_nickname_effect` is deliberately **not** used: it overwrites a
  nickname flagged `is_bad`, and AGOT canon is full of bad-sounding names that
  must survive.
- `var:bc_notable_battles >= <N>` — not his first notable field. A name earned
  across several great days reads as earned. This is what the counter is for; it
  is not speculative state.

The pool is new `nick_bc_*` keys in a new file. AGOT ships five nickname files
and roughly 490 generic nicknames under `nick_agot_*`, none of which are awarded
for a single battle. Format is trivial — `nick_bc_x = {}` plus `nick_bc_x:0` and
`nick_bc_x_desc:1` localization.

**The counter.** `bc_notable_battles` on side commanders only, guarded with the
vanilla create-or-increment pattern from `combat_events.txt:100`:

```
if = {
    limit = { NOT = { exists = var:bc_notable_battles } }
    set_variable = { name = bc_notable_battles value = 1 }
}
else = { change_variable = { name = bc_notable_battles add = 1 } }
```

It is never cleared — that is the point, and it is why it lives on commanders
only, keeping the leak surface to one variable on characters who lead armies.
Distinct from `combat_event_0001_tracker`, which counts consecutive wins and
resets on any loss.

## Files

All new. Zero collisions by construction; `common/nicknames/` currently has no
collisions in the playset at all.

| Path | Change |
|---|---|
| `common/character_memory_types/bc_memories.txt` | add `bc_battle_memory` |
| `common/nicknames/bc_nicknames.txt` | new — the `nick_bc_*` pool |
| `common/scripted_triggers/bc_scripted_triggers.txt` | add `bc_battle_is_notable_trigger` |
| `common/scripted_effects/bc_scripted_effects.txt` | add the memory, nickname and counter effects |
| `common/game_rules/bc_game_rules.txt` | add `bc_aftermath` (off / default / generous) |
| `events/bc_events.txt` | `bc_chronicles.0090` grades before it cleans up |
| `localization/english/bc_l_english.yml` | memory descriptions ×3 perspectives, nickname names and descs |

Variable names to avoid, all live in the playset: `battle_poi_*`, `epic_*`,
`battle_location` on a province, `artifact_battles_won_var`,
`combat_event_0001_tracker`. Ours are `bc_`-prefixed except the memory-scoped
`battle_location`, which is namespaced by living on the memory.

## Failure modes

- **Double memory on the commander.** Guarded by never creating one for him.
- **Nickname vandalism.** One gate, `has_any_nickname = no`, in one effect. If it
  is wrong, canon names are destroyed permanently across the save. It is the
  single highest-risk line in the design and belongs in exactly one place.
- **Bar too low.** Every knight in Westeros ends up with a wall of memories and
  the mark means nothing. Mitigated by measuring before setting — see below.
- **Bar too high.** Nothing ever fires, which is how vanilla's battle
  point-of-interest already behaves in AGOT. Detected by the same instrumentation.
- **Knight loop cost.** Bounded: once per battle, not once per five-day phase
  tick, and 0090 already walks this list.
- **`slain_combatants` / `prisoners_of_war`** are available at combat end and
  used by both vanilla graders, but only demonstrably on the winner hook. This
  design deliberately depends on neither.

## Calibration

Thresholds cannot be guessed, and a restart costs about seven minutes, so the
run that sets them must also be the run that tests everything else.

`bc_chronicles.0090` logs a size bucket on every combat end, unconditionally and
independently of the bar:

```
if = { limit = { combat = { num_total_troops >= 40000 } } debug_log = "BC: size 40k+" }
else_if = { limit = { combat = { num_total_troops >= 20000 } } debug_log = "BC: size 20k+" }
...
```

`debug_log` takes a literal string, so buckets rather than interpolated numbers.
`ck3.py probe 'BC: size'` then returns the real distribution of battle sizes in
this playset, and the bar is set against it rather than against vanilla's.

Same treatment for `percent_enemies_killed`. Both sets of markers are stripped
once the numbers are chosen.

## Verification

Folded into the restart already owed for the previous pass, which must also
answer whether the two knight events fire, whether `bc_shieldbrother_memory`
renders, whether `[shieldbrother.GetFullName]` resolves, whether the retuned
weights behave, and whether a toast body runs for an AI character.

Aftermath adds:

- `probe 'BC: size'` and `'BC: blood'` — the distribution, for setting the bar
- `probe 'BC: notable'` — how often the bar is cleared
- a knight's memory list rendering `bc_battle_memory` with the province name
- `probe 'BC: nickname'` — and, if zero, a companion marker on each failed gate,
  so a nickname that never fires is explained rather than merely absent

## Rejected

- **A memory for everyone who fought.** Duplicates the commander's existing
  battle memory. Knights only.
- **A bespoke script value for scoring.** `calc_true_if` is the engine's own
  points system and is what vanilla uses for this exact question, twice.
- **Reusing `battle_poi_number_value`.** Always 18000 in AGOT.
- **`set_nickname_effect`.** Overwrites nicknames flagged `is_bad`, which in a
  Westeros playset includes canon names worth keeping.
- **`troops_ratio` for odds.** Post-battle, so it measures the result.
- **Carrying phase-event deeds into the aftermath** so the marks reflect what
  each man actually did. The better story, and the intended successor to this
  design, but it requires a per-character counter on every participant that must
  be cleared on both sides or leak forever, and it builds on the knight phase
  events, which have never yet been observed firing. Revisit once the run
  reports.
