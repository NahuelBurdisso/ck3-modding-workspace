# Battle Chronicles Expansion — Plan 4: The Man Across the Field (C)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A commander who loses a notable battle to the same man twice starts to hate him,
by name and in CK3's own relation graph. Beating him back takes as many wins as the losses
cost.

**Architecture:** One running grudge per commander, held in two ledger variables —
`bc_nemesis` (who) and `bc_nemesis_losses` (how badly). A notable loss to the man in
`bc_battle_foe` creates or escalates it; a notable win against him decrements it; reaching
zero removes the relation and both variables. A rung ladder maps the counter to `grudge` /
`rival` / `nemesis`, clamped by a new game rule. All three relations already exist in
vanilla.

**Tech Stack:** CK3 script (Paradox clausewitz script), targeting CK3 1.19.0.6 under the
AGOT playset. Workspace CLI is `python ck3.py` run from `D:/ck3/tools`.

**Spec:** `D:/ck3/docs/specs/2026-08-13-battle-chronicles-expansion-design.md`, Section 4.

**Depends on:**
- Plan 1 complete — this plan writes into `events/bc_aftermath_events.txt` and
  `bc_battle_open_effect`, and reads `bc_battle_foe`, all of which plan 1 creates.
- **Nothing else.** `bc_battle_foe` has been written by `bc_battle_open_effect` since plan
  1 and read by nobody. This plan is its first consumer.
- Plans 2 and 3 are **not** dependencies and this plan does not touch their files. It can
  ship before, after, or between them.

**Not gated on any DIAG question.** Q1 through Q4 all concern other sub-projects. C reads
nothing the DIAG run measured.

---

## Read this before task 1

Plan 1's entire "Read this before task 1" applies unchanged — the verification loop, the
`validate`-is-syntax-only rule, the cleared-log rule, the mod-is-its-own-git-repo rule, the
sweep pass condition (row 3 is a rule: any line beginning `BC: `), and the non-negotiables.
**Read it first.** What follows is only what is new in plan 4.

### The spec's removal ladder is written against an unshipped form. Do not copy it.

Section 4 writes the removal ladder as `remove_relation_nemesis = var:bc_nemesis` and states
"No scope save is needed." **That claim is not supported and this plan overrides it.**

Measured, this session, across the whole of vanilla `game/common` + `game/events` and the
whole of AGOT:

| form | shipped uses |
|---|---|
| `has_relation_X = var:Y` | **yes** — `bp1_yearly_james.txt:1160-1161`, `00_agot_mega_wars_script_values.txt:1424,1430` |
| `set_relation_X = var:Y` | **zero** |
| `remove_relation_X = var:Y` | **zero** |

Every shipped `set_relation_*` / `remove_relation_*` call targets a **saved scope**, `root`,
or a `$PARAM$`. The spec's citation of `bp1_yearly_james.txt` establishes the `var:` form for
the **trigger** only, which is the half that is genuinely shipped.

`validate` cannot tell the difference — it has no knowledge of effect keys or target forms —
so a `var:` target that the engine declines would be a **silent no-op that this plan's
static checks would pass**. **Every effect in this plan therefore saves `var:bc_nemesis`
into `scope:bc_rivalry_foe` and targets that.** One extra line per effect, and it removes
the only unproven form in C.

**It also makes the spec's ordering warning moot.** Section 4 warns that the two
`remove_variable` lines must come after the ladder because "the ladder reads the variable it
is about to delete". With a saved scope the ladder no longer reads the variable at all. Keep
the ordering anyway — it costs nothing and the next person to read it will expect it — but
do not present it as load-bearing, because it is not.

### The step size *N* is a script value, and it is deliberately inert until plan 5

Section 4 defines *N* as 1 for an ordinary notable battle and 2 when `scope:wipe` holds.
`scope:wipe` is Section 5's, and plan 5 is not written. **Write the script value now anyway**
— `exists = scope:wipe` on a scope nothing ever saves is a clean `no`, not an error, exactly
as `exists` on a missing variable is safe. Until plan 5 lands, `bc_rivalry_step_value` is
always 1 and C behaves as the spec's ordinary case.

The alternative — hardcoding 1 now and threading a parameter through five effects later — is
how Section 4's own note says an earlier draft broke: it hardcoded the create branch to 1
and quietly made "a wipe takes a stranger straight to `rival`" false. **One value, read in
all four arithmetic sites, is the whole point.** Do not inline the 1.

### Four new permanent variables? No — two.

| variable | holds | lives on | lifetime |
|---|---|---|---|
| `bc_nemesis` | the character he is carrying a grudge against | commander | **ledger** — cleared only by reaching 0 or by the dead-foe wipe |
| `bc_nemesis_losses` | how many losses are owed | commander | **ledger**, same |

`bc_battle_foe` already exists and is **scratch** — `bc_clear_scratch_effect` clears it at
combat end, which is why C must run before that. One new scope, `bc_rivalry_foe`, saved and
used inside single effect calls.

**`bc_clear_scratch_effect` must never learn about `bc_nemesis` or `bc_nemesis_losses`.**
They are the feature.

### New markers

All begin `BC: `, so plan 1's sweep row 3 covers them.

| marker | meaning |
|---|---|
| `BC: nemesis new` | a first loss created a running grudge |
| `BC: nemesis escalate` | another loss to the same man |
| `BC: nemesis held` | lost to someone else while a grudge was already running — nothing happened, by design |
| `BC: nemesis rung grudge` / `rival` / `nemesis` | which relation was set |
| `BC: nemesis rule off` | the counter moved but `bc_rivalry_off` suppressed the relation |
| `BC: nemesis decrement` | a win reduced the counter without clearing it |
| `BC: nemesis cleared` | the counter hit 0; relation and both variables gone |
| `BC: nemesis wipe` | the dead-foe housekeeping in `bc_battle_open_effect` fired |

---

## File structure

| path | plan action | responsibility |
|---|---|---|
| `common/game_rules/bc_game_rules.txt` | modify (task 1) | the `bc_rivalry` rung cap |
| `common/script_values/bc_script_values.txt` | modify (task 2) | `bc_rivalry_step_value` |
| `common/scripted_effects/bc_rivalry_effects.txt` | **create** (task 3) | all of C's effects |
| `common/scripted_triggers/bc_scripted_triggers.txt` | modify (task 9) | `bc_facing_nemesis_trigger` |
| `common/scripted_effects/bc_scripted_effects.txt` | modify (task 8) | the dead-foe wipe in `bc_battle_open_effect` |
| `events/bc_aftermath_events.txt` | modify (task 7) | both graders call C |
| `common/combat_phase_events/bc_commander_phase_events.txt` | modify (task 9) | the read-back |
| `localization/english/bc_l_english.yml` | modify (tasks 1, 6) | 15 keys total |

**C gets its own effects file.** `bc_scripted_effects.txt` already carries the seam, the
nickname and the cleanup; C is five effects with one shared invariant, and mixing them in
would put the relation ladder a hundred lines from the counter that drives it. This mirrors
plan 3's `bc_reputation_effects.txt`.

**`bc_facing_nemesis_trigger` does go in the shared triggers file**, unlike plan 3, because
it has two call sites in two different files and is the one thing in C that later plans are
expected to reuse.

---

### Task 1: The game rule and its localization

**Files:**
- Modify: `mods/battle_chronicles/common/game_rules/bc_game_rules.txt`
- Modify: `mods/battle_chronicles/localization/english/bc_l_english.yml`

- [ ] **Step 1: Read the existing rules and the loc convention**

```bash
cd /d/ck3/mods/battle_chronicles
cat common/game_rules/bc_game_rules.txt
grep -n "rule_bc_\|setting_bc_" localization/english/bc_l_english.yml
grep -c "^ bc_\|^ rule_bc_\|^ setting_bc_" localization/english/bc_l_english.yml
```

Three rules ship today — `bc_frequency`, `bc_swing`, `bc_aftermath` — each with
`categories = { flavor }`, a `default =`, and three empty-brace options.

**Four if plan 6 has landed**, which adds `bc_wounds` with **two** options rather than three.
Plan 6 is declared independent of this plan, so the order they land in is not fixed. Nothing
in this task depends on the number; read the file and append after whatever is last.

The loc convention is **two keys per rule plus two per option** — `rule_<key>`,
`rule_<key>_desc`, then `setting_<option>` and `setting_<option>_desc` for each. A
three-option rule is therefore **eight** keys, which is what the three shipped rules have:
24 lines for 3 rules. **Not "four per rule".**

**Write the key count down.** Task 6 step 4 checks the total rose by exactly 15 across both
localization tasks, and that is not a check you can run without the number from before.

