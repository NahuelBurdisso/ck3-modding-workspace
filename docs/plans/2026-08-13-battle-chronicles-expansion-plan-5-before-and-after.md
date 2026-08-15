# Battle Chronicles Expansion — Plan 5: Before and After (D)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Three gaps at the two ends of a battle — a choice made before the first blood, an
annihilation that counts for more than a win, and the knights who did not come back.

**Architecture:** Sub-project D is three unrelated pieces sharing only their position at the
edges of a combat. **The wipe** turns vanilla's existing `scope:wipe` into a top tier for
notability, for B's style streak, and for C's rivalry counter — three one-line reads of one
new scripted trigger. **The dead knights** invert the graders' `is_alive = yes` filter into a
single aggregate toast per side. **The eve** claims `on_combat_start`, an entirely unused
hook, for one throttled pop-up before a large battle.

**Tech Stack:** CK3 script (Paradox clausewitz script), targeting CK3 1.19.0.6 under the
AGOT playset. Workspace CLI is `python ck3.py` run from `D:/ck3/tools`.

**Spec:** `D:/ck3/docs/specs/2026-08-13-battle-chronicles-expansion-design.md`, Section 5.

**Depends on all four earlier plans.** This is the last plan of the expansion's first arc and
it is the only one that touches every other plan's files:

| plan | what plan 5 needs from it |
|---|---|
| 1 | the consolidated graders in `events/bc_aftermath_events.txt`, `bc_addressed_toast_effect` **with its `TYPE` parameter**, and **DIAG Q2's verdict** |
| 2 | `bc_add_verb_effect` and the family-2 modifiers `bc_bloodied` / `bc_shieldwall`, which the eve's first two options apply |
| 3 | `bc_style_streak_effect`, whose increment becomes a script value here |
| 4 | `bc_rivalry_step_value`, whose inline wipe test this plan collapses into a named trigger — it was already live, not dormant — and `var:bc_nemesis`, which the eve's description reads |

**Gated on DIAG Q2 — the eve only.** Q2 asks whether a `scope = combat` event fires at all.
Tasks 1 through 5 are the wipe and the dead knights; neither touches `on_combat_start` and
neither cares about Q2. **If Q2 failed, stop after task 5 and skip to task 10.** That is the
whole dependency, and it is why the eve is last rather than first.

---

## Read this before task 1

Plan 1's entire "Read this before task 1" applies unchanged — the verification loop, the
`validate`-is-syntax-only rule, the cleared-log rule, the mod-is-its-own-git-repo rule, the
sweep pass condition, and the non-negotiables. **Read it first.** What follows is only what
is new in plan 5.

### `scope:wipe` is real, it is symmetric, and it survives into an event

Everything the wipe half of this plan rests on, measured in the **loaded** files:

| claim | evidence |
|---|---|
| both end hooks pass it | AGOT `common/on_action/combat_on_actions.txt:13` (`# scope:wipe - Was this a wipe?` above `on_combat_end_winner`) and `:527` (the same comment above `on_combat_end_loser`) |
| it is readable as an existence test | AGOT `combat_on_actions.txt:100` — `exists = scope:wipe` |
| it is readable as a boolean | AGOT `combat_on_actions.txt:758` — `scope:wipe = yes`, bare, in the loser hook's own `effect` block |
| **it reaches events raised from the `events = { }` list** | AGOT `events/war_events/combat_events.txt:781` and `:947` read `scope:wipe = yes` inside `combat_event.1001`, which `on_combat_end_winner` raises from its `events` list at `combat_on_actions.txt:17` |

**The last row is the load-bearing one.** The mod's graders are raised the same way from the
same lists, so they see the same scope. Nothing in this plan needs to thread it anywhere.

**Cite AGOT's line numbers, not vanilla's.** AGOT overrides
`common/on_action/combat_on_actions.txt` wholesale and the numbers differ — vanilla's
`exists = scope:wipe` is at `:91`, AGOT's at `:100`. The spec quotes a mixture. AGOT's are
the ones that describe the running game. The `combat_events.txt` path is
`events/war_events/combat_events.txt`, not `events/combat_events.txt`.

### The spec's `AND = { exists = scope:wipe  scope:wipe = yes }` is written as siblings. Do not copy it.

Section 5 says to read the scope as a conjunction, because shipped script uses both idioms
and it is unsettled whether the scope always exists carrying a boolean or exists only when
true. **The conjunction is right; the sibling shape is not.**

`exists = scope:X` is safe on a missing scope. A **comparison** against a missing scope is
not — it is the same error a missing-variable read produces, and CK3 does not short-circuit
and guarantees no evaluation order among siblings. Under the reading where the scope exists
only on a wipe, the spec's `AND` block would log an error on **every non-wipe combat end in
the world**, which is nearly all of them.

Task 1 writes it as a `trigger_if` instead, which is the shape plan 4's
`bc_facing_nemesis_trigger` already uses and the shape the graders' own
`every_side_knight` limit uses. One extra line, correct under either reading, and safe under
both.

(That limit is at `bc_events.txt:231-234` **today**; plan 1 task 6 moves both graders into
`bc_aftermath_events.txt`, so by the time plan 5 runs the line numbers are gone. Search for
`trigger_if` rather than seeking to a line.)

### Plan 4 told you not to touch a comment. This plan changes it.

Plan 4 task 9 step 2 says: *"Do not touch the 'Five substantive rows plus the game rule'
comment"*, because it counts `calc_true_if` rows and the number is load-bearing for the
`amount >= 2` bar.

**Task 2 adds a row, so the comment becomes wrong and must be updated.** That is not a
contradiction — plan 4 adds a *trigger* to the file and changes no rows; plan 5 adds a
*row*. If task 2 leaves the comment at five, the next person to read
`bc_battle_is_notable_trigger` will count six and conclude the file is lying.

### The wipe row is a scripted trigger, and that is the point

The trigger's own header (`bc_scripted_triggers.txt:103-108`) warns: *"DO NOT wrap any of
these rows in a nested scripted trigger - a nested trigger counts as one row no matter how
many tests it holds."*

**Task 2 does exactly that, deliberately.** The warning exists to stop someone folding three
independent tests into one row and silently lowering the bar. Here the whole point is that a
wipe is worth **one** point of the two required — it makes a battle notable *combined with*
any single other row, which every wipe already satisfies on blood or warscore. The
`trigger_if` inside `bc_was_wipe_trigger` is one test with a guard, not three tests.

**Write the wipe as two bare sibling rows and every wipe becomes notable on its own**, at
which point the trigger stops being a judgement and becomes a passthrough. That is the actual
failure this warning is about.

### Notability must stay symmetric, and the wipe is

The same header: *"The bar must be SYMMETRIC - both sides must reach the same verdict, or
one side's knights get a memory of a battle the other side's knights do not."*

`scope:wipe` is passed to **both** hooks (AGOT `:13` and `:527`), so both graders see the
same value and reach the same verdict. Symmetric for free, like `num_total_troops` and
`warscore_value`. No extra work — but check it if the row is ever moved.

### Three step values, three different rules. They are not interchangeable.

| counter | create branch | increment | why |
|---|---|---|---|
| C's `bc_nemesis_losses` | ***N*** (task 4) | ***N*** | a tally of damage done to you, where the first blow's severity is exactly the thing being counted |
| B's `bc_style_streak` | **always 1** (task 3) | ***N*** | a streak is a claim about *repetition*, and nothing repeated has happened on the first battle |
| B's `bc_terrain_streak` | **always 1** | **always 1** | its threshold is 2, so any bonus would award a terrain trait from a single battle |

The asymmetry between the first two rows is deliberate and is the reason "two wipes fought
the same way earn the trait" is true rather than "one wipe plus a mismatch": the first wipe
is a mismatch and creates the streak at 1, the second matches and adds 2, reaching 3.

**Do not unify these into one script value.** They read the same scope and mean different
things.

### New variables: none

Plan 5 adds no ledger and no scratch variables. It adds one flag (`bc_eve_cooldown`, 90
days), two script values, two scripted triggers, and reads one scope the engine already
provides.

### New markers

All begin `BC: `, so plan 1's sweep row 3 covers them.

| marker | meaning |
|---|---|
| `BC: wipe` | a combat end was an annihilation. Fires on both sides |
| `BC: dead knights` | at least one knight of this side did not survive, and the toast was raised |
| `BC: eve fired` | the `scope = combat` event ran. **Q2's verdict, re-confirmed on every large battle** |
| `BC: eve offered` | a human commander passed both gates and got the pop-up |
| `BC: eve popup 0011` | the pop-up itself opened |

---

## File structure

| path | plan action | responsibility |
|---|---|---|
| `common/scripted_triggers/bc_scripted_triggers.txt` | modify (tasks 1, 2, 6) | `bc_was_wipe_trigger`, the notability row, `bc_eve_facing_nemesis_trigger` |
| `common/script_values/bc_script_values.txt` | modify (tasks 3, 4) | `bc_style_step_value`; `bc_rivalry_step_value` routed through `bc_was_wipe_trigger` |
| `common/scripted_effects/bc_reputation_effects.txt` | modify (task 3) | the style streak increment |
| `events/bc_aftermath_events.txt` | modify (task 5) | the dead-knight toast in both graders, and the `BC: wipe` marker — the only effect context in the mod that can emit one |
| `common/scripted_effects/bc_scripted_effects.txt` | modify (task 6) | `bc_start_eve_cooldown_effect` |
| `events/bc_combat_start_events.txt` | modify (tasks 7, 8) | the eve, hidden event and pop-up |
| `common/scripted_effects/bc_eve_effects.txt` | **create** (task 7) | `bc_eve_offer_effect` |
| `common/on_action/bc_on_actions.txt` | modify (task 9) | the `on_combat_start` hook |
| `localization/english/bc_l_english.yml` | modify (tasks 5, 8) | 9 keys total |
| `README.md` | modify (final task) | the run log — the wipe, the dead knights, and the eve if Q2 passed |

