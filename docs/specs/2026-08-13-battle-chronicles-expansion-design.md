# Battle Chronicles — The Expansion

Date: 2026-08-13
Status: design, not implemented
Mod: `mods/battle_chronicles`
Predecessors: `2026-08-12-battle-chronicles-design.md`, `2026-08-12-battle-chronicles-aftermath-design.md`

**Citation convention.** All line numbers are against the file **as loaded**, which
for every game file cited here except one means **AGOT's** copy, since AGOT replaces
those files wholesale. The one exception is marked `vanilla` inline:
`00_scripted_relations.txt`, which AGOT does not override — it ships
`00_agot_scripted_relations.txt` alongside instead.

---

## The problem

The mod works. A battle produces moments, a momentum swing, and — since the
aftermath layer — a memory, a tally and occasionally a name. But the moments and the
aftermath are two separate machines that never speak. `bc_chronicles.0091` knows the
battle was big and bloody; it does not know the banner fell on day ten, that the
commander rallied a broken line, or that he did it against the same man who beat him
last spring.

Nothing survives the phase-event boundary. At combat end the engine offers size,
losses, warscore and location. It cannot offer *what happened*. If the moments do not
write it down as they occur, no later system can ever know.

This design closes that gap and builds four systems on top of it.

---

## The locked decisions

Six choices were settled during design and everything below follows from them.

| decision | choice |
|---|---|
| integration shape | **The Ledger** — one seam, every moment reports through `bc_record_moment_effect` |
| lethality | **wounds yes, death never** |
| ledger scope | **commanders only**, 5 ledger variables + 5 scratch, world-wide (AI included) |
| reputation | **earn existing vanilla/AGOT commander traits** — no new trait art |
| pacing | **scale moments to battle size**, with a floor so no battle goes silent |
| volume | **spine first, then grow** |

Four sub-projects sit on the spine:

- **A — The Texture of Battle**: more verbs than "advantage up, advantage down".
- **B — The Commander's Reputation**: fighting a certain way makes you a certain kind
  of commander.
- **C — The Man Across the Field**: the enemy commander becomes a person.
- **D — Before and After**: the eve of battle, and the dead afterwards.

---

## Section 1 — The spine

### The one seam

Every moment — phase event or pop-up option — reports itself through a single
scripted effect:

```
bc_record_moment_effect = { TIER = minor|major|decisive  KIND = <kind>  SWING = up|down }
```

Nothing else writes **moment** state. This is the only place the "state never lives
inside a toast" rule has to be enforced, the only place the variable leak surface
has to be audited, and the only place a fifth system would have to hook.

`SWING` exists because polarity is real in the shipped events and is carried by
neither of the other two parameters. `bc_horse_killed_under_him` and
`bc_van_breaks_through` are both KIND `bloodied`, and one applies
`bc_faltering_minor_effect` while the other applies `bc_momentum_major_effect`. The
wound gate is written against `SWING = down`, so without it the gate is not
expressible.

### Opening the battle

Two scratch variables — `bc_battle_size` and `bc_battle_foe` — need a combat scope to
write. **The seam cannot write them**, because eight of the eighteen moment call sites
are pop-up options, and `bc_events.txt:10-12` records as an invariant that those
character events hold no combat scope at all. And the pop-up is the *common* first
moment of a player-led battle: `bc_banner_falls`
(`bc_commander_phase_events.txt:62-66`) marks the chronicle and then
`trigger_event = bc_chronicles.0001`, so the seam is reached only from the option.

Battle-opening is therefore a second, separate effect:

```
bc_battle_open_effect = yes
```

called at the **top of every commander and knight phase event's `effect` block** —
before `bc_mark_chronicle_effect`, before any `trigger_event` — where
`scope:combat_side` always exists. It writes `bc_battle_size` and `bc_battle_foe` on
the side commander if unset, and does nothing otherwise. It is idempotent by design:
it runs on every phase event of the battle and only the first one does any work.

So: one combat-scoped effect at the top of every phase event opens the battle, and one
scope-free effect records every moment.

**All writes land on the side commander.** The three `type = knight` events root on
the knight, so they call the seam from inside
`scope:combat_side.side_commander ?= { ... }`. **Nothing in this mod ever writes a
`bc_` variable onto a knight.** Per-character state on every participant is exactly
the failure the aftermath spec's Rejected section used to defer this design — it must
be cleared on both sides or it leaks forever, and there are far more knights than
commanders.

### Three tiers of state

| tier | storage | lifetime | holds |
|---|---|---|---|
| **Momentum** | character modifier | 20 days, wiped at combat end | the live advantage swing |
| **Scratch** | character variables | this battle only, cleared at combat end | what happened in *this* battle |
| **Ledger** | character variables | forever | who this commander is |

Momentum must stay a modifier — it is what the engine reads for combat advantage.
Scratch and ledger must be variables: the mod's own `bc_cleanup_effect` strips every
modifier at combat end, so anything modifier-shaped cannot persist by construction.

### Scratch variables — five

| variable | written | read |
|---|---|---|
| `bc_battle_moments` | seam, every call | pacing floor, escalation ladder |
| `bc_battle_style` | seam, when the moment's tier ≥ the stored high-water tier | B, at combat end |
| `bc_battle_size` | `bc_battle_open_effect` | verb-family gate, chronicle-flag duration |
| `bc_battle_wounded` | `bc_wound_effect` | wound gate — one per character per battle |
| `bc_battle_foe` | `bc_battle_open_effect` | C, at combat end |

**Clearing means `remove_variable`, not `set_variable value = 0`.** Three of the five
cannot hold zero — `bc_battle_style` is a flag, `bc_battle_foe` is a character,
`bc_battle_wounded` is a presence test — and the distinction is load-bearing for the
other two: it is how `bc_battle_open_effect` detects the first phase event of a battle,
and it is which arm of the pacing floor's `OR` fires.