- [ ] **Step 2: Append the rule**

Append to `common/game_rules/bc_game_rules.txt`, after `bc_aftermath`:

```
# The rung cap, not an on/off switch for the counter.
#
# AGOT hangs murder schemes off `nemesis`. A mod that silently manufactures
# nemeses is changing far more than battles, so the top rung is opt-in and the
# default stops at `rival`.
#
# THE CAP CLAMPS THE RUNG, IT DOES NOT SKIP THE AWARD. The rule test sits inside
# the TOP arm's limit in bc_rivalry_set_relation_effect, so under bc_rivalry_rival
# a counter of 5 fails that arm, falls through to `>= 2`, and sets `rival` - not
# nothing. Putting the rule test in an outer gate instead would make a man who
# beat you five times LESS hated than one who beat you twice.
#
# bc_rivalry_off SUPPRESSES THE RELATION ONLY. bc_nemesis, bc_nemesis_losses and
# bc_facing_nemesis_trigger all keep working, so a player who turns it off still
# gets the narrative - the man who has beaten you twice - without the mod touching
# CK3's relation graph or AGOT's murder schemes. Suppressing the counter too would
# make the off switch delete the feature rather than its side effects, and would
# leave bc_rivalry_clear_effect with nothing to remove.
#
# THE COUNTER IS NEVER CAPPED. It keeps climbing past the cap, so lowering this
# design's own thresholds in a later version is not a data migration. Raising the
# RULE mid-campaign is impossible anyway - game rules are baked into a save.
bc_rivalry = {
	categories = { flavor }

	default = bc_rivalry_rival

	bc_rivalry_off = {}
	bc_rivalry_rival = {}
	bc_rivalry_nemesis = {}
}
```

**Three options, not four.** There is no `bc_rivalry_grudge` cap: `grudge` is the bottom
rung and is what a single loss produces under every setting that is not `off`, so a cap at
`grudge` and a cap at `off` would differ only in whether a one-directional -60 opinion is
applied. Not worth a setting.

- [ ] **Step 3: Add the eight localization keys**

Append to the game-rules block of `localization/english/bc_l_english.yml`, **after the last
existing `setting_bc_` line**. **One leading space per line**, matching the file:

**"After the last `setting_bc_` line", not "after `setting_bc_aftermath_generous_desc`."**
Plan 6 task 1 also adds a rule and also appends to this block, and the two plans are declared
independent of each other — anchoring on a specific rule's last key would interleave them.

```
 rule_bc_rivalry:0 "Battle Chronicles: Rivalry"
 rule_bc_rivalry_desc:0 "Whether losing a notable battle to the same commander twice makes an enemy of him. The mod tracks the man regardless; this decides how far the grudge is allowed to go."
 setting_bc_rivalry_off:0 "Off"
 setting_bc_rivalry_off_desc:0 "No relations are set. Battles still remember who beat you, and the field still reads differently when you meet him again, but CK3's relation graph is left alone — and so are the schemes A Game of Thrones hangs off it."
 setting_bc_rivalry_rival:0 "Rival"
 setting_bc_rivalry_rival_desc:0 "A first loss is a grudge; a second makes him a rival. It stops there however many times he beats you."
 setting_bc_rivalry_nemesis:0 "Nemesis"
 setting_bc_rivalry_nemesis_desc:0 "The full ladder. Three losses to one man makes him a nemesis — which in A Game of Thrones is a man you may find yourself planning to kill."
```

- [ ] **Step 4: Validate and commit**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
```

Expected: exit 0.

**`validate` proves only brace balance and BOM here. It does not know what a game rule is.**
`grep -n "game_rule\|setting_\|rule_" ck3.py` returns nothing — the tool has no game-rule
awareness at all, so it cannot tell you that `bc_rivalry_off` needs a `setting_bc_rivalry_off`
key. A rule whose options have no `setting_` keys renders as raw tokens in the game-rule screen
and validates perfectly.

Check it statically instead, scoped to this rule:

```bash
cd /d/ck3/mods/battle_chronicles
grep -n "^ rule_bc_rivalry" localization/english/bc_l_english.yml
grep -n "^ setting_bc_rivalry" localization/english/bc_l_english.yml
grep -n "bc_rivalry" common/game_rules/bc_game_rules.txt
```

Expected **2**, then **6**, then **5** lines — the rule name and its `_desc`; three options
times name and `_desc`; and in the rules file the rule, its `default =`, and the three option
blocks. Every option token in the third must appear in the second.

**Scoped to `bc_rivalry`, and `^ `-anchored.** A total over all rules would be wrong the moment
plan 6 lands, and the leading-space anchor is what counts key definitions rather than any
mention of the name in a `_desc` body.

The rule only truly renders correctly when someone opens the game-rule screen. Plan 6 task 6
step 2 does that; if plan 6 is not being run, do it once by hand.

```bash
cd /d/ck3/mods/battle_chronicles
git add common/game_rules/bc_game_rules.txt localization/english/bc_l_english.yml
git commit -m "feat: add the bc_rivalry rung cap game rule

Defaults to rival rather than nemesis because AGOT hangs murder schemes off
nemesis, and a mod that silently manufactures nemeses is changing far more than
battles. The off setting suppresses the relation only - the counter and the
read-back keep working."
```

---

### Task 2: The step size

**Files:**
- Modify: `mods/battle_chronicles/common/script_values/bc_script_values.txt`

- [ ] **Step 1: Read the file's existing conventions**

```bash
cd /d/ck3/mods/battle_chronicles && cat common/script_values/bc_script_values.txt
```

Note the comment at `:15-16` recording that the engine scales `side_strength` down by 1000 —
that is the kind of measured note this file carries. Match the style.

- [ ] **Step 2: Append the value**

```
# --- rivalry step size ------------------------------------------------------
#
# ONE STEP SIZE, USED IN ALL FOUR ARITHMETIC SITES: the create branch, the
# escalate branch, the floor guard, and the decrement. Section 4 of the design
# records that an earlier draft hardcoded the create branch to 1, which quietly
# made "a wipe takes a stranger straight to rival" false and made the design's own
# worked example unreachable. Do not inline the 1 anywhere.
#
# scope:wipe IS SECTION 5's AND IS NOT SAVED BY ANYTHING YET. Until plan 5 lands
# this value is always 1. `exists` on a scope nothing ever saves is a clean `no`,
# not an error - the same rule that makes `exists` on a missing variable safe -
# so this is inert rather than broken, and plan 5 turns it on by saving the scope
# and changing nothing here.
bc_rivalry_step_value = {
	if = {
		limit = { exists = scope:wipe }
		value = 2
	}
	else = {
		value = 1
	}
}
```

**The bare `value = X` inside each branch with no base value outside is shipped vanilla** —
`swing_scales_discounts_multiplier_value`, `00_diarchy_values.txt:3224-3237`, is a full
if/else_if/else of exactly this shape. This is the same precedent plan 2's
`bc_chronicle_flag_days_value` rests on.

- [ ] **Step 3: Validate and commit**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
```

Expected: exit 0.

```bash
cd /d/ck3/mods/battle_chronicles
git add common/script_values/bc_script_values.txt
git commit -m "feat: add bc_rivalry_step_value

One step size read by all four of C's arithmetic sites. Inert at 1 until plan 5
saves scope:wipe, which is deliberate - threading a parameter through five
effects later is how the design's own earlier draft broke the create branch."
```

---

### Task 3: The file header and the rung ladder

**Files:**
- Create: `mods/battle_chronicles/common/scripted_effects/bc_rivalry_effects.txt`

- [ ] **Step 1: Confirm the markers do not exist**

```bash
cd /d/ck3/tools && python ck3.py probe "BC: nemesis"
```

Expected: **exit 1** — `probe` exits 1 when nothing matches. A match here means a previous
attempt left code behind; find it before continuing.

- [ ] **Step 2: Write the header and the rung ladder**

Create the file. **UTF-8, no BOM** — script files in this mod carry no BOM; only the
localization file does.

