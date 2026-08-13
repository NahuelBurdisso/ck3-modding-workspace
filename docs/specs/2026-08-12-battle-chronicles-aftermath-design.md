# Battle Chronicles — Aftermath

Date: 2026-08-12
Status: design, not implemented
Mod: `mods/battle_chronicles`
Predecessor: `2026-08-12-battle-chronicles-design.md`

All line citations are against the file **as loaded**. AGOT wins load order on
most files cited here, so those are AGOT's line numbers, not vanilla's. The
exceptions:

| File | Loaded from |
|---|---|
| `character_memories_events.txt`, `00_memory_values.txt` | vanilla only; AGOT ships no override |
| `memories_l_english.yml` | AGOT, but through `localization/replace/` — which is why `ck3.py where localization/english/...` reports vanilla as the sole source |
| `agot_knight_on_actions.txt` | **AGOT: The Knighting Ceremony** (workshop `3673468355`), a whole-file override of AGOT's |
| `zz_gr_memory_tracking.txt` | **Grand Remembrance** (workshop `3678529052`), its own file |

## The problem

Battle Chronicles opens by claiming it produces "a story instead of a casualty
count". Nine of its ten chronicles do not. `bc_chronicles.0090` strips every
momentum modifier at combat end, the opinion modifiers decay within a few years,
and only `bc_shieldbrother_memory` outlives the war. The mod changes how a battle
feels while it runs. It leaves nothing behind.

This design adds an aftermath layer on the combat-end hook the mod already owns.

## What already exists

Read out of the live playset before designing. It removed more of the original
idea than it kept.

**Both commanders already get a battle memory — but on very different terms.**

- Loser, `combat_on_actions.txt:543-572`: a bare
  `if = { limit = { exists = side_commander, exists = enemy_side.side_commander } }`.
  No random gate. The losing commander gets `battle_lost_memory` **every time**.
- Winner, `combat_on_actions.txt:90-139`: the same existence check wrapped in
  `random = { chance = { value = 10 ... } }`, rising to 100 on a wipe or when the
  enemy commander's primary title tier is **equal or higher**. Base case is
  **10%**.

Both store the province in a memory variable:

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

Both branches also require the **enemy** side to have a commander, so a
leaderless enemy suppresses the memory on both sides.

Consequence for this design: any memory we create for a side commander duplicates
his memory of the same field 100% of the time when he lost and 10% of the time
when he won. Detecting the winner's roll is *expressible* — `any_memory = {
memory_type = battle_won_memory memory_creation_date = current_date }` — but it
would only be correct if AGOT's `effect` block on `on_combat_end_winner` runs
before the merged `events = { }` list, and nothing establishes that ordering. A
guard that is right or wrong depending on an unverified execution order is worse
than not needing one. **Commanders get no memory from us**, and the deeper reason
is that a second memory of the same battle would be noise even if it were safe.

**The knight gets nothing, but his sword does.** `combat_on_actions.txt:199`
walks `every_side_knight` and sets `artifact_battles_won_var = 1` on his equipped
primary armament; `:223` is the increment branch for a weapon that already has
one. The weapon accumulates a battle count. The man carries no record he was
there.

**Vanilla grades battles twice, and neither grade gives a person anything he can
see.** `combat_event.3000` writes a map point-of-interest onto the province.
`historical_artifacts.0100` (`historical_artifacts_events.txt:1018-1059`, itself
`hidden = yes, scope = combat_side` — direct precedent for this whole approach)
stores `epic_battle_location` / `epic_loser` on the primary participant to name
an artifact later. Both use the same idiom:

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
    # ... plus two any_in_list rows over slain_combatants and prisoners_of_war
}
```

`calc_true_if` is the engine's own points system and is the precedent for "was
this battle important enough". This design uses it rather than a bespoke script
value. Both graders are hooked from `on_combat_end_winner` only
(`combat_on_actions.txt:21, :25`), which is why their use of `slain_combatants`
and `prisoners_of_war` is safe for them and is **not** safe for us.

**`battle_poi_number_value` is unusable in AGOT.** It multiplies 3000 by a ladder
keyed on `current_year`, topping out at ×6 above 1400. AGOT's earliest bookmark
is `start_date = 8082.1.1` and every other is later, so the ladder is always
maxed and the unit is always 18000. AGOT copied `08_bp3_values.txt` with a single
unrelated edit and no retuning of this value. Do not reference it. (This does not
mean the map point-of-interest never fires: `combat_event.3000` needs 3 of nine
rows and six of them — `troops_ratio`, `warscore_value >= 15`, the
`slain_combatants` and `prisoners_of_war` rows, and the two `is_ai = no` rows —
do not touch `battle_poi_number_value` at all.)