**`events/bc_combat_start_events.txt` already exists** if Q2 passed — plan 1 task 16 step 2
renames `bc_diag_events.txt` to it and leaves `bc_chronicles.0900` stripped to a shell. Task
7 replaces that shell. If Q2 failed the file is gone and so is the eve.

**The eve gets one small effects file rather than a home in `bc_scripted_effects.txt`.**
`bc_eve_offer_effect` is the only effect in the mod called from a `scope = combat` context,
which is the one scope nothing else in the mod has ever run in. Keeping it separate means
the file that holds it can carry that warning in its header instead of burying it.

---

### Task 1: `bc_was_wipe_trigger`

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_triggers/bc_scripted_triggers.txt`

- [x] **Step 1: Confirm the marker does not exist**

```bash
cd /d/ck3/tools && python ck3.py probe "BC: wipe"
```

Expected: **exit 1** — `probe` exits 1 when nothing matches. A match means a previous attempt
left code behind; find it before continuing.

**The marker itself is written in task 5 step 3b, not here.** `bc_was_wipe_trigger` is a
trigger and cannot hold a `debug_log`, and so are all three of its consumers, so the only
place in the mod that can emit `BC: wipe` is an `if` inside the graders' `immediate`.

- [x] **Step 2: Write the trigger**

Append to `common/scripted_triggers/bc_scripted_triggers.txt`, in a new section after the
notability trigger:

```
# --- was this an annihilation ------------------------------------------------
#
# READS scope:wipe, WHICH THE ENGINE PASSES TO BOTH COMBAT-END HOOKS. AGOT
# combat_on_actions.txt:13 documents it above on_combat_end_winner and :527 above
# on_combat_end_loser, so both graders see the same value and any bar built on it
# is SYMMETRIC for free - which bc_battle_is_notable_trigger's header requires.
#
# IT SURVIVES INTO AN EVENT RAISED FROM THE `events = { }` LIST. Proven by
# vanilla: combat_event.1001 is raised from on_combat_end_winner's list
# (AGOT combat_on_actions.txt:17) and reads `scope:wipe = yes` at AGOT
# events/war_events/combat_events.txt:781 and :947. Nothing has to thread it.
#
# SCOPE-INDEPENDENT. A saved scope is readable from any scope in the event, so
# this trigger is equally valid on the combat side (task 2's notability row) and
# on the commander inside side_commander ?= { } (task 3's script value).
#
# TRIGGER_IF, NOT THE SPEC'S `AND = { exists = scope:wipe  scope:wipe = yes }`.
# The conjunction is right and the sibling shape is wrong. Shipped script uses
# BOTH idioms - `exists` at combat_on_actions.txt:100, `= yes` at :758 - which
# means it is unsettled whether the scope always exists carrying a boolean or
# exists only when true. Under the second reading the spec's AND compares against
# a missing scope on EVERY non-wipe combat end in the world, which is nearly all
# of them, and CK3 does not short-circuit and guarantees no evaluation order among
# siblings. `exists` is safe on a missing scope; the COMPARISON is what has to be
# nested. Same rule, same reason, as every variable guard in plans 3 and 4.
bc_was_wipe_trigger = {
	exists = scope:wipe
	trigger_if = {
		limit = { exists = scope:wipe }
		scope:wipe = yes
	}
}
```

**Do not touch the "Five substantive rows plus the game rule" comment in this step.** Task 2
changes it, deliberately and with the row it describes.

- [x] **Step 3: Validate and commit**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
```

Expected: exit 0.

```bash
cd /d/ck3/mods/battle_chronicles
git add common/scripted_triggers/bc_scripted_triggers.txt
git commit -m "feat: add bc_was_wipe_trigger

Written as a trigger_if rather than the design document's AND of two siblings.
Shipped script uses both the exists and the = yes idiom, so it is unsettled
whether scope:wipe always exists; under the reading where it does not, the
sibling form compares against a missing scope on every non-wipe combat end in
the world."
```

---

### Task 2: The wipe as a notability row

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_triggers/bc_scripted_triggers.txt`

- [x] **Step 1: Read the trigger and count its rows**

```bash
cd /d/ck3/mods/battle_chronicles
sed -n '/^bc_battle_is_notable_trigger = {/,/^}/p' common/scripted_triggers/bc_scripted_triggers.txt
sed -n '/^bc_battle_is_notable_trigger = {/,/^}/p' common/scripted_triggers/bc_scripted_triggers.txt | grep -c "^[[:space:]][[:space:]][a-zA-Z]"
```

You should see `amount >= 2` and **six direct children**: two `combat = { num_total_troops }`
rows, an `OR` for blood, an `OR` for odds, a `combat = { warscore_value }` row, and
`has_game_rule = bc_aftermath_generous`. Six children, described by the header as "five
substantive rows plus the game rule".

**The second command must print 7 — `amount >= 2` plus those six children.** Write it down.
Step 4 re-runs the identical command and requires **8**. The two-level indent anchor is what
makes the count mean anything: the two `OR` blocks' contents are indented deeper and are not
counted, which is exactly the distinction `calc_true_if` itself makes.

**`[[:space:]][[:space:]]`, not `\t\t`.** POSIX basic regex has no `\t` escape — `grep -c
"^\t\t[a-zA-Z]"` searches for a literal `tt` and returns **0** on this file, silently, which
is indistinguishable from "the trigger moved" and would send you looking for the wrong thing.
`grep -P` is not available in this environment either (`-P supports only unibyte and UTF-8
locales`). The bracket class is the portable form, and it costs nothing here: the file is
tab-indented throughout, so nothing at three tabs can match a pattern whose third character
must be a letter.

**If you count seven children, or the grep prints 8, plan 5 has already run.** Stop and check
git log.

- [x] **Step 2: Add the row**

Add `bc_was_wipe_trigger = yes` as a direct child of `calc_true_if`, **after the warscore row
and before the game rule**:

```
bc_battle_is_notable_trigger = {
	calc_true_if = {
		amount >= 2

		combat = { num_total_troops >= 10000 }
		combat = { num_total_troops >= 20000 }
		OR = {
			percent_enemies_killed >= 50
			enemy_side.percent_enemies_killed >= 50
		}
		OR = {
			enemy_side.side_max_army_size >= bc_our_host_gap_value
			side_max_army_size >= bc_their_host_gap_value
		}
		combat = { warscore_value >= 25 }
		bc_was_wipe_trigger = yes
		has_game_rule = bc_aftermath_generous
	}
}
```

**One row, worth one point.** A wipe does not make a battle notable by itself; it makes a
battle notable combined with any single other row, which every wipe will already satisfy on
blood or warscore. That is the design, and it is the reason this is a scripted trigger rather
than two bare rows.

**A nested scripted trigger counting as one row is normally the hazard the header warns
about, and here it is the mechanism.** See "The wipe row is a scripted trigger" in this
plan's preamble before you decide the header forbids this.

**Placement inside `calc_true_if` does not matter to the engine** — `calc_true_if` counts,
it does not order. It is placed with the substantive rows and above the game rule because the
game rule is the off-ramp and reads last.

- [x] **Step 3: Update the header comment**

Find the line beginning `# Five substantive rows plus the game rule.` and replace that
sentence with:

```
# Six substantive rows plus the game rule. The two size rows nest, so the bar
# actually reads "huge, or big plus one other thing". Deliberate: thirty
# thousand men on a field is notable whatever else happened. It also means the
# blood, odds and warscore rows never decide the largest battles, so read their
# calibration ladders against the sub-huge population.
#
# THE SIXTH ROW - bc_was_wipe_trigger - WAS ADDED AFTER THE 2026-08-13
# CALIBRATION AND IS NOT IN THAT SAMPLE. The 39 battles below were measured
# before scope:wipe was read at all, so the ladders describe a five-row trigger.
# A wipe is worth one point of the two, so the row cannot raise the pass rate on
# its own; it can only promote a battle that already had one other row. Re-run
# the calibration if that assumption is ever questioned - do not adjust the
# thresholds to compensate for it.
```

**Leave the four calibration ladders and the "Re-derive by restoring the ladders from git
history" line exactly as they are.** They are a measurement, not a description, and they are
still accurate for the rows they name.

**This is the comment plan 4 task 9 step 2 told you not to touch.** Plan 4 adds a trigger to
this file and changes no rows; plan 5 adds a row. If plan 4 has not shipped yet, its
instruction will still be correct when it does — it refers to the count, and the count is
now six.

- [x] **Step 4: Verify the row count changed and nothing else did**

```bash
cd /d/ck3/mods/battle_chronicles
sed -n '/^bc_battle_is_notable_trigger = {/,/^}/p' common/scripted_triggers/bc_scripted_triggers.txt | grep -c "^[[:space:]][[:space:]][a-zA-Z]"
grep -c "Five substantive rows" common/scripted_triggers/bc_scripted_triggers.txt
grep -c "Six substantive rows" common/scripted_triggers/bc_scripted_triggers.txt
```

Expected: **8**, then **0**, then **1**.

The first count is `amount >= 2` plus **seven** direct children that begin at two tabs — six
before this task plus `bc_was_wipe_trigger = yes`. It was 7 in step 1 and must be 8 now; if it
is still 7 the row went inside one of the `OR` blocks, where it would be an alternative to a
blood or odds test rather than a row of its own.

```bash
cd /d/ck3/tools && python ck3.py validate --strict
```

Expected: exit 0.

- [x] **Step 5: Commit**

```bash
cd /d/ck3/mods/battle_chronicles
git add common/scripted_triggers/bc_scripted_triggers.txt
git commit -m "feat: an annihilation is a notability row

One row worth one point, not a short-circuit: a wipe promotes a battle that
already had one other row, which every wipe satisfies on blood or warscore.
Updated the row-count comment, which was load-bearing for the amount >= 2 bar,
and recorded that the sixth row postdates the 39-battle calibration."
```

---

### Task 3: A wipe advances the style streak by two