`bc_battle_style` holds the KIND of the **highest-tier** moment of the battle, ties
broken by the **last** such moment. Not last-wins: a decisive stand on day five should
name the battle even if a minor scuffle followed it. Stored as `flag:<kind>`.

`bc_battle_size` exists because the size gates are otherwise unevaluable from a pop-up
option, per the invariant above. Written once by `bc_battle_open_effect` in a phase
event where the combat scope exists; read freely everywhere thereafter.

`bc_battle_foe` is captured at the opening of the battle, not read at combat end,
because the man commanding at the end may not be the man who commanded during the
moments — commanders die, are captured and are replaced mid-combat.
`enemy_side.side_commander` does resolve at combat end: AGOT
`combat_on_actions.txt:438` reads it unguarded. But most vanilla readers guard it
(`:93`, `:121` inside that guard, `:547`), so it can be absent, and by this design's
own reasoning `bc_battle_foe` is *more* likely than `bc_nemesis` to name a dead man by
the time it is read. **Every `bc_battle_foe` read is guarded by `exists` plus
`is_alive = yes`, with a lazy wipe on failure** — the same rule Section 4 applies to
`bc_nemesis`.

### Ledger variables — five

Never cleared. On side commanders only.

| variable | written | read |
|---|---|---|
| `bc_notable_battles` | combat end, notable win. Existing name kept for save compatibility | the nickname gate |
| `bc_style_last` | combat end, notable battle | B, next notable battle |
| `bc_style_streak` | combat end, notable battle | B, the trait award threshold |
| `bc_nemesis` | C, on a notable loss | C escalation, phase-event gates |
| `bc_nemesis_losses` | C | C escalation |

Ten variables total per commander, every one with a named reader. An earlier draft
carried fifteen; `bc_battles_led`, `bc_times_routed`, `bc_last_outcome`,
`bc_battle_worst_tier`, `bc_battle_best_tier` and `bc_battle_held` were all defined
and never read by anything, and were cut under the "spine first, then grow" decision.
`bc_battle_worst_tier` in particular was redundant: the wound gate is evaluated at
write time inside the seam, where the tier is a parameter.

### KIND enumeration

`KIND` is one of six values, stored `flag:<kind>`. Every existing moment source maps
to a (TIER, KIND) pair. This table is the input to all of sub-project B, so it is
part of the spine, not part of B.

Option labels below are the shipped ones, so an implementer wires the right KIND to the
right option index.

| call site | file | TIER | KIND | SWING |
|---|---|---|---|---|
| `bc_banner_falls` toast branch | commander | major | `wild` | down |
| `bc_chronicles.0001` opt a — "Then I will carry it myself." | pop-up | minor | `entrenched` | up |
| `bc_chronicles.0001` opt b — fall back | pop-up | minor | `measured` | down |
| `bc_chronicles.0001` opt c — charge to it | pop-up | **decisive** | `wild` | down |
| `bc_rally_the_line` toast branch | commander | minor | `ordered` | up |
| `bc_chronicles.0002` opt a — rally by prowess | pop-up | major | `ordered` | up |
| `bc_chronicles.0002` opt b — pay them | pop-up | minor | `measured` | up |
| `bc_chronicles.0002` opt c — steady them | pop-up | minor | `entrenched` | up |
| `bc_horse_killed_under_him` | commander | minor | `bloodied` | down |
| `bc_flank_collapses` | commander | **decisive** | `wild` | down |
| `bc_van_breaks_through` toast branch | commander | major | `bloodied` | up |
| `bc_chronicles.0003` opt a — press it | pop-up | major | `bloodied` | up |
| `bc_chronicles.0003` opt b — consolidate | pop-up | minor | `measured` | up |
| `bc_ground_favours_us` | commander | minor | `adapted` | up |
| `bc_lines_bogged_down` | commander | minor | `adapted` | down |
| `bc_knight_holds_the_breach` | knight | major | `entrenched` | up |
| `bc_knight_shames_himself` | knight | minor | `wild` | down |
| `bc_shieldbrother_forged` | knight | minor | `ordered` | up |

**TIER as listed is the *requested* tier, and the escalation ladder in Section 6 is a
ceiling that can only lower it.** That is why exactly two sites request `decisive`,
both `SWING = down`: a ceiling cannot manufacture a tier nobody asks for, and if no
site requested `decisive` the whole rung — and with it every wound in the mod — would
be unreachable by construction. The two chosen are the mod's two genuine catastrophes:
the flank going and the commander charging a fallen banner alone.

The swing game rule acts on the *momentum modifier* the event applies, not on this
tier. They are separate ladders that happen to share vocabulary.

### Consolidation

`bc_chronicles.0090` (cleanup, both hooks), `.0091` (winner) and `.0092` (loser)
become **one event per side**. Cleanup and grading need the same scopes and both must
run at combat end; keeping them separate means iterating `every_side_knight` twice.

**The consolidated event carries no `trigger`.** `.0091`/`.0092` currently carry
`trigger = { NOT = { has_game_rule = bc_aftermath_off } }` and `.0090` deliberately
carries none — and `.0090` is the *only* caller of `bc_cleanup_effect`. Consolidating
naively would put momentum stripping behind the aftermath off switch, so a player who
turned aftermath off would get `advantage ±10` modifiers bleeding twenty days into the
next battle. That is precisely the bug `bc_scripted_effects.txt:98-99` exists to
prevent, reintroduced silently and only for the players who touched a setting.

The game rule therefore moves to an inner `if` wrapping the grading branch only:

| outside the gate — always runs | inside the gate |
|---|---|
| `bc_cleanup_effect` on commander and knights | the notability grade |
| scratch clearing on the commander | knight battle memories |
| — | B, C and the nickname |

The consolidation itself is behaviour-neutral when done correctly, so it belongs in
stage 0 alongside the other structural work — and stage 1 depends on it, because
scratch clearing lives in the consolidated event.