**AGOT runs a large, live nickname system, and it is gated on the slot we would
take.** `agot_nicknames_pulse` drives roughly 1,630 `give_nickname` calls across
`agot_nicknames_events.txt`. Its generic entry `agot_nicknames.0100` opens
with `has_any_nickname = no` (`agot_nicknames_events.txt:162`), as does vanilla's
`assign_random_nickname_effect` (`00_nickname_effects.txt:41`). Its heroic branch
requires `prowess >= 25` and bold AI and awards exactly the martial flavour an
aftermath nickname would want — `nick_agot_breakspear`,
`nick_agot_shieldbreaker`, `nick_agot_greatheart`, `nick_agot_thunderbolt`. There
are 2,758 unique `nick_agot_*` keys defined across the five files in
`common/nicknames/`, including house-specific dynastic pools.

The exclusion this causes is unavoidable: *any* nickname from any source closes
every AGOT pool for that character. What is avoidable is what he ends up called.
A private `nick_bc_*` pool spends that one slot on a name the mod invented;
AGOT's pool spends it on a name from the setting. That is the whole of the
argument, and it is enough. See Design.

**Existing battle nicknames are career-scale.** `nick_the_undefeated` needs 100
victories without a loss, tracked in `combat_event_0001_tracker`
(`combat_events.txt:112`) and reset to 0 by any defeat (`:151-153`).
`nick_the_triumphant` is for beating the man who holds it.

