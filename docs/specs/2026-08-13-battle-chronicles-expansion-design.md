# Battle Chronicles — The Expansion

Date: 2026-08-13
Status: design, not implemented
Mod: `mods/battle_chronicles`
Predecessors: `2026-08-12-battle-chronicles-design.md`, `2026-08-12-battle-chronicles-aftermath-design.md`

All line citations are against the file **as loaded**. AGOT wins load order on most
files cited here, so those are AGOT's line numbers. Where a vanilla line differs it
is given as `vanilla :N`.

---

## The problem

The mod works. A battle now produces moments, a momentum swing, and — since the
aftermath layer — a memory, a tally and occasionally a name. But the moments and
the aftermath are two separate machines that never speak. `bc_chronicles.0091`
knows the battle was big and bloody; it does not know the banner fell on day ten,
that the commander rallied a broken line, or that he did it against the same man
who beat him last spring.

Nothing survives the phase-event boundary. At combat end the engine offers size,
losses, warscore and location. It cannot offer *what happened*. If the moments do
not write it down as they occur, no later system can ever know.

This design closes that gap and builds four systems on top of it.

---

## The locked decisions

Six choices were settled during design and everything below follows from them.

| decision | choice |
|---|---|
| integration shape | **The Ledger** — one seam, every moment reports through `bc_record_moment_effect` |
| lethality | **wounds yes, death never** |
| ledger scope | **commanders only**, ~7 fixed variables, world-wide (AI included) |
| reputation | **earn existing vanilla/AGOT commander traits** — no new trait art |
| pacing | **scale moments to battle size**, with a floor so no battle goes silent |
| volume | **spine first, then grow** |

Four sub-projects sit on the spine:

- **A — The Texture of Battle**: more verbs than "advantage up, advantage down".
- **B — The Commander's Reputation**: fighting a certain way makes you a certain
  kind of commander.
- **C — The Man Across the Field**: the enemy commander becomes a person.
- **D — Before and After**: the eve of battle, and the field afterwards.

---

## Section 1 — The spine

### The one seam

Every moment — phase event or pop-up option — reports itself through a single
scripted effect:

```
bc_record_moment_effect = { TIER = minor|major|decisive  KIND = <verb> }
```

Nothing else writes battle state. This is the only place the "state never lives
inside a toast" rule has to be enforced, the only place the variable leak surface
has to be audited, and the only place a fifth system would have to hook.

### Three tiers of state

| tier | storage | lifetime | holds |
|---|---|---|---|
| **Momentum** | character modifier | 20 days, wiped at combat end | the live advantage swing |
| **Scratch** | character variables | this battle only, zeroed at both ends | what happened in *this* battle |
| **Ledger** | character variables | forever | who this commander is |

Momentum must stay a modifier — it is what the engine actually reads for combat
advantage. Scratch and ledger must be variables: our own `bc_cleanup_effect` strips
every modifier at combat end, so anything modifier-shaped cannot persist by
construction.

### Scratch variables

Written by the seam, read at combat end, cleared at both combat start and combat
end.

| variable | meaning |
|---|---|
| `bc_battle_moments` | count of moments so far this battle |
| `bc_battle_worst_tier` | 1/2/3, highest-tier *faltering* moment |
| `bc_battle_best_tier` | 1/2/3, highest-tier *momentum* moment |
| `bc_battle_style` | the KIND of the highest-tier moment of the battle |
| `bc_battle_wounded` | set once a wound has been applied, caps at one per battle |
| `bc_battle_held` | set if the commander was faltering and then rallied |
| `bc_battle_foe` | the enemy side commander as seen during the battle |

`bc_battle_style` is set by the **highest-tier** moment of the battle, ties broken
by the **last** such moment. Not last-wins: a decisive stand on day five should
name the battle even if a minor scuffle followed it.

`bc_battle_foe` is captured during the battle, not read at combat end. The man
commanding at the end may not be the man who commanded during the moments —
commanders die, are captured, and are replaced mid-combat. `enemy_side.side_commander`
*does* resolve at combat end (vanilla uses it eight times across both hooks,
`combat_on_actions.txt:37, :39, :84, :112, :429, :463`) — the reason to capture
early is fidelity, not scope safety.