---

## Section 2 — The verbs of battle (A)

Three families. Family 1 exists today; families 2 and 3 are new.

### Family 1 — the tide

The existing advantage ladder: `bc_momentum_minor/major/decisive` and
`bc_faltering_minor/major/decisive` (`bc_momentum_modifiers.txt:17-47`), reached
through the swing wrappers. Unchanged.

### Family 2 — character

New character modifiers giving a battle a *shape*, not just a direction. All 20-day
like momentum, all stripped at combat end.

| modifier | effect keys | narrative |
|---|---|---|
| `bc_bloodied` | `army_damage_mult` up, `army_toughness_mult` down | traded blood for ground |
| `bc_shieldwall` | `army_toughness_mult` up, `army_damage_mult` down | dug in and refused to move |
| `bc_spent_horse` | `knight_effectiveness_mult` down | the knights are blown |
| `bc_pursuit` | `army_pursuit_mult` up | the enemy is running and we are on them |

`knight_effectiveness_mult` is confirmed valid on a character modifier —
`00_martial_lifestyle_modifiers.txt:251`,
`warfare_stablemaster_tamed_wild_horse_modifier`.

These need loc — four names plus four descriptions — but they do **not** appear where
the momentum ladder does. `bc_momentum_modifiers.txt:5-8` records that a character
**`advantage`** modifier moves the battle breakdown and is listed next to
`Commander Martial Skill`; none of the four keys above is `advantage`, so they surface
in the army-stat breakdown instead. Same loc obligation, different tooltip. Confirm
where each actually renders during stage 2 rather than assuming.

### Family 3 — flesh

Wounds. Never death. The mod may create `wounded_1` and **nothing else**.

```
bc_wound_effect = {
	if = {
		limit = { NOT = { has_trait = wounded } }
		change_trait_rank = { trait = wounded rank = 1 max = 1 }
		set_variable = { name = bc_battle_wounded value = yes }
	}
}
```

A man who already carries any rank of `wounded` is untouched. `max = 1` makes the
ceiling structural rather than a property of the guard.

**Why not `increase_wounds_no_death_effect`** (`20_health_effects.txt:1081`). Two
reasons, and the second is the real one:

1. *It is not rank-controlled.* Its first branch (`:1087-1096`) applies **rank 3**
   outright to a character with `fragile_bones` at 50+ track XP, and its second
   (`:1097-1106`) applies rank 2 to any `fragile_bones` character. A mod calling it
   cannot promise it only ever creates `wounded_1`.
2. *`wounded_3` is the doorway to every lethal path.* `increase_wounds_effect`
   (`:1209`) kills outright at rank 3, and `maimed_in_battle_effect` (`:1232`) routes
   every branch through it. Separately, the `die_surgery` gate (`:3626-3648`) fires
   when a **risky** treatment fails and either the man is `wounded_3` under an
   amputation-class strategy, or `is_ai = yes AND health <= 0` — the AI arm with no
   wound-rank requirement at all. `health.4105` (`health_events.txt:10483`) then
   executes a real `death = { death_reason = death_treatment killer = scope:physician }`
   at `:10562`, gated on that flag at `:10556`.

To be precise about what the vanilla effect does *not* do: at **rank 1** it is safe.
`:1130-1140` routes rank 1 to `safe_wound_treatment_effect` (`:2304`), and only when a
court physician is available; the risky path that the `die_surgery` gate requires is
reachable only through `risky_wound_treatment_effect` (`:2418`). The 10% infection
roll at `:1119-1127` fires `health.0201`, not the rank-2/rank-3 events. So the honest
statement is: the vanilla effect is safe at the rank this mod wants, and unsafe at
ranks this mod must never reach — and since the mod cannot stop it reaching them, it
does not call it.

**By never creating `wounded_2`, the mod also never raises baseline lethality.** A
mod-created `wounded_2` would put a commander one *vanilla* wound from `wounded_3`,
which would make the mod indirectly lethal even though it never calls a lethal
effect. That would violate the locked decision in spirit while satisfying it in
letter.

**Rank 1 is already heavy.** `wounded_1` (`00_traits.txt:6316`) carries `martial -1`,
`intrigue -1`, `health -1`, `prowess -2` and — the real cost —
`disables_combat_leadership = yes`. A wounded commander cannot lead an army. That is a
months-long consequence from one moment.

**Wounds heal for free.** `wounded_recovery_pulse` (`health_on_actions.txt:369`) hangs
off `yearly_health_pulse` (`:4`) four times a year, and its trigger is
`OR = { has_trait = wounded  has_infected_or_gangrenous_wound_trigger = yes }`. A wound
applied by raw `change_trait_rank` inherits the entire vanilla recovery system at zero
implementation cost.

**Wound gates**, all four required:

1. the moment is `TIER = decisive` **and** `SWING = down` — the two seam parameters,
   evaluated inside the seam where both are in hand
2. `bc_battle_size >= 10000`
3. `bc_battle_wounded` unset
4. game rule not `bc_wounds_off`

Gate 1 is reachable from exactly two call sites (`bc_flank_collapses` and
`bc_chronicles.0001` opt c), and only when the escalation ceiling has already reached
`decisive` — five moments into the battle. Combined with gate 2, wounds are rare by
construction, which is the intent.

---

## Section 3 — The commander's reputation (B)

### The hole this fills

CK3 already lets a commander get *better* at commanding by fighting:
`commander_trait_leveling_leveling_effect` (`00_war_effects.txt:2883`) is called on
`every_side_commander` at both combat ends (`combat_on_actions.txt:492` winner XP 1,
`:681` loser XP 0.5). But **every branch of it is gated `has_trait = X`** — it levels
traits you already have and never grants one. The only granter is
`give_random_commander_trait_effect` (`00_martial_lifestyle_effects.txt:13`), a flat
`random_list` behind a lifestyle perk, with its terrain branches gated on *owning*
that terrain (`any_sub_realm_barony = { title_province = { terrain = ... } }`).