**AGOT already uses this hook for an aftermath of its own.**
`agot_knight_on_combat_end_winner` rolls a post-battle knighting
(`agot_knight_on_actions.txt:48-53`, as loaded — the playset mod "AGOT: The
Knighting Ceremony" whole-file-overrides AGOT's copy to reroute it). It is
knighting, not
memories or names, so it does not overlap — but the hook is not ours alone.
Grand Remembrance also hooks `on_combat_end_winner` (`zz_gr_memory_tracking.txt:50`)
to track battles for player-tracked characters, granting nothing.

## The gap

A notable battle is currently remembered by a province, an artifact, and a sword.
The men who fought it carry nothing that depends on whether it mattered.

Aftermath fills exactly that:

- grade the battle at its end, on its own numbers
- if it clears the bar, every **knight** on the side carries a memory of that field
- the commander who won a notable field is named for it — **from AGOT's own pool**

## Design

### Where it runs

`bc_chronicles.0090` is one event ID fired from both `on_combat_end_winner` and
`on_combat_end_loser` (`bc_on_actions.txt`), and nothing in its body records
which hook invoked it. `is_combat_side_pursuing` exists and reads "is this side
the winner of the combat", but every script use of it in vanilla and AGOT is
*during* combat, inside `is_army_in_combat = yes`; its value at combat end is
unproven, and this design will not rest on it.

Two new hidden events instead, both `hidden = yes` + `scope = combat_side` with
**no `type =`**, matching `bc_chronicles.0090` (`bc_events.txt:146-149`) and the
vanilla precedent `historical_artifacts.0100` (`:1018-1020`):

| Event | Hook | Job |
|---|---|---|
| `bc_chronicles.0090` | both | cleanup, unchanged |
| `bc_chronicles.0091` | `on_combat_end_winner` | grade, knight memories (won), nickname |
| `bc_chronicles.0092` | `on_combat_end_loser` | grade, knight memories (lost) |

Outcome is then structural, not inferred. `bc_on_actions.txt` keeps its
`events = { }`-only shape, which is required — an `on_action` `effect` block does
not merge across files and the winner is decided by alphabetical filename.

### Grading

`bc_battle_is_notable_trigger`, `calc_true_if`, evaluated with the combat side as
root. Values are read directly; `root.percent_enemies_killed` and
`root.enemy_side.side_max_army_size` are both read as plain values in loaded
script (`combat_events.txt:2506`, `combat_on_actions.txt:442`).

| Condition | Meaning |
|---|---|
| `combat = { num_total_troops >= <SIZE_BIG> }` | a large field |
| `combat = { num_total_troops >= <SIZE_HUGE> }` | a famous field |
| `OR = { percent_enemies_killed >= <BLOOD>, enemy_side.percent_enemies_killed >= <BLOOD> }` | a bloody field |
| `OR = { enemy_side.side_max_army_size >= bc_our_host_gap_value, side_max_army_size >= bc_their_host_gap_value }` | one host was `<ODDS>`× the other |
| `combat = { warscore_value >= <SCORE> }` | it decided something |
| `has_game_rule = bc_aftermath_generous` | a free point when the player asked for one; see The game rule |

**`amount >= 2`**, matching `historical_artifacts.0100`. Five substantive rows.
The two size rows nest — `<SIZE_HUGE>` implies `<SIZE_BIG>` — so what the bar
actually reads is **"huge, or big plus one other thing"**. That is deliberate: a
field of thirty thousand men is notable whatever else happened on it. It also
means the blood, odds and warscore rows never matter for the largest battles, so
their ladders should be read against the *sub-huge* population when calibrating.
The sixth row is the game rule, which hands out a free point under
`bc_aftermath_generous`, so generous reads "any one real row at all". Above 2 the bar starts requiring coincidences rather than significance, and the
run will say whether even 2 is too many.

**The bar must be symmetric, and only two rows are symmetric for free.**
`num_total_troops` and `warscore_value` are `combat`-scoped and identical from
either side. Blood is made symmetric by the explicit `OR` across `enemy_side`.

The odds row is the one that has to be built rather than written. Its natural
form — "we came outnumbered" — is true for the underdog only, and one asymmetric
row under `calc_true_if` counting makes the two sides disagree about whether the
battle was notable. But a bare OR of both directions is worse, not better: `A < B
OR A > B` is just `A != B`, which is true in almost every battle and would donate
a free point to both sides, silently dropping the bar to "any one other row"
while the symmetry check still passed.

What the row needs is a **threshold**, so that it asks "was one host much larger"
rather than "were the hosts unequal". That is what the two script values are for:

```
bc_our_host_gap_value   = { value = root.side_max_army_size            multiply = <ODDS> }
bc_their_host_gap_value = { value = root.enemy_side.side_max_army_size multiply = <ODDS> }
```

**`root.`, not a bare operand.** Both rows put a scope path on the left —
`enemy_side.side_max_army_size >= bc_our_host_gap_value` — and if the engine
resolves an unprefixed script value on the right in the *left* operand's scope,
`bc_our_host_gap_value` would evaluate as the enemy host and the row would read
`enemy >= enemy × 1.5`: permanently false, on both sides, while still passing the
winner-versus-loser symmetry check that is supposed to catch exactly this. That
resolution rule is unverified and the design should not depend on knowing it.
Anchoring removes the question. Vanilla anchors too, though at the call site
rather than in the value: `vastly_outnumbered_combat_side_threshold` has a bare
`side_strength` operand (`00_combat_values.txt:7-10`) and every one of its four
call sites writes the full path on both sides
(`00_commander_phase_events.txt:186, :316`, `00_knight_phase_events.txt:797, :998`).
This mod's own `bc_outnumbered_threshold_value` anchors in the value itself, with
`scope:combat_side.` — the same instinct, a different root, because those values
are read from phase events where `scope:combat_side` is what exists.

Each side then asks whether either host was at least `<ODDS>` times the other.
Both sides compute the same answer, and `<ODDS>` is a real tunable — 1.5 to
start, matching the existing threshold values. **`<ODDS>` must be strictly
greater than 1.** At exactly 1 the row degenerates back to `A != B` and
reproduces the free-point failure it was built to avoid; at less than 1 it is
true always.

This does not avoid using `side_max_army_size` as a trigger, and it is not
trying to. That use has no script precedent anywhere
in vanilla, AGOT or the playset (every occurrence is as a script value operand:
`combat_on_actions.txt:442, :476`, `zz_gr_memory_tracking.txt:74`) but it is
documented as legal — the API dump lists `side_max_army_size` with traits
`<, <=, =, !=, >, >=` and supported scope `combat_side`. Unprecedented, not
unsupported. If it turns out to be neither, the row is the one piece of the bar
that can be dropped without touching anything else.

**Starting odds, not ending odds.** `troops_ratio` exists and vanilla uses it,
but the API documents `side_army_size` as current and `side_max_army_size` as
max possible, so at combat *end* a ratio of current strengths reflects the
outcome rather than the odds. This is an inference from the API text, not a
demonstrated fact — it also implies vanilla's own `troops_ratio <= 0.5` in its
winner-side graders is permanently false, which is consistent but unverified.
`side_max_army_size` on both sides is the strength each side brought, and is
independently corroborated: Grand Remembrance computes casualties as
`side_max_army_size - side_army_size` (`zz_gr_memory_tracking.txt:74`).

**Thresholds are placeholders, not values.** Vanilla's numbers (20000 troops, 75%
slain) are calibrated for CK3 army sizes; Westerosi hosts are larger, and a bar
copied across would fire on ordinary battles. They still need somewhere to start,
so the run ships with vanilla's numbers as the opening guess — `<SIZE_BIG>`
20000, `<SIZE_HUGE>` 30000, `<BLOOD>` 75, `<SCORE>` 25 (vanilla's own
`warscore_value >= 25`), `<ODDS>` 1.5 — and the markers below report the real
distribution so all five can be reset in one pass. `<SCORE>` is the least
trustworthy of them: it is the only row whose scale is not troops, and AGOT's
warscore is not obviously on vanilla's scale, so it gets its own marker ladder
alongside size, blood and odds. See Calibration.

