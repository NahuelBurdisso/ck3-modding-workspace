# Battle Chronicles Expansion — Plan 6: Family 3, the Flesh

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A commander who is on the losing end of a decisive moment, in a large battle that
has already been going for a while, can be wounded — once per battle, never worse than
`wounded_1`, never dead.

**Architecture:** One scripted effect holding four gates, called from the decisive arm of the
seam's tier ladder. No new events, no new pop-ups, no new toast routing. The trait is applied
with raw `change_trait_rank` rather than any vanilla wound effect, and healing is inherited
from vanilla's `wounded_recovery_pulse` at zero cost.

**Tech Stack:** CK3 script (Paradox clausewitz script), targeting CK3 1.19.0.6 under the
AGOT playset. Workspace CLI is `python ck3.py` run from `D:/ck3/tools`.

**Spec:** `D:/ck3/docs/specs/2026-08-13-battle-chronicles-expansion-design.md`, Section 2,
"Family 3 — flesh", plus Section 6's "verb families gate on size".

**This is the smallest plan of the expansion and the one with the highest blast radius per
line.** `wounded_1` carries `disables_combat_leadership = yes`. Every gate below exists to
keep that from landing on the wrong person, at the wrong time, or twice.

**Depends on plan 1, and on plan 1 only.**

| what plan 6 needs | where it comes from |
|---|---|
| `bc_record_effective_tier_effect` and its ceiling ladder | plan 1 task 8 |
| `var:bc_battle_size`, the 1/2/3 bucket | plan 1 task 7, `bc_battle_open_effect` |
| the bucket boundaries gate 2 is calibrated against | plan 1 task 14, DIAG **Q3** |
| `bc_battle_wounded` already listed in `bc_clear_scratch_effect` | plan 1 task 12 |
| `bc_addressed_toast_effect` **with its `TYPE` parameter** | plan 1 task 4 |
| every seam call running on a side commander | plan 1 task 11 |
| `SWING` in the seam's signature | plan 1 task 8 |

**Plan 2 is not a dependency.** It is easy to assume it is — `bc_battle_size` and the size-gate
nesting pattern both look like plan 2 material — but the variable, its ladder and its measured
boundaries are all plan 1's, and plan 2 only *reads* them. **Plan 6 can ship straight after
plan 1.** The single place plan 2 shows up is one expected count in task 4 step 4, which states
both values.

**Independent of plans 3, 4 and 5.** Nothing here reads or writes reputation, rivalry, or
anything at the edges of a combat.

---

## Read this before task 1

Plan 1's entire "Read this before task 1" applies unchanged — the verification loop, the
`validate`-is-syntax-only rule, the cleared-log rule, the mod-is-its-own-git-repo rule, the
sweep pass condition, and the non-negotiables. **Read it first.** What follows is only what
is new in plan 6.

### `bc_battle_tier` is a high-water mark. The spec tells you to read it. Do not.

Spec Section 2, gate 1: *"Gate 1 is the effective tier, not the requested one — the value the
seam has just written to `bc_battle_tier`, after Section 6's ceiling has been applied."*

**The first half of that sentence is right and the second half names the wrong variable.**
Read plan 1's `bc_write_style_effect`:

```
bc_write_style_effect = {
	if = {
		limit = { NOT = { exists = var:bc_battle_tier } }
		set_variable = { name = bc_battle_tier value = $RANK$ }
		...
	}
	else_if = {
		limit = { var:bc_battle_tier <= $RANK$ }
		set_variable = { name = bc_battle_tier value = $RANK$ }
		...
	}
}
```

**It only ever writes upward.** `bc_battle_tier` is the *highest* rank the battle has reached,
kept as a high-water mark so `bc_battle_style` can name the battle after its biggest moment
rather than its last one. Plan 1's own comment says so: *"bc_battle_style holds the KIND of
the HIGHEST-TIER moment of the battle."*

So `var:bc_battle_tier = 3` does not mean *this moment was decisive*. It means *some moment
in this battle was decisive, possibly six moments ago*. Writing gate 1 against it would let a
`minor` `bc_lines_bogged_down` wound a commander because a `bc_flank_collapses` had fired
earlier — the requested tier would be `minor`, the effective tier would be `minor`, and the
gate would pass anyway.

**The effective tier is not stored anywhere and does not need to be.** It is known exactly,
by construction, inside the three arms of `bc_record_effective_tier_effect` — that ladder *is*
the ceiling, and its first arm is the definition of "this moment resolved to decisive". Task 4
puts the wound call there. Nothing new is stored and nothing has to be re-derived.

**Do not add a `bc_battle_effective_tier` scratch variable to work around this.** It would be
a seventh scratch variable that exists only to carry a value across two lines of the same
effect, and it would have to be added to `bc_clear_scratch_effect`, whose list plan 1
deliberately wrote complete.

### A wound can never reach a knight, and that is plan 1's doing, not this plan's

`wounded_1` disables combat leadership. Landing it on a random courtier knight — of which a
single battle produces 41 rolls — would be the worst version of this feature.

It cannot happen, and the reason is structural rather than a guard in this plan. Plan 1
task 11 step 4 asserts that all six seam calls in `bc_knight_phase_events.txt` sit **inside**
a `scope:combat_side.side_commander ?= { }` block, and its verification step exists precisely
to catch a call that escaped one. `bc_wound_effect` runs wherever the seam runs, so it runs on
the side commander, always.

**Task 5 re-runs that assertion rather than trusting it**, because plan 6 is the first thing
in the mod for which a leak would be actively harmful rather than merely untidy.

### `wounded_1` is silent. The mod has to say it happened.

AGOT `common/traits/00_traits.txt:6330` — `wounded_1` carries `flag = no_message`. Applying
it produces **no vanilla notification at all**. A commander would simply stop being able to
lead armies with nothing on screen to explain why.

That is why task 3 exists. Every other trait this mod grants is a reputation trait the player
chose their way into over several battles; this one arrives in a single moment and takes
something away.

### Never `wounded_2`, and `max = 1` is what guarantees it, not the guard

```
change_trait_rank = { trait = wounded rank = 1 max = 1 }
```

`effects.log:3507` — `change_trait_rank = { trait = trait_group rank = change max = maximum
new rank }`, character scope. **`rank` is a delta, not an absolute.** `wounded` is a real
trait group: AGOT `00_traits.txt:6346`, `:6385` and `:6424` carry `group = wounded` with
`level = 1`, `2` and `3`.

So `rank = 1` means *one rung up* and `max = 1` means *and never above rung 1*. The
`NOT = { has_trait = wounded }` guard makes the effect a no-op on an already-wounded man;
`max = 1` makes the ceiling structural, so that if the guard is ever loosened the mod still
cannot create a `wounded_2`.

**Why that matters more than it looks.** The mod never calls a lethal effect, but a
mod-created `wounded_2` would put a commander one *vanilla* wound from `wounded_3`, and
`wounded_3` is the doorway to every lethal path in `20_health_effects.txt` — `increase_wounds_effect`
(`:1209`) kills outright at rank 3, `maimed_in_battle_effect` (`:1232`) routes every branch
through it, and the `die_surgery` gate (`:3626-3648`) has an `is_ai = yes AND health <= 0`
arm with no wound-rank requirement at all. Creating `wounded_2` would make the mod indirectly
lethal while satisfying "death never" in letter. **The locked decision is "wounds yes, death
never", and `max = 1` is the line that keeps it.**