```
# Battle Chronicles - the man across the field.
#
# ONE RUNNING GRUDGE PER COMMANDER, held in two LEDGER variables:
#
#   bc_nemesis         character   who he is carrying it against
#   bc_nemesis_losses  integer     how many losses are owed
#
# bc_clear_scratch_effect must NEVER learn about either. They are the feature.
# bc_battle_foe, which C reads, IS scratch and is cleared at combat end - which is
# why C must run before bc_clear_scratch_effect in both graders.
#
# EVERYTHING HERE IS CALLED ON THE COMMANDER, from inside `side_commander ?= { }`
# in the graders, inside their `is_alive = yes` gate.
#
# EVERY RELATION EFFECT TARGETS scope:bc_rivalry_foe, NEVER var:bc_nemesis.
# Measured across all of vanilla common/ + events/ and all of AGOT:
# `has_relation_X = var:Y` is shipped (bp1_yearly_james.txt:1160-1161,
# 00_agot_mega_wars_script_values.txt:1424,1430) but `set_relation_X = var:Y` and
# `remove_relation_X = var:Y` have ZERO shipped uses - every call targets a saved
# scope, root, or a $PARAM$. The design document says no scope save is needed;
# that is unsupported and this file overrides it. validate has no knowledge of
# effect target forms, so a target the engine declines would be a SILENT NO-OP
# that every static check in this plan would pass.
#
# ALL THREE RELATIONS ALREADY EXIST IN VANILLA, at
# 00_scripted_relations.txt:43 (grudge), :54 (rival), :70 (nemesis). AGOT ships
# 00_agot_scripted_relations.txt ALONGSIDE rather than overriding, so these are
# vanilla definitions and they load unchanged. This file defines no relations.

# --- the rung ladder --------------------------------------------------------
#
# CALLED ON THE COMMANDER, with bc_nemesis and bc_nemesis_losses BOTH known to
# exist and bc_nemesis known to be ALIVE. Both callers write the counter
# immediately before calling, and the entry point proved the foe alive.
#
# THRESHOLDS, NOT EXACT VALUES, in DESCENDING order. Section 5's wipe rule
# increments by 2, so the counter SKIPS values and an exact-match table would
# leave 4 with no row. Descending order means the first arm that matches wins and
# there is no unreachable value above the top rung.
#
# THE CAP CLAMPS, IT DOES NOT SKIP. has_game_rule = bc_rivalry_nemesis sits in the
# TOP arm's limit only. Under bc_rivalry_rival a counter of 5 fails the top arm,
# falls to `>= 2`, and sets rival - which is the whole point. Putting the rule
# test in an outer gate instead would make a five-loss foe set NOTHING.
#
# NO EXPLICIT TEARDOWN ON THE WAY UP. rival's `opposites` list contains grudge
# (00_scripted_relations.txt:56) and nemesis's contains both rival and grudge
# (:72-73), so the ENGINE removes the lower rung when a higher one is set.
# Escalation is purely set_relation_*.
#
# THE TOP TWO RUNGS ARE MUTUAL, THE BOTTOM ONE IS NOT. rival carries
# `corresponding = rival` (:64) and nemesis `corresponding = nemesis` (:82);
# grudge carries neither. So a first loss puts a one-directional -60 on the loser
# only, while a second makes the WINNER a rival of the loser too, at -60 both
# ways, and a third makes it -120 both ways. That is intended - the man who keeps
# beating you notices you back - but it means C reaches into the opinion of a
# character it never ran on, which is the real reason bc_rivalry defaults to
# `rival` rather than `nemesis`.
#
# IT ALSO MAKES THE CLEAR SYMMETRIC. remove_relation_rival/_nemesis take the
# corresponding side with them, so a commander who beats his rival back to zero
# is not left as the target of a relation he can no longer see.
#
# set_relation_X = { target = ... reason = ... } is the shipped form -
# effects.log:9770 (grudge), :9810 (nemesis), :9860 (rival), all character scope.
# The reason keys are free-form loc keys; vanilla names them things like
# `nemesis_danelaw_rejection`.
bc_rivalry_set_relation_effect = {
	if = {
		limit = { has_game_rule = bc_rivalry_off }
		debug_log = "BC: nemesis rule off"
	}
	else = {
		var:bc_nemesis = { save_scope_as = bc_rivalry_foe }
		if = {
			limit = {
				var:bc_nemesis_losses >= 3
				has_game_rule = bc_rivalry_nemesis
			}
			set_relation_nemesis = {
				target = scope:bc_rivalry_foe
				reason = bc_reason_battle_nemesis
			}
			debug_log = "BC: nemesis rung nemesis"
		}
		else_if = {
			limit = { var:bc_nemesis_losses >= 2 }
			set_relation_rival = {
				target = scope:bc_rivalry_foe
				reason = bc_reason_battle_rival
			}
			debug_log = "BC: nemesis rung rival"
		}
		else = {
			set_relation_grudge = {
				target = scope:bc_rivalry_foe
				reason = bc_reason_battle_grudge
			}
			debug_log = "BC: nemesis rung grudge"
		}
	}
}
```

**`var:bc_nemesis_losses >= 3` and `has_game_rule = bc_rivalry_nemesis` are siblings and
that is safe**, because the counter is proven to exist by the caller — not because of
evaluation order. CK3 does not short-circuit and guarantees no order among siblings; the
safety here comes from the invariant, and the header states it. **If you ever call this
effect from a site that has not just written `bc_nemesis_losses`, this breaks silently.**

- [ ] **Step 3: Validate and commit**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
```

Expected: exit 0. **`validate` will not warn about the three `bc_reason_battle_*` keys** —
it has no knowledge of the `reason =` field, so those are checked by eye in task 6, not here.

```bash
cd /d/ck3/mods/battle_chronicles
git add common/scripted_effects/bc_rivalry_effects.txt
git commit -m "feat: add the rivalry rung ladder

Descending thresholds rather than exact values, because Section 5's wipe rule
increments by 2 and an exact table would leave 4 with no row. The rule test sits
in the top arm's limit so the cap clamps the rung instead of skipping the award."
```

---

### Task 4: Escalation on a loss

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_rivalry_effects.txt`

- [ ] **Step 1: Write the escalation**

```
# --- escalation -------------------------------------------------------------
#
# CALLED ON THE COMMANDER on a NOTABLE LOSS, with bc_battle_foe known to exist
# and known ALIVE - the entry point proved both.
#
# NEVER OVERWRITE AN EXISTING bc_nemesis. One running grudge per commander; a
# second rival dilutes the first into noise. That is what the `else` is for, and
# it is why it logs rather than doing nothing quietly.
#
# THE CREATE BRANCH USES THE STEP VALUE, NOT 1. A first loss that is a wipe
# writes 2 and takes a stranger straight to `rival`. Section 4 records that an
# earlier draft hardcoded this branch to 1 and quietly made that sentence false.
#
# `var:bc_nemesis = var:bc_battle_foe` is safe in the else_if because the first
# arm already tested `NOT = { exists = var:bc_nemesis }` and else_if arms ARE
# ordered with respect to each other. It is only siblings WITHIN one trigger block
# that have no guaranteed order.
bc_rivalry_loss_effect = {
	if = {
		limit = { NOT = { exists = var:bc_nemesis } }
		set_variable = { name = bc_nemesis value = var:bc_battle_foe }
		set_variable = { name = bc_nemesis_losses value = bc_rivalry_step_value }
		bc_rivalry_set_relation_effect = yes
		bc_rivalry_toast_effect = yes
		debug_log = "BC: nemesis new"
	}
	else_if = {
		limit = { var:bc_nemesis = var:bc_battle_foe }
		change_variable = { name = bc_nemesis_losses add = bc_rivalry_step_value }
		bc_rivalry_set_relation_effect = yes
		bc_rivalry_toast_effect = yes
		debug_log = "BC: nemesis escalate"
	}
	else = {
		debug_log = "BC: nemesis held"
	}
}
```

**`set_variable value = <script value>` and `change_variable add = <script value>` are both
shipped** — `07_dlc_ep3_scripted_effects.txt` and `00_activity_hunt_effects.txt` use both
forms against named `_value` script values. Verified this session across vanilla
`game/common`.

`bc_rivalry_toast_effect` is written in task 6. **This file will not validate cleanly as a
unit until then** — but `validate` is syntax-only and does not resolve effect names, so it
will still exit 0. That is not evidence the call works; task 10 step 2 is.

- [ ] **Step 2: Validate and commit**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
```

Expected: exit 0.

```bash
cd /d/ck3/mods/battle_chronicles
git add common/scripted_effects/bc_rivalry_effects.txt
git commit -m "feat: add rivalry escalation on a notable loss

The create branch takes the step value rather than a literal 1, so a first loss
that is also a wipe goes straight to rival once plan 5 saves scope:wipe. Losing
to a different man while a grudge is running does nothing - one running grudge
per commander."
```

---

### Task 5: The decrement and the clear

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_rivalry_effects.txt`

- [ ] **Step 1: Understand why the floor guard cannot be a constant**

This is the sharpest thing in plan 4 and it is worth reading twice.