The trigger takes the combat side as root and does **not** use
`scope:combat_side`. The header of `bc_scripted_triggers.txt` currently declares
that every trigger in the file assumes `scope:combat_side` exists; that header
must be amended, because this one is the exception.

**The grade runs in `immediate`, not in the event `trigger`.** The cited
precedent `historical_artifacts.0100` puts its `calc_true_if` in the event
trigger, and copying that would be wrong here: the calibration markers below have
to fire on *every* combat end, including the ones that fail the bar, or they
measure only the battles that already passed. The events fire on every combat
end, log, then branch on the grade. The only thing in their `trigger` is the
`bc_aftermath_off` check.

### What a notable battle leaves — knights

```
if = {
    limit = { exists = scope:bc_battle_province }
    every_side_knight = {
        limit = {
            is_alive = yes
            NOT = { this = root.side_commander }
        }
        ...
    }
}
```

`NOT = { this = root.side_commander }` protects the one guarantee this design
makes — that **we** never give a commander a battle memory, because vanilla
already does. Nothing in the API says whether `every_side_knight` includes the
commander; vanilla runs `every_side_knight` and `every_side_commander` back to
back without deduplicating (`combat_events.txt:2087-2093`, `:2119-2125`), which
hints the sets are disjoint but does not prove it. The guard costs nothing if
they are.

The province check is an enclosing `if`, not part of the `limit` — it is a
property of the battle, and re-asking it once per knight is noise.

`is_alive = yes` because commanders and knights die in the combat that just
ended. Vanilla guards its own knight handling at combat end for exactly this
reason — inside its post-battle knight `random_list`, every outcome branch opens
`is_alive = yes` (`combat_events.txt:854`, and `:1028` with the comment `# Don't
kill knights who are already dead!`), and the side commander is guarded the same
way at `:87`. The mod's own knight phase events already gate on it.

The province scope must be saved by us. Vanilla saves `battle_province` in the
on_action's `effect` block, which this mod cannot do, so it is saved at the top
of the event instead:

```
combat.location ?= { save_scope_as = bc_battle_province }
```

Then, per knight:

```
bc_battle_memory_effect = { TYPE = bc_battle_memory_won }

# bc_scripted_effects.txt
bc_battle_memory_effect = {
    create_character_memory = { type = $TYPE$ }
    scope:new_memory ?= {
        set_variable = { name = battle_location value = scope:bc_battle_province }
    }
}
```

One effect parameterised by `$TYPE$` rather than two, matching the mod's existing
`bc_add_momentum_effect = { MODIFIER = ... }` (`bc_scripted_effects.txt:12-17`).
The won/lost split is a localization decision, not a behavioural one.

**`scope:new_memory` directly, without the double-scoping dance.** Vanilla's
battle memories re-save it into a second scope first
(`combat_on_actions.txt:127-135`), carrying the comment "we have to do this weird
double-scoping due to some kind of dark pact with Code, else things won't work"
(`00_knight_phase_events.txt:564`, and `harm_events.txt:673, :770`). Four sites in
total, and they are the exception. Twenty-odd shipped sites write
`scope:new_memory` straight — `hajj_events.txt:81, :1022`,
`ep4_decision_events.txt:56, :240, :347, :628, :765, :858` (one of which stores a
*saved scope* as the value, `scope:new_primary_title`, which is our exact case),
`adoption_events.txt:82, :95`, `bp3_journey_events.txt:519`, and more. The API
dump states it as the contract outright: `create_character_memory` is
"**Saved as scope:new_memory**". The dance is cargo cult, and copying it would
have added a decision — temporary scope or not — to a question that does not
exist. If the restart shows the variable unset, the double-scoping is the
fallback.

