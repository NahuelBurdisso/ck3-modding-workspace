# Battle Chronicles — Aftermath

Date: 2026-08-12
Status: design, not implemented
Mod: `mods/battle_chronicles`
Predecessor: `2026-08-12-battle-chronicles-design.md`

All line citations are against the file **as loaded**. AGOT wins load order on
most files cited here, so those are AGOT's line numbers, not vanilla's. The
exceptions are `character_memories_events.txt`, which only vanilla ships, and
`memories_l_english.yml`, which AGOT overrides through `localization/replace/`.

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
- Winner, `combat_on_actions.txt:90-136`: the same existence check wrapped in
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

Consequence for this design: there is no way to detect whether the vanilla roll
fired. Any memory we create for a side commander duplicates his memory of the
same field 100% of the time when he lost and 10% of the time when he won.
**Commanders get no memory from us.**

**The knight gets nothing, but his sword does.** `combat_on_actions.txt:199`
walks `every_side_knight` and sets `artifact_battles_won_var = 1` on his equipped
primary armament; `:223` is the increment branch for a weapon that already has
one. The weapon accumulates a battle count. The man carries no record he was
there.

**Vanilla grades battles twice, and neither grade touches a person.**
`combat_event.3000` writes a map point-of-interest onto the province.
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
maxed and the unit is always 18000. AGOT copied `08_bp3_values.txt` verbatim
without retuning, which is why vanilla's battle point-of-interest is close to
unreachable in Westeros. Do not reference it.

**AGOT runs a large, live nickname system, and it is gated on the slot we would
take.** `agot_nicknames_pulse` drives roughly 1,630 `give_nickname` calls across
`agot_nicknames_events.txt`. Its generic entry `agot_nicknames.0100` opens
with `has_any_nickname = no`, as does vanilla's `assign_random_nickname_effect`
(`00_nickname_effects.txt:41`). Its heroic branch requires `prowess >= 25` and
bold AI and awards exactly the martial flavour an aftermath nickname would want —
`nick_agot_breakspear`, `nick_agot_shieldbreaker`, `nick_agot_greatheart`,
`nick_agot_thunderbolt`. There are 2,588 unique `nick_agot_*` keys across five
files, including house-specific dynastic pools. (`agot_nicknames.0100:162`.)

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
(`agot_knight_on_actions.txt:45-50`), and the playset mod "AGOT: The Knighting
Ceremony" whole-file-overrides that file to reroute it. It is knighting, not
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

Two new hidden events instead, both `scope = combat_side`:

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