```
if = {
	limit = { var:bc_nemesis_losses <= bc_rivalry_step_value }
	set_variable = { name = bc_nemesis_losses value = 0 }
}
else = {
	change_variable = { name = bc_nemesis_losses subtract = bc_rivalry_step_value }
}
```

**The guard must be `<= <the same step value>`, not a constant.** Both constants fail, in
opposite directions:

| written | failure |
|---|---|
| `<= 2` | over-fires. An ordinary win (*N* = 1) against a two-loss foe zeroes the counter and runs the whole removal ladder — erasing a `rival` after a single win when the counter says two are owed |
| `<= 1` | under-fires. A wipe win (*N* = 2) against a one-loss foe produces **−1**, after which a literal `= 0` test never fires again and the rivalry slot jams permanently on a negative counter |

Only `<= N` is right in both directions, and it stays right for any future step size.

**The clear condition is written `<= 0` regardless**, belt and braces, so that a negative
counter arriving by any route this plan did not foresee still clears instead of jamming.

- [ ] **Step 2: Write the decrement**

```
# --- decrement --------------------------------------------------------------
#
# CALLED ON THE COMMANDER on a NOTABLE WIN, and ONLY when the entry point has
# proved that bc_nemesis exists, is alive, and IS bc_battle_foe. Beating anyone
# else does nothing.
#
# THE FLOOR GUARD IS `<= bc_rivalry_step_value`, NOT A CONSTANT. See step 1 - both
# constants fail, in opposite directions, and `<= 2` is the one that silently
# erases a rival after a single win.
#
# NOT clamp_variable. It exists (effects.log:223-227) but has ZERO uses in
# vanilla, and it takes `max` as well as `min`, so it would need an invented
# ceiling. change_variable's `min` operation (:198-203) is likewise unexercised
# here and its semantics - floor, versus "take the smaller of the two" - are not
# stated in the dump. The explicit branch is longer and is the only one whose
# behaviour is certain.
#
# THE RUNG LADDER IS NOT RE-RUN ON THE WAY DOWN. Relations escalate only, never
# downgrade: a decrement that lands above 0 changes the counter and nothing else.
# An ordinary win against a two-loss rival leaves him a rival with the counter at
# 1; a second win takes it to 0 and removes the relation outright. So a rival
# costs two wins to be rid of. Re-running the ladder would demote him to `grudge`
# in between, which removes a relation the player never asked to remove.
bc_rivalry_win_effect = {
	if = {
		limit = { var:bc_nemesis_losses <= bc_rivalry_step_value }
		set_variable = { name = bc_nemesis_losses value = 0 }
	}
	else = {
		change_variable = { name = bc_nemesis_losses subtract = bc_rivalry_step_value }
	}

	if = {
		limit = { var:bc_nemesis_losses <= 0 }
		bc_rivalry_clear_effect = yes
	}
	else = {
		debug_log = "BC: nemesis decrement"
	}
}
```

**`subtract = <script value>` is shipped** — `chariot_race_base_cost_value` and three
`_static_max` values are used exactly this way in vanilla. Verified this session.

- [ ] **Step 3: Write the clear**

```
# --- the clear --------------------------------------------------------------
#
# CALLED ON THE COMMANDER with bc_nemesis known to exist and known alive.
#
# REMOVAL ORDER IS LOAD-BEARING: test nemesis FIRST and rival LAST. `nemesis`
# carries `relation_aliases = { rival }` (00_scripted_relations.txt:81), so
# has_relation_rival is TRUE FOR A NEMESIS. Testing rival first would fire
# remove_relation_rival on a man whose actual relation is nemesis, leaving the
# nemesis relation in place with its variables gone - unremovable, because the
# counter that would find him again has just been deleted.
#
# EXACTLY ONE OF THE THREE IS EVER HELD, and the ENGINE guarantees it rather than
# this mod: rival's `opposites` contains grudge (:56) and nemesis's contains both
# rival and grudge (:72-73), so setting a higher rung removed the lower one.
#
# THE TWO remove_variable LINES COME LAST. With the saved scope they no longer
# HAVE to - the ladder reads scope:bc_rivalry_foe, not the variable - but the
# order is what the next reader will expect, and reverting to a var: target later
# would make it load-bearing again without anyone noticing.
#
# NOTHING HERE IS GATED ON bc_rivalry_off. The off switch suppresses SETTING a
# relation; if a player turns it off mid-campaign, relations already set must
# still be removable when their counter reaches zero. has_relation_* on a man who
# has none is a clean `no`, so running the ladder costs nothing.
bc_rivalry_clear_effect = {
	var:bc_nemesis = { save_scope_as = bc_rivalry_foe }
	if = {
		limit = { has_relation_nemesis = scope:bc_rivalry_foe }
		remove_relation_nemesis = scope:bc_rivalry_foe
	}
	else_if = {
		limit = { has_relation_rival = scope:bc_rivalry_foe }
		remove_relation_rival = scope:bc_rivalry_foe
	}
	else_if = {
		limit = { has_relation_grudge = scope:bc_rivalry_foe }
		remove_relation_grudge = scope:bc_rivalry_foe
	}
	remove_variable = bc_nemesis
	remove_variable = bc_nemesis_losses
	debug_log = "BC: nemesis cleared"
}
```

- [ ] **Step 4: Validate and commit**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
```

Expected: exit 0.

```bash
cd /d/ck3/mods/battle_chronicles
git add common/scripted_effects/bc_rivalry_effects.txt
git commit -m "feat: add the rivalry decrement and clear

The floor guard compares against the step value rather than a constant: <= 2
would erase a rival after one win, <= 1 would jam the counter at -1 after a wipe
win. The removal ladder tests nemesis first because nemesis aliases rival, and
testing rival first would strip the alias and strand the real relation."
```

---

### Task 6: The entry point and the toast

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_rivalry_effects.txt`
- Modify: `mods/battle_chronicles/localization/english/bc_l_english.yml`

- [ ] **Step 1: Write the entry point**

```
# --- the entry point --------------------------------------------------------
#
# bc_rivalry_effect = { OUTCOME = win|lose }
#
# CALLED ON THE COMMANDER, from inside
# `side_commander ?= { if = { limit = { is_alive = yes } } }` in both graders,
# INSIDE the notability gate and INSIDE the aftermath game-rule gate, and BEFORE
# bc_clear_scratch_effect - which removes bc_battle_foe.
#
# `flag:$OUTCOME$ = flag:lose`, NOT `$OUTCOME$ = lose`. A bare `$OUTCOME$ = lose`
# substitutes to `lose = lose`, an unknown key, a SILENT NO-OP that validate
# passes.
#
# EVERY GUARD IS NESTED, NOT SIBLING. CK3 does not short-circuit and guarantees no
# evaluation order among siblings, so `exists = var:X` beside a read of var:X does
# not protect the read. `exists` itself is safe on a missing variable; it is the
# READ that has to be nested.
#
# THE ALIVE CHECK IS NOT OPTIONAL. Characters die constantly and set_relation_* on
# a dead man is a permanent error-log line. CK3 keeps dead characters as real
# objects, so `is_alive` on one is a clean `no` rather than an error - which is
# exactly what makes this guard sufficient and the dead-foe wipe (task 8) merely
# housekeeping.
bc_rivalry_effect = {
	if = {
		limit = { exists = var:bc_battle_foe }
		if = {
			limit = { var:bc_battle_foe = { is_alive = yes } }
			if = {
				limit = { flag:$OUTCOME$ = flag:lose }
				bc_rivalry_loss_effect = yes
			}
			else_if = {
				limit = { exists = var:bc_nemesis }
				if = {
					limit = { var:bc_nemesis = var:bc_battle_foe }
					bc_rivalry_win_effect = yes
				}
			}
		}
	}
}
```

**The win path is an `else_if`, and the inner test is nested rather than folded in.**
Folding `var:bc_nemesis = var:bc_battle_foe` into the `else_if` limit beside
`exists = var:bc_nemesis` would be a missing-variable read on every win by a commander who
has no running grudge — which is nearly every win in the game.

**There is no `else` on the inner `if`.** Winning against a man who is not your nemesis is
not an event; it is the overwhelmingly common case and logging it would flood `debug.log`.

- [ ] **Step 2: Write the toast**