Localization reads the variable back with the vanilla accessor. AGOT **does**
override this file, but through `localization/replace/english/memories_l_english.yml`
rather than the ordinary path, which is why `ck3.py where localization/english/...`
reports vanilla as the only source — the tool does not look in `replace/`. The
accessors are byte-identical in both copies — the description form at `:927-929`
in the loaded one, the title form at `:555-556`:

```
# description
[ROOT.Var('battle_location').GetProvince.GetName]
# title
[ROOT.Var('battle_location').GetProvince.GetNameNoTooltip]
```

Two accessors, not one. The title uses `GetNameNoTooltip`, as vanilla's own
battle-memory titles do ("Battle of …"); `GetName` there would nest a tooltip
inside a memory-list entry.

Two memory types, `bc_battle_memory_won` and `bc_battle_memory_lost`, so the
polarity token is right and the localization stays simple. Categories follow
their vanilla counterparts including that token — `{ positive martial war battle }`
and `{ negative martial war battle }` (`character_memories_1.txt:2668`, `:2637`)
— with `icon = "battle.dds"`. No `participants` block: the memory is about a
field, not a person, and `became_incapable_due_to_battle_concussion`
(`character_memories_events.txt:1278-1296`) is the precedent for a
participant-free memory type carrying `battle_location`.

**`duration = { years = 40 }`, not `memory_default_duration`.** Every precedent
cited above uses the default, and the default would destroy this feature. It
resolves to `value = 5` plus large bonuses that only rulers, duchy-tier holders
and the player's own circle collect (`00_memory_values.txt:1-61`) — a landless AI
knight scores **5**. That is precisely the population this feature exists for, so
the field they fought on would be forgotten within five years while the mod's
opening claim is that it "leaves nothing behind" today. The mod already made this
exact decision once: `bc_shieldbrother_memory` sets forty years with the comment
that this is what is left after everything else has gone
(`bc_memories.txt:40-44`). Nothing in the restart would catch a wrong duration —
it tests rendering, not expiry — so it has to be right by construction.

This also repairs a known dead loop. `bc_chronicles.0090` already walks
`every_side_knight` calling `bc_cleanup_effect`, which is a no-op: two knight
chronicles apply momentum to `scope:combat_side.side_commander` rather than to
the knight (`bc_knight_phase_events.txt:94, :167`) and the third,
`bc_shieldbrother_forged`, applies none at all, so knights never hold a momentum
modifier for `bc_cleanup_effect` to strip. The new events give that walk real
work.

### What a notable battle leaves — the commander

On a notable battle he won, in `bc_chronicles.0091` only:

```
side_commander ?= {
    if = {
        limit = {
            is_alive = yes
            has_any_nickname = no
            exists = var:bc_notable_battles
            var:bc_notable_battles >= <N>
            martial >= 14
        }
        bc_aftermath_nickname_effect = yes
    }
}
```

The counter is incremented **before** this check, so `<N>` counts the battle just
fought. `exists` guards the read; a `var:` comparison against a variable that was
never set does not evaluate to false safely.

`martial >= 14`, not prowess — this names a commander for commanding, and it is
the same threshold the mod already uses for its high-martial phase-event bonus
(`bc_commander_phase_events.txt:305`). It is deliberately not AGOT's heroic gate
of `prowess >= 25` plus bold AI; a man can be the finest field commander in
Westeros and a mediocre swordsman, and that is exactly who this is for.

`<N> = 3` to start. Three notable fields won is already a career in a setting
where most lords fight a handful of battles and few of those clear the bar. The
run reports the notable-battle rate, which is what says whether 3 is a career or
a formality.

**The pool is exactly AGOT's heroic list — all 27 entries, weight 1 each, no null
entry** (`agot_nicknames_events.txt:186-213`, `nick_agot_the_warrior` through
`nick_agot_the_painter`). No null, because the gate above has already decided the
man deserves a name; the list only decides which. Copying the whole list rather
than a hand-picked subset keeps the mod out of the business of judging which of
AGOT's names are martial enough, and means the pool tracks AGOT if AGOT extends
it — the keys are referenced, not redefined.

**The award is announced with a toast**, `event_toast_effect_good`, on the
commander. It is the mod's own rule that state comes first and presentation
second, and this is presentation: `give_nickname` runs in the effect block,
outside the toast, so the AI commander is named whether or not anyone is watching.
Vanilla announces its own battle nickname the same way rather than silently
(`combat_events.txt:209`).