### Ledger variables

Never cleared. On side commanders only — the men who lead armies — which is what
keeps the leak surface bounded.

| variable | meaning |
|---|---|
| `bc_battles_led` | every battle commanded, notable or not |
| `bc_notable_battles` | notable battles **won**. Existing name kept for save compatibility |
| `bc_times_routed` | notable battles lost while faltering at the end |
| `bc_last_outcome` | won / lost / wiped |
| `bc_style_last` | the style of the last notable battle |
| `bc_style_streak` | consecutive notable battles sharing that style |
| `bc_nemesis` | the character this commander has a running grudge with |
| `bc_nemesis_losses` | how far the grudge has escalated |

Seven-to-eight variables on commanders only. Compare: a single vanilla character
routinely carries dozens.

### Consolidation

`bc_chronicles.0090` (cleanup, both hooks), `.0091` (winner) and `.0092` (loser)
become **one event per side**. The cleanup and the grading both need the same
scopes and both must run at combat end; keeping them separate means iterating
`every_side_knight` twice and reasoning about ordering between two events on the
same hook.

**Scratch-clearing must sit outside the game-rule gate.** `.0091`/`.0092` currently
carry `trigger = { NOT = { has_game_rule = bc_aftermath_off } }`. If scratch
clearing lived inside that trigger, a player with aftermath off would accumulate
scratch forever and every battle would inherit the last one's moment count.

---

## Section 2 — The verbs of battle (A)

Three families. Family 1 exists today; families 2 and 3 are new.

### Family 1 — the tide

The existing advantage ladder: `bc_momentum_minor/major/decisive` and
`bc_faltering_minor/major/decisive`, reached through the swing wrappers in
`bc_scripted_effects.txt`. Unchanged.

### Family 2 — character

New character modifiers giving a battle a *shape*, not just a direction. All are
20-day like momentum and all are stripped at combat end.

| modifier | key | narrative |
|---|---|---|
| `bc_bloodied` | `army_damage_mult` up, `army_toughness_mult` down | traded blood for ground |
| `bc_shieldwall` | `army_toughness_mult` up, `army_damage_mult` down | dug in and refused to move |
| `bc_spent_horse` | `knight_effectiveness_mult` down | the knights are blown |
| `bc_pursuit` | `army_pursuit_mult` up | the enemy is running and we are on them |

`knight_effectiveness_mult` is confirmed valid on a character modifier —
`00_martial_lifestyle_modifiers.txt:247`, `warfare_stablemaster_tamed_wild_horse_modifier`.

### Family 3 — flesh

Wounds. Never death.

```
bc_wound_effect = {
	if = {
		limit = { NOT = { has_trait = wounded } }
		change_trait_rank = { trait = wounded rank = 1 max = 2 }
	}
	else_if = {
		limit = { has_trait = wounded_1 }
		change_trait_rank = { trait = wounded rank = 1 max = 2 }
	}
}
```

**Why raw `change_trait_rank` and not the vanilla effect.** The obvious call is
`increase_wounds_no_death_effect` (`20_health_effects.txt:1076`, AGOT `:1081`). Its
name is a lie by omission. It applies the rank, then rolls a 10% infection chance
and fires `health.0102`/`health.0104` if untreated. That chain reaches
`wound_treatment_results_effect` (`:3482`), whose death gate at `:3448-3469` sets
`die_surgery` when a risky treatment fails and either the man is `wounded_3` under
an amputation-class strategy **or** `is_ai = yes AND health <= 0` — the AI arm has
no wound-rank requirement at all. `health.4105` (AGOT `health_events.txt:10483`)
then executes a real `death = { death_reason = death_treatment killer = scope:physician }`
at `:10562`, gated on that flag at `:10556`. So the vanilla "no death" effect can
kill, and most reliably for the AI, which is almost every commander in the world.
`increase_wounds_effect` (`:1204`) is worse — it kills outright at rank 3
(`:1221`) — and `maimed_in_battle_effect` (`:1227`) routes every branch through it.