### Why not `increase_wounds_no_death_effect`

It is `20_health_effects.txt:1081` and its name is a promise it does not keep for a caller
that needs rank control. Its first branch (`:1087-1096`) applies **rank 3** outright to a
character with `fragile_bones` at 50+ track XP; its second (`:1097-1106`) applies rank 2 to
any `fragile_bones` character. A mod calling it cannot promise it only ever creates
`wounded_1`.

To be fair to it: at rank 1 it is safe. `:1130-1140` routes rank 1 to
`safe_wound_treatment_effect`, and the risky path the `die_surgery` gate requires is reachable
only through `risky_wound_treatment_effect` (`:2418`). **The honest statement is that the
vanilla effect is safe at the rank this mod wants and unsafe at the ranks this mod must never
reach — and since the caller cannot stop it reaching them, the mod does not call it.**

### Healing is free and must stay that way

AGOT `common/on_action/health_on_actions.txt:369` — `wounded_recovery_pulse`, hung off
`yearly_health_pulse` (`:4`) **four times a year** via four `delay` blocks. Its trigger:

```
	trigger = {
		OR = {
			has_trait = wounded
			has_infected_or_gangrenous_wound_trigger = yes
		}
	}
```

Its `random_events` give `400 = health.0001 #Recover from Wounded` against a total weight of
1150 — roughly a one-in-three chance per pulse, four pulses a year.

**A wound applied by raw `change_trait_rank` inherits all of this at zero implementation
cost**, because the pulse tests the trait group and does not care who applied it. **Do not
add a duration, a timed removal, or a recovery event.** Anything this plan writes to take the
trait away would race the vanilla pulse and produce two recoveries for one wound.

### The SWING half of gate 1 is inert today. Leave it in.

Plan 1 wires exactly two call sites at `TIER = decisive`:

| site | seam call |
|---|---|
| `bc_flank_collapses` | `{ TIER = decisive KIND = wild SWING = down }` |
| `bc_chronicles.0001` opt c | `{ TIER = decisive KIND = wild SWING = down }` |

**Both already carry `SWING = down`, so the swing test never rejects anything as the mod
stands.** That is not a reason to drop it. `SWING` exists in the seam's signature *because*
the wound gate needs it — spec Section 1 says so outright — and the first `TIER = decisive
SWING = up` site anyone adds would otherwise wound a commander for winning.

State this in the effect's own comment. An implementer who measures that the row never fires
will otherwise delete it as dead code.

### The four gates, and which one is a read

| # | gate | written as | safe as a sibling? |
|---|---|---|---|
| 1a | effective tier is decisive | **structural** — the call sits in the decisive arm | n/a |
| 1b | `SWING = down` | `flag:$SWING$ = flag:down` | yes — a flag comparison reads nothing |
| 2 | battle is size 3 | `var:bc_battle_size >= 3` | **NO. This is a read and must be nested** |
| 3 | not already wounded this battle | `NOT = { exists = var:bc_battle_wounded }` | yes — `exists` is safe on a missing variable |
| 4 | game rule | `NOT = { has_game_rule = bc_wounds_off }` | yes |
| — | not already carrying a wound | `NOT = { has_trait = wounded }` | yes |

**`flag:$SWING$ = flag:down`, never `$SWING$ = down`.** A bare `$SWING$ = down` substitutes
textually to `down = down`, an unknown key, which is a silent no-op that `validate` passes.
This is the same failure plan 1 documents for `$TIER$ = decisive`, and the `flag:` form is the
shipped idiom — vanilla `00_animal_effects.txt:1659`, AGOT
`00_agot_character_data_effects.txt:1427-1463`.

**Gate 2's absent case is real, not defensive padding.** `bc_chronicles.0001` opt c is one of
the two decisive call sites and it is a **pop-up option**. A pop-up answered after the combat
has already ended runs after `bc_clear_scratch_effect`, so `var:bc_battle_size` is gone. Plan 2
hit exactly this for the family-2 apply and nested the same way.

### New variables: none

`bc_battle_wounded` already exists — plan 1 task 12 put it in `bc_clear_scratch_effect`
deliberately, ahead of anything writing it, with the comment *"bc_battle_wounded is listed
although nothing writes it until plan 6. Clearing a variable that does not exist is a no-op;
forgetting to add it later is not."* **Plan 6 is the plan that writes it. Do not add it to the
clear list again.**

### New markers

All begin `BC: `, so plan 1's sweep row 3 covers them.

| marker | meaning |
|---|---|
| `BC: wound` | a commander was wounded. All four gates passed |

**One marker, deliberately.** `BC: moment decisive` already fires on every entry to the arm
this hangs off, so the ratio of the two counts is the gate-rejection rate and no second marker
is needed to measure it.

---

## File structure

| path | plan action | responsibility |
|---|---|---|
| `common/game_rules/bc_game_rules.txt` | modify (task 1) | the `bc_wounds` rule |
| `common/scripted_effects/bc_ledger_effects.txt` | modify (tasks 2, 3, 4) | `bc_wound_effect`; `SWING` threaded into `bc_record_effective_tier_effect` |
| `localization/english/bc_l_english.yml` | modify (tasks 1, 3) | 8 keys |
| `README.md` | modify (final task) | the run log, appended in the existing `## First live run (2026-08-12)` style |

**`bc_wound_effect` lives in `bc_ledger_effects.txt`, beside the seam, not in
`bc_scripted_effects.txt`.** It is called from exactly one place, that place is two effects
above it in the same file, and its correctness depends on where in that ladder it is called
from. Splitting them across files would hide the one thing a reader has to see.

**No new file.** Plan 5 created one for the eve because the eve runs in a scope nothing else
in the mod uses. Family 3 runs in the seam's scope, like everything else.

---

### Task 1: The `bc_wounds` game rule

**Files:**
- Modify: `mods/battle_chronicles/common/game_rules/bc_game_rules.txt`
- Modify: `mods/battle_chronicles/localization/english/bc_l_english.yml`

- [x] **Step 1: Record the localization baseline**

```bash
cd /d/ck3/mods/battle_chronicles
grep -c "^ bc_\|^ rule_bc_\|^ setting_bc_" localization/english/bc_l_english.yml
```

**Write the number down.** Task 3 step 4 checks the total rose by exactly 8 across both
localization tasks in this plan, and that is not a check you can run without the number from
before.

- [x] **Step 2: Read the file's warning before touching it**

```bash
cd /d/ck3/mods/battle_chronicles && sed -n '1,20p' common/game_rules/bc_game_rules.txt
```

The header records that **a modded game rule is baked into every save made with it**, and
that disabling the mod afterwards makes that save fail to load with
`Failed to read key reference: bc_frequency_default`. Adding a fourth rule adds a fourth key
to that set. **That is expected and is not a reason to skip the rule** — the alternative is a
mod that can wound a player's commander with no way to turn it off — but it does mean the
rule must land in one commit and never be renamed afterwards.

- [x] **Step 3: Add the rule**

Append to `common/game_rules/bc_game_rules.txt`:

```

bc_wounds = {
	categories = { flavor }

	default = bc_wounds_default

	bc_wounds_off = {}
	bc_wounds_default = {}
}
```

**Two options, not three.** The other three rules are low/default/high ladders because they
scale a frequency. This one is a switch: a wound either can happen or it cannot. A "frequent
wounds" option would need a second set of gate values and would have nothing to tune them
against until the DIAG-style run in task 6 has happened at least once.

**`default = bc_wounds_default`, so wounds are ON by default.** That is a deliberate choice
and matches `bc_aftermath`, which also defaults on. The feature is the point of the plan; a
rule that defaults off is a feature nobody sees.

**`categories = { flavor }`, matching the other three.** Do not invent a category.

- [x] **Step 4: Add the six rule localization keys**

Append to `localization/english/bc_l_english.yml`, **after the last existing `setting_bc_`
line**, so the rule keys stay in one block. **One leading space per line.**

**"After the last `setting_bc_` line", not "after `setting_bc_aftermath_generous_desc`."**
Plan 4 task 1 also adds a game rule and also appends to this block, and plan 6 is declared
independent of plan 4 — the order the two land in is not fixed. Anchoring on a specific rule's
last key would interleave them.

```

 rule_bc_wounds:0 "Battle Chronicles: Wounds"
 rule_bc_wounds_desc:0 "Whether a commander can be hurt in the fighting. He is never killed, and never worse than wounded — but a wounded man cannot lead an army until he mends."
 setting_bc_wounds_off:0 "Off"
 setting_bc_wounds_off_desc:0 "Commanders come off every field whole. Battles still turn on their decisions; nothing is ever taken out of them."
 setting_bc_wounds_default:0 "Default"
 setting_bc_wounds_default_desc:0 "A commander on the wrong side of a decisive moment, in a large battle that has already been going a while, may be carried off it. At most once per battle, and never more than once at a time."
```

**The `_desc` on the rule itself states the two guarantees**, because the game-rule screen is
the only place in the game a player can read what the mod promises before it happens to them.
"He is never killed" is the locked decision, in the player's own words.