```
# --- the toast --------------------------------------------------------------
#
# ROUTED, NOT BROADCAST. bc_addressed_toast_effect (bc_reward_effects.txt) raises
# on the subject if he is human and on his liege if he is not, because nearly
# every commander in the world is AI.
#
# CALLED FROM BOTH ESCALATION BRANCHES, AFTER bc_rivalry_set_relation_effect, so
# that the rung it describes is the rung that was actually set - including when
# the cap clamped it. Calling it before would describe a rung the player did not
# get.
#
# IT MIRRORS THE LADDER'S THRESHOLDS AND ITS CAP, arm for arm. If the two ever
# disagree the toast lies, so they are written adjacent and the cap test is
# duplicated deliberately rather than factored out - factoring it into a trigger
# would put the two a file apart, which is the pair most likely to drift.
#
# ALL THREE ARMS PASS event_toast_effect_bad. This is the mod's first bad-news
# routed toast; plan 1 made TYPE a required parameter of
# bc_addressed_toast_effect precisely so this one is not a green tick. An omitted
# TYPE is not an error in CK3 - the literal `type = $TYPE$` reaches the toast and
# validate passes it - so task 10 step 7 counts the call sites against the TYPE
# rows.
#
# UNDER bc_rivalry_off THERE IS NO TOAST AT ALL. The counter moved but nothing
# happened to the man, and announcing "he is your rival now" when he is not would
# be the one place the off switch leaked.
bc_rivalry_toast_effect = {
	if = {
		limit = { has_game_rule = bc_rivalry_off }
	}
	else = {
		save_scope_as = bc_rivalry_subject
		var:bc_nemesis = { save_scope_as = bc_rivalry_foe }
		if = {
			limit = {
				var:bc_nemesis_losses >= 3
				has_game_rule = bc_rivalry_nemesis
			}
			bc_addressed_toast_effect = {
				TYPE = event_toast_effect_bad
				TITLE = bc_rivalry_toast
				DESC = bc_rivalry_nemesis_desc
				SUBJECT = scope:bc_rivalry_subject
			}
		}
		else_if = {
			limit = { var:bc_nemesis_losses >= 2 }
			bc_addressed_toast_effect = {
				TYPE = event_toast_effect_bad
				TITLE = bc_rivalry_toast
				DESC = bc_rivalry_rival_desc
				SUBJECT = scope:bc_rivalry_subject
			}
		}
		else = {
			bc_addressed_toast_effect = {
				TYPE = event_toast_effect_bad
				TITLE = bc_rivalry_toast
				DESC = bc_rivalry_grudge_desc
				SUBJECT = scope:bc_rivalry_subject
			}
		}
	}
}
```

**An empty `if` body with the work in the `else` is deliberate.** The alternative —
`if = { limit = { NOT = { has_game_rule = bc_rivalry_off } } ... }` — reads the same and is
one negation further from the rule name. Both are correct; if the empty body offends, invert
it, but do not delete the gate.

- [ ] **Step 3: Write the seven localization keys**

Append to `localization/english/bc_l_english.yml`, in a new section after the reputation
keys. **One leading space per line.**

```
# --- rivalry ----------------------------------------------------------------

 bc_reason_battle_grudge:0 "beat him on the field"
 bc_reason_battle_rival:0 "has beaten him twice on the field"
 bc_reason_battle_nemesis:0 "has broken him three times on the field"
 bc_rivalry_toast:0 "The Man Across the Field"
 bc_rivalry_grudge_desc:0 "[bc_rivalry_foe.GetName] took the field from [bc_rivalry_subject.GetName] today. That is all it is so far — a name, and a face to put to it."
 bc_rivalry_rival_desc:0 "Twice now. [bc_rivalry_subject.GetName] has lost to [bc_rivalry_foe.GetName] twice, and the second time it stopped being bad luck."
 bc_rivalry_nemesis_desc:0 "Three fields, three defeats, one man. [bc_rivalry_subject.GetName] has stopped thinking about the war and started thinking about [bc_rivalry_foe.GetName]."
```

**The three `bc_reason_battle_*` keys are written from the loser's side** — they appear in
the relations tooltip as the reason the relation exists, and vanilla phrases them as
fragments (`nemesis_danelaw_rejection`, `rival_tried_to_embezzle`). Match that.

**`validate --strict` will NOT warn about the reason keys.** It has no knowledge of the
`reason =` field, so if one is misspelled in task 3 the tooltip renders the raw key and
nothing anywhere reports it. **Check the three spellings against task 3 by eye now:**

```bash
cd /d/ck3/mods/battle_chronicles
grep -oh "bc_reason_battle_[a-z]*" common/scripted_effects/bc_rivalry_effects.txt \
  localization/english/bc_l_english.yml | sort | uniq -c
```

Expected: exactly three lines, each with a count of **2** — one use, one definition. A
count of 1 on any line is a typo on one side or the other.

- [ ] **Step 4: Verify the total key count**

```bash
cd /d/ck3/mods/battle_chronicles
grep -c "^ bc_\|^ rule_bc_\|^ setting_bc_" localization/english/bc_l_english.yml
head -c 8 localization/english/bc_l_english.yml | cat -A
```

Against the baseline recorded in task 1 step 1, the count must have risen by exactly **15**
— 8 from task 1, 7 from here. The BOM must still be present (`M-oM-;M-?`); editors strip it
silently, which is why it is checked after the edits as well as before.

- [ ] **Step 5: Validate and commit**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
```

Expected: exit 0. **Nothing more — and in particular, not the absence of a
missing-localization WARN.** `ck3lib/validate.py:182-185` checks only top-level definition
keys in the three categories at `:37`: `common/traits`, `common/decisions`,
`common/character_interactions`. Every key this task adds is *referenced* from a scripted
effect or belongs to `common/game_rules`, none of which that check can see. Steps 3 and 4
are the real gates on this task's localization; this command only says the files parse.

```bash
cd /d/ck3/mods/battle_chronicles
git add common/scripted_effects/bc_rivalry_effects.txt localization/english/bc_l_english.yml
git commit -m "feat: add the rivalry entry point, toast and localization

The toast runs after the rung is set so it describes the rung actually applied,
including when the game rule clamped it, and is suppressed entirely under
bc_rivalry_off - announcing a rival the mod did not create is the one place that
switch could leak."
```

---

### Task 7: Wire both graders

**Files:**
- Modify: `mods/battle_chronicles/events/bc_aftermath_events.txt`

- [ ] **Step 1: Add the call to `bc_chronicles.0091` (the winner)**

Inside `side_commander ?= { if = { limit = { is_alive = yes } } }`, after whatever else that
block contains, add:

```
						bc_rivalry_effect = { OUTCOME = win }
```

**If plan 3 has already shipped**, that block contains `bc_notable_battle_counter_effect`
and `bc_reputation_effect = { OUTCOME = win }`. Put C **after** both. Order between C and B
does not matter — they share no variable — but a fixed order is one less thing to reason
about later.

**If plan 3 has not shipped**, the block contains the counter and the nickname `if`. Put C
after them.

- [ ] **Step 2: Add the call to `bc_chronicles.0092` (the loser)**

The loser grader has no `side_commander ?=` block in plan 1's version. **If plan 3 shipped
first it added one**; add C inside it:

```
						bc_rivalry_effect = { OUTCOME = lose }
```

**If plan 3 has not shipped**, create the block, inside the notability gate, after the
knight memory block:

```
				side_commander ?= {
					if = {
						limit = { is_alive = yes }
						bc_rivalry_effect = { OUTCOME = lose }
					}
				}
```

**Do not add `bc_notable_battle_counter_effect` here.** That counter is wins only and the
loser grader's header says so.

- [ ] **Step 3: Confirm placement against the load-bearing body order**

Plan 1's grader header states the order: cleanup outside the gate, grading inside, scratch
clearing outside and last. **C is grading.**

```bash
cd /d/ck3/mods/battle_chronicles
grep -n "bc_rivalry_effect\|bc_clear_scratch_effect\|bc_battle_is_notable_trigger\|bc_aftermath_off" \
  events/bc_aftermath_events.txt
```

Read the line numbers in order for each event. In both, the order must be: `bc_aftermath_off`
gate, notability gate, `bc_rivalry_effect`, then `bc_clear_scratch_effect` last.

**If `bc_clear_scratch_effect` appears before `bc_rivalry_effect` in either event, C is
dead** — `bc_battle_foe` would already be gone, the entry point's first guard would swallow
it silently, and no marker would fire. That silence is why this is checked by eye rather
than left to the runtime pass.

- [ ] **Step 4: Verify the call count and the outcome spelling**

```bash
cd /d/ck3/mods/battle_chronicles
grep -c "bc_rivalry_effect" events/bc_aftermath_events.txt
grep -n "bc_rivalry_effect = {" events/bc_aftermath_events.txt
```

Expected: **2**, and one must read `OUTCOME = win` and the other `OUTCOME = lose`. Two
`win`s would mean no commander in the world ever acquires a nemesis, and nothing else in
this plan would report it.

- [ ] **Step 5: Validate, index, conflicts, deploy**

```bash
cd /d/ck3/tools && python ck3.py validate --strict && python ck3.py index && python ck3.py conflicts && python ck3.py deploy
```

Expected: all exit 0. **`conflicts` reads a sqlite index that only `index` rebuilds** — never
run it alone.

- [ ] **Step 6: Commit**

```bash
cd /d/ck3/mods/battle_chronicles
git add events/bc_aftermath_events.txt
git commit -m "feat: both graders now run the rivalry chain