**`amount >= 2`**, matching `historical_artifacts.0100`. Five substantive rows,
two of which a very large battle satisfies together, so 2 means "big and
something else, or two somethings" while 1 would mean "big" alone. The sixth row
is the game rule, which hands out a free point under `bc_aftermath_generous` and
so expresses "1" without a second copy of the list. Above 2 the bar starts
requiring coincidences rather than significance, and the run will say whether
even 2 is too many.

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
bc_our_host_gap_value   = { value = side_max_army_size            multiply = <ODDS> }
bc_their_host_gap_value = { value = enemy_side.side_max_army_size multiply = <ODDS> }
```

Each side then asks whether either host was at least `<ODDS>` times the other.
Both sides compute the same answer, and `<ODDS>` is a real tunable — 1.5 to
start, matching the existing threshold values. **`<ODDS>` must be strictly
greater than 1.** At exactly 1 the row degenerates back to `A != B` and
reproduces the free-point failure it was built to avoid; at less than 1 it is
true always.

This shape — a `combat_side` trigger on the left, a script value on the right —
is the same one this mod already proved in game with
`bc_outnumbered_threshold_value`. It does not avoid using `side_max_army_size`
as a trigger, and it is not trying to. That use has no script precedent anywhere
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

`every_side_knight` with `limit = { is_alive = yes, exists = scope:bc_battle_province }`.
Vanilla guards its own knight iterators at combat end for exactly this reason
(`combat_events.txt:854`, and `:1028` with the comment `is_alive = yes # Don't
kill knights who are already dead!`), and guards the side commander the same way
at `:87`. The mod's
own knight phase events already gate on it.

The province scope must be saved by us. Vanilla saves `battle_province` in the
on_action's `effect` block, which this mod cannot do, so it is saved at the top
of the event instead:

```
combat.location ?= { save_scope_as = bc_battle_province }
```

Then, per knight:

```
create_character_memory = { type = bc_battle_memory_won }
scope:new_memory = { save_temporary_scope_as = bc_memory }
scope:bc_memory = {
    set_variable = { name = battle_location value = scope:bc_battle_province }
}
```

`save_temporary_scope_as`, not `save_scope_as`. Both vanilla precedents for the
double-scoping quirk (`harm_events.txt:672-681`, and the comment about "some
kind of dark pact with Code" at `00_knight_phase_events.txt:564`) are
single-character call sites outside any iterator, so neither settles the question.
Temporary is correct here because the scope is rebound on every iteration and is
wanted only for the statement that immediately follows it; a non-temporary scope
would outlive the loop for no reason.

Localization reads the variable back with the vanilla accessor. AGOT **does**
override this file, but through `localization/replace/english/memories_l_english.yml`
rather than the ordinary path, which is why `ck3.py where localization/english/...`
reports vanilla as the only source — the tool does not look in `replace/`. The
accessor is byte-identical in both copies, at `:927-929` in the loaded one:

```
[ROOT.Var('battle_location').GetProvince.GetName]
```

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
        random_list = { ... give_nickname = nick_agot_<heroic> ... }
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

**The pool is AGOT's, not ours.** Both choices consume the same
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
included. Worse, a martial-distinction gate selects precisely the high-prowess,
bold commander AGOT's own heroic branch wants. And our rate is far higher than
AGOT's: `agot_nicknames.0100` is weight 2 of roughly 172 in `agot_nicknames_pulse`
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

This makes AGOT a hard dependency for the nickname branch, which is acceptable —
the mod is an AGOT mod and its README already says to load it after AGOT. It is
a change from the mod's existing stance of avoiding hard dependencies, but that
stance was about *optional* playset mods such as Seasons of Ice and Fire.

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
| `common/scripted_effects/bc_scripted_effects.txt` | add the memory, nickname and counter effects |
| `common/script_values/bc_script_values.txt` | add `bc_our_host_gap_value`, `bc_their_host_gap_value`; note in the file header that these two read the combat side as **root**, unlike the two existing values, which are written against `scope:combat_side` (`bc_script_values.txt:19, :24`) |
| `common/on_action/bc_on_actions.txt` | `.0091` to `on_combat_end_winner`, `.0092` to `on_combat_end_loser` |
| `common/game_rules/bc_game_rules.txt` | add `bc_aftermath` (`bc_aftermath_off` / `_default` / `_generous`) |
| `events/bc_events.txt` | add `bc_chronicles.0091` and `.0092` |
| `localization/english/bc_l_english.yml` | memory titles and descriptions, three perspectives each |

No new files, and no new nickname file — the AGOT-pool decision removes it.
Every path is already mod-owned, so the zero-collision property is unchanged by
construction rather than by checking.

Variable names to avoid, all live in the playset: `battle_poi_*`, `epic_*`,
`artifact_battles_won_var`, `combat_event_0001_tracker`, and `battle_province` /
`battle_memory` as scope names. Ours are `bc_`-prefixed except the memory-scoped
`battle_location`, which is namespaced by living on the memory.

## Failure modes

- **Duplicate commander memory.** Avoided by never creating one for him. The
  vanilla roll is undetectable, so this is the only safe answer.
- **Nickname exclusion.** Reduced by drawing from AGOT's pool rather than a
  private one, but not eliminated: any name closes every AGOT pool for that
  character, dynastic included. Controlled by rarity and by `bc_aftermath_off`.
- **Dead characters.** `is_alive = yes` on the knight loop and the commander
  branch. Commanders and knights can die in the combat that just ended.
- **Leaderless sides.** `side_commander ?=` and `combat.location ?=` throughout.
- **Scope leak in the knight loop.** `save_temporary_scope_as` — and this is the
  one unproven line in the design. See Verification.
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

`bc_chronicles.0091` / `.0092` log buckets on every combat end, unconditionally
and independently of the bar. **Every marker is tagged with which side logged
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

- `probe 'BC: win size'` / `'BC: lose size'`, and the same for blood and odds —
  the distributions, for setting the four thresholds
- `probe 'BC: win notable'` vs `'BC: lose notable'` — **the counts must match
  exactly**. Any divergence means the bar is asymmetric. Equal counts alone do
  not prove the bar is right, only that it is even; the size distribution is what
  says whether it is set sensibly.
- a knight's memory list rendering `bc_battle_memory_*` with the province name.
  **This is the highest-risk line in the design.** Every shipped precedent for
  the `scope:new_memory` double-scoping quirk is a single-character call site
  outside any iterator; nothing proves `scope:new_memory` rebinds correctly on
  each pass of `every_side_knight`, and nothing proves
  `save_temporary_scope_as` is the right half of that pair. The failure is not
  loud — it renders as every knight's memory naming the same province, or as a
  memory with no province at all. So the check is specifically: **open two
  different knights from the same battle and confirm both name the province the
  battle was fought in.** If it fails, the fallback is
  `save_scope_as` inside the loop, accepting the leak.
- `probe 'BC: nickname'` — and, if zero, a companion marker on each failed gate,
  so a nickname that never fires is explained rather than merely absent

## Rejected

- **A memory for the side commander.** He already has one, guaranteed if he lost
  and on a 10% roll if he won, and the roll is undetectable.
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