- [x] **Step 5: Validate and commit**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
```

Expected: exit 0.

**`validate` proves only brace balance and BOM here. It does not know what a game rule is.**
`grep -n "game_rule\|setting_\|rule_" ck3.py` returns nothing — the tool has no game-rule
awareness at all, so it cannot tell you that `bc_wounds_off` needs a `setting_bc_wounds_off`
key, and a rule whose options have no `setting_` keys renders as raw tokens in the game-rule
screen while validating perfectly.

**The only check for these six keys is task 6 step 2**, which reads the game-rule screen before
loading a save. Do not treat a clean `validate` here as evidence the rule is correct.

Two things you *can* check statically:

```bash
cd /d/ck3/mods/battle_chronicles
grep -n "^ rule_bc_wounds" localization/english/bc_l_english.yml
grep -n "^ setting_bc_wounds" localization/english/bc_l_english.yml
grep -n "bc_wounds" common/game_rules/bc_game_rules.txt
```

Expected **2**, then **4**, then **4** lines:

| grep | lines |
|---|---|
| `rule_bc_wounds` | the rule's name and its `_desc` |
| `setting_bc_wounds` | `off`, `off_desc`, `default`, `default_desc` |
| the rules file | `bc_wounds = {`, `default = bc_wounds_default`, and the two option blocks |

**Scoped to `bc_wounds`, not a total over all rules.** A total would be wrong the moment
another plan adds a rule, and plan 6 is declared independent of plans 3, 4 and 5 — the order it
lands in is not fixed.

**`^ ` — caret then a space — is the anchor, and it is doing real work.** Every loc key in this
file carries exactly one leading space, so the anchored pattern counts *key definitions* rather
than any mention of the name. Without it these greps would silently start counting prose the
moment someone writes a `_desc` that names an option.

Every option token in the third grep must have both a `setting_` and a `setting_..._desc` key
in the second. That pairing is exactly what task 6 step 2 renders.

```bash
cd /d/ck3/mods/battle_chronicles
git add common/game_rules/bc_game_rules.txt localization/english/bc_l_english.yml
git commit -m "feat: add the bc_wounds game rule

A switch rather than a low/default/high ladder - a wound either can happen or it
cannot, and there is nothing to tune a middle rung against yet. Defaults on,
like bc_aftermath. Adds a fourth modded rule key to every save made with the
mod, which the file's header already warns about."
```

---

### Task 2: `bc_wound_effect`

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_ledger_effects.txt`

- [x] **Step 1: Confirm the marker does not exist**

```bash
cd /d/ck3/tools && python ck3.py probe "BC: wound"
```

Expected: **exit 1** — `probe` exits 1 when nothing matches. This is the failing test. A match
means a previous attempt left code behind; find it before continuing.

Then record one baseline, **before any edit in this plan**:

```bash
cd /d/ck3/mods/battle_chronicles
grep -n "bc_battle_tier" common/scripted_effects/bc_ledger_effects.txt | grep -v "#" | wc -l
```

**Write the number down.** Task 5 step 2 re-runs this exact command and requires the same
number. This plan must not add a single code-level read of `bc_battle_tier`, and the number
cannot be predicted in the abstract because plans 1 and 2 both write to this file — so it has
to be taken here, before the first edit, rather than asserted later.

The comment block in the next step names `bc_battle_tier` twice while explaining why not to
read it, which is why the filter is on both the baseline and the check.

- [x] **Step 2: Write the effect**

Append to `common/scripted_effects/bc_ledger_effects.txt`, **after**
`bc_record_effective_tier_effect` and `bc_write_style_effect`, so the file reads in call
order:

```
# --- family 3, the flesh ----------------------------------------------------
#
# bc_wound_effect = { SWING = up|down }
#
# CALLED FROM THE DECISIVE ARM OF bc_record_effective_tier_effect, AND NOWHERE
# ELSE. That placement IS gate 1a: the arm is the definition of "this moment
# resolved to decisive", after the ceiling has been applied.
#
# DO NOT REWRITE THIS AGAINST var:bc_battle_tier. The spec says to and the spec is
# wrong on that one word. bc_battle_tier is a HIGH-WATER MARK - bc_write_style_effect
# above only ever writes it upward, so once any moment of a battle has been
# decisive it reads 3 for the rest of the battle. Gating on it would let a MINOR
# moment wound a commander because a decisive one happened six moments earlier.
#
# THE COMMANDER, ALWAYS. Every seam call site in bc_knight_phase_events.txt sits
# inside a `scope:combat_side.side_commander ?= { }` block, which plan 1 task 11
# step 4 asserts and plan 6 task 5 re-asserts. wounded_1 carries
# `disables_combat_leadership = yes`; landing it on a courtier knight - of which
# one battle produces 41 rolls - is the failure this whole chain prevents.
#
# `flag:$SWING$ = flag:down`, NEVER `$SWING$ = down`. A bare comparison substitutes
# textually to `down = down`, an unknown key, which is a SILENT NO-OP that validate
# passes - every wound would fire regardless of swing. Same failure as
# `$TIER$ = decisive`; same shipped fix (vanilla 00_animal_effects.txt:1659).
#
# THE SWING ROW IS INERT TODAY AND STAYS. Both TIER = decisive call sites already
# pass SWING = down, so this row rejects nothing as the mod stands. SWING exists in
# the seam's signature BECAUSE of this gate - spec Section 1 says so - and the
# first `decisive` + `up` site anyone adds would otherwise wound a man for winning.
#
# THE SIZE READ IS NESTED, THE OTHER FOUR ROWS ARE NOT. CK3 does not short-circuit
# and guarantees no evaluation order among siblings, so a comparison in the outer
# limit would evaluate even when the variable is absent. `exists`, `has_trait`,
# `has_game_rule` and a flag comparison are all safe on absence; only
# `var:bc_battle_size >= 3` is a read.
#
# THE ABSENT SIZE CASE IS REAL. bc_chronicles.0001 opt c is one of the two decisive
# call sites and it is a POP-UP OPTION. Answered after the combat ended, it runs
# after bc_clear_scratch_effect and there is no bc_battle_size to read.
#
# max = 1 IS THE LINE THAT KEEPS "DEATH NEVER". rank is a DELTA (effects.log:3507),
# `wounded` is a real trait group (AGOT 00_traits.txt:6346), and max caps the new
# rank. The has_trait guard makes this a no-op on an already-wounded man; max = 1
# makes the ceiling structural, so the mod cannot create a wounded_2 even if the
# guard is later loosened. A mod-created wounded_2 would put a commander one
# VANILLA wound from wounded_3, which is the doorway to every lethal path in
# 20_health_effects.txt - indirectly lethal while satisfying "death never" in
# letter.
#
# NO DURATION, NO TIMED REMOVAL, NO RECOVERY EVENT. Vanilla's
# wounded_recovery_pulse (AGOT health_on_actions.txt:369) fires four times a year
# off yearly_health_pulse and triggers on `has_trait = wounded`, so a raw
# change_trait_rank inherits the entire recovery system for free. Anything written
# here to take the trait away would race it.
bc_wound_effect = {
	if = {
		limit = {
			flag:$SWING$ = flag:down
			NOT = { has_game_rule = bc_wounds_off }
			NOT = { exists = var:bc_battle_wounded }
			NOT = { has_trait = wounded }
			exists = var:bc_battle_size
		}
		if = {
			limit = { var:bc_battle_size >= 3 }
			change_trait_rank = {
				trait = wounded
				rank = 1
				max = 1
			}
			set_variable = { name = bc_battle_wounded value = yes }
			debug_log = "BC: wound"
		}
	}
}
```

**`set_variable = { name = X value = yes }` is shipped vanilla** —
`01_exp1_historical_artifacts_creation_effect.txt:270` and four more in the same file.
Verified.

**`bc_battle_wounded` is set inside the inner `if`, not the outer one.** It records that a
wound happened, not that one was considered. Setting it in the outer block would make the
first decisive-and-down moment of a *small* battle block the wound for the rest of that
battle, which is a bug that would only ever show up as "wounds are rarer than the gates say".

**No toast yet.** Task 3 adds it. This step is deliberately the mechanism alone, so that if
the runtime run shows wounds firing at the wrong rate the toast is not in the way of reading
why.

- [x] **Step 3: Confirm nothing calls it yet**

```bash
cd /d/ck3/mods/battle_chronicles
grep -rn "bc_wound_effect" common/ events/ | grep -v "#"
```

Expected: **exactly one line**, the definition. Task 4 adds the second. If a call site already
exists, task 4 has run out of order and the file needs reading before anything else happens.

- [x] **Step 4: Validate and commit**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
```

Expected: exit 0.

**`validate` proves nothing about this task beyond brace balance.** It does not know that
`wounded` is a trait group, that `change_trait_rank` takes `max`, or that `bc_wounds_off` is
a game-rule option. All three were verified against the dumps and the loaded AGOT files
before this plan was written; task 5 re-checks the two that a typo could break.

```bash
cd /d/ck3/mods/battle_chronicles
git add common/scripted_effects/bc_ledger_effects.txt
git commit -m "feat: add bc_wound_effect

Four gates, one of which is structural: the effect is only ever called from the
decisive arm of the tier ladder, because the effective tier is not stored
anywhere and bc_battle_tier is a high-water mark rather than the current
moment's tier.

max = 1 rather than a guard alone. rank is a delta, so max is what makes the
wounded_1 ceiling structural - and a mod-created wounded_2 would put a commander
one vanilla wound from the ranks that kill."
```

---

### Task 3: Say that it happened

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_ledger_effects.txt`
- Modify: `mods/battle_chronicles/localization/english/bc_l_english.yml`

- [x] **Step 1: Understand why this task is not optional**

AGOT `common/traits/00_traits.txt:6330` — `wounded_1` carries `flag = no_message`. **The trait
arrives with no vanilla notification of any kind.** Without this task a player's commander
silently stops being able to lead armies and nothing on screen says why.

Every other trait this mod grants is a reputation trait earned across several battles, where
the player has been watching it accumulate. This one is taken, in one moment, and removes
something.

- [x] **Step 2: Add the toast**

In `bc_wound_effect`, inside the inner `if`, after `set_variable` and `debug_log`:

```
			save_scope_as = bc_wounded_commander
			bc_addressed_toast_effect = {
				TYPE = event_toast_effect_bad
				TITLE = bc_wounded_toast
				DESC = bc_wounded_toast_desc
				SUBJECT = scope:bc_wounded_commander
			}
```

**`TYPE = event_toast_effect_bad`.** `TYPE` is a required parameter of
`bc_addressed_toast_effect` as of plan 1 task 4 and there is no default — an omitted one emits
the literal text `type = $TYPE$` and `validate` passes it.

**The `save_scope_as` is not optional.** `bc_addressed_toast_effect` writes
`left_icon = $SUBJECT$`, a scripted effect does not rebind ROOT, and its liege arm has already
changed scope by the time `left_icon` is evaluated — so `SUBJECT` must be a saved scope, never
`this`. Same reason plan 5's dead-knight block saves one.

**State first, presentation second.** The trait, the variable and the marker are all written
before the toast, following the rule `bc_knight_phase_events.txt:18-24` records from the first
live run: effects nested inside a `send_interface_toast` are not trustworthy for an AI
character, and most commanders in the world are AI.

**An AI commander's wound routes to his liege**, which is `bc_addressed_toast_effect`'s whole
job. That is not noise: `send_interface_toast` only renders for the player actually playing
the scoped character, so a wound in a war on the other side of the map reaches nobody.

- [x] **Step 3: Add the two localization keys**

Append to `localization/english/bc_l_english.yml`. **One leading space per line.**

```

# --- the flesh --------------------------------------------------------------

 bc_wounded_toast:0 "Carried From the Field"
 bc_wounded_toast_desc:0 "[bc_wounded_commander.GetName] was brought down in the thick of it and carried out. He will live. He will not sit a horse at the head of an army until he mends."
```

**The desc states the consequence in plain words**, because `disables_combat_leadership` has
no tooltip a player will find at the moment it starts mattering — they find it weeks later,
when they cannot assign him to an army.

**`[bc_wounded_commander.GetName]`, matching the mod's existing convention** — bare saved-scope
name, no `scope:` prefix, as in `[shieldbrother.GetFullName]` and `[owner.GetName]`.

- [x] **Step 4: Verify the key count**

```bash
cd /d/ck3/mods/battle_chronicles
grep -c "^ bc_\|^ rule_bc_\|^ setting_bc_" localization/english/bc_l_english.yml
head -c 8 localization/english/bc_l_english.yml | cat -A
grep -c "bc_wounded_commander" common/scripted_effects/bc_ledger_effects.txt
for k in bc_wounded_toast bc_wounded_toast_desc; do
  u=$(grep -c "= $k$" common/scripted_effects/bc_ledger_effects.txt)
  d=$(grep -c "^ $k:" localization/english/bc_l_english.yml)
  echo "$k use=$u def=$d"
done
```

Against the baseline recorded in task 1 step 1, the count must have risen by exactly **8** —
6 from task 1, 2 from here. The BOM must still be present (`M-oM-;M-?`); editors strip it
silently, which is why it is checked after the edits as well as before. The third must be
**2** — the `save_scope_as` and the `SUBJECT =`.

The loop must print `use=1 def=1` on both rows. **This is the only check in this plan that
pairs a toast key with its definition**, and it exists because step 5's `validate --strict`
cannot: the key is referenced, not defined, so `--strict` never looks at it.

**The `= $k$` anchor is what makes the two rows independent.** `bc_wounded_toast` is a
substring of `bc_wounded_toast_desc`, so an unanchored count would read **2** on the first
row and hide a missing `TITLE`. The `$` end-anchor works because both are written as
`TITLE = bc_wounded_toast` and `DESC = bc_wounded_toast_desc`, each alone on its line.

- [x] **Step 5: Validate and commit**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
```

Expected: exit 0, and nothing else. **There will be no WARN about `bc_wounded_toast` either
way.** `ck3lib/validate.py:182-185` checks top-level definition keys and only in the three
categories at `:37` — `common/traits`, `common/decisions`,
`common/character_interactions`. This key is *referenced* from a scripted effect, so the
check never looks at it, and its silence means nothing. Step 4's count is the gate.

That distinction matters more here than anywhere else in this plan: `wounded_1` carries
`flag = no_message`, so a missing key does not degrade the notification — it *is* the
notification, rendered as raw key text.

```bash
cd /d/ck3/mods/battle_chronicles
git add common/scripted_effects/bc_ledger_effects.txt localization/english/bc_l_english.yml
git commit -m "feat: tell a commander he was carried off the field

wounded_1 carries flag = no_message, so the trait arrives with no vanilla
notification at all - a commander would silently stop being able to lead armies
with nothing on screen to explain it. The desc states the consequence in words,
because disables_combat_leadership has no tooltip a player finds at the moment
it starts mattering."
```

---

### Task 4: Hang the wound off the decisive arm

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_ledger_effects.txt`

This is the task the whole plan is shaped around. Two edits, both in one file, both small.

- [x] **Step 1: Confirm `bc_record_effective_tier_effect` has exactly one call site**

```bash
cd /d/ck3/mods/battle_chronicles
grep -n "bc_record_effective_tier_effect" common/scripted_effects/bc_ledger_effects.txt | grep -v "#"
```

Expected: **exactly two lines** — the definition `bc_record_effective_tier_effect = {`, and the
one call inside `bc_record_moment_effect` reading
`bc_record_effective_tier_effect = { TIER = $TIER$ KIND = $KIND$ }`.

**The `grep -v "#"` is load-bearing.** Task 2's header comment carries the line
`# CALLED FROM THE DECISIVE ARM OF bc_record_effective_tier_effect, AND NOWHERE`. Unfiltered,
this check reports the correct file as three.

**If there is more than one call site, stop.** The whole design rests on the ceiling ladder
being reached through exactly one door, because that is what makes `$SWING$` guaranteed to be
in scope inside it.

- [x] **Step 2: Thread `SWING` through the seam**

In `bc_record_moment_effect`, change the one call line:

```
	bc_record_effective_tier_effect = { TIER = $TIER$ KIND = $KIND$ }
```

to:

```
	bc_record_effective_tier_effect = { TIER = $TIER$ KIND = $KIND$ SWING = $SWING$ }
```

**No call site of `bc_record_moment_effect` changes.** All eighteen already pass `SWING` — plan
1 declared the parameter for exactly this purpose and plan 2 gave it its first consumer. Step 4
proves it rather than assuming it.

**The other two arms of the ladder never read `$SWING$`, and that is fine.** CK3 substitutes
scripted-effect parameters textually; an unused one is simply not substituted anywhere. Plan 1
shipped `SWING` unused for a whole plan on exactly this basis.

- [x] **Step 3: Call the wound from the decisive arm**

In `bc_record_effective_tier_effect`, in the **first** arm — the one whose `limit` is
`flag:$TIER$ = flag:decisive` and `var:bc_battle_moments >= 5` — append after
`debug_log = "BC: moment decisive"`:

```
		# Family 3 hangs here and ONLY here. This arm IS the effective tier: it is
		# the point at which the ceiling has already been applied and the answer is
		# `decisive`. bc_wound_effect's header explains at length why the obvious
		# alternative - reading var:bc_battle_tier - is wrong.
		#
		# LAST IN THE ARM ON PURPOSE. Effects in a block run top to bottom, so
		# "BC: wound" can only ever be written AFTER the "BC: moment decisive" that
		# caused it. Task 6 reads the two counts as a ratio and that ordering is
		# what makes the pairing legible in a 500k-line log.
		bc_wound_effect = { SWING = $SWING$ }
```

The arm now reads:

```
	if = {
		limit = {
			flag:$TIER$ = flag:decisive
			var:bc_battle_moments >= 5
		}
		bc_write_style_effect = { RANK = 3 KIND = $KIND$ }
		debug_log = "BC: moment decisive"
		<the nine comment lines from the block above go here>
		bc_wound_effect = { SWING = $SWING$ }
	}
```

**The angle-bracket line is a placeholder for this plan's prose only — do not type it.** The
comment block from the previous code block goes there verbatim.

**Do not add the call to the `major` or `minor` arms, and do not add a fourth arm.** A wound is
the consequence of a decisive reverse; there is no "half a wound" and `wounded_1` is the only
rank this mod will ever grant.

**Do not move it above `bc_write_style_effect`.** The style write is the battle's name and must
happen whether or not a wound lands. Putting the wound first buries the more important write
under the rarer one for no gain.

- [x] **Step 4: Verify both edits landed and no call site was touched**

```bash
cd /d/ck3/mods/battle_chronicles
git status --short
grep -F 'SWING = $SWING$' common/scripted_effects/bc_ledger_effects.txt | grep -v "#" | wc -l
grep -n "bc_wound_effect" common/scripted_effects/bc_ledger_effects.txt | grep -v "#"
```

`git status --short` must show **exactly one modified file**,
`common/scripted_effects/bc_ledger_effects.txt`. Nothing under `events/` or
`common/combat_phase_events/` may appear. If it does, someone edited a call site — revert it;
the seam's signature has not changed.

The second must be **3 if plan 2 has landed, 2 if it has not**:

| line | added by | always present? |
|---|---|---|
| `bc_record_effective_tier_effect = { TIER = $TIER$ KIND = $KIND$ SWING = $SWING$ }` | step 2 above | yes |
| `bc_wound_effect = { SWING = $SWING$ }` | step 3 above | yes |
| `bc_apply_verb_effect = { KIND = $KIND$ SWING = $SWING$ }` | plan 2 task 6 | **only after plan 2** |

**This is the one check in the plan whose number depends on another plan**, which is why it
names both. Plan 6 is otherwise a direct successor to plan 1. Settle which of the two you are
looking at with `grep -c bc_apply_verb_effect` on the same file before reading anything into
the number.

**One short of whichever value applies, with `bc_wound_effect = { SWING = $SWING$ }` present,
means step 2 was skipped** and `$SWING$` never reaches the ladder — in which
case `bc_wound_effect`'s gate substitutes to the literal text `flag:$SWING$ = flag:down`, which
is an unknown key and a **silent no-op that `validate` passes**, and every decisive moment in a
large battle wounds its commander regardless of swing. This is the single worst failure this
plan can produce and this count is the only thing that catches it.

**`grep -F`, not plain `grep`.** In a basic regular expression the trailing `$` of `$SWING$` is
an end-of-line anchor, so the unescaped pattern matches the wrong set of lines. **And
`| grep -v "#" | wc -l` rather than `grep -c`**, because the pattern is call syntax and call
syntax is exactly what a header comment documents — the plan's own comments happen to write
`SWING = up|down` rather than `SWING = $SWING$` today, but that is a coincidence to not depend
on.

The third must be **exactly two lines** — the definition from task 2 and the call from step 3.

- [x] **Step 5: Validate and commit**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
```

Expected: exit 0.

```bash
cd /d/ck3/mods/battle_chronicles
git add common/scripted_effects/bc_ledger_effects.txt
git commit -m "feat: wound a commander on a decisive reverse

The wound hangs off the decisive arm of the tier ladder rather than reading
var:bc_battle_tier, which the spec suggested. bc_battle_tier is a high-water
mark - once any moment of a battle has been decisive it reads 3 for the rest of
it - so gating on it would let a minor moment wound a commander because a
decisive one fired six moments earlier. The arm is the effective tier by
construction and nothing new has to be stored.

SWING is threaded through the ladder to reach the gate. It has exactly one
consumer per hop and the seam's eighteen call sites are unchanged."
```

---

### Task 5: Static verification

**Files:** none — this task only reads.

Every check here is a filtered grep with a stated expected number, and every number was
counted against the tree rather than inferred from intent. Where a number depends on a
previous plan it says so.

- [x] **Step 1: Re-assert that a wound cannot reach a knight**

```bash
cd /d/ck3/mods/battle_chronicles
grep -n "bc_record_moment_effect\|bc_battle_open_effect" common/combat_phase_events/bc_knight_phase_events.txt
```

Expected: **6 hits, every one of them indented inside a `side_commander ?=` block.** This is
plan 1 task 11 step 4's command, verbatim, re-run for a reason: plan 6 is the first feature for
which a leak out of that block is actively harmful rather than merely untidy. `wounded_1`
carries `disables_combat_leadership = yes`, and one battle produces roughly 41 knight rolls.

Read the surrounding lines and confirm the indentation by eye. **Plan 6 changes nothing in this
file**, so any deviation from 6 is drift introduced by another plan and must be chased down
before this one ships.

- [x] **Step 2: `bc_battle_tier` is untouched by this plan**

```bash
cd /d/ck3/mods/battle_chronicles
grep -c "bc_battle_tier" common/scripted_effects/bc_ledger_effects.txt
grep -n "bc_battle_tier" common/scripted_effects/bc_ledger_effects.txt | grep -v "#" | wc -l
```

The **second** number must be **identical to the baseline recorded in task 2 step 1**. Not a
number this plan can predict in the abstract — plans 1 and 2 both write to this file — which is
exactly why it is recorded before the first edit and compared after the last.

**A rise means someone rewrote the gate against `var:bc_battle_tier`**, which is the one thing
`bc_wound_effect`'s header spends five lines forbidding. It is a plausible mistake: the spec
says to do it, the code reads naturally, and it produces a mod that wounds commanders on minor
moments with nothing at runtime reporting it.

The first, unfiltered number is printed only so the two can be compared: it will be much
larger, because task 2's header names the variable twice while explaining the trap.

**RUN CORRECTION — the measured numbers.** Baseline at task 2 step 1: filtered **5**,
unfiltered **8**. After the plan: filtered **5**, unchanged, which is the check. Unfiltered
rose to **11**, not the 10 the "names it twice" sentence implies — task 2's header names
`bc_battle_tier` three times and task 4 step 3's comment block names it once more. **The
unfiltered number is not a check and must never be turned into one**; it moves with every
comment anyone writes, which is precisely why the filtered one is the assertion.

- [x] **Step 3: Every seam call still carries `SWING`**

```bash
cd /d/ck3/mods/battle_chronicles
grep -rF "bc_record_moment_effect = {" common/ events/ | grep -v "#" | wc -l
grep -rF "bc_record_moment_effect = {" common/ events/ | grep -v "#" | grep -c "SWING ="
```

**The first must be exactly one MORE than the second**, and the extra is the effect's own
definition line, which does not pass a `SWING` to itself. The numbers are **19** and **18** —
plan 1's eighteen call sites plus the definition.

**Those two absolutes are stable across the whole expansion.** Plans 2 through 6 add no seam
call site: plan 2 wires the verb ladder *inside* the seam, plans 3 and 4 never mention it, and
plan 5's only reference to it is a comment explaining why the eve options bypass it. If either
number has moved, a seventh plan exists or someone added a call by hand — in which case check
the gap, not the absolutes.

**Equal, or a gap of two or more, both mean a call site is missing its `SWING`.** Such a site
substitutes to the literal `flag:$SWING$ = flag:down` inside the gate — an unknown key, a
silent no-op, and `validate` passes it.

- [x] **Step 4: `bc_battle_wounded` has exactly three roles**

```bash
cd /d/ck3/mods/battle_chronicles
grep -rn "bc_battle_wounded" common/ events/ | grep -v "#"
```

Expected: **exactly three lines**.

| line | where | added by |
|---|---|---|
| `remove_variable = bc_battle_wounded` | `bc_clear_scratch_effect` | plan 1 task 12 |
| `NOT = { exists = var:bc_battle_wounded }` | `bc_wound_effect`'s outer `limit` | task 2 |
| `set_variable = { name = bc_battle_wounded value = yes }` | `bc_wound_effect`'s inner `if` | task 2 |

**RUN CORRECTION — the first row is the bare form, not the braced one.** Plan 1 shipped
`remove_variable = bc_battle_wounded` at `bc_ledger_effects.txt:461`, and the whole clear list
is written that way. The plan wrote it braced. Cosmetic — the grep matches either — but a
reader checking the row against the file by eye would otherwise conclude the line was missing
and go add a second one, which is the exact failure the next paragraph warns about.

**Four lines means the variable was added to `bc_clear_scratch_effect` a second time.** Plan 1
put it there ahead of anything writing it, deliberately, and plan 6's preamble says not to add
it again — but the natural instinct on shipping a new variable is to go add it to the clear
list, and a duplicate `remove_variable` is harmless at runtime and therefore invisible.

**The `grep -v "#"` is load-bearing.** Plan 1's clear list carries a comment explaining why the
variable is listed although nothing writes it yet.

- [x] **Step 5: The toast caller sweep**

```bash
cd /d/ck3/mods/battle_chronicles
grep -rF "bc_addressed_toast_effect = {" common/ events/ | grep -v "#" | wc -l
grep -rF "TYPE = event_toast_effect_" common/ events/ | grep -v "#" | wc -l
```

**The first must be exactly one MORE than the second, not equal to it.** The extra is
`bc_addressed_toast_effect`'s own definition line, which does not pass a `TYPE` to itself.

**Both greps need the filter**, or the arithmetic is comparing a filtered set to an unfiltered
one. This plan adds one to each side, so whatever gap plans 1 through 5 left, it is unchanged.

`TYPE` has no default. An omitted one emits the literal text `type = $TYPE$` into the toast
block and `validate` passes it.

- [x] **Step 6: `wounded` is a real trait group and `max` is a real key**

```bash
grep -n "group = wounded" "D:/SteamLibrary/steamapps/workshop/content/1158310/2962333032/common/traits/00_traits.txt"
grep -n "change_trait_rank" /d/ck3/docs/api/1.19.0.6/effects.log
```

The first must show **exactly three** hits — `wounded_1`, `wounded_2` and `wounded_3` — at AGOT
`00_traits.txt:6346`, `:6385` and `:6424`. The second must show the signature
`{ trait = trait_group rank = change max = maximum new rank }` at `effects.log:3507`.

**Three, not one.** `wounded` is the name of the *group*, not of any trait — which is precisely
why `change_trait_rank` takes it and `rank = 1  max = 1` resolves to `wounded_1`. If this grep
returns one hit, AGOT has restructured the group and `max = 1` no longer means what task 2's
comment says it means.

**`validate` knows neither of these.** It checks brace balance, BOM, loc keys and descriptor
keys; it has no knowledge of trait names, effect keys or effect argument forms. A typo in
`trait = wounded` or `max = 1` produces a file that validates cleanly and does nothing, or
worse, does something unbounded.

**AGOT overrides vanilla's `00_traits.txt` wholesale**, so the AGOT path above is the one that
loads. Do not check the vanilla copy.

- [x] **Step 7: The full sweep**

```bash
cd /d/ck3/tools
python ck3.py validate --strict && python ck3.py index && python ck3.py conflicts
```

Expected: `validate` exit 0 with no WARN naming a `bc_` key; `conflicts` reporting **zero file
collisions**.

**`index` before `conflicts`, always.** `conflicts` reads a sqlite index that only `index`
rebuilds, so running it alone compares today's tree against yesterday's index and passes
vacuously. This plan creates no new filenames — every edit is to a file that already exists —
so the index is unlikely to have moved, but a vacuous pass is worth nothing either way and
`index` takes about two minutes.

```bash
cd /d/ck3/tools && python ck3.py deploy
```

- [x] **Step 8: Commit nothing**

This task writes no files. If `git status --short` is not empty, a check was "fixed" instead of
being reported. Read what changed and why before continuing.

---

### Task 6: The runtime run

**Files:** none permanently. Step 7 makes one temporary edit and step 9 proves it was reverted.

**A game restart costs about seven minutes. This run must answer every question below.** Read
the whole task before launching.

> **RUN RESULT (2026-08-14) — INCONCLUSIVE, AND THIS TASK STAYS OPEN.** The run was
> taken (batched with plan 5 task 11) and landed exactly on the first row of step 4's
> table: **`BC: moment decisive` at its shipped line fired 0 times**, so `BC: wound` was
> 0 for the only reason that carries no information. **Nothing about family 3 was
> tested.**
>
> Two traps this run walked into, recorded so the next one does not:
>
> 1. **Step 1 was not honoured.** `debug.log` was not cleared, so the sweep read a
>    cumulative log spanning several sessions. That is survivable for ratios but fatal
>    for this task, whose every question is an absolute count.
> 2. **The one `BC: moment decisive` in the log is from a PREVIOUS BUILD.** It is logged
>    at `bc_ledger_effects.txt:258`; the current build logs it at `:273`. Without the
>    line number it would have read as a decisive moment that failed to wound — the
>    opposite conclusion. **When a log spans builds, the file:line in a `probe` line is
>    the only thing that says which build wrote it.**
>
> The next attempt must clear the logs first, and must reach a battle of **5+ moments**
> with a losing swing — `decisive` needs `var:bc_battle_moments >= 5`, which is a long
> battle, and none occurred.

- [ ] **Step 1: Clear the logs, with the game NOT running**

```bash
cd "D:/Documents/Paradox Interactive/Crusader Kings III/logs" && rm -f debug.log error.log
```

**Every question in this task is a count**, and counts against a log carrying three previous
sessions are meaningless.

**If the game is open, Windows holds these files and the `rm` fails.** Close it from inside the
game. **Do not force-kill it** — that loses whatever save state the run was built on, and the
seven minutes it cost to get there.

- [ ] **Step 2: Launch and check the game-rule screen before loading anything**

```bash
cd /d/ck3/tools && python ck3.py launch
```

At the new-game screen, open the game rules and find the `Battle Chronicles:` entries. There
are **at least four** — `Frequency`, `Swing`, `Aftermath` and the new `Wounds` — and **five if
plan 4 has landed**, which adds `Rivalry`. Plan 6 is independent of plan 4, so the total is not
a number this plan can assert. **Check `Wounds` specifically; ignore the count.**

| what to see | what it means if wrong |
|---|---|
| an entry reading `Battle Chronicles: Wounds` | a raw `rule_bc_wounds` token means task 1's loc did not land |
| every other `Battle Chronicles:` entry still named in English | task 1 appended into the middle of another rule's key block |
| `Battle Chronicles: Wounds` has **two** options, `Off` and `Default` | raw `setting_bc_wounds_off` tokens mean the option keys are missing |
| `Default` is preselected | `default = bc_wounds_default` did not take |
| the rule's description names the two guarantees | this is the only place in the game a player can read them before the mod does it to them |

**Do this before loading a save.** It costs nothing, it is the only check for four of the eight
new localization keys, and `validate --strict` only catches a key that is entirely absent — not
one that is present with the wrong name.

- [ ] **Step 3: Play into a large battle and watch**

Load a save with an ongoing or imminent war and let a **large** battle run to its end. Gate 2
requires `var:bc_battle_size >= 3`, the top bucket.

Watch for a red toast titled **Carried From the Field**.

| what to see | why |
|---|---|
| the toast is **red**, not neutral or gold | `TYPE = event_toast_effect_bad` |
| the portrait is the **commander**, not a knight | `SUBJECT = scope:bc_wounded_commander` resolved |
| the name in the body is a real name | a literal `[bc_wounded_commander.GetName]` means the saved scope was lost |
| the wounded commander can no longer be assigned to lead an army | `disables_combat_leadership` |

**A wound is rare by design and you may well see none.** That is a valid outcome for this step,
not a failure; step 7 exists for exactly that case. Do not lower a gate before the unrelaxed
counts have been taken.

- [ ] **Step 4: Take the counts**

Exit the game, then:

```bash
cd /d/ck3/tools
python ck3.py probe "BC: moment decisive"
python ck3.py probe "BC: moment major"
python ck3.py probe "BC: moment minor"
python ck3.py probe "BC: wound"
```

`probe` exits 1 when nothing matches, so a `BC: wound` exit 1 is "no wound fired", not a
tooling failure.

| shape | reading |
|---|---|
| `BC: moment decisive` count is **0** | the run never produced a decisive moment. Nothing about family 3 was tested — the ladder needs `var:bc_battle_moments >= 5` **and** a call site requesting `decisive`, and only two sites request it. Play another battle before drawing any conclusion |
| decisive > 0, `BC: wound` **0** | expected on most runs. Gates 2, 3 and 4 rejected everything. Go to step 7 |
| `BC: wound` count **≤** decisive count, and every `BC: wound` line follows a `BC: moment decisive` | the pass shape. The ratio is the gate-rejection rate |
| `BC: wound` count **>** decisive count | impossible if the call sits where task 4 put it. Someone added a second call site. `grep -n "bc_wound_effect"` and remove it |
| `BC: wound` appears **twice in one battle** | gate 3 failed. `bc_battle_wounded` is either not being set or is being cleared mid-battle. Check `bc_clear_scratch_effect`'s trigger, not `bc_wound_effect` |

**Read the ratio, not the absolute counts.** `probe` globs every `*.log` in the log directory
and groups per line, so if a marker lands in more than one file every count is inflated by the
same factor and only the ratio survives. Every number in the table above is a comparison
between two markers for exactly that reason.

**The ratio measured here is the real one**, because no gate has been relaxed yet. Write it
down — it is the only number that tells anyone whether family 3 fires often enough to be a
feature or rarely enough to be a curiosity, and there is nothing to tune against until it
exists.

- [ ] **Step 5: Check for reads of missing variables**

```bash
cd /d/ck3/tools
python ck3.py probe "bc_battle_size"
python ck3.py probe "bc_battle_wounded"
```

Expected: **exit 1 for both.** Neither name is written to any log by design — this plan's only
`debug_log` is the fixed string `BC: wound`.

**Any match is a real finding.** The engine names the variable in its error line when script
reads one that does not exist, so a hit here is the nesting rule having been broken — most
likely `var:bc_battle_size >= 3` having been flattened into the outer `limit` alongside the
`exists`. Read the surrounding line before assuming otherwise.

- [ ] **Step 6: Check the on_action collision line**

```bash
cd /d/ck3/tools && python ck3.py probe "more than one 'effect' defined"
```

Expected: **exit 1**. Plan 6 adds no on_action and no `effect = { }` block, so this is a
regression check on the plans below it rather than a check on this one. It is here because it
costs nothing on a run that is already happening and because the failure it catches is silent
in-game — the engine keeps one `effect` block, decided by alphabetical filename order, and
logs only this line.

- [ ] **Step 7: Only if step 4 showed no wound — force one**

Skip this step entirely if step 3 showed the toast.

In `bc_wound_effect`, **temporarily** change the inner gate:

```
			limit = { var:bc_battle_size >= 3 }
```

to:

```
			limit = { var:bc_battle_size >= 1 }
```

**One lever, and only this one.** Do not touch `flag:$SWING$ = flag:down`, the `has_trait`
guard, `max = 1`, or the ladder's `>= 5`. Each of those is a correctness property; the size
gate is a tuning number, so relaxing it changes how often the code runs without changing what
it does when it runs.

```bash
cd /d/ck3/tools && python ck3.py deploy && python ck3.py launch
```

Play into any battle long enough to reach five moments and see the toast. Then re-run step 4's
counts.

**The ratio from this second run is NOT the production rejection rate** and must not be written
down as one. Gate 2 has been removed from it. Its only job is to prove the presentation half of
step 3's table — that the toast renders, is red, carries the commander, and resolves its name.

- [ ] **Step 8: Revert the lever**

```bash
cd /d/ck3/mods/battle_chronicles
git checkout -- common/scripted_effects/bc_ledger_effects.txt
git diff --exit-code common/scripted_effects/bc_ledger_effects.txt
git status --short
```

`git diff --exit-code` must exit **0** and `git status --short` must print **nothing**.

**`git checkout -- <one file>` is safe here and only here**, because task 4 step 5 committed
that file and step 7 is the only uncommitted change in the tree. If `git status --short` shows
anything else before you run it, stop and read it — that is someone else's work and this
command would destroy it.

```bash
cd /d/ck3/tools && python ck3.py deploy
```

**Re-deploy after reverting.** The deployed copy still carries `>= 1` until this runs, and a
mod that wounds commanders in skirmishes is exactly the outcome the plan's own game-rule
description promises it will not produce.

- [ ] **Step 9: Record the numbers**

`README.md` already has a run-log convention: `## First live run (2026-08-12)`,
`## Calibration run, 2026-08-13 (39 combat ends, both sides logged)`,
`## Confirmation run, 2026-08-13 (Generous, 5 combat ends)`. Add one more in the same shape,
headed with the date and the number of combat ends, holding the four counts from step 4 —
decisive, major, minor, wound — and the derived ratio.

**Then edit `## Not yet verified in game`.** If the toast was seen, say so and do not add a
line. If step 3 showed no wound and step 7 was needed, add a line saying the wound *rate* is
still unmeasured in production conditions and that `"BC: wound"` is a permanent marker, so
`probe 'BC:'` will report it the first time it happens unassisted — the same wording that
section already uses for the nickname award.

**That section is the plan's real handoff.** Two of the three existing runs recorded in this
file exist because someone read it and went and settled what it listed.

**This is the plan's deliverable as much as the code is.** Six plans have now shipped and
nothing yet has recorded how often family 3 actually fires. The next person to ask "should the
size gate be 2?" has no way to answer it except by re-running this task, and a restart costs
seven minutes.

```bash
cd /d/ck3/mods/battle_chronicles
git add README.md
git commit -m "docs: record the family 3 firing rate from the first live run

The decisive:wound ratio is the gate-rejection rate and is the only number that
says whether wounds are a feature or a curiosity. Taken from an unrelaxed run;
the forced run in step 7 measures presentation only and its ratio is not
comparable."
```

---

## What this plan deliberately does not do

| not done | why |
|---|---|
| a second wound rank | "wounds yes, death never" is a locked decision, and a mod-created `wounded_2` puts a commander one vanilla wound from `wounded_3`, the doorway to every lethal path in `20_health_effects.txt` |
| a recovery event, duration or timed removal | vanilla's `wounded_recovery_pulse` already fires four times a year off `yearly_health_pulse` and triggers on the trait group. Anything written here would race it and produce two recoveries for one wound |
| wounds for knights | `disables_combat_leadership` on a courtier is invisible and pointless, and one battle produces roughly 41 knight rolls. The commander-only guarantee is structural, inherited from plan 1 |
| a `high`/`low` frequency rule | there is nothing to tune the middle rung against until task 6 has produced a firing rate at least once. Add it in a later plan, with the number in hand |
| an aftermath event about the wound | the toast is the whole presentation. An event would need a scope the seam does not hold and a pop-up for something the player did not choose |
| a wound for the winning side | `SWING = down` is gate 1b. A commander does not get carried off for winning |