So the game lets you get better at commanding by fighting, but never lets you become a
*kind* of commander by fighting. That is the hole.

### Style traits

At combat end, if the battle was notable: compare `bc_battle_style` against
`bc_style_last`. Match increments `bc_style_streak`; mismatch sets `bc_style_last` to
the new style and `bc_style_streak` to 1. At `bc_style_streak >= 3`, award the matching
trait and reset the streak to 0.

The two reset values differ on purpose: a mismatch means the battle just fought *is*
the first of a new streak, so 1. An award means the streak has been spent, so 0.

| style | trait |
|---|---|
| `bloodied` | `aggressive_attacker` |
| `entrenched` | `unyielding_defender` |
| `adapted` | `flexible_leader` |
| `measured` | `cautious_leader` |
| `wild` | `reckless` |
| `ordered` | `organizer` |

The streak counts notable battles of **either outcome**. A man who loses three battles
the same way has still shown you who he is.

### Terrain traits

Awarded from `scope:bc_battle_province` at combat end with **no new state** — the
province is already in scope for the memory writes. Gated on *fighting* there, not
owning there, which is the deliberate difference from the vanilla granter.

The terrain→trait mapping mirrors vanilla's own, read out of
`00_war_effects.txt:2883` onward:

| terrain | trait | trait line |
|---|---|---|
| `drylands`, `desert`, `desert_mountains`, `oasis` | `desert_warrior` | `00_traits.txt:15045` |
| `farmlands`, `plains`, `steppe` | `open_terrain_expert` | `:15818` |
| `hills`, `mountains`, `wetlands` | `rough_terrain_expert` | `:16054` |
| `forest`, `taiga` | `forest_fighter` | `:16532` |
| `jungle` | `jungle_stalker` | `:15232` |

All five are `category = commander`, `flag = commander_trait_flag`.

**`winter_soldier` is deliberately excluded.** It reads as a terrain trait and is not
one: `00_traits.txt:17135` gives it `category = winter_commander`, so it would escape
the `number_of_commander_traits` cap below; vanilla's own terrain branch lists exactly
the five above and omits it; and there is no `terrain =` key corresponding to winter,
so there is no province-derived path to it in the first place.

Also skipped: `logistician`, `military_engineer`, `forder`, `holy_warrior`, `reaver` —
none of them is a thing a battle can teach you.

### Shared gates

- `number_of_commander_traits < 3` — a commander should not collect the set.
- `NOT = { has_trait = <the trait about to be awarded> }`. Without this, a commander
  who already holds `aggressive_attacker` and keeps fighting that way re-triggers the
  award every third notable battle, spending the reward budget on a no-op `add_trait`.
  When the check fails, **the streak still resets to 0** — otherwise every subsequent
  battle re-enters the same dead branch.
- **`cautious_leader` and `reckless` are `opposites` of each other**
  (`00_traits.txt:16684-16686` and `:15523-15525`; no other pair among the six has an
  `opposites` block). The `has_trait` check above does not catch this: a commander
  holding `reckless` who builds a `measured` streak passes every stated gate and the
  engine then silently refuses the `add_trait`. That is worse than the treadmill —
  the streak resets, the reward is consumed, and nothing happens, forever.
  **The decision: the opposite is removed, and the new trait replaces it.** A man who
  fought recklessly for a decade and has now won three battles by caution has changed,
  and that is a better story than a permanently jammed award. Implement as
  `remove_trait = <opposite>` immediately before the `add_trait`, gated on holding it,
  and mention it in the award toast description.
- A battle may award **either** a nickname **or** a trait, never both. **The trait
  wins.** A nickname is decoration; a trait changes how the man fights. Evaluate the
  trait branch first and set a temporary flag that suppresses the nickname branch.
- Every award toast goes through a shared `bc_addressed_toast_effect`, extracted from
  `bc_aftermath_nickname_toast_effect`. `send_interface_toast` bodies do not reliably
  run for an AI character, so every award must route to the liege when the subject is
  AI, and that rule belongs in one effect rather than in five copies.

### Risk

`number_of_commander_traits < 3` may be dead on arrival — the same failure mode as
`has_any_nickname = no`, which disqualified 3 of the 4 AGOT commanders sampled. Must
be measured before B ships. See the DIAG pass, Q1.

---

## Section 4 — The man across the field (C)

### Escalation

Read `bc_battle_foe` at combat end. On a **notable loss** to him, increment
`bc_nemesis_losses` and set the relation for the new level:

| `bc_nemesis_losses` | relation |
|---|---|
| 1 | `grudge` |
| 2 | `rival` |
| 3 | `nemesis` |

On a **notable win** against the current `bc_nemesis`, decrement. At 0, clear
`bc_nemesis` and `bc_nemesis_losses`, and remove the relation.

`grudge` is one-directional — `00_scripted_relations.txt:43` (vanilla; AGOT ships
`00_agot_scripted_relations.txt` alongside rather than overriding) has no
`corresponding` key. That is exactly right for a first loss: he humiliated you, he has
not noticed you. `rival` (`:54`) and `nemesis` (`:70`) are mutual, at opinion -60 and
-120. `set_relation_*` / `has_relation_*` appear 300+ times across 40+ AGOT files for
these three relations alone, so the idiom is thoroughly shipped in the playset.

### Rules

- **Never overwrite an existing `bc_nemesis`.** One running grudge per commander. A
  second rival dilutes the first into noise.
- **Relations escalate only, never downgrade.** Decrementing below the threshold that
  set `nemesis` does not demote him to `rival`. Removing a relation the player never
  asked to remove is worse than leaving it. Only reaching 0 removes anything.