The shape above makes death-never structural: a man at rank 2 or 3 is never
touched, so `wounded_3` can never be created by this mod, so no branch of the
vanilla death chain is reachable.

**Rank 1 is already heavy.** `wounded_1` (AGOT `00_traits.txt:6316`) carries
`martial -1`, `intrigue -1`, `health -1`, `prowess -2` and — the real cost —
`disables_combat_leadership = yes`. A wounded commander cannot lead an army. That
is a months-long consequence from one moment, which is why rank 2 is not needed for
weight.

**Wounds heal for free.** `wounded_recovery_pulse` (`health_on_actions.txt:360`)
hangs off `yearly_health_pulse` four times a year and its trigger is a bare
`has_trait = wounded`. A wound applied by raw `change_trait_rank` inherits the
entire vanilla recovery system at zero implementation cost.

**Wound gates**, all four required:

1. only from a `decisive`-tier faltering moment
2. only in a battle already notable by size
3. `bc_battle_wounded` unset — one per character per battle
4. game rule `bc_wounds_off` not set

---

## Section 3 — The commander's reputation (B)

### The hole this fills

CK3 already lets a commander get *better* at commanding by fighting:
`commander_trait_leveling_leveling_effect` (`00_war_effects.txt:2588`) is called on
`every_side_commander` at both combat ends (`combat_on_actions.txt:482-484` winner
XP 1, `:669-671` loser XP 0.5). But **every branch of it is gated
`has_trait = X`** — it levels traits you already have and never grants one. The
only granter is `give_random_commander_trait_effect`
(`00_martial_lifestyle_effects.txt:13`), a flat `random_list` from a lifestyle perk,
with its terrain branches gated on *owning* that terrain
(`any_sub_realm_barony = { title_province = { terrain = ... } }`).

So: the game lets you get better at commanding by fighting, but never lets you
become a *kind* of commander by fighting. That is the hole.

### Style traits

At combat end, if the battle was notable: compare `bc_battle_style` against
`bc_style_last`. Match increments `bc_style_streak`; mismatch resets it to 1 and
overwrites `bc_style_last`. At `bc_style_streak >= 3`, award the matching trait and
reset the streak to 0.

| style | trait |
|---|---|
| bloodied | `aggressive_attacker` |
| entrenched | `unyielding_defender` |
| adapted | `flexible_leader` |
| measured | `cautious_leader` |
| wild | `reckless` |
| ordered | `organizer` |

The streak counts notable battles of **either outcome**. A man who loses three
battles the same way has still shown you who he is.

### Terrain traits

Awarded from `scope:bc_battle_province` at combat end with **no new state** — the
province is already in scope for the memory writes. Gated on *fighting* there, not
owning there, which is the deliberate difference from the vanilla granter.

Trait list (all AGOT `00_traits.txt`, all `category = commander`,
`flag = commander_trait_flag`): `desert_warrior` :15045, `jungle_stalker` :15232,
`open_terrain_expert` :15818, `rough_terrain_expert` :16054, `forest_fighter` :16532,
`winter_soldier` :17133.

Deliberately skipped: `logistician`, `military_engineer`, `forder`, `holy_warrior`,
`reaver` — none of them is a thing a battle can teach you.

### Shared gates

- `number_of_commander_traits < 3` — a commander should not collect the set.
- A battle may award **either** a nickname **or** a trait, never both. Two
  reputation grants from one battle reads as a bug even when it is not.
- The award toast goes through a shared `bc_addressed_toast_effect`, extracted from
  the nickname toast. `send_interface_toast` bodies only run for a player-controlled
  character; every award in the mod must route to the liege when the subject is AI,
  and that rule belongs in one effect, not five.

### Risk

`number_of_commander_traits < 3` may be dead on arrival. This is the same failure
mode as `has_any_nickname = no`, which disqualified 3 of the 4 AGOT commanders
sampled. Must be measured before B ships — see the DIAG pass.