The outcome is carried by a parameter rather than inferred from which event is
running, because nothing in an event body can tell which of on_combat_end_winner
or on_combat_end_loser invoked it."
```

---

### Task 8: The dead-foe wipe

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_scripted_effects.txt`

- [ ] **Step 1: Understand what this is and what it is not**

**This is housekeeping, not safety.** Every read of `bc_nemesis` in this mod is already
guarded by `exists` plus `is_alive = yes`, and CK3 keeps dead characters as real objects, so
`is_alive` on a dead man is a clean `no` rather than an error. The guards are already
sufficient.

**The wipe exists to stop the variable living on a commander forever** — otherwise a
commander whose nemesis died holds a dead reference for the rest of his life and can never
acquire a new one, because `bc_rivalry_loss_effect`'s first arm tests
`NOT = { exists = var:bc_nemesis }`. Without this, one dead foe permanently disables C for
that commander. **That is the actual bug being fixed, and it is a real one.**

**It cannot be lazy, and Section 4 explains why.** The obvious design — wipe it wherever the
`is_alive` guard fails — does not work at the read site that matters. `bc_nemesis` is read in
two kinds of place:

| read site | context | can it wipe? |
|---|---|---|
| `bc_facing_nemesis_trigger` (task 9), and any later event `desc` branch | pure **trigger** — a `chance` modifier | **no.** No effect runs in a trigger; the guard can only decline to fire |
| `bc_rivalry_loss_effect` / `_win_effect` / `_clear_effect` | **effect** | yes, but they run only at the end of a **notable** battle, and only after the entry point already proved the *foe* alive — the dead nemesis is never reached |

So the one site that could wipe is the one the dangling reference never reaches.
`bc_battle_open_effect` is where it has to go: an effect, guaranteed to run on the commander
in **every** battle notable or not, already executing at the top of every phase event and
already writing `bc_battle_foe`.

**It lags the read by one phase event, and that is harmless.** An event's `is_valid` runs
before its `effect` block, so the first roll of the first battle after the man dies reads the
dangling variable and only the roll after that sees it gone. The guard handles that read
cleanly. The lag is not worth engineering away.

- [ ] **Step 2: Find `bc_battle_open_effect` and read its closing lines**

```bash
cd /d/ck3/mods/battle_chronicles
grep -n "bc_battle_open_effect" common/scripted_effects/bc_scripted_effects.txt
```

It ends with the 1/2/3 size ladder — `else = { set_variable = { name = bc_battle_size value = 1 } }`
— followed by the closing brace. **Append inside that closing brace.**

If plan 2 has shipped, the ladder's boundaries may read 10000 / `<Q3's measured value>`
instead of 10000 / 2000. Either way the ladder is the last thing in the effect.

- [ ] **Step 3: Append the wipe**

```
	# --- housekeeping: drop a dead nemesis ----------------------------------
	#
	# HOUSEKEEPING, NOT SAFETY. Every bc_nemesis read is already guarded by
	# `exists` plus `is_alive = yes`, and a dead character is a real object in
	# CK3, so is_alive on one is a clean `no` rather than an error.
	#
	# WHAT THIS ACTUALLY FIXES: bc_rivalry_loss_effect's first arm tests
	# `NOT = { exists = var:bc_nemesis }`, so a commander holding a dead
	# reference can never acquire a new nemesis. One dead foe would disable C
	# for that commander permanently.
	#
	# HERE RATHER THAN AT THE READ SITES because both read sites are pure
	# TRIGGER contexts - a phase event's is_valid and an event desc branch - and
	# no effect runs in a trigger. This effect is the one place an effect is
	# guaranteed to run on the commander during a battle.
	#
	# NESTED, NOT SIBLING. `exists = var:bc_nemesis` beside a read of
	# var:bc_nemesis would be a missing-variable read on every commander in the
	# world who has no nemesis, on every phase event roll - which is most of
	# them.
	#
	# Both variables go together. Leaving bc_nemesis_losses behind would let the
	# next grudge inherit the dead man's counter and start at `rival`.
	if = {
		limit = { exists = var:bc_nemesis }
		if = {
			limit = { NOT = { var:bc_nemesis = { is_alive = yes } } }
			remove_variable = bc_nemesis
			remove_variable = bc_nemesis_losses
			debug_log = "BC: nemesis wipe"
		}
	}
```

**This does not remove the relation.** A relation with a dead man is CK3's own business and
it handles it; removing it here would need the ladder, the ladder needs the scope, and the
scope needs a character the game considers gone. The variables are the mod's; the relation is
not.

- [ ] **Step 4: Verify the wipe landed inside the right effect**

```bash
cd /d/ck3/mods/battle_chronicles
awk '/^bc_battle_open_effect = \{/,/^\}/' common/scripted_effects/bc_scripted_effects.txt | grep -c "nemesis"
```

Expected: **more than 0**. If it is 0, the block landed outside the effect — at file scope,
where it is syntactically valid and never runs.

```bash
cd /d/ck3/tools && python ck3.py validate --strict
```

Expected: exit 0.

- [ ] **Step 5: Commit**

```bash
cd /d/ck3/mods/battle_chronicles
git add common/scripted_effects/bc_scripted_effects.txt
git commit -m "fix: drop a dead nemesis in bc_battle_open_effect

Not a safety fix - every read is already guarded and a dead character is a clean
is_alive = no. Without it, bc_rivalry_loss_effect's create arm tests NOT exists
and a commander whose nemesis died could never acquire another one."
```

---

### Task 9: The read-back

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_triggers/bc_scripted_triggers.txt`
- Modify: `mods/battle_chronicles/common/combat_phase_events/bc_commander_phase_events.txt`

- [ ] **Step 1: Understand what the read-back can and cannot see**

Section 4 calls the read-back "the only thing in the design that makes a commander feel like
the same man twice." It is also the part of C most easily written wrong, because of **when**
a weight is evaluated.

`bc_battle_open_effect` writes `bc_battle_foe` in the **effect** block of a phase event.
Weights and `is_valid` are evaluated **before** the effect. Therefore:

| roll | what `bc_battle_foe` holds at weight time |
|---|---|
| first roll of a battle | **nothing** — `bc_clear_scratch_effect` removed it at the end of the last battle |
| every roll after | this battle's foe, written by the previous roll |

**So the read-back misses the first roll of every battle and is correct thereafter.** That
is acceptable — phase events roll every 5 days and any battle long enough to be notable rolls
several times — and it is stated here so that a later reader does not mistake it for a bug.
**Do not try to fix it by reading the combat scope directly in the trigger**; that path is
unverified and the failure mode is an error log on every roll of every battle in the world.

- [ ] **Step 2: Add the trigger**

Append to `common/scripted_triggers/bc_scripted_triggers.txt`:

```
# Is the man across the field the man who has beaten me before?
#
# CALLED ON THE COMMANDER, in TRIGGER contexts only - weight multipliers and
# is_valid blocks. It must therefore be safe to evaluate on every commander in
# the world on every phase event roll, most of whom have no nemesis at all.
#
# THE TWO `exists` ROWS ARE SAFE AS SIBLINGS - `exists` on a missing variable is
# safe, and only a READ of a missing variable logs an error. The trigger_if
# repeats them and does the reading, which is the shipped pattern this mod
# already uses in the graders' every_side_knight limit.
#
# IT MISSES THE FIRST ROLL OF EVERY BATTLE, deliberately. bc_battle_foe is
# written in the EFFECT of a phase event and weights are evaluated BEFORE the
# effect, so the first roll of a battle sees nothing and every roll after sees
# this battle's foe. Reading the combat scope directly instead would fix that at
# the cost of an unverified scope path evaluated on every roll of every battle in
# the world.
bc_facing_nemesis_trigger = {
	exists = var:bc_nemesis
	exists = var:bc_battle_foe
	trigger_if = {
		limit = {
			exists = var:bc_nemesis
			exists = var:bc_battle_foe
		}
		var:bc_nemesis = var:bc_battle_foe
		var:bc_nemesis = { is_alive = yes }
	}
}
```