- **Game rule `bc_rivalry`, defaulting to `bc_rivalry_rival`.** AGOT hangs murder
  schemes off `nemesis`; a mod that silently manufactures nemeses is changing far more
  than battles. Players who want the top rung opt in.
- **Every `bc_nemesis` read is guarded** by `exists` plus `is_alive = yes`, with a lazy
  wipe when the guard fails. Characters die constantly and a dangling character
  reference is a permanent error-log line. Same rule for `bc_battle_foe` (Section 1).

### Read-back

This is what closes the loop. `bc_nemesis` gates phase events: fighting the man who
beat you twice should not read like fighting a stranger. It is the only thing in the
design that makes a commander feel like the same man twice.

---

## Section 5 — Before and after (D)

D was drafted much larger and then cut hard, because most of it already exists.
Vanilla's `on_combat_end_winner` already handles prisoners (`combat_event.1001`), both
commanders' battle memories, banner looting (`artifact.6000`), the map
point-of-interest (`combat_event.3000`), glory (`combat_event.2101`), the Undefeated
nickname (`combat_event.0001`), and legitimacy loss on the loser
(`combat_on_actions.txt:587`). Prisoners and captured banners were cut on those
grounds. A fourth item — marking the battlefield province with
`add_province_modifier` — was cut in review: province modifiers accumulate forever, it
was the design's largest save-bloat risk, and it was the weakest item in it on
value-per-risk.

Three gaps remain.

### 1. The eve

`on_combat_start` is **empty in the loaded file** — AGOT `combat_on_actions.txt:3-4`
is a bare `on_combat_start = { }`, Root = Combat. An entirely unclaimed hook. It does
one thing:

- one throttled pop-up on the eve of a large battle

Root is the Combat, so the commanders are reached via `combat_attacker.side_commander`
and `combat_defender.side_commander` (`event_targets.log:1054`, `:1060`).

The eve pop-up gets its **own 90-day `bc_eve_cooldown` flag**. Sharing the existing
60-day `bc_popup_cooldown` would starve the mid-battle chronicles: the eve fires
first, every time, and would consume the budget before the battle began.

**Scratch clearing does not live here.** An earlier draft put it on `on_combat_start`,
which made all of sub-project C depend on a hook whose scope resolution is unverified
(DIAG Q2). Clearing happens instead at combat end, in the consolidated event, outside
the game-rule gate — which is where the cleanup already runs and where the scopes are
proven. `on_combat_start` therefore carries presentation only, and if Q2 comes back
negative, only the eve pop-up dies.

### 2. `scope:wipe`

Both end hooks pass a `scope:wipe` — was this an annihilation. It is not unclaimed:
vanilla reads it at `combat_on_actions.txt:100` (adds +90 to the winner's
battle-memory chance) and at `combat_events.txt:781` and `:947` (capture chance). But
nothing exposes it to the player as an outcome in its own right, and the mod does not
read it at all.

It becomes the top tier of three things. Each needs a stated mechanism, because
"the top tier" is not implementable:

1. **Notability.** One more row in `bc_battle_is_notable_trigger`'s `calc_true_if`.
   Not a short-circuit: the trigger's own header (`bc_scripted_triggers.txt:103-108`)
   warns that rows are counted as direct children, so a wipe is worth one point of the
   two required — it makes a battle notable when combined with any single other row,
   which every wipe will already satisfy on blood or warscore.
2. **Reputation.** The streak increments by **2** instead of 1 on a wipe, so two
   wipes fought the same way earn the trait. Nothing else about B changes.
3. **Rivalry.** `bc_nemesis_losses` increments by **2** instead of 1, and the
   relation is then set from the resulting value using Section 4's table unchanged —
   so a wipe takes a stranger straight to `rival`, and a second wipe to `nemesis`.
   This is the whole of the interaction: Section 4's table remains the single source
   of truth for value→relation, and "escalate only, never downgrade" is untouched.
   A wipe **win** likewise decrements by 2.

**Read it as `AND = { exists = scope:wipe  scope:wipe = yes }`.** Shipped script uses
both idioms — `exists = scope:wipe` at `combat_on_actions.txt:100`, `scope:wipe = yes`
at `combat_events.txt:781` — which means it is unsettled whether the scope always
exists and carries a boolean or exists only when true. The conjunction is correct
under either reading and costs one line.

### 3. The dead

`.0091`/`.0092` both carry `limit = { is_alive = yes }` on `every_side_knight`, which
silently drops exactly the knights whose deaths were worth telling. Invert it into a
second pass over the dead.

The dead-knight toast must be **one aggregate toast per battle per liege**, not one per
knight. A liege who lost six knights should be told once.

---

## Section 6 — The pacing curve

### The problem

Phase events roll every `COMBAT_EVENT_DAYS = 5`. A skirmish and a two-month siege
battle currently get the same 15-day chronicle cooldown, so the long battle gets a
constant stream of moments and the short one often gets none.

### Everything in this section is commander-only

`bc_chronicle_ready_trigger` and `bc_mark_chronicle_effect` are **shared between
commander and knight events** and are per-character by design —
`bc_knight_phase_events.txt:8-9` says so, and the knight events call the trigger at
`:52`, `:125`, `:193` and `:227` and the effect at `:75`, `:151`, `:236` and `:240`.

Section 1 guarantees that no `bc_` variable is ever written onto a knight. So on a
knight, `bc_battle_moments` and `bc_battle_size` never exist. Rewriting the shared
trigger and effect in place would therefore:

- make the pacing floor's `NOT = { exists = var:bc_battle_moments }` arm **always
  true on a knight**, disabling the 15-day knight cooldown entirely — and `type = knight`
  fires for every knight on every side of every combat in the world, 41 fires from a
  single battle in the probe run. That is the mod's largest event-spam surface,
  un-gated;
- make the size-scaled duration read a missing variable once per knight per chronicle
  mark. `bc_script_values.txt:18-23` carries a standing warning about exactly this
  class of scope mistake.