**Files:**
- Modify: `mods/battle_chronicles/common/script_values/bc_script_values.txt`
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_reputation_effects.txt`

**Depends on plan 3.** If `bc_reputation_effects.txt` does not exist, plan 3 has not shipped
and this task cannot run. Skip to task 4 and come back.

- [x] **Step 1: Write the script value**

Append to `common/script_values/bc_script_values.txt`:

```
# --- B's streak step ---------------------------------------------------------
#
# TWO ON A WIPE, ONE OTHERWISE, AND IT IS READ IN EXACTLY ONE PLACE - the MATCH
# branch of bc_style_streak_effect. The two CREATE branches stay a literal 1.
#
# THE ASYMMETRY WITH C IS DELIBERATE AND IS THE WHOLE MECHANISM. C's counter uses
# its step in the create branch too, because it is a tally of damage done to you
# and the first blow's severity is exactly the thing being counted. A STREAK is a
# claim about repetition, and nothing has repeated on the first battle. Because
# the create branch stays 1, "two wipes fought the same way earn the trait" is
# true: the first wipe is a mismatch, creates the streak at 1, the second matches
# and adds 2, reaching the threshold of 3. Use the step in the create branch and
# it becomes "one wipe plus one mismatch", which is a different feature.
#
# THE TERRAIN STREAK IS NOT AFFECTED AND MUST NOT BE. Its threshold is 2, so a
# by-2 step would award a terrain trait from a single battle and reopen exactly
# the budget problem plan 3's award-ordering rule exists to close.
bc_style_step_value = {
	if = {
		limit = { bc_was_wipe_trigger = yes }
		value = 2
	}
	else = {
		value = 1
	}
}
```

**A full if/else of bare `value = X` with no base value outside is shipped vanilla** —
`swing_scales_discounts_multiplier_value`, `00_diarchy_values.txt:3224-3237`. Verified.

- [x] **Step 2: Wire it into the match branch, and only the match branch**

In `common/scripted_effects/bc_reputation_effects.txt`, find `bc_style_streak_effect` and
change **one line**:

```
	else_if = {
		limit = { var:bc_style_last = var:bc_battle_style }
		change_variable = { name = bc_style_streak add = bc_style_step_value }
		debug_log = "BC: style streak"
	}
```

**Nothing else in that effect changes.** The first and third branches keep
`set_variable = { name = bc_style_streak value = 1 }`, byte-identical to each other, for the
reason plan 3 records: the only difference between them is the guard, and there is no single
guard covering both that does not reintroduce a read of `var:bc_style_last` when it does not
exist.

**`change_variable = { add = <script value> }` is shipped vanilla.** Verified.

- [x] **Step 3: Verify the step lands in exactly one place**

```bash
cd /d/ck3/mods/battle_chronicles
grep -rn "bc_style_step_value" common/
grep -n "bc_style_streak value = 1" common/scripted_effects/bc_reputation_effects.txt
grep -n "bc_terrain_streak" common/scripted_effects/bc_reputation_effects.txt
```

Expected, in order:
- **two** hits — the definition in `bc_script_values.txt` and the single use in
  `bc_reputation_effects.txt`. A third hit means it reached a create branch.
- **two** hits — the two create branches, both still a literal 1.
- every `bc_terrain_streak` line still reading `1`. **A `bc_style_step_value` anywhere near
  a terrain line is the bug this step exists to catch.**

> **RUN CORRECTION (2026-08-14).** The bare count on the first grep is **three**. Task 1's own
> comment block names `bc_style_step_value` while explaining that the wipe trigger is
> scope-independent. Filter it — `grep -rn "bc_style_step_value" common/ | grep -v "#"` returns
> two. Same house rule plans 2, 3 and 4 each hit: any verification grep whose pattern appears
> in the shipped comment must be filtered, or anchored on call syntax.

```bash
cd /d/ck3/tools && python ck3.py validate --strict
```

Expected: exit 0.

- [x] **Step 4: Commit**

```bash
cd /d/ck3/mods/battle_chronicles
git add common/script_values/bc_script_values.txt \
        common/scripted_effects/bc_reputation_effects.txt
git commit -m "feat: a wipe advances the style streak by two

The create branches stay at 1 on purpose - a streak is a claim about repetition
and nothing has repeated on the first battle - which is what makes two wipes
fought the same way earn the trait rather than one wipe plus a mismatch. The
terrain streak is untouched: its threshold is 2 and a bonus would award from a
single battle."
```

---

### Task 4: Route C's step value through the named trigger

**Files:**
- Modify: `mods/battle_chronicles/common/script_values/bc_script_values.txt`

**Depends on plan 4.** If `bc_rivalry_step_value` does not exist, plan 4 has not shipped;
skip to task 5 and come back.

- [x] **Step 1: Understand that this changes no behaviour, and that that is the point**

**This task does not turn anything on.** `scope:wipe` is engine-provided on both combat-end
hooks — AGOT documents it at `common/on_action/combat_on_actions.txt:12` and `:527` — so
plan 4's step value has returned 2 on a wipe since the day plan 4 shipped. Nothing in this
mod ever "saved" the scope, and an earlier draft of both plans said otherwise.

Plan 4 wrote the test as an inline conjunction, character-for-character the body task 1 has
now given a name:

```
bc_rivalry_step_value = {
	if = {
		limit = {
			exists = scope:wipe
			trigger_if = {
				limit = { exists = scope:wipe }
				scope:wipe = yes
			}
		}
		value = 2
	}
	else = {
		value = 1
	}
}
```

**So this is a de-duplication, not a fix.** After task 1 there are two copies of the same
four-line conjunction about the same unsettled question — whether the scope always exists
carrying a boolean, or exists only when true. Two copies of an unsettled reading is exactly
the thing that diverges the next time someone learns the answer. Collapse them to one.

Verify the behaviour is unchanged rather than assuming it: the replacement is `= yes` on a
trigger whose body is the block above, so it is the same test by construction. If plan 4's
value does **not** look like the block above — if it is a bare `limit = { exists =
scope:wipe }` — you are looking at the pre-correction draft, and swapping it to the trigger
**does** change behaviour, in the direction of correctness. Say so in the commit message.

- [x] **Step 2: Replace the test**

```
bc_rivalry_step_value = {
	if = {
		limit = { bc_was_wipe_trigger = yes }
		value = 2
	}
	else = {
		value = 1
	}
}
```

Update plan 4's comment above it if it names `exists = scope:wipe`; the trigger is now the
single place the reading is decided, and both step values go through it.

- [x] **Step 3: Verify nothing else tests the scope directly**

```bash
cd /d/ck3/mods/battle_chronicles
grep -rn "scope:wipe" common/ events/ | grep -v "#"
```

Expected: **exactly three lines, all inside `bc_was_wipe_trigger`** — `exists = scope:wipe`,
the `limit`'s copy of it, and `scope:wipe = yes`. Every other reader goes through the trigger.
A fourth line is a second opinion about an unsettled question, and the two will diverge.

**The `grep -v "#"` is load-bearing.** Task 1's comment block explains the scope at length and
names it on three lines; task 4 step 2 may add a fourth. Without the filter this check reports
its own documentation as a failure.

```bash
cd /d/ck3/tools && python ck3.py validate --strict
```

Expected: exit 0.

- [x] **Step 4: Commit**

```bash
cd /d/ck3/mods/battle_chronicles
git add common/script_values/bc_script_values.txt
git commit -m "refactor: route the rivalry step through bc_was_wipe_trigger

Plan 4 inlined the same exists + trigger_if conjunction this trigger now wraps,
so behaviour is unchanged - the wipe step has been live since plan 4 shipped,
because scope:wipe is engine-provided rather than something a script saves.

The point is that the mod now has exactly one opinion about the unsettled
question of whether the scope always exists carrying a boolean or exists only
when true. Two copies of that guess would have diverged the moment someone
learned the answer."
```

---

### Task 5: The dead knights

**Files:**
- Modify: `mods/battle_chronicles/events/bc_aftermath_events.txt`
- Modify: `mods/battle_chronicles/localization/english/bc_l_english.yml`

- [x] **Step 1: Record the localization baseline**

```bash
cd /d/ck3/mods/battle_chronicles
grep -c "^ bc_\|^ rule_bc_\|^ setting_bc_" localization/english/bc_l_english.yml
```

**Write the number down.** Task 8 step 4 checks the total rose by exactly 9 across both
localization tasks in this plan, and that is not a check you can run without the number from
before.

- [x] **Step 2: Understand why this is a presence test and not an iteration**

The graders filter `every_side_knight` with `is_alive = yes`, which silently drops exactly
the knights whose deaths were worth telling.

**The fix is not a second iteration.** A liege who lost six knights should be told once, and
CK3 script cannot group an iteration by an arbitrary key — there is no way to fan the dead
out into one toast per distinct liege. **It does not need to:** on a combat side the knights
are the side commander's, so **one toast raised once on `side_commander` is already one per
liege.** Written as `any_side_knight = { is_alive = no }`, a trigger, with no iteration at
all.

**The toast names no individual knight.** That is the price of aggregating and it is why the
localization budget is two keys rather than one per name.

**A side whose commander is absent gets no toast**, which is correct: there is nobody to
tell. That is what the `?=` expresses.

- [x] **Step 3: Add the block to both graders**

In `events/bc_aftermath_events.txt`, add to **both** `bc_chronicles.0091` and
`bc_chronicles.0092`, **inside the notability gate** and **outside the
`exists = scope:bc_battle_province` gate**:

```
			# --- the knights who did not come back ----------------------
			#
			# A PRESENCE TEST, NOT AN ITERATION. One aggregate toast per
			# battle per liege. CK3 cannot group an iteration by an arbitrary
			# key, so there is no way to fan the dead out into one toast per
			# distinct liege - and no need, because on a combat side the
			# knights are the side commander's, so raising it once on him is
			# already once per liege.
			#
			# THE SAVE_SCOPE_AS IS NOT OPTIONAL. bc_addressed_toast_effect
			# writes left_icon = $SUBJECT$, a scripted effect does not rebind
			# ROOT, and its liege arm has already changed scope by the time
			# left_icon is evaluated - so SUBJECT must be a saved scope, never
			# `this`.
			#
			# event_toast_effect_bad. This and plan 4's rivalry toast are the
			# reason TYPE is a parameter of bc_addressed_toast_effect at all.
			#
			# OUTSIDE THE PROVINCE GATE, INSIDE THE NOTABILITY GATE. A battle
			# whose location does not resolve still killed knights, so the
			# province gate must not swallow this. The notability gate must
			# not be escaped: without it every skirmish in the world raises a
			# toast on somebody.
			#
			# NO is_alive GATE ON THE COMMANDER, unlike everything else in
			# this event. A commander who fell with his knights is exactly the
			# case worth telling, and bc_addressed_toast_effect routes a dead
			# man's toast to his liege because a dead character is never
			# human. Adding is_alive = yes here would silence the worst day
			# the side had.
			if = {
				limit = { any_side_knight = { is_alive = no } }
				side_commander ?= {
					save_scope_as = bc_bereaved_commander
					debug_log = "BC: dead knights"
					bc_addressed_toast_effect = {
						TYPE = event_toast_effect_bad
						TITLE = bc_dead_knights_toast
						DESC = bc_dead_knights_toast_desc
						SUBJECT = scope:bc_bereaved_commander
					}
				}
			}