**Do not touch the "Five substantive rows plus the game rule" comment** anywhere in this
file. It counts `calc_true_if` rows inside `bc_battle_is_notable_trigger` — not the number of
triggers in the file — and the number is load-bearing for that trigger's threshold. Changing
it would change what "notable" means.

- [ ] **Step 3: Wire the read-back into every commander phase event**

The block is called `chance`, not `weight` — every commander phase event has
`chance = { base = <n>  modifier = { ... } }` and the modifiers already there are the two
`bc_frequency` game-rule ones. Add a third to each, at the end of its `chance` block:

```
		modifier = {
			factor = 1.5
			bc_facing_nemesis_trigger = yes
		}
```

**Indentation is two tabs** for `modifier` and three for its contents, matching the existing
`has_game_rule = bc_frequency_low` modifier one line above. Read one existing `chance` block
first and match it — the header records that these were retuned after 59 commander fires, so
the surrounding structure is measured and this is an addition to it, not a replacement.

**The same factor on every event, not seven tuned ones.** A per-event tuning pass needs its
own runtime measurement and belongs to a later plan.

**1.5, and nothing else changes.** The read-back's job is that a grudge match produces more
moments than a battle against a stranger. It deliberately does **not** change which moments
fire, gate any event on the nemesis, or add nemesis-specific text — all three are real
designs and all three belong to a later plan, because each needs its own localization and its
own runtime measurement. **C is complete without them**; this makes it felt.

- [ ] **Step 4: Verify the wiring**

```bash
cd /d/ck3/mods/battle_chronicles
grep -c "^	type = commander" common/combat_phase_events/bc_commander_phase_events.txt
grep -c "bc_facing_nemesis_trigger" common/combat_phase_events/bc_commander_phase_events.txt
grep -n "bc_facing_nemesis_trigger" common/scripted_triggers/bc_scripted_triggers.txt
```

**The first two numbers must be equal.** As of plan 1 both are **7** —
`bc_banner_falls`, `bc_rally_the_line`, `bc_horse_killed_under_him`, `bc_flank_collapses`,
`bc_van_breaks_through`, `bc_ground_favours_us`, `bc_lines_bogged_down`. If plan 2 or a later
plan has added commander phase events the number is higher, which is why the check compares
the two counts rather than hardcoding 7.

**The `^\t` anchor on the first grep is load-bearing.** The file's header comment contains the
words `type = commander` at line 8, so an unanchored `grep -c` returns 8 and the check would
be off by one forever.

The third command must show exactly one line — the definition.

```bash
cd /d/ck3/tools && python ck3.py validate --strict && python ck3.py index && python ck3.py conflicts && python ck3.py deploy
```

Expected: all exit 0.

- [ ] **Step 5: Commit**

```bash
cd /d/ck3/mods/battle_chronicles
git add common/scripted_triggers/bc_scripted_triggers.txt \
        common/combat_phase_events/bc_commander_phase_events.txt
git commit -m "feat: phase events fire more often against a running nemesis

The trigger reads bc_battle_foe, which is written in a phase event's effect
while weights are evaluated before it, so this misses the first roll of every
battle and is correct thereafter. Reading the combat scope directly would fix
that at the cost of an unverified path evaluated on every roll in the world."
```

---

### Task 10: Static verification

**Files:** none — this task only reads.

- [ ] **Step 1: No relation effect targets a variable**

```bash
cd /d/ck3/mods/battle_chronicles
grep -rn "set_relation_[a-z]* = var:\|remove_relation_[a-z]* = var:" common/ events/
grep -rn "target = var:" common/
```

Expected: **no output from either.** Both forms have zero shipped uses in vanilla and AGOT,
`validate` cannot detect them, and the failure mode is a silent no-op. Every relation effect
in C must target `scope:bc_rivalry_foe`.

```bash
cd /d/ck3/mods/battle_chronicles
grep -c "scope:bc_rivalry_foe" common/scripted_effects/bc_rivalry_effects.txt
grep -c "save_scope_as = bc_rivalry_foe" common/scripted_effects/bc_rivalry_effects.txt
```

**Expected: exactly 9, then exactly 3.** The two greps see disjoint sets of lines —
`save_scope_as = bc_rivalry_foe` has no `scope:` prefix, so the saves are invisible to the
first pattern and must be counted separately.

| grep | where the hits are | count |
|---|---|---|
| `scope:bc_rivalry_foe` | rung ladder: 3 × `target = scope:bc_rivalry_foe` | 3 |
| | clear: 3 × `has_relation_*` + 3 × `remove_relation_*` | 6 |
| | toast: **none** — it routes on `scope:bc_rivalry_subject` and reaches the foe only through loc | 0 |
| `save_scope_as = bc_rivalry_foe` | rung ladder, clear, toast — one each | 3 |

A first count below 9 means one site still targets the variable.

- [ ] **Step 2: Every effect C calls actually exists**

```bash
cd /d/ck3/mods/battle_chronicles
grep -ohE "^\s*bc_[a-z_]+_effect = (yes|\{)" common/scripted_effects/bc_rivalry_effects.txt \
  | grep -oE "bc_[a-z_]+_effect" | sort -u > /tmp/bc_c_calls
while read e; do
  grep -rq "^$e = {" common/scripted_effects/ || echo "MISSING: $e"
done < /tmp/bc_c_calls
```

Expected: **no `MISSING:` output.** `validate` does not resolve effect names, so a call to a
misspelled effect passes cleanly and does nothing forever. `bc_addressed_toast_effect` should
resolve into `bc_reward_effects.txt`; if it does not, plan 1 task 4 left it in
`bc_scripted_effects.txt` and the grep above still finds it.

- [ ] **Step 3: No parameter is compared without `flag:`**

```bash
cd /d/ck3/mods/battle_chronicles
grep -rn '\$[A-Z_]*\$ = [a-z]' common/scripted_effects/ | grep -v 'flag:\$'
```

Expected: **no output**. The only parameter comparison in C is `flag:$OUTCOME$ = flag:lose`,
and the `grep -v` exists to drop exactly that line — **without it this check reports its own
correct code as a failure**, because `flag:$OUTCOME$ = flag:lose` contains `$OUTCOME$ = f`
and matches the pattern. A bad line reads `$OUTCOME$ = lose` with no `flag:` anywhere on it,
so it survives the filter.

`[A-Z_]`, not `[A-Z]`: a parameter named `$SOME_PARAM$` would slip through the narrower
class.

- [ ] **Step 4: No missing-variable read**

Read `bc_rivalry_effects.txt` end to end and check every `limit` containing a `var:`
**comparison**. A bare `exists = var:X` row is not a comparison and needs no guard. There are
**nine**, and this is the full list:

| where | comparison | what makes it safe |
|---|---|---|
| entry point | `var:bc_battle_foe = { is_alive = yes }` | nested inside `exists = var:bc_battle_foe` |
| entry point | `var:bc_nemesis = var:bc_battle_foe` | nested inside `exists = var:bc_nemesis`; the foe was proven two levels up |
| `bc_rivalry_loss_effect` arm 2 | `var:bc_nemesis = var:bc_battle_foe` | arm 1 already tested `NOT = { exists = var:bc_nemesis }`, and else_if arms are ordered |
| rung ladder arm 1 | `var:bc_nemesis_losses >= 3` | both callers write it on the line above |
| rung ladder arm 2 | `var:bc_nemesis_losses >= 2` | same |
| `bc_rivalry_win_effect` | `var:bc_nemesis_losses <= bc_rivalry_step_value` | the entry point proved `bc_nemesis` exists, and the two are always written together |
| `bc_rivalry_win_effect` | `var:bc_nemesis_losses <= 0` | the branch above unconditionally wrote it |
| toast arm 1 | `var:bc_nemesis_losses >= 3` | called only from the two branches that just wrote it |
| toast arm 2 | `var:bc_nemesis_losses >= 2` | same |

Plus **three more outside `bc_rivalry_effects.txt`**, all nested:

| where | comparison | what makes it safe |
|---|---|---|
| `bc_facing_nemesis_trigger` | `var:bc_nemesis = var:bc_battle_foe` | inside a `trigger_if` whose limit carries both `exists` rows |
| `bc_facing_nemesis_trigger` | `var:bc_nemesis = { is_alive = yes }` | same `trigger_if` |
| task 8 wipe | `NOT = { var:bc_nemesis = { is_alive = yes } }` | nested inside `exists = var:bc_nemesis` |