**The pacing curve therefore adds new commander-only variants and leaves the shared
ones alone:**

| existing, unchanged, used by knight events | new, used by commander events |
|---|---|
| `bc_chronicle_ready_trigger` — flag only | `bc_chronicle_ready_commander_trigger` — flag or floor |
| `bc_mark_chronicle_effect` — `days = 15` | `bc_mark_chronicle_commander_effect` — size-scaled |

This also preserves `bc_shieldbrother_forged`'s two calls on two different characters
(`:236`, `:240`) without touching them.

### Scale at write time

`bc_mark_chronicle_commander_effect` replaces the hardcoded `days = 15` with a script
value scaled by `bc_battle_size`:

| `bc_battle_size` | flag duration |
|---|---|
| under 2,000 | 40 days |
| 2,000 – 9,999 | 20 days |
| 10,000+ | 10 days |

`add_character_flag` accepts a script value for `days` (`effects.log:2892`).

**Scaling happens at write time, not read time**, because the flag's duration is a
property of the battle, fixed the moment the flag is written. Re-deriving it on every
read would compute the same answer every time. This is a preference for the obvious
form, not a performance rule — an earlier draft justified it as "never touch a combat
scope in `bc_chronicle_ready_trigger`", which proves too little: every phase event's
`is_valid` already reads `scope:combat_side.side_strength` and
`scope:combat_side.combat.location` on the same rolls
(`bc_scripted_triggers.txt:15-61`).

### The floor

`bc_chronicle_ready_commander_trigger` passes when no moment has yet occurred, so a
battle that has produced nothing can always produce its first, regardless of the flag:

```
bc_chronicle_ready_commander_trigger = {
	OR = {
		NOT = { has_character_flag = bc_chronicle_recent }
		NOT = { exists = var:bc_battle_moments }
	}
}
```

One `exists` arm, not two. Scratch is cleared with `remove_variable`, so
`bc_battle_moments` is either absent or ≥ 1 and there is no zero case to test. The
`exists` arm is not defensive padding — it *is* the floor.

Reading a missing variable is an error-log line — the mod documents this at
`bc_events.txt:308-311` — so had the floor been written as a value comparison it would
have been the single highest-volume error-spam source the expansion could introduce.

### Verb families gate on size

| `bc_battle_size` | families available |
|---|---|
| any | 1 — the tide |
| 2,000+ | 1, 2 — character |
| 10,000+ | 1, 2, 3 — flesh |

A skirmish between two hundred men should not maim anyone.

The flesh row is gated on size alone. An earlier draft read "10,000+ **and** notable",
but notability is `bc_battle_is_notable_trigger`, which is written against
ROOT = combat side (`bc_scripted_triggers.txt:98-101` says so in a header warning) and
cannot be evaluated mid-battle from a phase event, let alone from a pop-up option with
no combat scope at all. Size alone is evaluable from scratch everywhere.

### Escalation ladder

Within one battle, the tier available scales with moments already recorded. **The
ceiling is read after the seam increments `bc_battle_moments`**, so the first moment of
a battle sees 1, not 0, and there is no zero case:

| `bc_battle_moments` | tier ceiling |
|---|---|
| 1–2 | minor |
| 3–4 | major |
| 5+ | decisive |

A ceiling only lowers. A site requesting `minor` on the tenth moment still gets
`minor`.

**Two ladders, not three.** An earlier draft also scaled tier by battle size directly.
Cut: big battles last longer, so they naturally accumulate more moments and reach the
higher rungs on their own. Size stays as the verb-family gate only. Three
multiplicative ladders would be untunable.

### Risk

The `< 2,000` threshold is invented. The 2026-08-13 calibration run recorded `under 5k`
as a single bucket of 26 of 39 battles and never subdivided it. Must be measured. See
the DIAG pass, Q3.

---

## Section 7 — Structure, measurement, sequencing

### Files

| path | new? | contents |
|---|---|---|
| `common/scripted_effects/bc_ledger_effects.txt` | new | `bc_record_moment_effect`, `bc_battle_open_effect`, scratch + ledger writes, scratch clearing |
| `common/scripted_effects/bc_reward_effects.txt` | new | trait grant, `bc_wound_effect`, `bc_aftermath_nickname_effect`, `bc_notable_battle_counter_effect`, `bc_battle_memory_effect`, `bc_addressed_toast_effect` |
| `common/scripted_effects/bc_scripted_effects.txt` | modify | momentum ladder, `bc_clear_faltering_effect`, flattened `bc_cleanup_effect`, the two chronicle-mark effects, `bc_start_popup_cooldown_effect` |
| `common/scripted_triggers/bc_ledger_triggers.txt` | new | scratch/ledger reads, `exists`+`is_alive` guards |
| `common/scripted_triggers/bc_scripted_triggers.txt` | modify | add `bc_chronicle_ready_commander_trigger`; existing triggers unchanged |
| `common/script_values/bc_script_values.txt` | modify | chronicle-flag duration by size |
| `common/modifiers/bc_battle_modifiers.txt` | new | the four family-2 modifiers |
| `common/game_rules/bc_game_rules.txt` | modify | `bc_wounds`, `bc_rivalry` |
| `common/on_action/bc_on_actions.txt` | modify | add `on_combat_start`; end hooks now one event each |
| `common/combat_phase_events/bc_commander_phase_events.txt` | modify | seam calls, size gates, nemesis gates |
| `common/combat_phase_events/bc_knight_phase_events.txt` | modify | seam calls routed through `side_commander` |
| `events/bc_events.txt` | modify | player pop-ups only; seam calls in options |
| `events/bc_aftermath_events.txt` | new | the consolidated combat-end graders |
| `events/bc_eve_events.txt` | new | `on_combat_start` and the eve pop-up |
| `localization/english/bc_l_english.yml` | modify | see below |