```

**`any_side_knight` is a real trigger** — `triggers.log:10838`, `any_side_knight = { <count> <triggers> }`.

**Both graders get it, with identical text.** The winner also loses knights, and a winner
told nothing about his dead is the same gap on the other side.

- [x] **Step 3b: Add the wipe marker to both graders**

**Nothing else in this plan can write `BC: wipe`.** `bc_was_wipe_trigger` is a trigger, and a
trigger cannot hold a `debug_log`; its three consumers are a `calc_true_if` row and two script
values, all of which are trigger or value context too. Without this step task 11 step 5 probes
for a marker that no code emits, and a wipe that never appears would be indistinguishable from
a wipe that never happened.

In `events/bc_aftermath_events.txt`, add to **both** `bc_chronicles.0091` and
`bc_chronicles.0092` as the **first thing in `immediate`**, above the existing
`if = { limit = { bc_battle_is_notable_trigger = yes } ... }`:

```
		# --- measurement only ------------------------------------------------
		#
		# OUTSIDE THE NOTABILITY GATE ON PURPOSE, unlike the dead-knight block
		# below. This marker exists to answer two questions no static check can:
		# how often a wipe actually happens, and whether both sides agree it did.
		# Gating it on notability would only ever show wipes that were already
		# going to be notable, which is the population the row cannot affect.
		#
		# NO STATE. This writes nothing and reads nothing but scope:wipe. It is
		# the same kind of row as the calibration markers, and it stays.
		if = {
			limit = { bc_was_wipe_trigger = yes }
			debug_log = "BC: wipe"
		}
```

**Identical in both graders.** A marker on one side only would make every wipe look asymmetric
and would falsify the one thing task 11 step 5 is checking for.

**Two tabs**, matching the sibling `if` below it — `immediate` is at one tab inside the event.

- [x] **Step 4: Add the two localization keys**

Append to `localization/english/bc_l_english.yml`. **One leading space per line.**

```
# --- the dead ---------------------------------------------------------------

 bc_dead_knights_toast:0 "They Did Not All Come Back"
 bc_dead_knights_toast_desc:0 "Some of the men who rode out under [bc_bereaved_commander.GetName]'s banner are still on that field. The heralds will have their names by morning."
```

**The desc names no knight**, deliberately — there is no iteration to name one from, and
"the heralds will have their names by morning" is the sentence that makes the absence read
as restraint rather than as a gap.

- [x] **Step 5: Verify the placement**

```bash
cd /d/ck3/mods/battle_chronicles
grep -c "bc_dead_knights_toast" events/bc_aftermath_events.txt
grep -c "TITLE = bc_dead_knights_toast$" events/bc_aftermath_events.txt
grep -c "any_side_knight" events/bc_aftermath_events.txt
grep -n "bc_bereaved_commander" events/bc_aftermath_events.txt localization/english/bc_l_english.yml
grep -c 'debug_log = "BC: wipe"' events/bc_aftermath_events.txt
```

Expected: **4**, then **2**, then **2**, then **five** lines, then **2**.

**Four, not two.** `bc_dead_knights_toast_desc` contains `bc_dead_knights_toast` as a
substring, so each grader contributes two matching lines — the `TITLE` and the `DESC`. The
second grep is the one that actually counts graders: the `$` anchor excludes the `_desc` line,
so it must be exactly **2**, one per grader.

`any_side_knight` is **2**, one per grader. The existing `every_side_knight` iterations do not
contain the substring and are not counted.

`bc_bereaved_commander` is **five** lines — two `save_scope_as`, two `SUBJECT =`, one loc key.
The comment block added in step 3 does not name the scope, deliberately, so this count stays
readable without filtering.

Then read both graders by eye and confirm, for each:

| check | why it matters |
|---|---|
| the block sits **inside** `limit = { bc_battle_is_notable_trigger = yes }` | outside it, every skirmish in the world raises a toast |
| the block sits **outside** `limit = { exists = scope:bc_battle_province }` | inside it, a battle whose location does not resolve loses its dead |
| the block is **not** inside any `every_side_knight` | inside one, it fires once per surviving knight |
| the `BC: wipe` marker sits **outside** the notability gate, as the first thing in `immediate` | inside it, the marker only ever reports wipes that were already notable, which is the population the new row cannot affect |

```bash
cd /d/ck3/tools && python ck3.py validate --strict
```

Expected: exit 0, and nothing else. **Do not read this as confirming the loc keys.**
`ck3lib/validate.py:182-185` checks top-level definition keys only, and only in the three
categories at `:37` — `common/traits`, `common/decisions`,
`common/character_interactions`. A key referenced from an event's toast is in none of them,
so `--strict` is silent about `bc_dead_knights_toast` whether it exists or not. The four
counts at the top of this step are the check.

- [x] **Step 6: Commit**

```bash
cd /d/ck3/mods/battle_chronicles
git add events/bc_aftermath_events.txt localization/english/bc_l_english.yml
git commit -m "feat: tell a commander when his knights did not come back

A presence test rather than a second iteration: CK3 cannot group an iteration by
liege, and it does not need to, because on a combat side the knights are the
commander's - so one toast on him is already one per liege. No is_alive gate on
the commander, because a commander who fell with his knights is the case most
worth telling.

Also adds the BC: wipe marker to both graders, outside the notability gate. It
is the only place in the mod that can emit one - bc_was_wipe_trigger is a
trigger and all three of its consumers are trigger or script-value context."
```

---

**STOP HERE IF DIAG Q2 FAILED.** Tasks 6 through 9 are the eve. If plan 1's task 14 recorded
that `BC: DIAG Q2 combat-scoped event fired` never appeared, `events/bc_combat_start_events.txt`
does not exist, `on_combat_start` was never claimed, and there is nothing to build on. Go
straight to task 10, and skip its eve-specific steps.

> **RUN CORRECTION (2026-08-14) — STOPPED HERE. THE GATE ABOVE IS THE WRONG GATE.**
>
> Q2 has **two** halves and this plan only checks one of them. The half it checks passed: the
> `scope = combat` event fired 152 times. The half it does not check **failed**, and it is the
> half tasks 6-9 are built on.
>
> `combat_attacker.side_commander` and `combat_defender.side_commander` were both probed as
> `combat_<side>.side_commander ?= { debug_log = ... }` across those same 152 fires and **both
> logged zero**. The `?=` swallowed it in silence. The mod file this plan proposes to overwrite
> records the finding in its own header and states the conclusion outright: *"an eve pop-up
> CANNOT reach the two sides through those links."*
>
> **Task 7 step 3 is written entirely on those two links.** As drafted the eve would log
> `BC: eve fired` on every large battle and then do nothing — no saves, no offers, no pop-up —
> and task 11 step 4's table would read that as the second row, "inconclusive, fight another
> one", forever.
>
> Two further drift items in the same tasks, both minor next to the above:
> - The shell logs **`BC: combat start`**, not `BC: DIAG Q2 combat-scoped event fired`. Task 11
>   step 2's `probe "eve"` is unaffected; the gate wording above is what is stale.
> - The shell event is still **`bc_chronicles.0900`** and `on_combat_start` still names it, so
>   task 9 step 2's `grep -rn "bc_chronicles.0900"` expecting no output requires task 7 to have
>   actually replaced it.
>
> **A route the plan did not consider: `every_combat_side`** — supported scope `combat`,
> target `combat_side`, confirmed in the 1.19.0.6 API dump. Paired with `enemy_side`, which
> `bc_battle_is_notable_trigger` already uses, it reaches both commanders and each one's foe
> without the two-pass ordering the plan needs. **It is unproven from a `scope = combat` event
> in exactly the way the failed links were**, so it must ship behind its own marker and be
> measured, per the mod file's own instruction: *"whichever route is chosen must be proven with
> its own marker before anything is built on it."*
>
> Tasks 1-5 are complete and committed. Tasks 6-9 need this decision before they can be
> written.

---

### Task 6: The cooldown and the read-back trigger

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_scripted_effects.txt`
- Modify: `mods/battle_chronicles/common/scripted_triggers/bc_scripted_triggers.txt`

- [x] **Step 1: Add the cooldown effect**

Append to `common/scripted_effects/bc_scripted_effects.txt`, immediately after
`bc_start_popup_cooldown_effect`:

```
# --- the eve's own throttle -------------------------------------------------
# 90 days, and a SEPARATE FLAG from bc_popup_cooldown on purpose.
#
# Sharing the 60-day pop-up cooldown would starve the mid-battle chronicles: the
# eve fires FIRST, every time, before a single phase event has rolled, so it would
# consume the budget before the battle began and the player would never see a
# moment from inside a fight again.
#
# Longer than 60 because the eve is rarer by construction - it needs a 5000-man
# battle - and because two eves in a season reads as a tic rather than as an
# occasion.
#
# A FLAG, not a modifier, for the reason bc_start_popup_cooldown_effect records:
# modifiers are wiped at combat end, so a modifier-based lockout silently resets
# every battle.
bc_start_eve_cooldown_effect = {
	add_character_flag = {
		flag = bc_eve_cooldown
		days = 90
	}
}
```

- [x] **Step 2: Add the read-back trigger**

Append to `common/scripted_triggers/bc_scripted_triggers.txt`:

```
# --- is the man across the field the one who has beaten me before -----------
#
# THE EVE'S read-back, and it is NOT bc_facing_nemesis_trigger. That one reads
# var:bc_battle_foe, which bc_battle_open_effect writes in a PHASE EVENT's effect
# - and at on_combat_start no phase event has rolled, so bc_battle_foe still holds
# nothing or holds the LAST battle's foe. Using it here would be silently wrong on
# every eve.
#
# THE EVE DOES NOT NEED IT. on_combat_start runs at combat scope, so task 7's
# hidden event reaches BOTH commanders directly and saves each side's man before
# offering. scope:bc_eve_foe is therefore this battle's opposing commander,
# known exactly, with no phase event involved. The eve is the one place in the mod
# that has the real answer rather than a one-roll-stale one.
#
# CALLED ON THE COMMANDER, in a TRIGGER context - an event desc branch. It must be
# safe for a commander who has no nemesis, which is nearly all of them, and safe
# when the other side is leaderless and nothing saved the scope.
#
# THE TWO `exists` ROWS ARE SAFE AS SIBLINGS. `exists` on a missing variable or a
# missing scope is safe; only a READ has to be nested, which is what the
# trigger_if does.
bc_eve_facing_nemesis_trigger = {
	exists = var:bc_nemesis
	exists = scope:bc_eve_foe
	trigger_if = {
		limit = {
			exists = var:bc_nemesis
			exists = scope:bc_eve_foe
		}
		var:bc_nemesis = scope:bc_eve_foe
	}
}
```

**No `is_alive` row.** The eve's foe is commanding a battle that is starting, so he is alive
by construction — unlike plan 4's trigger, which reads a variable that can outlive its
subject.

**If plan 4 has not shipped, `var:bc_nemesis` never exists** and this trigger is a permanent
`no`. That is safe and the eve simply always shows the stranger text. It is not a reason to
delay the eve.

- [x] **Step 3: Validate and commit**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
```

Expected: exit 0.

```bash
cd /d/ck3/mods/battle_chronicles
git add common/scripted_effects/bc_scripted_effects.txt \
        common/scripted_triggers/bc_scripted_triggers.txt
git commit -m "feat: add the eve cooldown and its own nemesis read-back

A separate 90-day flag rather than the 60-day pop-up cooldown, because the eve
fires before any phase event and would otherwise consume the budget before the
battle began. The read-back is a second trigger rather than plan 4's, because
bc_battle_foe is written by a phase event and holds the last battle's foe at
on_combat_start."
```

---

### Task 7: The hidden combat event and the offer

**Files:**
- Modify: `mods/battle_chronicles/events/bc_combat_start_events.txt`
- Create: `mods/battle_chronicles/common/scripted_effects/bc_eve_effects.txt`

- [x] **Step 1: Read what plan 1 left behind**

```bash
cd /d/ck3/mods/battle_chronicles
cat events/bc_combat_start_events.txt
```

Plan 1 task 16 step 2 renamed `bc_diag_events.txt` to this and stripped `bc_chronicles.0900`
to a shell that logs `BC: DIAG Q2 combat-scoped event fired` and nothing else. **The shell is
the proof that this event shape works**; task 7 replaces it rather than adding beside it.

- [x] **Step 2: Write the offer effect**

Create `common/scripted_effects/bc_eve_effects.txt`. **UTF-8, no BOM** — script files in this
mod carry no BOM; only the localization file does.

```
# Battle Chronicles - the eve.
#
# THE ONLY EFFECT IN THIS MOD CALLED FROM A `scope = combat` CONTEXT. Everything
# else runs on a character, a combat side, or inside a phase event. Nothing in
# vanilla or AGOT declares `scope = combat` - `scope = combat_side` is universal,
# 30 declarations across both - so this whole path exists because DIAG Q2 measured
# that it works, not because anything shipped proves it.
#
# CALLED ON THE COMMANDER. The caller has already stepped into
# combat_attacker.side_commander or combat_defender.side_commander with `?=`, so a
# leaderless side never reaches this.
#
# FOE IS A SCOPE, PASSED AS A PARAMETER, AND MAY NOT EXIST. A side can be
# leaderless, in which case the caller never saved it. `exists = $FOE$`
# substitutes to `exists = scope:bc_eve_defender`, which is safe on a missing
# scope; the SAVE below is the read that has to be guarded.
#
# THE COOLDOWN IS TAKEN BEFORE THE EVENT IS RAISED, not in the event. An event
# raised on a character is not guaranteed to have been answered - or even opened -
# by the time anything else runs, and the throttle is about how often the mod
# INTERRUPTS, not about how often the player replies.
#
# is_ai = no IS NOT POLISH. on_combat_start fires for EVERY combat in the world.
# Without this row the hook raises a character_event on every AI commander of
# every qualifying battle on the map. The mod's existing pop-ups are gated the
# same way (bc_scripted_triggers.txt:93-96) for the same reason.
#
# NOT bc_can_interrupt_player_trigger. That trigger tests bc_popup_cooldown, which
# is the mid-battle budget the eve must not spend. The two rows are written out
# here so that the two throttles cannot be accidentally merged later.
bc_eve_offer_effect = {
	if = {
		limit = {
			is_ai = no
			NOT = { has_character_flag = bc_eve_cooldown }
		}
		if = {
			limit = { exists = $FOE$ }
			$FOE$ = { save_scope_as = bc_eve_foe }
		}
		bc_start_eve_cooldown_effect = yes
		debug_log = "BC: eve offered"
		trigger_event = bc_chronicles.0011
	}
}
```

**`save_scope_as = bc_eve_foe` runs on the commander who is about to be asked**, so the scope
belongs to that event chain and the pop-up's `desc` can read it. It is saved before
`trigger_event`, not after, because a scope saved after the raise is not in the raised
event's chain.

- [x] **Step 3: Replace the shell with the real hidden event**

In `events/bc_combat_start_events.txt`, replace `bc_chronicles.0900` entirely:

```
namespace = bc_chronicles

# Battle Chronicles - the eve of a battle.
#
# ROOT IS THE COMBAT. This file holds the only `scope = combat` event in the mod.
# Nothing in vanilla or AGOT declares that scope; DIAG Q2 measured that it fires.
# If this file ever stops producing `BC: eve fired`, the scope is the first
# suspect and nothing else in the mod is affected.
#
# on_combat_start is EMPTY in the loaded file - AGOT combat_on_actions.txt:3-4 is
# a bare `on_combat_start = { }`. An entirely unclaimed hook.

# ---------------------------------------------------------------------------
# The eve. Hidden, combat-scoped, raised by on_combat_start.
# ---------------------------------------------------------------------------
bc_chronicles.0010 = {
	hidden = yes
	scope = combat

	# THE CHEAP ORDER. Both rows are evaluated at combat scope, before anything
	# iterates or steps into a character. The size gate rejects the overwhelming
	# majority of the world's combats in one trigger.
	#
	# num_total_troops IS WRITTEN BARE HERE, and this is the one place in the mod
	# where that is right: it is scope `combat` (triggers.log:9537-9540) and Root
	# IS the combat. bc_battle_is_notable_trigger has to write
	# `combat = { num_total_troops }` only because it starts from a combat SIDE.
	#
	# 5000, DELIBERATELY HALF THE NOTABILITY FLOOR OF 10000. A battle can be worth
	# an eve without turning out to be worth remembering, and the eve has to decide
	# before anyone knows which it is.
	#
	# NO OWN GAME RULE. bc_aftermath_off is the mod's "no combat-end and no
	# combat-start ceremony" switch and the eve is ceremony.
	trigger = {
		NOT = { has_game_rule = bc_aftermath_off }
		num_total_troops >= 5000
	}

	immediate = {
		debug_log = "BC: eve fired"

		# BOTH SIDES ARE REACHED because either commander may be the player -
		# and at most one can be, so the two blocks cannot both fire for the
		# same person.
		#
		# EACH SIDE'S COMMANDER IS SAVED BEFORE EITHER IS OFFERED. The offer
		# needs the OTHER side's man, so both saves must happen first;
		# interleaving them would leave the attacker's offer with no defender
		# scope on the first pass.
		#
		# combat_attacker / combat_defender are event_targets.log:1054 and
		# :1060, both returning a combat side, and side_commander is :1415.
		combat_attacker.side_commander ?= {
			save_scope_as = bc_eve_attacker
		}
		combat_defender.side_commander ?= {
			save_scope_as = bc_eve_defender
		}

		combat_attacker.side_commander ?= {
			bc_eve_offer_effect = { FOE = scope:bc_eve_defender }
		}
		combat_defender.side_commander ?= {
			bc_eve_offer_effect = { FOE = scope:bc_eve_attacker }
		}
	}
}
```

**Two passes over the two commanders, not one.** The offer needs the opposing commander's
scope, and a single interleaved pass would run the attacker's offer before the defender was
ever saved. The second pass costs two scope resolutions on a combat that has already passed
the size gate.

**`scope:bc_eve_attacker` and `scope:bc_eve_defender` are saved on the commanders but live in
the event's chain**, which is why the second pass can read the one saved in the first.

- [x] **Step 4: Validate and commit**

```bash
cd /d/ck3/tools && python ck3.py validate --strict && python ck3.py index && python ck3.py conflicts
```

Expected: all exit 0. `conflicts` is run here because this task adds a file.

```bash
cd /d/ck3/mods/battle_chronicles
git add events/bc_combat_start_events.txt common/scripted_effects/bc_eve_effects.txt
git commit -m "feat: raise the eve on both commanders of a large battle