**Why AGOT's pool and not ours.** Both choices consume the same
`has_any_nickname = no` slot and both therefore close AGOT's whole nickname
system for that character. They differ only in what the character is left
holding. Drawing from AGOT's heroic martial names —
`nick_agot_breakspear`, `nick_agot_shieldbreaker`, `nick_agot_greatheart`,
`nick_agot_thunderbolt` — means the mod is not adding a name so much as
**deciding when and why AGOT's name arrives**, and a player who never reads the
mod list sees a name that belongs to the setting.

**This still displaces AGOT's dynastic names, and there is no gate that prevents
it.** Every dynastic event gates on `has_any_nickname = no` independently of the
generic one (`agot_nicknames_events.txt:1332-1340` for the Lannister pool), so
*any* name we award closes *every* AGOT pool for that character, house names
included. The `martial >= 14` gate at least does not aim at the same men AGOT's
heroic branch wants — that branch needs `prowess >= 25` and bold AI, and the two
populations only partly overlap — but it does not have to, because the dynastic
pools have no skill gate at all. And our rate is far higher than AGOT's: `agot_nicknames.0100` is weight 2 of 174 in `agot_nicknames_pulse`
(`agot_nicknames_on_actions.txt:1-71`), driven off a five-year pulse, and inside
it the heroic branch is weight 50 against a 1000-weight null
(`agot_nicknames_events.txt:177-186`).

So the displacement is real and is accepted rather than mitigated. The only
honest control is **rarity**: a notable battle, won, by a living commander with
martial distinction, on his `<N>`th notable field. `<N>` has to stay high enough
that a commander who earns one has fought a career AGOT's pulse would not have
described better. If that proves wrong in play, `bc_aftermath_off` exists for it.

`has_any_nickname = no`, not vanilla's `set_nickname_effect` — that effect
deliberately overwrites any nickname flagged `is_bad`
(`00_nickname_effects.txt:8-11`), and a Westeros playset is full of
bad-sounding canon names worth keeping.

This is the first time mod *script* references an AGOT key. The dependency itself
is not new — `descriptor.mod` already declares `dependencies = { "A Game of
Thrones" }` — and the stance the mod does hold, avoiding hard dependencies, was
always about *optional* playset mods such as Seasons of Ice and Fire, which is
why the terrain triggers use plain vanilla keys.

### The game rule

`bc_aftermath`, three options, following the shape of the mod's existing
`bc_frequency` and `bc_swing` — including the naming convention, where every
option key repeats the rule name and is read with `has_game_rule`
(`bc_game_rules.txt:7-8, :17-25`):

| Option | Effect |
|---|---|
| `bc_aftermath_off` | no grading, no memories, no nicknames. The mod behaves exactly as it does today. |
| `bc_aftermath_default` | as designed. `amount >= 2`, `<N>` as set. |
| `bc_aftermath_generous` | one free `calc_true_if` point, so one real row suffices; notable fields and names are commoner |

`default = bc_aftermath_default`, declared as the mod's other two rules declare
theirs (`bc_game_rules.txt:20, :30`), and `categories = { flavor }` to match.

Wired in two places:

- **`off` sits in the event `trigger`** of `bc_chronicles.0091` and `.0092`:
  `NOT = { has_game_rule = bc_aftermath_off }`. The events then do not fire at
  all, which silences the calibration markers too — correct, because off means
  the feature is not running and there is nothing to calibrate. This is the one
  thing that belongs in the trigger rather than in `immediate`; the *grade* still
  runs in `immediate` for the reason given above.
- **`generous` is a sixth `calc_true_if` row**, `has_game_rule =
  bc_aftermath_generous`, sitting in the same list as the other five. Under
  `generous` it contributes a free point, so `amount >= 2` becomes "one real row"
  without a second copy of the list. `calc_true_if` counts its direct children
  and a nested scripted trigger would count as one row, so branching on two
  parallel `calc_true_if` blocks would mean maintaining the list twice; this way
  there is only ever one list. It is also symmetric for free — both sides read
  the same game rule.

`off` is not decoration. The nickname branch knowingly displaces AGOT's own
nickname system for the characters it touches, and a player who wants AGOT's
pulse untouched needs a way to say so. Note the warning already in
`bc_game_rules.txt:10-13`: a game rule is baked into every save made with it, so
this must ship with the feature rather than be added later.

### The counter

`bc_notable_battles`, on side commanders only, incremented in `bc_chronicles.0091`
**only** — notable battles **won** — and **before** the nickname check, using the
create-or-increment pattern at `combat_events.txt:90-107`:

```
if = {
    limit = { NOT = { exists = var:bc_notable_battles } }
    set_variable = { name = bc_notable_battles value = 1 }
}
else = { change_variable = { name = bc_notable_battles add = 1 } }
```

Wins only, because it exists to gate the nickname and the nickname is for the man
who won great fields. Counting defeats would let a commander be named for
presiding over `<N>` disasters, and would break the "several great days" argument
that is the only real control on the nickname's rarity. It follows that the
loser's event does not touch the counter at all, and that the two events are not
mirror images — `.0092` grades and writes knight memories, nothing more.

It is never cleared — that is the point, and it is why it lives on commanders
only, keeping the leak surface to one variable on characters who lead armies.
Distinct from `combat_event_0001_tracker`, which counts consecutive wins and
resets on any loss; this one is cumulative and survives defeat, it just does not
grow on it.

## Files

| Path | Change |
|---|---|
| `common/character_memory_types/bc_memories.txt` | add `bc_battle_memory_won`, `bc_battle_memory_lost` |
| `common/scripted_triggers/bc_scripted_triggers.txt` | add `bc_battle_is_notable_trigger`; amend the file header's scope invariant |
| `common/scripted_effects/bc_scripted_effects.txt` | add `bc_battle_memory_effect = { TYPE = ... }`, `bc_notable_battle_counter_effect`, `bc_aftermath_nickname_effect` |
| `common/script_values/bc_script_values.txt` | add `bc_our_host_gap_value`, `bc_their_host_gap_value`; note in the file header that these two read the combat side as **root**, unlike the two existing values, which are written against `scope:combat_side` (`bc_script_values.txt:19, :24`) |
| `common/on_action/bc_on_actions.txt` | `.0091` to `on_combat_end_winner`, `.0092` to `on_combat_end_loser` |
| `common/game_rules/bc_game_rules.txt` | add `bc_aftermath` (`bc_aftermath_off` / `_default` / `_generous`) |
| `events/bc_events.txt` | add `bc_chronicles.0091` and `.0092` |
| `localization/english/bc_l_english.yml` | 2 memory titles + 2 descriptions × 3 perspectives; the nickname toast; and the 8 game-rule keys — `rule_bc_aftermath`, `rule_bc_aftermath_desc`, and `setting_bc_aftermath_<option>` / `_desc` for each of the three options, following `bc_l_english.yml:26-42` |

No new files, and no new nickname file — the AGOT-pool decision removes it.
Every path is already mod-owned, so the zero-collision property is unchanged by
construction rather than by checking.

Variable names to avoid, all live in the playset: `battle_poi_*`, `epic_*`,
`artifact_battles_won_var`, `combat_event_0001_tracker`, and `battle_province` /
`battle_memory` as scope names. Ours are `bc_`-prefixed except the memory-scoped
`battle_location`, which is namespaced by living on the memory.

## Failure modes

- **Duplicate commander memory.** Avoided by never creating one for him, and by
  excluding him from the knight loop in case `every_side_knight` includes him.
- **Nickname exclusion.** Reduced by drawing from AGOT's pool rather than a
  private one, but not eliminated: any name closes every AGOT pool for that
  character, dynastic included. Controlled by rarity and by `bc_aftermath_off`.
- **Dead characters.** `is_alive = yes` on the knight loop and the commander
  branch. Commanders and knights can die in the combat that just ended.
- **Leaderless sides.** `side_commander ?=` and `combat.location ?=` throughout.
- **`scope:new_memory` not rebinding per iteration.** No shipped precedent for
  creating a memory inside an iterator. The one unproven line in the design, with
  a known fallback. See Verification.
- **Bar too low.** Every knight in Westeros ends up with a wall of memories and
  the mark means nothing. **Bar too high.** Nothing fires, which is how vanilla's
  battle point-of-interest already behaves in AGOT. Both detected by the same
  instrumentation.
- **Asymmetric grading.** The odds row in its natural one-sided form makes winner
  and loser disagree; a bare two-way OR instead collapses to `!=` and makes the
  bar far too low while *still passing* a symmetry check. Both failures are
  silent. The script-value threshold addresses both, and the side-tagged markers
  are what would catch a regression.
- **Knight loop cost.** Bounded: once per battle, not once per five-day phase
  tick, and the event already walks this list.
- **`slain_combatants` / `prisoners_of_war`** are available at combat end and
  used by both vanilla graders, but only on the winner hook. This design
  deliberately depends on neither.

## Calibration

Thresholds cannot be guessed, and a restart costs about seven minutes, so the run
that sets them must also be the run that tests everything else.