---

## Section 4 — The man across the field (C)

### Escalation

Read `bc_battle_foe` at combat end. On a **notable loss** to him:

| `bc_nemesis_losses` | relation set |
|---|---|
| 1 | `grudge` |
| 2 | `rival` |
| 3 | `nemesis` |

On a **notable win** against the current `bc_nemesis`, decrement. At 0, clear the
relation and both variables.

`grudge` is one-directional (`00_scripted_relations.txt:43` — no `corresponding`),
which is exactly right for a first loss: he humiliated you, he has not noticed you.
`rival` (`:54`) and `nemesis` (`:70`) are mutual. AGOT does not override this file;
it ships `00_agot_scripted_relations.txt` alongside, and `set_relation_*` /
`has_relation_*` appear 45 times across 12 AGOT files.

### Rules

- **Never overwrite an existing `bc_nemesis`.** One running grudge per commander.
  A second rival dilutes the first into noise.
- **Relations escalate only, never downgrade.** Decrementing `bc_nemesis_losses`
  below the threshold that set `nemesis` does not demote him to `rival`. Removing a
  relation the player never asked to remove is worse than leaving it.
- **Game rule `bc_rivalry_max`, defaulting to `rival`.** AGOT hangs murder schemes
  and worse off `nemesis`; a mod that silently manufactures nemeses is changing far
  more than battles. Players who want the full ladder opt in.
- **Every `bc_nemesis` read is guarded** by `exists` plus `is_alive = yes`, with a
  lazy wipe when the guard fails. Characters die constantly and a dangling character
  reference in a variable is a permanent error-log line.

### Read-back

This is what closes the loop. `bc_nemesis` gates phase events: fighting the man who
beat you twice should not read like fighting a stranger. This is the *only* thing
that makes a commander feel like the same man twice.

---

## Section 5 — Before and after (D)

D was drafted much larger and then cut hard, because most of it already exists.
Vanilla's `on_combat_end_winner` already handles prisoners (`combat_event.1001`),
both commanders' battle memories, banner looting (`artifact.6000`), the map
point-of-interest (`combat_event.3000`), glory (`combat_event.2101`), the Undefeated
nickname (`combat_event.0001`), and legitimacy loss on the loser side
(`combat_on_actions.txt:561-578`). Prisoners and captured banners were cut from the
verb list on those grounds.

Four genuine gaps remain.

### 1. The eve

`on_combat_start` is **completely empty in vanilla** (`combat_on_actions.txt:3-4`,
Root = Combat). An entirely unclaimed hook. It does three things:

- zero the scratch on both commanders — the reliable place to do it, because it runs
  before any moment can be recorded
- write `bc_battle_foe` on both sides
- one throttled pop-up on the eve of a large battle

Root is the Combat, so the commanders are reached via `combat_attacker.side_commander`
and `combat_defender.side_commander` (`event_targets.log:1054`, `:1060`).

The eve pop-up gets its **own 90-day `bc_eve_cooldown` flag**. Sharing the existing
60-day `bc_popup_cooldown` would starve the mid-battle chronicles: the eve fires
first, every time, and would consume the budget before the battle began.

### 2. `scope:wipe`

Both end hooks hand us a `scope:wipe` boolean — was this an annihilation — and
nothing in the game or the mod reads it. It becomes the top tier of everything:
the top rung of the notability grade, the strongest reputation signal, the fastest
rivalry escalation.

### 3. The field

`add_province_modifier` on `combat.location`, so a field where something happened
carries it for a while.

**This is the mod's largest save-bloat risk.** Province modifiers accumulate
forever. Every application must be duration-bounded and must check-and-refresh
rather than blindly adding a second copy.

### 4. The dead

`.0091`/`.0092` both carry `limit = { is_alive = yes }` on `every_side_knight`,
which silently drops exactly the knights whose deaths were worth telling. Invert it
into a second pass over the dead.

The dead-knight toast must be **one aggregate toast per battle per liege**, not one
per knight. A liege who lost six knights should be told once.

---