**Nine plus three is twelve. If your read finds a thirteenth anywhere, it is new and it is
unguarded.**

Separately, there are **three reads that are not comparisons and not in any limit** —
`var:bc_nemesis = { save_scope_as = bc_rivalry_foe }`, once each in the rung ladder, the
clear, and the toast. A scope-change read of a missing variable logs the same error a
comparison does, so they need the same invariant. All three are reached only from the two
escalation branches (which wrote `bc_nemesis` on the line above) or from
`bc_rivalry_win_effect` (which the entry point reached only after proving
`exists = var:bc_nemesis`). **If you add a fourth caller to any of those three effects, check
this before anything else.**

- [ ] **Step 5: The ledger variables are not cleared**

```bash
cd /d/ck3/mods/battle_chronicles
grep -rn "bc_nemesis" common/scripted_effects/bc_ledger_effects.txt
```

Expected: **no output**. If `bc_clear_scratch_effect` learned about either variable, every
grudge would evaporate at every combat end and C could never escalate past a first loss.

- [ ] **Step 6: The step value is never inlined**

```bash
cd /d/ck3/mods/battle_chronicles
grep -n "bc_rivalry_step_value" common/scripted_effects/bc_rivalry_effects.txt | grep -v "#"
```

Expected: **exactly four hits** — the create branch, the escalate branch, the floor guard,
and the decrement. A literal `1` or `2` in any of those four places is the exact bug
Section 4 records an earlier draft making.

**The `grep -v "#"` is load-bearing.** Task 5 step 2's own comment block contains the line
`# THE FLOOR GUARD IS \`<= bc_rivalry_step_value\`, NOT A CONSTANT`, in this same file.
Unfiltered, this check reports the correct count as five and fails on correct code — the
same shape of defect as the parameter grep in step 3.

- [ ] **Step 7: Every toast call names a TYPE**

```bash
cd /d/ck3/mods/battle_chronicles
grep -rc "bc_addressed_toast_effect = {" common/scripted_effects/ | grep -v ':0'
grep -rc "TYPE = event_toast_effect_" common/scripted_effects/ | grep -v ':0'
grep -rn "TYPE = event_toast_effect_" common/scripted_effects/bc_rivalry_effects.txt
```

**The first total must be exactly one MORE than the second, not equal to it.** The pattern
`bc_addressed_toast_effect = {` matches the effect's own definition line as well as every
call site, and a definition passes no `TYPE` to itself. Equal means a caller is missing one.

The third must show **exactly three lines, all
`event_toast_effect_bad`** — losing to the same man twice is not good news, and this is the
mod's first routed toast that is not.

An omitted `TYPE` produces no error anywhere: CK3 substitutes parameters textually, the
literal string `type = $TYPE$` reaches `send_interface_toast`, and `validate` sees balanced
braces. **Only this count catches it.**

- [ ] **Step 8: Full static pass**

```bash
cd /d/ck3/tools && python ck3.py validate --strict && python ck3.py index && python ck3.py conflicts && python ck3.py deploy
```

Expected: all exit 0.

---

### Task 11: Run it

**This is the runtime checkpoint.** A game restart costs about seven minutes, so this run
must answer everything it can.

- [ ] **Step 1: Clear the logs — game closed**

Delete `error.log` and `debug.log` from
`D:\Documents\Paradox Interactive\Crusader Kings III\logs`. Write any unrecorded findings
from the previous run into the README first.

- [ ] **Step 2: Confirm the rule exists before fighting anything**

Start a game and open the game-rules screen. **`Battle Chronicles: Rivalry` must be present
with three options and readable descriptions.** A raw key here means task 1 step 3's
localization did not land, and every other check in this task would still pass.

This is also the only check that the mod still loads at all — a game rule with a malformed
option list fails at load, not at use.

- [ ] **Step 3: Fight, and fight the same man twice**

C needs **notable losses**, which is the hardest thing in the expansion to produce on demand:
`bc_battle_is_notable_trigger` was calibrated against 39 combat ends and most battles fail it,
and you have to *lose*.

**What this run must show is that the counter moves.** `BC: nemesis new` is the minimum bar.
`BC: nemesis escalate` and a rung above `grudge` are a bonus and should not be expected in one
session.

- [ ] **Step 4: Sweep the rivalry markers**

```bash
cd /d/ck3/tools && python ck3.py probe "BC: nemesis"
```

**`probe` globs every `*.log` in the log directory including `debug.log`, matches per line,
and groups per LINE rather than per error.** It exits 1 when nothing matches.

| what came back | what it means |
|---|---|
| `BC: nemesis new` appears | C is live. This is the pass condition |
| nothing, but `BC: lose notable` appeared | **the entry point is swallowing everything.** Either `bc_battle_foe` is not being written, or `bc_clear_scratch_effect` runs before C — check task 7 step 3 |
| nothing, and no `BC: lose notable` either | no notable loss happened. Inconclusive, not a failure. Fight more, or set `bc_aftermath_generous` |
| `BC: nemesis rung grudge` without `BC: nemesis new` above it | impossible as written; if you see it, the rung ladder is being called from somewhere it should not be |
| `BC: nemesis rule off` | the rule is set to off. Change it and re-run — the rung ladder is unverified until one fires |
| `BC: nemesis held` | a commander lost to a second man while a grudge was running. Correct behaviour, and worth seeing at least once |

- [ ] **Step 5: Confirm the relation actually landed**

**This is the one thing no marker proves.** `set_relation_grudge` targeting a saved scope is
the form this plan chose *because* the variable form is unshipped — but that reasoning is an
argument, not a measurement.

Find the commander who produced `BC: nemesis new`, open his character screen, and **look at
his relations**. A `grudge` must be listed, against the right man, with the tooltip reading
`beat him on the field`.

| what you see | what it means |
|---|---|
| the grudge, with the reason text | C works end to end. **Record this in the README** — it is the only evidence the target form is right |
| the grudge, with a raw `bc_reason_battle_grudge` key | the effect works; task 6 step 3's loc key is misspelled on one side |
| no grudge at all, but the marker fired | **the saved-scope target is also being declined.** Do not guess — this is the point to stop and re-derive the target form from a shipped call site |

- [ ] **Step 6: Error sweep**

```bash
cd /d/ck3/tools && python ck3.py probe "bc_"
```

Plan 1's three-row pass condition, unchanged. **Watch specifically for missing-variable reads
naming `bc_nemesis`, `bc_nemesis_losses` or `bc_battle_foe`.** All three are guarded; a hit
means a guard was written as a sibling row rather than nested, which is the exact mistake
task 10 step 4 exists to prevent and which no static check in this plan can catch.

**Also watch for anything naming a dead character.** C is the first thing in the mod to hold
a character reference across battles, so it is the first thing that can produce one.

- [ ] **Step 7: Record and commit**

Write into `README.md`:
- whether the relation was seen on a character screen, and with what reason text — **this is
  the load-bearing finding of the whole run**
- which markers fired and which did not
- that `bc_nemesis` and `bc_nemesis_losses` are permanent ledger variables that
  `bc_clear_scratch_effect` must never touch
- that `set_relation_*` / `remove_relation_*` must target a saved scope and never a variable,
  and that the design document says otherwise

```bash
cd /d/ck3/mods/battle_chronicles
git add README.md
git commit -m "docs: record the plan 4 runtime findings"
```

---

## Not in this plan

| item | why not | where it goes |
|---|---|---|
| Nemesis-specific phase event text | Needs its own localization pass and its own weight retune. C is complete without it | a later plan |
| Gating whole events on `bc_facing_nemesis_trigger` | Same, plus it would need new events rather than an addition to existing ones | a later plan |
| The `scope:wipe` step of 2 | Section 5's. `bc_rivalry_step_value` is written to accept it and is inert until then | plan 5 |
| Removing a relation when the foe dies | CK3's own business. The mod removes its variables and leaves the relation graph alone | nowhere |
| A `bc_rivalry_grudge` cap option | `grudge` is the bottom rung; a cap there differs from `off` only in whether a one-directional -60 opinion applies | nowhere |
| Reading the combat scope in `bc_facing_nemesis_trigger` | Would fix the first-roll blind spot at the cost of an unverified scope path evaluated on every roll of every battle in the world | nowhere, unless the blind spot proves to matter |
| Reconciling two commanders who each hold a counter against the other | `rival` and `nemesis` are mutual, so if A and B have both escalated against each other and A then beats B down to 0, A's clear removes the shared relation while B's counter still reads 2. B's next loss to A re-sets it. The desync is invisible in play and self-healing; chasing it means every clear has to reach into another character's ledger | nowhere |