`bc_chronicles.0091` / `.0092` log buckets on every combat end the events fire
on, independently of the bar. **Every marker is tagged with which side logged
it**, because the two events fire on the same battle and untagged markers would
double-count the distribution and, worse, make the winner-versus-loser comparison
below impossible — the one test that catches an asymmetric bar:

```
# in .0091 (winner)
if = { limit = { combat = { num_total_troops >= 40000 } } debug_log = "BC: win size 40k+" }
else_if = { limit = { combat = { num_total_troops >= 20000 } } debug_log = "BC: win size 20k+" }
...
# in .0092 (loser), identical ladder, "BC: lose size ..."
```

Buckets rather than interpolated numbers because `ck3.py probe` tallies repeated
markers; `debug_log` does support localization interpolation with ROOT, SCOPE and
PREV available, but a unique string per battle cannot be counted. Same treatment
for `percent_enemies_killed`, for `warscore_value`, and for the odds gap. All
markers are stripped once the numbers are set.

## Verification

Folded into the restart already owed for the previous pass, which must also
answer whether the two knight events fire, whether `bc_shieldbrother_memory`
renders, whether `[shieldbrother.GetFullName]` resolves, whether the retuned
weights behave, and whether a toast body runs for an AI character.

Aftermath adds:

- `probe 'BC: win size'` / `'BC: lose size'`, and the same for blood, warscore
  and odds — four ladders, for setting all five thresholds (`<SIZE_BIG>` and
  `<SIZE_HUGE>` come off the one size distribution)
- `probe 'BC: win notable'` vs `'BC: lose notable'` — **the counts must match
  exactly**. Any divergence means the bar is asymmetric. Equal counts alone do
  not prove the bar is right, only that it is even; the size distribution is what
  says whether it is set sensibly.
- a knight's memory list rendering `bc_battle_memory_*` with the province name.
  **This is the highest-risk line in the design.** No shipped script anywhere
  creates a character memory inside an `every_*` iterator, so nothing proves
  `scope:new_memory` rebinds on each pass rather than sticking to the first
  memory created. The failure is not loud — it renders as one knight with a
  correct memory and the rest with an empty one, or as every memory naming the
  same field. So the check is specifically: **open two different knights from the
  same battle and confirm both name the province the battle was fought in.** If
  it fails, the fallback is to save the memory into a per-iteration scope
  (`scope:new_memory = { save_temporary_scope_as = bc_memory }`) before writing
  the variable.
- `probe 'BC: nickname'` — and, if zero, a companion marker on each failed gate,
  so a nickname that never fires is explained rather than merely absent

## Rejected

- **A memory for the side commander.** He already has one, guaranteed if he lost
  and on a 10% roll if he won. Detecting the roll is expressible with
  `any_memory` + `memory_creation_date`, but only correct if the on_action's
  `effect` runs before its `events` list, which is unestablished — and a second
  memory of the same field would be noise even if the guard were sound.
- **`save_temporary_scope_as` after `create_character_memory`.** Copies a
  four-site vanilla idiom whose own comment admits it is unexplained, when twenty
  shipped sites and the API dump say `scope:new_memory` is usable directly.
  Retained only as the fallback if the restart shows the variable unset.
- **A private `nick_bc_*` pool.** Squats the `has_any_nickname = no` slot AGOT's
  own nickname system depends on, and adds a name nobody asked for. AGOT's pool
  displaces the same slot but at least returns a name from the setting.
- **A bare two-way OR for the odds row.** `A < B OR A > B` is `A != B`. It is
  symmetric, which makes it pass the one check designed to catch a broken odds
  row, while quietly granting both sides a free `calc_true_if` point.
- **`set_nickname_effect`.** Overwrites nicknames flagged `is_bad`, which in a
  Westeros playset includes canon names worth keeping.
- **Inferring the outcome inside a single event.** `is_combat_side_pursuing` is
  documented for it but is only ever used mid-combat in shipped script. Two
  events, one per hook, costs nothing and removes the question.
- **A bespoke script value for scoring.** `calc_true_if` is the engine's own
  points system and is what vanilla uses for this exact question, twice.
- **Reusing `battle_poi_number_value`.** Always 18000 in AGOT.
- **`troops_ratio` for odds.** Post-battle, so it measures the result.
- **Carrying phase-event deeds into the aftermath** so the marks reflect what
  each man actually did. The better story, and the intended successor to this
  design, but it requires a per-character counter on every participant that must
  be cleared on both sides or leak forever, and it builds on the knight phase
  events, which have never yet been observed firing. Revisit once the run
  reports.