Two passes over the two commanders rather than one, because the offer needs the
opposing commander's scope and a single interleaved pass would run the
attacker's offer before the defender had been saved. The size gate is written
bare because Root is the combat here - the one place in the mod where that is
true."
```

---

### Task 8: The pop-up

**Files:**
- Modify: `mods/battle_chronicles/events/bc_combat_start_events.txt`
- Modify: `mods/battle_chronicles/localization/english/bc_l_english.yml`

- [x] **Step 1: Write the event**

Append to `events/bc_combat_start_events.txt`:

```
# ---------------------------------------------------------------------------
# The eve, as the player sees it. A character_event on the commander.
#
# THE ONLY MOMENT IN THE MOD WHERE THE PLAYER COMMITS AHEAD OF KNOWING ANYTHING.
# Every other choice answers something that has already happened.
#
# TWO OPTIONS APPLY A FAMILY-2 MODIFIER BY NAME, and these are the only call sites
# in the mod that do. Everywhere else the (KIND, SWING) table inside
# bc_record_moment_effect decides which modifier a moment implies. There is no
# moment here - nothing has happened yet - so there is no seam call to route
# through and the option names the posture directly. It still goes through
# bc_add_verb_effect rather than add_character_modifier, so the 20-day duration
# stays in one place per family.
#
# NO OPTION APPLIES MOMENTUM. The battle has not started. The eve is about shape,
# not advantage, and momentum is the tide.
#
# THE THIRD OPTION IS NOT FREE. Declining to commit is a choice, and a commander
# who never commits should not be indistinguishable from one who does.
# ---------------------------------------------------------------------------
bc_chronicles.0011 = {
	type = character_event
	title = bc_chronicles.0011.t
	theme = martial

	# first_valid, not a bare desc. The nemesis branch is the read-back plan 4
	# promises and the eve is the cheapest place in the mod to deliver it - one
	# desc branch, no new event, no new state.
	desc = {
		desc = bc_chronicles.0011.desc_intro
		first_valid = {
			triggered_desc = {
				trigger = { bc_eve_facing_nemesis_trigger = yes }
				desc = bc_chronicles.0011.desc_nemesis
			}
			desc = bc_chronicles.0011.desc_stranger
		}
	}

	left_portrait = {
		character = root
		animation = personality_bold
	}

	immediate = {
		debug_log = "BC: eve popup 0011"
	}

	option = {
		name = bc_chronicles.0011.a

		bc_add_verb_effect = { MODIFIER = bc_bloodied }
		add_stress = 10
	}

	option = {
		name = bc_chronicles.0011.b

		bc_add_verb_effect = { MODIFIER = bc_shieldwall }
	}

	option = {
		name = bc_chronicles.0011.c

		add_prestige = -25
	}
}
```

**No `trigger` on the event.** Both gates were taken in `bc_eve_offer_effect` before the raise
— re-testing them here would let a commander who passed the gate lose the event to a race
and take the cooldown for nothing.

- [x] **Step 2: Write the seven localization keys**

Append to `localization/english/bc_l_english.yml`. **One leading space per line.**

```
# --- the eve ----------------------------------------------------------------

 bc_chronicles.0011.t:0 "First Light"
 bc_chronicles.0011.desc_intro:0 "The host is formed up before the sun is properly over the ridge. Whatever is decided now will have to be lived with all day."
 bc_chronicles.0011.desc_nemesis:0 "And across the field, under the other banner, is [bc_eve_foe.GetName]. [ROOT.Char.GetFirstName] has been here before, against this man, and it did not go well."
 bc_chronicles.0011.desc_stranger:0 "Across the field the other host is still dressing its lines. Nobody over there is anybody [ROOT.Char.GetFirstName] knows."
 bc_chronicles.0011.a:0 "Press them at first light."
 bc_chronicles.0011.b:0 "Hold the ground and let them come."
 bc_chronicles.0011.c:0 "Wait. See how they form up."
```

**`[bc_eve_foe.GetName]` appears only in the nemesis branch**, which
`bc_eve_facing_nemesis_trigger` reaches only when the scope exists. A loc key that names a
scope which was never saved renders as an empty string with no error, so this is a
presentation bug rather than a crash — but the trigger already prevents it and the two must
stay in step.

- [x] **Step 3: Verify the desc branches resolve**

```bash
cd /d/ck3/mods/battle_chronicles
grep -c "bc_chronicles.0011" events/bc_combat_start_events.txt
grep -c "^ bc_chronicles.0011" localization/english/bc_l_english.yml
grep -rn "bc_eve_foe" events/ common/ localization/ | grep -v "#"
```

Expected: **8** in the event file (1 declaration + 7 key references), **7** in the
localization file, and `bc_eve_foe` on exactly **five** code lines:

| file | lines | what |
|---|---|---|
| `common/scripted_effects/bc_eve_effects.txt` | 1 | `$FOE$ = { save_scope_as = bc_eve_foe }` |
| `common/scripted_triggers/bc_scripted_triggers.txt` | 3 | the bare `exists`, the `limit`'s copy of it, and the comparison |
| `localization/english/bc_l_english.yml` | 1 | `[bc_eve_foe.GetName]` in `desc_nemesis` |

**Three rows in the trigger, not two** — the guard duplicates the `exists`, which is the whole
shape. The `grep -v "#"` drops task 6's comment block, which names the scope once while
explaining why the eve does not use plan 4's trigger.

The 8 counts only `events/bc_combat_start_events.txt`; `trigger_event = bc_chronicles.0011`
lives in `bc_eve_effects.txt` and is a ninth reference in a different file, and
`"BC: eve popup 0011"` does not contain the full string.

A `bc_eve_foe` in a desc the trigger does not guard is the bug this step exists to catch.

- [x] **Step 4: Verify the total key count**

```bash
cd /d/ck3/mods/battle_chronicles
grep -c "^ bc_\|^ rule_bc_\|^ setting_bc_" localization/english/bc_l_english.yml
head -c 8 localization/english/bc_l_english.yml | cat -A
```

Against the baseline recorded in task 5 step 1, the count must have risen by exactly **9** —
2 from task 5, 7 from here. The BOM must still be present (`M-oM-;M-?`); editors strip it
silently, which is why it is checked after the edits as well as before.

- [x] **Step 5: Validate and commit**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
```

Expected: exit 0, and nothing else. **`--strict` cannot see event loc keys.**
`ck3lib/validate.py:182-185` checks top-level definition keys in the three categories at
`:37` only — `common/traits`, `common/decisions`, `common/character_interactions`. `events/`
is not among them, so an event `desc` pointing at a key that does not exist passes this
command cleanly and renders its raw key in the pop-up. Step 3's 8-and-7 pairing is the
check that catches it.

```bash
cd /d/ck3/mods/battle_chronicles
git add events/bc_combat_start_events.txt localization/english/bc_l_english.yml
git commit -m "feat: add the eve pop-up

Three opening postures, two of which name a family-2 modifier directly - the
only call sites in the mod that do, because there is no moment before the
battle starts and therefore no seam call to route through. The third is the
honest out and costs prestige, because declining to commit is a choice."
```

---

### Task 9: Claim `on_combat_start`

**Files:**
- Modify: `mods/battle_chronicles/common/on_action/bc_on_actions.txt`

- [x] **Step 1: Add the hook**

Append to `common/on_action/bc_on_actions.txt`, after `on_combat_end_loser`:

```
# Root = Combat. EMPTY in the loaded file - AGOT combat_on_actions.txt:3-4 is a
# bare `on_combat_start = { }` - so this is an entirely unclaimed hook and
# bc_chronicles.0010 is its only entry.
#
# events = { }, NOT effect = { }, for the reason at the top of this file: only
# the list forms merge across files, and file read order inside common/on_action
# is ALPHABETICAL rather than playset load order.
on_combat_start = {
	events = {
		bc_chronicles.0010
	}
}
```

**If plan 1 left an `on_combat_start` block here for the DIAG event, replace its entry rather
than adding a second one.** Two entries would raise both events on every combat, and
`bc_chronicles.0900` no longer exists.

- [x] **Step 2: Verify the hook and the event agree**

```bash
cd /d/ck3/mods/battle_chronicles
grep -n "on_combat_start" -A 4 common/on_action/bc_on_actions.txt
grep -rn "bc_chronicles.0900" --exclude-dir=.git .
grep -n "effect = {" common/on_action/bc_on_actions.txt | grep -v "#"
```

Expected: one `on_combat_start` block naming exactly `bc_chronicles.0010`; **no output** for
`.0900`; and **no output** for the third.

**RUN CORRECTION — the `.0900` grep is not silent, and must not be.** It returns one line,
`README.md:229`, inside the permanent DIAG Q2 record. That paragraph reports a *measurement* —
"`bc_chronicles.0900` fired 151 times" — and editing the name out of it would falsify what was
measured. The line was kept and the sentence amended to say the probe is retired and replaced
on the same hook by `bc_chronicles.0010`, so a future reader is not sent hunting for an event
that no longer exists. **One README hit is the pass condition; a hit under `common/` or
`events/` is the failure this step is actually looking for.**

**`--exclude-dir=.git` on the second.** It searches from the mod root, and this plan's own
commit messages discuss `.0900` — without the flag the check would report `.git` objects
and read as a failure once those commits exist. The `.` in `bc_chronicles.0900` is also a
regex any-character, which is harmless here and would matter if a key like
`bc_chronicles_0900` ever existed.

**The third grep must be filtered.** The file's own header warns against `effect = { }` and
quotes the string twice while doing so, so an unfiltered `grep -c` returns **2** on a correct
file and the check would fail forever on nothing.