`bc_events.txt` is 379 lines holding two unrelated things: player-facing character
events and hidden `scope = combat_side` graders. Different ROOT, different lifecycle,
and the graders are the part that grows most under A/B/C/D. The split is structural,
not cosmetic.

**Localization is not an afterthought and is not free.** New keys required:

| what | keys |
|---|---|
| 4 family-2 modifiers | 8 (name + desc each), rendered in the combat breakdown |
| 6 style-trait award toasts | 12 |
| 5 terrain-trait award toasts | 10 |
| eve pop-up | title, desc, 2–3 options |
| aggregate dead-knight toast | 2 |
| game rule `bc_wounds` | 8 (rule name/desc + 2 options × name/desc/tooltip) |
| game rule `bc_rivalry` | 14 (4 options) |

UTF-8 with BOM, one leading space per line. Every stage that adds a player-facing
string adds its loc in the same stage — never deferred.

### Cleanup restructure

`bc_cleanup_effect` is currently six hand-written
`if = { limit = { has_character_modifier = X } remove_character_modifier = X }` blocks.
Family 2 adds four more modifiers and every future one must be remembered here or it
leaks past combat end.

`remove_character_modifier` on an absent modifier is a no-op. Verified:
`vizierate_remove_extravagance_modifiers_effect`
(`00_diarchy_scripted_effects.txt:2325-2341`) is a flat unguarded list of 16 tier
modifiers of which at most 4 can be held, so 12 of the 16 calls are always no-ops,
every call, by design.

So the guards go and `bc_cleanup_effect` becomes a flat list of ten
`remove_character_modifier` lines — one per modifier, adjacent to the modifier files,
impossible to half-forget.

**The flattening applies to `bc_cleanup_effect` only.** `bc_clear_faltering_effect`
keeps its guards and stays a separate effect, because `bc_rally_effect` calls it
mid-battle (`bc_scripted_effects.txt:92-95`) where a flat list of ten removals would
strip the commander's momentum along with his setback.

### Game rules

Written out in the existing style of `bc_game_rules.txt` (rule key, options, default;
no option sets `blocks_achievements`):

```
bc_wounds = {
	categories = { flavor }
	default = bc_wounds_default
	bc_wounds_off = {}
	bc_wounds_default = {}
}

bc_rivalry = {
	categories = { flavor }
	default = bc_rivalry_rival
	bc_rivalry_off = {}
	bc_rivalry_grudge = {}
	bc_rivalry_rival = {}
	bc_rivalry_nemesis = {}
}
```

`bc_rivalry_<level>` names the **highest** relation the mod may set. Both rules inherit
the existing warning: a modded game rule is baked into every save made with it, and
disabling the mod afterwards makes that save fail to load.

### The DIAG pass — one run, four questions

A game restart costs about seven minutes, so one run must answer everything. Each
question independently invalidates a design decision. All four are pure `debug_log`
with no state.

**Q1 — trait census.** Log `number_of_commander_traits` for every side commander at
combat end, as a raw count, not a pass/fail. B gates on `< 3`. If the median commander
already holds 3, B is dead on arrival.

**Q2 — `side_commander` at combat start.** Does it resolve from `on_combat_start` via
`combat_attacker.side_commander` / `combat_defender.side_commander`? If not, the eve
pop-up dies. Nothing else depends on it.

**Q3 — size ladder at 1k / 2k / 3k / 5k.** Subdivides the `under 5k` bucket that the
calibration run left whole, and settles the pacing curve's invented threshold.

**Q4 — does a toast body run for an AI subject?** The whole of
`bc_addressed_toast_effect` rests on the answer being no. The claim is well-supported
but under-evidenced: the only probe for it (`bc_knight_phase_events.txt:108`) sits
inside a knight event never observed firing, the mod's own comments hedge with "only
*reliably* runs", and vanilla puts real state inside toast bodies on AI-reachable
paths — `add_legitimacy = minor_legitimacy_loss` at `combat_on_actions.txt:587`, inside
`side_primary_participant`, which is usually AI. Log from inside a toast raised on a
known-AI character.

**Q5 — do the vanilla terrain keys resolve in Westeros?** Log
`combat.location`'s terrain at every combat end. AGOT deliberately abandoned plain
terrain keys in `give_random_commander_trait_effect` —
`00_martial_lifestyle_effects.txt:45-52` comments out
`terrain = desert / desert_mountains / oasis / drylands` in favour of
`agot_is_desert_terrain = yes`, and `:65-66` does the same for `terrain = jungle`. It
did *not* do this in `commander_trait_leveling_leveling_effect`, which is where
Section 3's table is read from, so the citation is sound — but it raises the
possibility that `desert_warrior` and `jungle_stalker` are unreachable in a Westeros
playset through plain `terrain =` keys. The mod restricts itself to vanilla terrain
keys on purpose (`bc_scripted_triggers.txt:32-35`, probe-verified), so this is a
measurement, not a design change: if those terrains never appear, drop the two traits.

Q2 requires hooking `on_combat_start`, which the mod does not currently do. The hook
ships in stage 1 carrying nothing but the logging event.

### Sequencing

| stage | ships | gated on |
|---|---|---|
| 0 | strip old DIAG markers, split files, flatten `bc_cleanup_effect`, **consolidate the three combat-end events into one per side** | — |
| 1 | the seam + `bc_battle_open_effect` + scratch + ledger + KIND table, wired to existing events; `on_combat_start` hook; DIAG pass | stage 0 |
| 2 | family 2 modifiers, pacing curve | Q3 |
| 3 | B — reputation | Q1, Q4 |
| 4 | C — rivalry | stage 1 |
| 5 | D — eve, wipe, dead knights | Q2 (eve only) |
| 6 | family 3 — wounds | stage 2 |

**Stage 1 ships no new player-visible behaviour.** That is the point: the seam is
proven by log before anything is built on it.