## Section 6 — The pacing curve

### The problem

Phase events roll every `COMBAT_EVENT_DAYS = 5`. A skirmish and a two-month siege
battle currently get the same 15-day chronicle cooldown, so the long battle gets a
constant stream of moments and the short one often gets none.

### Scale at write time

`bc_mark_chronicle_effect` currently hardcodes `days = 15`. It becomes a script
value scaled by battle size:

| `num_total_troops` | flag duration |
|---|---|
| under 2,000 | 40 days |
| 2,000 – 9,999 | 20 days |
| 10,000+ | 10 days |

**Scaling happens at write time, not read time.** The size read is a combat-scope
read, and `bc_chronicle_ready_trigger` runs on every candidate event on every roll.
**Hard rule: nothing in `bc_chronicle_ready_trigger` may touch a combat scope.**

### The floor

`bc_chronicle_ready_trigger` also passes when `bc_battle_moments` is 0 or unset —
so a battle that has produced nothing yet can always produce its first moment,
regardless of the flag. This is a cheap *variable* read, which is the only reason
the rule above survives.

### Verb families gate on size

| size | families available |
|---|---|
| any | 1 — the tide |
| 2,000+ | 1, 2 — character |
| 10,000+ **and** notable | 1, 2, 3 — flesh |

A skirmish between two hundred men should not maim anyone.

### Escalation ladder

Within one battle, the tier available scales with moments already recorded:

| `bc_battle_moments` | tier |
|---|---|
| 1–2 | minor |
| 3–4 | major |
| 5+ | decisive |

**Two ladders, not three.** An earlier draft also scaled tier by battle size
directly. That was cut: big battles last longer, so they naturally accumulate more
moments and reach the higher rungs on their own. Size stays as the verb-family
gate only. Three multiplicative ladders would be untunable.

### Risk

The `< 2,000` threshold is invented. The 2026-08-13 calibration run recorded
`under 5k` as a single bucket of 26 of 39 battles and never subdivided it. Must be
measured — see the DIAG pass.

---

## Section 7 — Structure, measurement, sequencing

### File structure

The mod is 1841 script lines across 11 files. This roughly doubles it. Split by
responsibility, not by sub-project:

```
common/scripted_effects/bc_ledger_effects.txt      NEW   the seam, scratch writes, ledger writes
common/scripted_effects/bc_reward_effects.txt      NEW   trait grant, wound, nickname, addressed toast
common/scripted_effects/bc_scripted_effects.txt    KEEP  momentum ladder + cleanup only
common/modifiers/bc_battle_modifiers.txt           NEW   family-2 character modifiers
common/modifiers/bc_province_modifiers.txt         NEW   the field-mark
common/scripted_triggers/bc_ledger_triggers.txt    NEW   scratch/ledger reads, nemesis guards
events/bc_aftermath_events.txt                     NEW   the combat-end graders, moved out
events/bc_eve_events.txt                           NEW   on_combat_start
events/bc_events.txt                               KEEP  player pop-ups only
```

`bc_events.txt` is 379 lines holding two unrelated things: player-facing character
events and hidden `scope = combat_side` graders. Different ROOT, different lifecycle,
and the graders are the part that grows most under A/B/C/D. The split is structural,
not cosmetic.

### Cleanup restructure

`bc_cleanup_effect` is currently six hand-written
`if = { limit = { has_character_modifier = X } remove_character_modifier = X }`
blocks. Family 2 adds four more modifiers and every future one must be remembered
here or it leaks past combat end.

`remove_character_modifier` on an absent modifier is a no-op. Verified:
`vizierate_remove_extravagance_modifiers_effect`
(`00_diarchy_scripted_effects.txt:2318-2333`) is a flat unguarded list of 16 tier
modifiers of which at most 4 can be held, so 12 of the 16 calls are always no-ops,
every call, by design.

So the guards go and the effect becomes a flat list of ten `remove_character_modifier`
lines — one per modifier, adjacent to the modifier file, impossible to half-forget.

### The DIAG pass — one run, three questions