**The last check is the one that has already cost a probe run.** An `effect = { }` in an
on_action does not merge — the engine keeps exactly one and logs
`[E][jomini_onaction.cpp:161]: There is more than one 'effect' defined using most recent`,
and "most recent" is decided alphabetically inside `common/on_action`, so
`bc_on_actions.txt` loses to `combat_on_actions.txt`.

- [x] **Step 3: Validate, deploy and commit**

```bash
cd /d/ck3/tools && python ck3.py validate --strict && python ck3.py index && python ck3.py conflicts && python ck3.py deploy
```

Expected: all exit 0.

```bash
cd /d/ck3/mods/battle_chronicles
git add common/on_action/bc_on_actions.txt
git commit -m "feat: claim on_combat_start for the eve

The hook is bare in the loaded file. events = { } rather than effect = { },
because only the list forms merge across files and file read order inside
common/on_action is alphabetical rather than playset load order."
```

---

### Task 10: Static verification

**Files:** none — this task only reads.

- [x] **Step 1: The wipe has exactly one reader**

```bash
cd /d/ck3/mods/battle_chronicles
grep -rn "scope:wipe" common/ events/ | grep -v "#"
grep -rn "bc_was_wipe_trigger" common/ events/ | grep -v "#"
```

The first must show **exactly three** lines, all inside `bc_was_wipe_trigger` — `exists`, the
`limit`'s copy, and the comparison. The second must show **four** — the definition, the
notability row, `bc_style_step_value`, and `bc_rivalry_step_value`.

**RUN CORRECTION — the second grep returns SIX, not four, and six is correct.** The plan's
count was written before task 5 existed in this form. The two extra lines are task 5's own
`BC: wipe` markers, `events/bc_aftermath_events.txt:67` and `:222`, one per grader. The full
correct census is: the definition (`bc_scripted_triggers.txt:282`), the notability row
(`:222`), `bc_style_step_value` (`bc_script_values.txt:187`), `bc_rivalry_step_value`
(`:160`), and the two markers. **Five would mean a grader lost its marker; four would mean
both did.**

**Both greps need the `grep -v "#"`.** Task 1's comment block names `scope:wipe` on three
lines, and task 2 step 3's replacement header names `bc_was_wipe_trigger` outright as the
sixth row. Unfiltered, this step fails on correct code.

**A second `scope:wipe` reader is a second opinion about an unsettled question.** Shipped
script uses both the `exists` and the `= yes` idiom and it is not known which reading is
correct; the whole point of the trigger is that the mod commits to one place.

- [x] **Step 2: The three step rules did not converge**

```bash
cd /d/ck3/mods/battle_chronicles
grep -n "^bc_style_step_value\|^bc_rivalry_step_value" common/script_values/bc_script_values.txt
grep -rn "bc_style_step_value" common/scripted_effects/ | grep -v "#"
grep -rn "bc_rivalry_step_value" common/scripted_effects/ | grep -v "#"
grep -rn "bc_terrain_streak" common/scripted_effects/
```

| grep | expected | what a miss means |
|---|---|---|
| definitions | one line each | one was deleted or duplicated |
| `bc_style_step_value` uses | **exactly one**, the match branch of `bc_style_streak_effect` | it reached a create branch, and "two wipes earn the trait" became "one wipe plus a mismatch" |
| `bc_rivalry_step_value` uses | **exactly four**, all in `bc_rivalry_effects.txt` — the create branch, the escalate branch, the floor guard, the decrement | plan 4's count, unchanged by plan 5 |
| `bc_terrain_streak` lines | every step still a literal **1** | a terrain trait can now be won from a single battle |

**The `^` anchors and the `grep -v "#"` are both load-bearing.** The definitions sit at column
zero while every reference is indented, and plan 4's decrement carries a comment line reading
`# THE FLOOR GUARD IS \`<= bc_rivalry_step_value\`, NOT A CONSTANT` inside
`bc_rivalry_effects.txt` — unfiltered, that comment makes the correct count read five.

- [x] **Step 3: The notability trigger has six substantive rows and says so**

```bash
cd /d/ck3/mods/battle_chronicles
sed -n '/^bc_battle_is_notable_trigger = {/,/^}/p' common/scripted_triggers/bc_scripted_triggers.txt | grep -c "^[[:space:]][[:space:]][a-zA-Z]"
grep -c "Five substantive rows" common/scripted_triggers/bc_scripted_triggers.txt
grep -n "amount >= " common/scripted_triggers/bc_scripted_triggers.txt
```

Expected: **8** (`amount >= 2` plus **seven** direct children), **0**, and `amount >= 2`
**unchanged**. Task 2 step 1 recorded 7 before the change; anything but 8 here means the row
did not land as a direct child.

**The bar must not have moved.** Adding a row and raising the bar in the same change is how a
calibration silently becomes uncalibrated — the sample behind the four ladders was measured
against `amount >= 2` on five rows.

- [x] **Step 4: Every toast call names a TYPE**

```bash
cd /d/ck3/mods/battle_chronicles
grep -rc "bc_addressed_toast_effect = {" common/ events/ | grep -v ':0'
grep -rc "TYPE = event_toast_effect_" common/ events/ | grep -v ':0'
grep -rn "TYPE = event_toast_effect_" events/bc_aftermath_events.txt
```

**The first total must be exactly one MORE than the second, not equal to it.** The pattern
`bc_addressed_toast_effect = {` matches the effect's own definition line in
`bc_scripted_effects.txt` as well as every call site, and the definition does not pass a
`TYPE` to itself. One more means every caller named a type; equal means one caller is missing
its `TYPE` *and* something else is wrong; two more means a caller was dropped.

The third must show **two lines, both `event_toast_effect_bad`** — one dead-knight toast per
grader.

An omitted `TYPE` produces no error anywhere: CK3 substitutes parameters textually, the
literal string `type = $TYPE$` reaches `send_interface_toast`, and `validate` sees balanced
braces. **Only this count catches it.**

- [x] **Step 5: The eve's two throttles did not merge**

```bash
cd /d/ck3/mods/battle_chronicles
grep -rn "bc_eve_cooldown\|bc_popup_cooldown" common/
grep -rn "bc_can_interrupt_player_trigger" common/scripted_effects/bc_eve_effects.txt
```

`bc_eve_cooldown` must appear in exactly two places — the effect that sets it and the gate in
`bc_eve_offer_effect`. `bc_popup_cooldown` must appear nowhere in the eve's files. The second
grep must produce **no output**.

**RUN CORRECTION — both greps in this step need `grep -v "#"`.** `bc_eve_effects.txt:32`
opens a comment paragraph with the words `NOT bc_can_interrupt_player_trigger. That trigger
tests bc_popup_cooldown, which is the mid-battle budget the eve must not spend.` — a header
written for exactly the reason this step exists. Unfiltered, the file that documents the rule
hardest is the file that fails the check. Filtered, the run is clean: `bc_eve_cooldown` on two
code lines (`bc_eve_effects.txt:39` gate, `bc_scripted_effects.txt:208` setter) and
`bc_popup_cooldown` on none in the eve's files.

**If the eve ever tests `bc_can_interrupt_player_trigger`, it is spending the mid-battle
budget** — the eve fires first, every time, and would consume it before the battle began.

- [x] **Step 6: Every effect the eve calls actually exists**

```bash
cd /d/ck3/mods/battle_chronicles
for e in bc_add_verb_effect bc_start_eve_cooldown_effect bc_eve_offer_effect bc_addressed_toast_effect; do
  grep -rq "^$e = {" common/scripted_effects/ || echo "MISSING: $e"
done
for m in bc_bloodied bc_shieldwall; do
  grep -rq "^$m = {" common/modifiers/ || echo "MISSING MODIFIER: $m"
done
```

Expected: **no output.** `validate` does not resolve effect or modifier names, so a call to a
misspelled one passes cleanly and does nothing forever. Two `MISSING MODIFIER` lines mean
plan 2 has not shipped and the eve's first two options are silent no-ops.

- [x] **Step 7: No missing-variable or missing-scope read**

Read `bc_eve_effects.txt` and the two new triggers end to end. Every read must be nested:

| where | read | what makes it safe |
|---|---|---|
| `bc_was_wipe_trigger` | `scope:wipe = yes` | inside a `trigger_if` carrying `exists = scope:wipe` |
| `bc_eve_facing_nemesis_trigger` | `var:bc_nemesis = scope:bc_eve_foe` | inside a `trigger_if` carrying both `exists` rows |
| `bc_eve_offer_effect` | `$FOE$ = { save_scope_as = bc_eve_foe }` | inside `limit = { exists = $FOE$ }` |

**Three reads, three guards. If your read finds a fourth, it is new and it is unguarded.**

There is a fourth read that is **not script** and does not belong in the table:
`[bc_eve_foe.GetName]` in `bc_chronicles.0011.desc_nemesis`. Localization is not evaluated
under the missing-variable rule — a token naming a scope that was never saved renders as an
empty string and logs nothing. Its guard is structural: the key is only ever selected by the
`triggered_desc` whose trigger is `bc_eve_facing_nemesis_trigger`, which cannot pass unless
the scope exists. **If that token ever moves into `desc_intro` or `desc_stranger` the guard is
gone**, silently, and the eve renders a sentence with a hole in it.

- [x] **Step 8: Full static pass**

```bash
cd /d/ck3/tools && python ck3.py validate --strict && python ck3.py index && python ck3.py conflicts && python ck3.py deploy
```

Expected: all exit 0.

---

### Task 11: Run it

**This is the runtime checkpoint.** A game restart costs about seven minutes, so this run
must answer everything it can.