**This is a graph, not a line.** Stages 2, 3 and 5 all unblock on the same DIAG run and
may ship in any order. Stage 4 needs only stage 1, because `bc_battle_foe` is written
by `bc_battle_open_effect`, not by the eve. Only stage 6 is strictly downstream of
another feature stage. Stages 0 and 1 are the only genuinely mandatory prefix.

**Order inside stage 0 matters**: the old DIAG markers must be stripped *before* the
new ones are added, or the log is two interleaved generations of markers.

---

## Carried-over hygiene

Folded into stage 0:

- **Strip every DIAG marker across the mod** — eleven in `bc_events.txt`, plus the
  probe `"BC: toast body ran (knight breach)"` at `bc_knight_phase_events.txt:108`
  (which is superseded by DIAG Q4). The calibration ladders documented in
  `bc_scripted_triggers.txt`'s header comment are **not** DIAG output and must survive
  — they are the only record of how the notability thresholds were derived.
- **`bc_aftermath_nickname_effect` has never executed at runtime.** Force-execute it
  once before anything is built on the reward path.
- **`bc_shieldbrother_forged` calls `bc_mark_chronicle_effect` twice, on two different
  characters** (`bc_knight_phase_events.txt:236`, `:240`). The pacing rework must not
  collapse that into one call.

---

## Failure modes

| failure | detection | mitigation |
|---|---|---|
| scratch leaks between battles | `bc_battle_moments` exists at the opening of a new battle | clearing is outside the game-rule gate; DIAG log in `bc_battle_open_effect` |
| scratch written to a knight | any `bc_` variable on a non-commander | all seam calls from knight events wrapped in `side_commander ?=` |
| momentum bleeds past combat end | `advantage` modifier visible outside combat | consolidated event carries no `trigger`; flat cleanup list |
| dangling character reference | error log names `bc_nemesis` / `bc_battle_foe` | `exists` + `is_alive` guard with lazy wipe on every read |
| error-log spam from the pacing floor | `probe` groups a high-count error on `bc_scripted_triggers.txt` | `NOT = { exists = ... }` arm before the value read |
| trait award becomes a no-op treadmill | commander repeatedly "awarded" a trait he holds | `NOT = { has_trait = X }` gate; streak resets to 0 even on the failed branch |
| trait award jams forever on an `opposites` pair | `reckless` commander builds `measured` streaks and never gains `cautious_leader` | `remove_trait = <opposite>` before the `add_trait` |
| knight chronicle cooldown silently disabled | knight toasts every 5 days, 41 knights per battle | the floor lives in `bc_chronicle_ready_commander_trigger`; the shared trigger is untouched |
| chronicle-flag duration undefined on a knight | error log names `bc_script_values.txt` once per knight per mark | knights keep `bc_mark_chronicle_effect` at `days = 15` |
| `bc_battle_size` missing when the first moment is a pop-up | size gates evaluate against nothing; C never arms | `bc_battle_open_effect` runs in the phase event, before any `trigger_event` |
| reward silently reaches nobody | award happens with no toast seen | `bc_addressed_toast_effect` routes to liege for AI subjects; DIAG Q4 |
| file collision with AGOT or the playset | `ck3.py conflicts` | every new file is `bc_`-prefixed and additive; no file is overridden |

## Verification

Per sub-project, beyond the DIAG pass:

- **Spine** — a battle produces N moments; the combat-end log reports the same N, a
  style, a size and a foe. Every scratch variable is absent at the start of the next
  battle. A battle whose first moment is a pop-up still logs a size and a foe. No
  `bc_` variable appears on any knight.
- **A** — a family-2 modifier is visible in the combat breakdown with its localized
  name, and is gone from the character sheet after combat end. A wound appears only in
  a 10,000+ battle, at rank 1, once.
- **B** — three notable battles with the same style produce exactly one trait award
  and one toast, and the fourth produces none.
- **C** — a second notable loss to the same commander produces `rival`, not a second
  `grudge`. A notable win against him decrements. `bc_rivalry_rival` prevents the
  `nemesis` rung.
- **D** — the eve pop-up fires at most once per 90 days per commander. The dead-knight
  toast is one per battle per liege, not one per knight.
- **Whole mod** — `ck3.py index` then `ck3.py conflicts` clean; `ck3.py validate
  --strict` clean; `ck3.py probe` over the error log finds no `bc_` entry (recall that
  `probe` exits 1 when nothing matches, so a non-zero exit is the pass condition).

---

## Constraints that shaped this design

Collected because each one killed at least one earlier draft.

- **`send_interface_toast` bodies do not reliably run for an AI character.** State must
  never live inside a toast; toasts about AI subjects route to the liege. Being
  confirmed as DIAG Q4.
- **Modifiers are wiped at combat end** by the mod's own cleanup, so persistence must
  be variables and cooldowns must be flags.
- **`effect = { }` in an `on_action` does not merge across files** — one is kept, winner
  by alphabetical filename. `events`, `random_events` and `on_actions` do merge. And
  `effect = { }` runs *concurrently with* the on_action's events, not before them.
- **`calc_true_if = { amount >= N ... }` counts direct children.** A nested scripted
  trigger counts as one row no matter how many tests it holds.
- **Game rules are baked into a save at creation** and cannot be changed mid-game, so
  every game rule must have a sane default.
- **A scripted effect does not rebind ROOT.** `left_icon` accepts only a character,
  artifact, title, dynasty or house — never a combat side.
- **Reading a missing variable is an error-log line.** Guard with `exists` before every
  `var:` read on a hot path.
- **Localization needs UTF-8 with BOM** and one leading space per line.
- **Zero file collisions is a hard requirement.** Verify with `ck3.py conflicts` after
  `ck3.py index`; a stale index makes `conflicts` always pass.
- **`ck3.py errors` cannot see mod script errors** — it tail-slices a ~500k-line log and
  mod errors appear near the top. Use `ck3.py probe`, which reads end to end and groups
  by file.