A game restart costs about seven minutes, so one run must answer everything. All
three questions are unmeasured and each independently invalidates a design decision.
All three are pure `debug_log` with no state.

**Q1 — trait census.** Log `number_of_commander_traits` for every side commander at
combat end, as a raw count, not a pass/fail. B gates on `< 3`. If the median
commander already holds 3, B is dead on arrival.

**Q2 — `side_commander` at combat start.** Does it resolve from `on_combat_start`
via `combat_attacker.side_commander` / `combat_defender.side_commander`? If not,
D's eve dies and the scratch-zeroing must move to the first moment of the battle.

**Q3 — size ladder at 1k / 2k / 3k / 5k.** Subdivides the `under 5k` bucket that
the calibration run left whole, and settles the pacing curve's invented threshold.

Q2 requires hooking `on_combat_start`, which the mod does not currently do. The hook
therefore ships one stage early carrying nothing but the logging event. That is
harmless and it is the only way to answer Q2 without a second restart.

### Sequencing

| stage | ships | gated on |
|---|---|---|
| 0 | strip old DIAG markers, split files, flatten cleanup | — |
| 1 | the seam + scratch + ledger, wired to existing events; `on_combat_start` hook; DIAG pass | — |
| 2 | family 2 modifiers, pacing curve | Q3 |
| 3 | B — reputation | Q1 |
| 4 | C — rivalry | stage 1 proven live |
| 5 | D — eve, wipe, field-mark, dead knights | Q2 |
| 6 | family 3 — wounds | stage 2 proven |

**Stage 1 ships no new player-visible behaviour.** That is the point: the seam is
proven by log before anything is built on it.

**This is a graph, not a line.** Stages 2, 3 and 5 all unblock on the same DIAG run
and may ship in any order. Only 4 (needs the seam live) and 6 (needs family 2) are
genuinely sequential.

**Order inside stage 0 matters**: the old DIAG markers must be stripped *before* the
new ones are added, or the log is two interleaved generations of markers.

---

## Carried-over hygiene

Not part of the four sub-projects, but must be folded into stage 0:

- **DIAG markers are still deployed** in `bc_events.txt`: `"BC: DIAG cleanup
  commander scope entered"`, `"BC: DIAG win commander scope entered"`, `"BC: DIAG
  commander alive"`, the counter ladder, `"BC: DIAG no nickname yet"`, `"BC: DIAG
  martial >= 14"`. Strip all of them.
- **`bc_aftermath_nickname_effect` has never executed at runtime.** It must be
  force-executed once before anything is built on the reward path.

---

## Constraints that shaped this design

Collected because each one killed at least one earlier draft.

- **`send_interface_toast` bodies only run for a player-controlled character.**
  Verified. State must never live inside a toast; toasts about AI subjects route to
  the liege.
- **Modifiers are wiped at combat end** by the mod's own cleanup, so persistence
  must be variables and cooldowns must be flags.
- **`effect = { }` in an `on_action` does not merge across files** — one is kept,
  winner by alphabetical filename. `events`, `random_events` and `on_actions` do
  merge. And `effect = { }` runs *concurrently with* the on_action's events, not
  before them.
- **`calc_true_if = { amount >= N ... }` counts direct children.** A nested scripted
  trigger counts as one row no matter how many tests it holds.
- **Game rules are baked into a save at creation** and cannot be changed mid-game,
  so every game rule must have a sane default.
- **A scripted effect does not rebind ROOT.** `left_icon` accepts only a character,
  artifact, title, dynasty or house — never a combat side.
- **Localization needs UTF-8 with BOM** and one leading space per line.
- **Zero file collisions is a hard requirement.** Verify with `ck3.py conflicts`
  after `ck3.py index`; a stale index makes `conflicts` always pass.
- **`ck3.py errors` cannot see mod script errors** — it tail-slices a ~500k-line
  log and mod errors appear near the top. Use `ck3.py probe`, which reads end to end
  and groups by file, and remember it exits 1 when nothing matches, so for an error
  sweep a non-zero exit is the pass condition.