> **RUN RESULT (2026-08-14) — BOTH FEATURES FAILED, AND THE MARKERS DIAGNOSED BOTH.**
> Whole-log counts: 5,623 `BC:` hits, 96 distinct markers, 169 combat ends per side,
> 137 notable wins and 137 notable losses.
>
> **The eve.** `BC: eve fired` **68**, `BC: eve side` **136**, `BC: eve commander` **0**.
> 136 is exactly 2×68, so the `scope = combat` event and `every_combat_side` both worked
> and `side_commander` produced nobody 136 times out of 136. It is not a broken link —
> the same `side_commander` reached a commander **385** times in the same log via
> `BC: chronicle mark commander`. **No commander is assigned to a combat side at
> `on_combat_start`.** That also retires DIAG Q2: `combat_attacker`/`combat_defender`
> were probably never the problem, there was nobody there to find. No routing fixes it,
> so the eve moved into the battle — see the amendment under step 4.
>
> **The dead-knight toast.** `BC: dead knights` **0** over 274 notable grader runs.
> Vanilla kills knights on `enemy_side` only, inside `combat_event.1001` (AGOT
> `combat_events.txt:849`), raised from `on_combat_end_winner` — see the amendment under
> step 5.
>
> **`BC: wipe`** fired **38** times on each side. Symmetric, which is the pass shape
> step 5 asks for.
>
> **Closed as a bonus:** `BC: floor admitted` fired **5** times, retiring the checkpoint
> run's "inconclusive, not a failure" note on plan 2's cooldown floor.

- [x] **Step 1: Clear the logs — game closed**

Delete everything in `D:\Documents\Paradox Interactive\Crusader Kings III\logs`. `probe`
globs **every** `*.log` in that directory, so a stale `debug.log` will produce hits from a
previous session and there is no way to tell them apart.

- [x] **Step 2: Confirm the eve exists before fighting anything**

Load a save and open the character screen of any commander. Nothing to see yet — the point of
this step is that the game **loaded**. A `scope = combat` event with a bad declaration is the
kind of thing that fails at load, not at fire.

```bash
cd /d/ck3/tools && python ck3.py probe "eve"
```

Expected: **exit 1** at this point. Anything here before a battle means the hook is firing on
something other than a combat.

- [x] **Step 3: Fight something large**

The eve needs **5000 total troops**, the dead-knight toast needs a **notable** battle with at
least one dead knight, and the wipe rows need an **annihilation**, which is rare.

Fight the largest battle available. If nothing is large enough, set `bc_aftermath_generous`
— it lowers the notability bar and costs nothing, and the eve's 5000 gate is independent of
it, so a small-battle session can still answer the dead-knight half.

**A wipe cannot be arranged and should not be waited for.** Its three consumers are verified
statically in task 10; this run confirms the marker fires *if* one happens.

- [x] **Step 4: Sweep the eve**

```bash
cd /d/ck3/tools && python ck3.py probe "BC: eve"
```

| what came back | what it means |
|---|---|
| `BC: eve fired`, `BC: eve offered`, `BC: eve popup 0011` | the eve works end to end. **This is the pass condition** |
| `BC: eve fired` only | the size gate passed and both commanders were AI, or the player was inside the 90-day cooldown. Inconclusive — fight another one |
| **nothing at all** | either no battle reached 5000, or the `scope = combat` event does not fire. Check for `BC: eve fired` on a battle you know was large before concluding anything |
| `BC: eve offered` without `BC: eve fired` above it | impossible as written; if you see it, something else is calling the offer effect |

> **RUN CORRECTION — THIS TABLE IS RETIRED, AND SO IS `BC: eve fired`.** The run landed
> in a row the table does not have: `BC: eve fired` **and** `BC: eve side` **without**
> `BC: eve commander`. The table assumed the iteration was the doubtful part; the
> iteration was fine and the commander did not exist yet. `bc_chronicles.0010` and the
> whole `on_combat_start` route are gone. The opening is now raised from the end of
> `bc_battle_open_effect`, which is already proven to run on the side commander, and the
> only two markers left are `BC: eve offered` (gate passed) and `BC: eve popup 0011`
> (event opened). A future run reads those two and nothing else.

**If the pop-up opened, read its second paragraph.** It must say either that the man across
the field is a stranger or name him. **A blank name in the nemesis branch means
`scope:bc_eve_foe` did not survive the `trigger_event`** — that is the one thing in the eve
no static check can prove.

- [x] **Step 5: Sweep the dead and the wipe**

```bash
cd /d/ck3/tools && python ck3.py probe "BC: dead knights"
cd /d/ck3/tools && python ck3.py probe "BC: wipe"
```

| what came back | what it means |
|---|---|
| `BC: dead knights` twice for one battle | both graders fired. Correct — each side tells its own commander |
| `BC: dead knights` once | one side lost no knights, or one side was leaderless. Both are correct |
| nothing, but `BC: win notable` appeared | no knight died in a notable battle. Inconclusive, not a failure |
| `BC: wipe` **twice for one combat end** | an annihilation happened and both graders agreed. This is the pass shape — the notability row is only symmetric if both sides see it |
| `BC: wipe` **once** | the two sides disagree about `scope:wipe`, which contradicts AGOT `combat_on_actions.txt:13` and `:527`. **This is a real failure** and it means the notability bar is asymmetric on wipes |
| no `BC: wipe` | expected. Wipes are rare and this is not a failure. It also does not prove the trigger works — task 10 is what proves that |

> **RUN CORRECTION — THE "TWICE FOR ONE BATTLE" PASS SHAPE WAS NEVER POSSIBLE.** The
> table's top two rows assume each side loses its own knights. It does not work that way:
> `combat_event.1001` (AGOT `combat_events.txt:849`) does its killing inside
> `enemy_side = { every_side_knight = { ... } }` and is raised from
> `on_combat_end_winner`, while `:846` walks the winner's own knights only to write
> battle history. **The dead of any battle are the loser's, and they are made dead on the
> winner's hook.** So `.0092` could never be ordered after the killing, and `.0091` was
> reading a side on which nobody dies. Zero hits over 274 notable grader runs was the
> only possible outcome.
>
> The copy in `.0092` is gone. `.0091` now reaches across to `enemy_side` and addresses
> the loser's commander — which is who the loc string always described. That needs our
> grader to dispatch after `combat_event.1001`, so the on_action file is renamed
> `zz_bc_on_actions.txt`. **The new pass shape is `BC: dead knights` ONCE per notable
> battle, on the winner's hook.** The row "twice for one battle" now means a bug.
>
> The `BC: wipe` rows of the table are unaffected and passed: 38 on each side.

> **SECOND RUN CORRECTION (2026-08-15) — THE `zz_` RENAME DID NOT WORK, AND CANNOT.**
> Per-step markers on a clean log: `BC: dk reached enemy side` **33**,
> `BC: dk found dead` **0**, `BC: dead knights` **0**. That is the "reached, not found"
> row: `enemy_side` steps correctly, `combat_event.1001` simply has not killed anyone
> yet when `.0091` looks.
>
> **Alphabetical filename order does not order the merged `events = { }` list.** It
> decides which `effect` block wins when two files claim the same on_action, and that is
> the whole of it. `zz_bc_on_actions.txt` sorts last among filenames and still ran
> before AGOT's 1001. **Do not try another prefix.** The file keeps the name — it is
> harmless and the header now records why it is not load-bearing.
>
> The read is **deferred one day** into `bc_chronicles.0093`, raised from `.0091` inside
> the same notability gate, so it no longer competes in the dispatch at all. The pass
> shape from the previous correction is unchanged — once per notable battle, addressed
> to the loser's commander — it just arrives a day later.
>
> **New failure mode to watch, and it is the only one left:** a combat side is a
> transient object and may not survive the day. `BC: dk deferred` is written at the call
> site, `BC: dk deferred fired` inside `.0093`. **First counting while the second is
> absent means the side object was freed**, and the fix is to re-hang the read on the
> commander character rather than the side. Both markers come out once that is settled.

**If the dead-knight toast fired, confirm the toast was actually seen.** A marker proves the
block ran; it does not prove `bc_addressed_toast_effect` routed anywhere. The toast should be
red rather than green — that is what `TYPE` was made a parameter for.

- [x] **Step 6: Error sweep**

```bash
cd /d/ck3/tools && python ck3.py probe "bc_"
```

Plan 1's three-row pass condition, unchanged. **Watch specifically for:**

- anything naming `scope:wipe` — the one unsettled reading in the plan
- anything naming `bc_eve_foe` or `bc_eve_attacker` / `bc_eve_defender` — a leaderless side
  is the case the `?=` and the `exists = $FOE$` guard exist for, and it is common
- anything naming `combat_attacker` or `combat_defender` — these are the mod's first uses of
  either, and a scope path that does not resolve logs on every large battle in the world

- [x] **Step 7: Record and commit**

Write into `README.md`:
- **whether `BC: eve fired` appeared** — this is Q2 re-confirmed under real conditions rather
  than under a DIAG event, and it is the load-bearing finding of the run
- whether the nemesis branch rendered a name, if it was reached
- whether the dead-knight toast was seen, and whether it was red
- whether `BC: wipe` ever appeared, and on both sides if so
- that `scope:wipe` has exactly one reader in the mod and why

```bash
cd /d/ck3/mods/battle_chronicles
git add README.md
git commit -m "docs: record the plan 5 runtime findings"
```

---

## Not in this plan

| item | why not | where it goes |
|---|---|---|
| Marking the battlefield province with `add_province_modifier` | Cut in spec review: province modifiers accumulate forever and it was the design's largest save-bloat risk, on its weakest item by value-per-risk | nowhere |
| Prisoners and captured banners | Vanilla already does both — `combat_event.1001` and `artifact.6000` | nowhere |
| Naming individual dead knights | CK3 cannot group an iteration by liege, and naming would mean one toast per knight, which is the thing the aggregate exists to avoid | nowhere |
| An eve option that applies momentum | The battle has not started. The eve is about shape, not advantage | nowhere |
| A `bc_eve` game rule | `bc_aftermath_off` already covers "no ceremony", and a third rule for one pop-up is a setting nobody will find | nowhere |
| Wipe-specific pop-up or event text | Every wipe already produces a notable battle and everything that follows from one. Dedicated text needs its own localization pass and its own measurement | a later plan |
| Reading `scope:wipe` in a phase event | It does not exist there — it is passed to the two end hooks only | nowhere |
