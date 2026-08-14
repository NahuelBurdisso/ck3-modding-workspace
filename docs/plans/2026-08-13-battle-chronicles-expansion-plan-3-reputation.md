# Battle Chronicles Expansion — Plan 3: The Commander's Reputation (B)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A commander who fights the same way three notable battles running becomes that
kind of commander — permanently, by earning a real CK3 commander trait. A commander who
keeps fighting the same ground earns the terrain trait for it.

**Architecture:** Two streak ladders sharing one mechanism. At combat end, on a notable
battle, the grader updates a `last`/`streak` pair for **style** (read from
`bc_battle_style`, which the seam wrote during the battle) and one for **terrain** (read
from `scope:bc_battle_province`). Then a single precedence chain — style, then terrain,
then the existing nickname — awards at most one thing per battle. No new trait art: all
eleven traits already exist in AGOT.

**Tech Stack:** CK3 script (Paradox clausewitz script), targeting CK3 1.19.0.6 under the
AGOT playset. Workspace CLI is `python ck3.py` run from `D:/ck3/tools`.

**Spec:** `D:/ck3/docs/specs/2026-08-13-battle-chronicles-expansion-design.md`, Section 3.

**Depends on:**
- Plan 1 complete — this plan writes into `events/bc_aftermath_events.txt` and calls
  `bc_addressed_toast_effect`, both of which plan 1 creates.
- Plan 1's DIAG run complete — **task 1 reads Q1 and can cancel this plan.**
- Plan 2 is **not** a dependency. B reads `bc_battle_style`, which plan 1 writes. The two
  can ship in either order.

---

## Read this before task 1

Plan 1's entire "Read this before task 1" applies unchanged — the verification loop, the
`validate`-is-syntax-only rule, the cleared-log rule, the mod-is-its-own-git-repo rule,
the sweep pass condition (row 3 is a rule: any line beginning `BC: `), and the
non-negotiables. **Read it first.** What follows is only what is new in plan 3.

### This plan can be cancelled by its own first task

`number_of_commander_traits < 3` is the gate the whole design rests on, and it may be
dead on arrival — the same failure mode as `has_any_nickname = no`, which disqualified 3
of the 4 AGOT commanders sampled during calibration. **Task 1 reads DIAG Q1 and decides.
Do not start task 3 before task 1 is done.**

### No new traits, no new art

All eleven traits already exist. AGOT overrides vanilla's `00_traits.txt` wholesale, so
**AGOT's definitions are what load** — verified: all eleven carry `category = commander`
and `flag = commander_trait_flag` in AGOT's file. This plan references them and defines
nothing.

This is also the mod's second and third references to AGOT keys, after the nickname pool.
The dependency is not new; `descriptor.mod` already declares
`dependencies = { "A Game of Thrones" }`. **But these eleven are vanilla keys that AGOT
happens to override, not AGOT-invented keys** — unlike the nicknames. They resolve in a
vanilla-only playset too.

### Four new permanent variables, and why that is the whole cost

| variable | holds | lives on |
|---|---|---|
| `bc_style_last` | `flag:<kind>` of the last notable battle's style | commander |
| `bc_style_streak` | consecutive notable battles of that style | commander |
| `bc_terrain_last` | `flag:<bucket>` — **the bucket, never the terrain key** | commander |
| `bc_terrain_streak` | consecutive notable battles in that bucket | commander |

Four — `bc_battle_style` and `bc_notable_battles` already exist. These are **ledger**
variables: never cleared, deliberately, and only ever written on commanders of sides in
notable battles. `bc_clear_scratch_effect` must not learn about them.

### Two new scratch variables, with a lifetime of one effect call

| variable | holds | created | destroyed |
|---|---|---|---|
| `bc_terrain_this` | `flag:<bucket>` for **this** battle | `bc_terrain_bucket_effect` | `remove_variable` at the end of `bc_reputation_effect` |
| `bc_award_taken` | `1` once an award has actually been made this battle | either award toast effect | same place |

**Neither belongs in `bc_clear_scratch_effect`.** That effect runs at combat end *after*
grading; putting them there would work by accident and would hide the fact that their
lifetime is one effect call, not one battle.

### New markers

All begin `BC: `, so plan 1's sweep row 3 covers them.

| marker | meaning |
|---|---|
| `BC: style streak` | a style streak advanced |
| `BC: style reset` | a style mismatch started a new streak |
| `BC: style award` | a style trait was granted |
| `BC: terrain streak` / `BC: terrain reset` / `BC: terrain award` | the same, for terrain |
| `BC: terrain NONE MATCHED` | a `terrain =` key no bucket covers — should be impossible |
| `BC: award blocked budget` | style threshold reached, `number_of_commander_traits` full |
| `BC: award blocked terrain` | terrain threshold reached and blocked — by precedence, by budget, or by an unresolved bucket; it does not distinguish them |
| `BC: award blocked has trait` | an award ladder ran and every arm found he already holds the trait |

The three `blocked` markers are not noise. They are how you find out whether Q1's verdict
was right in live play rather than in a one-session sample.

---

## File structure

| path | plan action | responsibility |
|---|---|---|
| `common/scripted_effects/bc_reputation_effects.txt` | **create** (task 3) | all of B: both bookkeepers, both award ladders, the precedence chain |
| `events/bc_aftermath_events.txt` | modify (task 7) | both graders call the chain |
| `localization/english/bc_l_english.yml` | modify (task 8) | award toast titles and descriptions |
| `common/scripted_triggers/bc_scripted_triggers.txt` | **untouched** | B's gates are inline; none is reused |

**No new triggers file.** Every gate in B is used exactly once, at the point it is
written. Extracting them would put the `has_trait` check a file away from the `add_trait`
it guards, which is the pair most likely to drift.

---

### Task 1: Read Q1 — and decide whether this plan ships at all

**Files:** none — this task only reads and decides.

- [ ] **Step 1: Find Q1's counts**

```bash
cd /d/ck3 && grep -n "Q1" docs/specs/2026-08-13-battle-chronicles-expansion-design.md
```

Q1 counted, across every commander at every combat end in the plan-1 run, how many
already hold 0, 1, 2, or 3+ commander traits.

**If the counts are not there, stop.** Plan 1 task 16 was not completed. Go run plan 1
task 15 — do not proceed on the assumption that the gate is fine.

- [ ] **Step 2: Decide**

| what Q1 shows | decision |
|---|---|
| a clear majority of commanders hold **fewer than 3** | **ship as designed.** `number_of_commander_traits < 3` stands |
| most hold 3 or more, but a meaningful minority hold fewer | **ship, and record the reach honestly** in the README: B will only ever touch that minority. Do not raise the cap to compensate — the cap exists so a commander does not collect the set |
| almost every commander already holds 3+ | **the gate is dead.** Do not ship B as written |

- [ ] **Step 3: If the gate is dead, choose the replacement before writing any code**

Two options, and this plan does **not** pick for you because Q1's shape decides it:

1. **Raise the cap to `< 5`.** Simplest. Costs the "should not collect the set"
   principle, and if AGOT hands out commander traits liberally at game start it just
   moves the wall.
2. **Count only traits B itself awarded**, with a `bc_traits_awarded` counter, and gate
   on that. Keeps the principle, ignores the starting loadout entirely, and costs one
   more ledger variable.

**Option 2 is the better answer if Q1 shows the starting loadout is the problem rather
than the ceiling**, which is what "almost every commander already holds 3+ at their first
notable battle" means. Record which was chosen and why in the README before task 3.

- [ ] **Step 4: Record the decision**

```bash
cd /d/ck3
git add docs/specs/2026-08-13-battle-chronicles-expansion-design.md
git commit -m "docs: record the Q1 verdict and B's budget gate"
```

A workspace commit, not a mod commit — nothing in the mod changed yet.

---

### Task 2: Read Q4 — and change nothing structural

**Files:** none.

- [ ] **Step 1: Find Q4's verdict**

```bash
cd /d/ck3 && grep -n "Q4" docs/specs/2026-08-13-battle-chronicles-expansion-design.md
```

Q4 asked whether a `send_interface_toast` **body** executes for a character nobody is
playing. The mod's README contradicted itself on this.

- [ ] **Step 2: Apply it — to comments only**

| Q4 verdict | what changes in plan 3 |
|---|---|
| bodies do **not** run for AI | nothing. Every award in this plan already puts `add_trait` outside the toast |
| bodies **do** run for AI | still nothing structural. Keep state outside toasts anyway |
| no verdict recorded (`subject AI` was 0) | nothing. Proceed as if bodies do not run |

**In all three cases the code is identical, and that is the point.** `bc_addressed_toast_effect`
exists for *addressing* — a toast about a courtier commander belongs on his liege because
nobody is playing the courtier — and that reason never depended on Q4. If Q4 came back
"bodies do run", correct the comment in `bc_addressed_toast_effect` and nothing else.

**Do not use a "bodies do run" verdict as licence to move an `add_trait` inside a toast.**
The addressing argument still routes half the toasts to a different character, so a body
executing there would apply the trait to the *liege*.

---

### Task 3: The style bookkeeper

**Files:**
- Create: `mods/battle_chronicles/common/scripted_effects/bc_reputation_effects.txt`

- [ ] **Step 1: Confirm the markers do not exist**

```bash
cd /d/ck3/tools && python ck3.py probe "BC: style"
```

Expected: **exit 1**. This is the failing test.

- [ ] **Step 2: Write the file header and the bookkeeper**

```
# Battle Chronicles - the commander's reputation.
#
# CK3 lets a commander get BETTER at commanding by fighting - vanilla's
# commander_trait_leveling_leveling_effect runs on every_side_commander at both
# combat ends. But every branch of it is gated `has_trait = X`: it levels traits
# you already have and never grants one. The only granter is
# give_random_commander_trait_effect, a flat random_list behind a lifestyle perk
# whose terrain branches are gated on OWNING that terrain. So the game never lets
# you become a KIND of commander by fighting. That is what this file does.
#
# EVERYTHING HERE IS CALLED ON THE COMMANDER, from inside `side_commander ?= { }`
# in the graders, inside their `is_alive = yes` gate. The four variables below are
# LEDGER, not scratch: never cleared, and bc_clear_scratch_effect must never learn
# about them.
#
#   bc_style_last     flag:<kind>    the last notable battle's style
#   bc_style_streak   integer        consecutive notable battles of that style
#   bc_terrain_last   flag:<bucket>  THE BUCKET, never the terrain key
#   bc_terrain_streak integer        consecutive notable battles in that bucket
#
# ALL ELEVEN TRAITS ALREADY EXIST. AGOT overrides vanilla's 00_traits.txt
# wholesale, so AGOT's definitions are what load; all eleven carry
# `category = commander` and `flag = commander_trait_flag` there. This file
# defines no traits.

# --- the style streak -------------------------------------------------------
#
# Compare this battle's style against the last one. Match increments; mismatch
# starts a new streak AT 1, because the battle just fought IS the first of it.
#
# THE WHOLE THING IS GUARDED ON `exists = var:bc_battle_style`. A notable battle
# in which no moment ever fired has no style, and B must do nothing rather than
# log a missing-variable read on every such combat end - which is most of them
# early in a game.
#
# THE FIRST-EVER BATTLE AND A MISMATCH DO THE SAME THING - a commander with no
# history is a commander starting a streak - so the obvious shape is to fold them
# into one branch:
#
#   OR = { NOT = { exists = var:bc_style_last }
#          NOT = { var:bc_style_last = var:bc_battle_style } }   # DO NOT WRITE THIS
#
# THAT IS THE ONE SHARP EDGE IN THIS EFFECT, AND IT IS WRONG. Both arms of an OR
# are evaluated - CK3 does not short-circuit and guarantees no evaluation order
# among siblings - so on the first battle the second arm reads a
# `var:bc_style_last` that does not exist, and reading a missing variable logs an
# error. Every commander in the world would produce one on his first notable
# battle.
#
# The three-branch shape below is therefore NOT a stylistic choice. The exists
# test is the OUTER branch, and the comparison happens only in an else_if that
# cannot be reached unless the variable exists. else_if arms ARE ordered with
# respect to each other; it is only siblings within one trigger block that are
# not.
bc_style_streak_effect = {
	if = {
		limit = { NOT = { exists = var:bc_style_last } }
		set_variable = { name = bc_style_last value = var:bc_battle_style }
		set_variable = { name = bc_style_streak value = 1 }
		debug_log = "BC: style reset"
	}
	else_if = {
		limit = { var:bc_style_last = var:bc_battle_style }
		change_variable = { name = bc_style_streak add = 1 }
		debug_log = "BC: style streak"
	}
	else = {
		set_variable = { name = bc_style_last value = var:bc_battle_style }
		set_variable = { name = bc_style_streak value = 1 }
		debug_log = "BC: style reset"
	}
}
```

**The first and third branches are byte-identical and must not be factored together.**
The only difference is the guard, and there is no single guard covering both that does
not reintroduce a read of `var:bc_style_last` when it does not exist. This is the same
trade `bc_write_style_effect` makes in `bc_ledger_effects.txt`, for the same reason.

**`change_variable` is safe in the second branch only**, because reaching it proves
`bc_style_last` exists, and `bc_style_streak` is written by the same two branches that
write `bc_style_last` — they are set together in both, always. That invariant is the
reason the create-or-increment shape is not needed here; **if you ever write
`bc_style_last` without `bc_style_streak`, this breaks silently.**

- [ ] **Step 3: Validate and commit**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
cd /d/ck3/mods/battle_chronicles
git add common/scripted_effects/bc_reputation_effects.txt
git commit -m "feat: add the style streak bookkeeper

Nothing calls it yet. Three branches rather than two so that the first-ever
battle never reads a missing bc_style_last."
```

---

### Task 4: The style award ladder

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_reputation_effects.txt`

- [ ] **Step 1: Write the ladder**

```
# --- the style award --------------------------------------------------------
#
# Six styles, six traits. Called only when the streak has reached 3 AND the
# budget gate passed - both are the caller's business, in the chain.
#
#   bloodied    aggressive_attacker
#   entrenched  unyielding_defender
#   adapted     flexible_leader
#   measured    cautious_leader
#   wild        reckless
#   ordered     organizer
#
# THE COMPARISON IS `var:bc_battle_style = flag:bloodied`. bc_battle_style holds a
# flag value, written as `set_variable = { ... value = flag:$KIND$ }` by the seam,
# so both sides are flag values and no conversion happens anywhere in B. This is
# NOT the `flag:$PARAM$ = flag:literal` idiom used for scripted-effect parameters
# - there is no parameter here, the left side is a variable read.
#
# EACH ARM CARRIES ITS OWN `NOT = { has_trait = X }`. It cannot be hoisted: the
# trait differs per arm. Without it, a commander who already holds
# aggressive_attacker and keeps fighting that way re-enters this branch every
# third notable battle and spends the reward budget on a no-op add_trait.
#
# reckless AND cautious_leader ARE `opposites` OF EACH OTHER, and they are the
# ONLY such pair among the eleven traits B can award - verified across the whole
# of AGOT's 00_traits.txt, not a window of it. `has_trait` does not catch this: a
# commander holding reckless who builds a `measured` streak passes every gate and
# the engine then SILENTLY refuses the add_trait. The streak resets, the reward is
# consumed, and nothing happens - forever. So the opposite is removed and the new
# trait replaces it. A man who fought recklessly for a decade and has now won
# three battles by caution has changed.
bc_style_award_effect = {
	if = {
		limit = {
			var:bc_battle_style = flag:bloodied
			NOT = { has_trait = aggressive_attacker }
		}
		add_trait = aggressive_attacker
		bc_style_award_toast_effect = { TRAIT = aggressive_attacker }
	}
	else_if = {
		limit = {
			var:bc_battle_style = flag:entrenched
			NOT = { has_trait = unyielding_defender }
		}
		add_trait = unyielding_defender
		bc_style_award_toast_effect = { TRAIT = unyielding_defender }
	}
	else_if = {
		limit = {
			var:bc_battle_style = flag:adapted
			NOT = { has_trait = flexible_leader }
		}
		add_trait = flexible_leader
		bc_style_award_toast_effect = { TRAIT = flexible_leader }
	}
	else_if = {
		limit = {
			var:bc_battle_style = flag:measured
			NOT = { has_trait = cautious_leader }
		}
		if = {
			limit = { has_trait = reckless }
			remove_trait = reckless
		}
		add_trait = cautious_leader
		bc_style_award_toast_effect = { TRAIT = cautious_leader }
	}
	else_if = {
		limit = {
			var:bc_battle_style = flag:wild
			NOT = { has_trait = reckless }
		}
		if = {
			limit = { has_trait = cautious_leader }
			remove_trait = cautious_leader
		}
		add_trait = reckless
		bc_style_award_toast_effect = { TRAIT = reckless }
	}
	else_if = {
		limit = {
			var:bc_battle_style = flag:ordered
			NOT = { has_trait = organizer }
		}
		add_trait = organizer
		bc_style_award_toast_effect = { TRAIT = organizer }
	}
	else = {
		debug_log = "BC: award blocked has trait"
	}
}
```

**The `else` arm is reachable and is not padding.** Every one of the six arms can fail its
`has_trait` row, and the whole ladder can fall through — that is exactly the case the
marker exists to report. It also catches a `bc_battle_style` holding a kind not in this
table, which would mean the seam's KIND vocabulary and this ladder have drifted apart.

- [ ] **Step 2: Write the award toast**

```
# One toast shape for every style award, so the six call sites cannot drift.
#
# ROUTED, NOT BROADCAST. bc_addressed_toast_effect (bc_reward_effects.txt) raises
# on the subject if he is human and on his liege if he is not, because nearly
# every commander in the world is AI and a toast raised on a man nobody plays
# reaches nobody. This is the ADDRESSING argument and it never depended on DIAG Q4.
#
# THE SUBJECT MUST BE A SAVED SCOPE. bc_addressed_toast_effect's liege arm has
# already changed scope by the time left_icon is evaluated, and a scripted effect
# does not rebind ROOT.
#
# THE TRAIT KEY IS ONLY IN THE DESC LOC KEY, not passed to the toast as data.
# There is one desc key per trait, so the localization can say what the man became
# in words rather than printing a trait name into a sentence.
#
# bc_award_taken IS THE AT-MOST-ONE-AWARD MARKER, and this is the only correct
# place for it. Task 6's chain reads it to suppress everything downstream. Setting
# it here rather than in the chain means it is written once per award ACTUALLY
# MADE - a style ladder that falls through on has_trait sets nothing, and terrain
# still gets its turn. Setting it in the chain instead would burn the battle's
# single award on a ladder that awarded nothing.
# It is SCRATCH with a lifetime of one effect call; bc_reputation_effect removes
# it unconditionally at the end.
bc_style_award_toast_effect = {
	save_scope_as = bc_award_subject
	set_variable = { name = bc_award_taken value = 1 }
	debug_log = "BC: style award"
	bc_addressed_toast_effect = {
		TYPE = event_toast_effect_good
		TITLE = bc_style_award_toast
		DESC = bc_style_award_$TRAIT$_desc
		SUBJECT = scope:bc_award_subject
	}
}
```

**`save_scope_as` inside this effect is safe and is the right place for it.** It runs on
the commander, in the commander's own scope, immediately before the call that needs it.
Saving it in the grader instead would put it forty lines from its only consumer.

**`DESC = bc_style_award_$TRAIT$_desc` builds a loc key by substitution.** That is legal —
`$PARAM$` substitutes textually — and it is why task 8 defines six `_desc` keys named
after the six traits exactly. **A typo here is a missing loc key, which `validate --strict`
catches**, unlike almost everything else in this mod.

- [ ] **Step 3: Validate and commit**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
```

Expected: exit 0 **with six missing-localization WARNs** for the keys task 8 has not
written yet, plus one for `bc_style_award_toast`. A WARN is not a failure — check the exit
code.

```bash
cd /d/ck3/mods/battle_chronicles
git add common/scripted_effects/bc_reputation_effects.txt
git commit -m "feat: add the style award ladder

Six styles, six existing traits, no new art. The measured and wild arms remove
their opposite first - reckless and cautious_leader are opposites of each other
and are the only such pair among the eleven, so without that the engine silently
refuses the add_trait and the reward is consumed forever."
```

---

### Task 5: The terrain bookkeeper and award

Terrain reuses the style machinery exactly, with two differences: the threshold is **2**,
and the bucket must be **derived**, because there is no scratch variable holding it.

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_reputation_effects.txt`

- [ ] **Step 1: Understand why terrain is not symmetric with style**

`bc_battle_style` is a variable the seam wrote during the battle. There is no
`bc_battle_terrain` and there cannot be one cheaply: **`terrain` is a trigger, not
something `set_variable value =` can read.** So the bucket has to be resolved by a
five-way `if` ladder over `scope:bc_battle_province` at combat end.

That ladder therefore has **two outputs from one pass** — the bucket it writes into
`bc_terrain_last`, and the trait it awards. One ladder, so the two cannot disagree.

**`bc_terrain_last` holds the bucket, never the terrain key.** `hills` and `mountains` are
both `rough_terrain_expert`; stored as raw keys they are a mismatch, the streak resets,
and `rough_terrain_expert` becomes near-unreachable. **The streak must be counted on the
thing being awarded.**

- [ ] **Step 2: Write the bucket resolver**

**Read this trap first — it is the one thing in task 5 to get right.** The obvious way to
write a five-way ladder that reads a province and writes to a commander is this, and it is
**WRONG. Do not type it:**

```
bc_terrain_bucket_effect = {
	scope:bc_battle_province = {
		if = {
			limit = { OR = { terrain = drylands  terrain = desert  ... } }
			root = { set_variable = { name = bc_terrain_this value = flag:desert } }   # WRONG
		}
		...
	}
}
```

**`root` is doing real work here and it does not point where it looks like it points.** Inside
`scope:bc_battle_province = { }` the scope is a **province**, and the variable must land
on the **commander**. The graders are `scope = combat_side`, so `root` inside them is the
combat side — **but this effect is called from inside `side_commander ?= { }`, and
`side_commander ?=` does not rebind ROOT either.** A scripted effect does not rebind ROOT.

**Therefore `root` here is the COMBAT SIDE, not the commander, and the code above is
wrong as written.** Fix it by saving the commander before entering the province scope.
**This is the version to type into the file** — the `root` version above goes nowhere:

```
# --- terrain: resolve the bucket -------------------------------------------
#
# CALLED ON THE COMMANDER, but reads scope:bc_battle_province, which the grader
# saved. Saved scopes are visible down the scope chain within one event execution
# - the memory writes already rely on this from inside every_side_knight.
#
# THE CALLER GUARDS ON `exists = scope:bc_battle_province`. combat.location is
# reached with `?=` and may not resolve; the graders already wrap their memory
# writes in the same guard for the same reason.
#
# save_scope_as = bc_terrain_subject IS NOT OPTIONAL. Inside
# `scope:bc_battle_province = { }` the scope is a PROVINCE, and the variable has
# to land on the COMMANDER. `root` will not do it: the graders are
# `scope = combat_side`, this effect is called from inside `side_commander ?= { }`,
# and NEITHER a scripted effect NOR `side_commander ?=` rebinds ROOT - so `root`
# here is the COMBAT SIDE. The variable would land on the side, and every read of
# it from the commander would miss.
#
# The five buckets between them cover every `terrain =` key in the game, so the
# `else` is unreachable in principle - which is exactly why it logs. An unhandled
# terrain key would otherwise write nothing and reset nothing, and the streak
# would quietly stall. The caller therefore does NOT assume this effect wrote
# anything; it guards the streak call on `exists = var:bc_terrain_this`.
#
# The mapping mirrors vanilla's own terrain branch, and all five traits carry
# `category = commander` / `flag = commander_trait_flag` in AGOT's 00_traits.txt.
# winter_soldier is deliberately absent: there is no `terrain =` key corresponding
# to winter, so there is no province-derived path to it at all.
bc_terrain_bucket_effect = {
	save_scope_as = bc_terrain_subject
	scope:bc_battle_province = {
		if = {
			limit = {
				OR = { terrain = drylands  terrain = desert  terrain = desert_mountains  terrain = oasis }
			}
			scope:bc_terrain_subject = { set_variable = { name = bc_terrain_this value = flag:desert } }
		}
		else_if = {
			limit = {
				OR = { terrain = farmlands  terrain = plains  terrain = steppe }
			}
			scope:bc_terrain_subject = { set_variable = { name = bc_terrain_this value = flag:open } }
		}
		else_if = {
			limit = {
				OR = { terrain = hills  terrain = mountains  terrain = wetlands }
			}
			scope:bc_terrain_subject = { set_variable = { name = bc_terrain_this value = flag:rough } }
		}
		else_if = {
			limit = {
				OR = { terrain = forest  terrain = taiga }
			}
			scope:bc_terrain_subject = { set_variable = { name = bc_terrain_this value = flag:forest } }
		}
		else_if = {
			limit = { terrain = jungle }
			scope:bc_terrain_subject = { set_variable = { name = bc_terrain_this value = flag:jungle } }
		}
		else = {
			debug_log = "BC: terrain NONE MATCHED"
		}
	}
}
```

**Write the saved-scope version, not the `root` version.** The `root` version is shown
only because it is the obvious thing to write and it is wrong; `bc_scripted_effects.txt`
already carries this exact lesson at `bc_aftermath_nickname_effect`, whose comment
explains that `left_icon` must be `scope:bc_named_commander` and not `root` for precisely
this reason.

**Verify the ROOT claim before writing either version** rather than trusting this plan:

```bash
cd /d/ck3/mods/battle_chronicles && grep -n "left_icon MUST be" -A 6 common/scripted_effects/bc_scripted_effects.txt
```

If plan 1 task 5 moved that comment into `bc_reward_effects.txt`, look there instead.

- [ ] **Step 3: Write the terrain streak, using `bc_terrain_this`**

The bucket resolver writes a **fifth variable**, `bc_terrain_this`, so the streak
comparison has something to compare against — exactly as `bc_battle_style` backs the style
streak. It is **scratch, not ledger**: it must be removed at the end of the chain.

```
# Same three-branch shape as bc_style_streak_effect, same reason: the first-ever
# battle must not read a missing bc_terrain_last. Threshold 2, not 3 - fighting
# the same ground twice is a weaker claim than fighting the same WAY three times,
# and terrain is not chosen. A commander goes where the war goes.
bc_terrain_streak_effect = {
	if = {
		limit = { NOT = { exists = var:bc_terrain_last } }
		set_variable = { name = bc_terrain_last value = var:bc_terrain_this }
		set_variable = { name = bc_terrain_streak value = 1 }
		debug_log = "BC: terrain reset"
	}
	else_if = {
		limit = { var:bc_terrain_last = var:bc_terrain_this }
		change_variable = { name = bc_terrain_streak add = 1 }
		debug_log = "BC: terrain streak"
	}
	else = {
		set_variable = { name = bc_terrain_last value = var:bc_terrain_this }
		set_variable = { name = bc_terrain_streak value = 1 }
		debug_log = "BC: terrain reset"
	}
}
```

- [ ] **Step 4: Write the terrain award**

```
# Five buckets, five traits. Called only when the streak has reached 2 and the
# budget gate passed. Reads bc_terrain_this, NOT the province - the bucket was
# already resolved once and resolving it twice is how the two answers drift apart.
bc_terrain_award_effect = {
	if = {
		limit = {
			var:bc_terrain_this = flag:desert
			NOT = { has_trait = desert_warrior }
		}
		add_trait = desert_warrior
		bc_terrain_award_toast_effect = { TRAIT = desert_warrior }
	}
	else_if = {
		limit = {
			var:bc_terrain_this = flag:open
			NOT = { has_trait = open_terrain_expert }
		}
		add_trait = open_terrain_expert
		bc_terrain_award_toast_effect = { TRAIT = open_terrain_expert }
	}
	else_if = {
		limit = {
			var:bc_terrain_this = flag:rough
			NOT = { has_trait = rough_terrain_expert }
		}
		add_trait = rough_terrain_expert
		bc_terrain_award_toast_effect = { TRAIT = rough_terrain_expert }
	}
	else_if = {
		limit = {
			var:bc_terrain_this = flag:forest
			NOT = { has_trait = forest_fighter }
		}
		add_trait = forest_fighter
		bc_terrain_award_toast_effect = { TRAIT = forest_fighter }
	}
	else_if = {
		limit = {
			var:bc_terrain_this = flag:jungle
			NOT = { has_trait = jungle_stalker }
		}
		add_trait = jungle_stalker
		bc_terrain_award_toast_effect = { TRAIT = jungle_stalker }
	}
	else = {
		debug_log = "BC: award blocked has trait"
	}
}

# Mirrors bc_style_award_toast_effect exactly, including the bc_award_taken write
# and the reason for it.
bc_terrain_award_toast_effect = {
	save_scope_as = bc_award_subject
	set_variable = { name = bc_award_taken value = 1 }
	debug_log = "BC: terrain award"
	bc_addressed_toast_effect = {
		TYPE = event_toast_effect_good
		TITLE = bc_terrain_award_toast
		DESC = bc_terrain_award_$TRAIT$_desc
		SUBJECT = scope:bc_award_subject
	}
}
```

**None of the five terrain traits has an `opposites` block**, verified across the whole of
AGOT's `00_traits.txt`, so there is no `remove_trait` arm here. Do not add one
symmetrically with the style ladder — it would be dead code that implies a rule that does
not exist.

- [ ] **Step 5: Validate and commit**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
cd /d/ck3/mods/battle_chronicles
git add common/scripted_effects/bc_reputation_effects.txt
git commit -m "feat: add the terrain bookkeeper and award

The bucket is derived by a five-way ladder because terrain is a trigger and no
set_variable can read it. bc_terrain_last stores the BUCKET, not the terrain key,
so hills-then-mountains counts as a streak rather than breaking one."
```

---

### Task 6: The precedence chain

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_reputation_effects.txt`

- [ ] **Step 1: Understand the two phases, because collapsing them is the trap**

Bookkeeping and awarding are **separate passes**, not one.

- **Bookkeeping runs unconditionally** on every notable battle, for both ladders. A style
  award must not stop the terrain streak from advancing — the streak is a record of what
  happened, and making it depend on award precedence would mean a commander's terrain
  history has holes in it wherever he happened to earn a style trait.
- **Awarding is a chain** — style, then terrain, then nickname — and awards **at most one
  thing per battle**.

- [ ] **Step 2: Understand the three defects that a plain `else_if` chain has here**

The obvious shape for "style, then terrain, then nickname, at most one" is a three-arm
`if / else_if / else_if`. It is wrong three separate ways, and all three are invisible to
`validate`. Read these before typing anything.

1. **Every arm's `limit` would read a variable that may not exist.**
   `exists = var:bc_style_streak` sitting as a *sibling* of `var:bc_style_streak >= 3` does
   **not** protect it — CK3 does not short-circuit and guarantees no evaluation order among
   siblings, which is stated imperatively in this mod's own source. The comparison is
   evaluated either way, and reading a missing variable logs an error. (`exists` itself on a
   missing variable is safe. So is `remove_variable`. It is only the *comparison* that must
   be nested.)

2. **The nickname arm is the worst case of defect 1, and it is new.** Today the nickname
   gate lives in `events/bc_events.txt` immediately below
   `bc_notable_battle_counter_effect`, and its own comment says the `exists` row is "belt
   and braces" — what actually makes it safe is that the counter unconditionally writes
   `bc_notable_battles` on the line above. **This plan moves that gate into an effect the
   LOSER grader also calls, and task 7 step 2 deliberately does not call the counter
   there.** A commander who has never won a notable battle therefore reaches
   `var:bc_notable_battles >= 3` with no such variable. The safety argument the shipped
   comment relies on is destroyed by the move, so the nesting is not optional here.

3. **Nesting the style guard around the whole chain would put terrain behind style.**
   The tempting repair for defect 1 is to wrap the three arms in
   `if = { limit = { exists = var:bc_battle_style } }`. But `bc_battle_style` only exists
   when the seam recorded at least one moment, and a notable battle with zero moments would
   then be unable to award **terrain** either — even though terrain has nothing to do with
   style and its streak advanced normally in phase 1. Style must not gate terrain.

**The resolution is to drop `else_if` entirely** and use three flat `if` blocks sequenced by
an explicit scratch marker, `bc_award_taken`, which the two toast effects already set (task
4 step 2, task 5 step 4). Flat `if`s can each nest their own guard, and the marker carries
the precedence that `else_if` used to.

**The marker is set on award MADE, not on arm ENTERED**, which is why it lives in the toast
effects rather than here. A style ladder that falls through on `has_trait` awards nothing
and sets nothing, and terrain still gets its turn — where an `else_if` chain would have
burned the battle's single award on a ladder that did nothing.

**Threshold-reached and award-made are separate events, and the reset follows the
threshold.** The streak resets to 0 the moment its threshold is reached, whether or not
anything was awarded. Four doors now lead to "threshold reached, nothing awarded" — the
budget gate, the `has_trait` check, losing to an earlier arm, and an unresolved bucket — and
if the streak survived any of them the commander would re-enter the dead branch on every
subsequent notable battle, forever. Resetting on threshold rather than on award is what
makes all four safe at once. **So the reset sits above the award, not inside it.**

- [ ] **Step 3: Write the chain**

```
# --- the chain --------------------------------------------------------------
#
# bc_reputation_effect = { OUTCOME = win|lose }
#
# CALLED ON THE COMMANDER, from inside `side_commander ?= { if = { limit = { is_alive = yes } } }`
# in both graders, INSIDE the notability gate and INSIDE the aftermath game-rule
# gate.
#
# TWO PHASES. Bookkeeping first and unconditionally; then at most one award.
# Collapsing them would make the terrain streak depend on whether a style award
# happened, which would put holes in a commander's terrain history.
#
# PHASE 2 IS THREE FLAT `if` BLOCKS, NOT AN else_if CHAIN. Precedence is carried
# by bc_award_taken instead. else_if cannot be used because every arm's gate needs
# its own NESTED exists guard - CK3 does not short-circuit and guarantees no
# evaluation order among siblings, so `exists = var:X` beside `var:X >= 3` in one
# limit does not protect the comparison - and nesting a guard is exactly what an
# else_if arm cannot do without leaving the chain.
#
# bc_award_taken IS SET BY THE TOAST EFFECTS, not here, so it means "an award was
# actually made" and not "an arm was entered". A style ladder that falls through
# on has_trait leaves it unset and terrain still gets its turn.
#
# THE RESET FOLLOWS THE THRESHOLD, NOT THE AWARD. set_variable ... value = 0 sits
# ABOVE the award attempt in both ladders, so it runs on all four block-doors:
# the budget gate, the has_trait check, losing to an earlier arm, and an
# unresolved bucket. If a streak survived any of them the commander would re-enter
# the dead branch on every subsequent notable battle, forever.
#
# THE OUTCOME IS A PARAMETER, and it has to be. Style and terrain grade EITHER
# outcome - a man who loses three battles the same way has still shown you who he
# is - but the nickname is a reward for winning. Without the parameter the
# nickname block would be reachable on a defeat, because its gate is
# `var:bc_notable_battles >= 3`, a CUMULATIVE tally that a man who has won three
# battles before still satisfies on the day he loses one.
#
# `flag:$OUTCOME$ = flag:win`, NOT `$OUTCOME$ = win`. A bare `$OUTCOME$ = win`
# substitutes to `win = win`, an unknown key, a SILENT NO-OP that validate passes.
bc_reputation_effect = {
	# --- phase 1: bookkeeping, always ---
	if = {
		limit = { exists = var:bc_battle_style }
		bc_style_streak_effect = yes
	}
	if = {
		limit = { exists = scope:bc_battle_province }
		bc_terrain_bucket_effect = yes
		if = {
			limit = { exists = var:bc_terrain_this }
			bc_terrain_streak_effect = yes
		}
	}

	# --- phase 2a: style ---
	if = {
		limit = { exists = var:bc_style_streak }
		if = {
			limit = { var:bc_style_streak >= 3 }
			set_variable = { name = bc_style_streak value = 0 }
			if = {
				limit = { number_of_commander_traits < 3 }
				bc_style_award_effect = yes
			}
			else = {
				debug_log = "BC: award blocked budget"
			}
		}
	}

	# --- phase 2b: terrain, only if style awarded nothing ---
	# The streak reset is INSIDE the threshold test but OUTSIDE the
	# bc_award_taken test, deliberately: a terrain threshold reached on a
	# battle that style already won still resets, or it would be re-reached
	# and re-blocked on every notable battle from here on.
	if = {
		limit = { exists = var:bc_terrain_streak }
		if = {
			limit = { var:bc_terrain_streak >= 2 }
			set_variable = { name = bc_terrain_streak value = 0 }
			if = {
				limit = {
					NOT = { exists = var:bc_award_taken }
					exists = var:bc_terrain_this
					number_of_commander_traits < 3
				}
				bc_terrain_award_effect = yes
			}
			else = {
				debug_log = "BC: award blocked terrain"
			}
		}
	}

	# --- phase 2c: the nickname, only if nothing above awarded ---
	# `exists = var:bc_notable_battles` may sit as a sibling because `exists`
	# on a missing variable is safe. The COMPARISON is what has to be nested,
	# and it is. This gate used to be safe by position - the counter wrote the
	# variable on the line above it - but the loser grader does not call the
	# counter, so position no longer proves anything.
	if = {
		limit = {
			NOT = { exists = var:bc_award_taken }
			flag:$OUTCOME$ = flag:win
			has_any_nickname = no
			martial >= 14
			exists = var:bc_notable_battles
		}
		if = {
			limit = { var:bc_notable_battles >= 3 }
			save_scope_as = bc_named_commander
			bc_aftermath_nickname_effect = yes
		}
	}

	# --- always: drop the scratch ---
	remove_variable = bc_terrain_this
	remove_variable = bc_award_taken
}
```

- [ ] **Step 4: Read these three things before moving on**

1. **Both `remove_variable` calls must be outside every branch**, as written. If
   `bc_terrain_this` lived inside the terrain block, a battle that took the style block
   would leave it on the commander and the *next* battle's terrain streak would compare
   against last battle's bucket. If `bc_award_taken` survived, every future battle would
   award nothing. `remove_variable` on a missing variable is safe, so the unconditional
   calls cost nothing.

2. **Neither `bc_terrain_this` nor `bc_award_taken` may be added to
   `bc_clear_scratch_effect`.** Both are created and destroyed inside one effect call at
   combat end, and `bc_clear_scratch_effect` runs *after* grading — adding them there would
   work by accident and hide the fact that their lifetime is one effect, not one battle.

3. **`var:bc_battle_style` and `var:bc_terrain_this` are proven to exist before either
   award ladder runs** — style by phase 2a's outer `exists = var:bc_style_streak` combined
   with the fact that phase 1 writes `bc_style_streak` only when `bc_battle_style` existed,
   terrain by the explicit `exists = var:bc_terrain_this` row in phase 2b. Task 9 step 3
   asks for that reasoning as a comment on each ladder. Write it there now.

   **The style argument has one hole worth naming:** `bc_style_streak` is *ledger*, so it
   survives between battles, and a notable battle with no moments at all would enter phase
   2a on a stale streak with no `bc_battle_style` to award from. It cannot fire — the streak
   is only ever advanced to 3 by a battle that had a style, and it is reset to 0 the moment
   it reaches 3 — but the ladder's `else` marker (`BC: award blocked has trait`) is what
   would report it if that reasoning is ever broken by a later plan. Do not remove that
   marker.

- [ ] **Step 5: Validate**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
```

Expected: exit 0.


- [ ] **Step 6: Commit**

```bash
cd /d/ck3/mods/battle_chronicles
git add common/scripted_effects/bc_reputation_effects.txt
git commit -m "feat: add the reputation precedence chain

Bookkeeping runs unconditionally; at most one award per battle, style then
terrain then nickname. Precedence is carried by a bc_award_taken scratch marker
rather than else_if, because every arm needs a nested exists guard and an
else_if arm cannot nest one without leaving the chain. The streak resets on
threshold reached rather than on award, which is what makes all four
block-doors safe at once."
```

---

### Task 7: Wire both graders

**Files:**
- Modify: `mods/battle_chronicles/events/bc_aftermath_events.txt`

- [ ] **Step 1: Replace the nickname block in `bc_chronicles.0091` (the winner)**

The winner grader currently holds, inside `side_commander ?= { if = { limit = { is_alive = yes } } }`:

```
						bc_notable_battle_counter_effect = yes

						if = {
							limit = {
								has_any_nickname = no
								...
							}
							save_scope_as = bc_named_commander
							bc_aftermath_nickname_effect = yes
						}
```

Replace the whole `if` block — **not** the counter call above it — with:

```
						bc_reputation_effect = { OUTCOME = win }
```

`bc_notable_battle_counter_effect` stays where it is and stays **before** the chain: the
nickname arm reads `var:bc_notable_battles >= 3`, so the counter must have already
incremented for this battle.

- [ ] **Step 2: Add the chain to `bc_chronicles.0092` (the loser)**

The loser grader has **no** `side_commander ?=` block today — the counter and the nickname
are winner-only, deliberately, and nothing else touched the commander. Add one, inside the
notability gate, after the knight memory block:

```
				side_commander ?= {
					if = {
						limit = { is_alive = yes }
						bc_reputation_effect = { OUTCOME = lose }
					}
				}
```

**`OUTCOME = lose` closes the nickname arm and nothing else.** Style and terrain grade both
outcomes.

**Do not add `bc_notable_battle_counter_effect` here.** That counter is wins only and the
loser grader's header says so.

- [ ] **Step 3: Confirm placement against the load-bearing body order**

Plan 1's grader header states the order: cleanup outside the gate, grading inside it,
scratch clearing outside and last. **The chain is grading.** It must sit inside the
`NOT = { has_game_rule = bc_aftermath_off }` gate, inside the notability gate, and
**before** `bc_clear_scratch_effect` — the chain reads `bc_battle_style`, which scratch
clearing removes.

```bash
cd /d/ck3/mods/battle_chronicles
grep -n "bc_reputation_effect\|bc_clear_scratch_effect\|bc_battle_is_notable_trigger\|bc_aftermath_off" \
  events/bc_aftermath_events.txt
```

Read the line numbers in order for each event. In both, the order must be: `bc_aftermath_off`
gate, notability gate, `bc_reputation_effect`, then `bc_clear_scratch_effect` last.

**If `bc_clear_scratch_effect` appears before `bc_reputation_effect` in either event, B is
dead** — every battle would grade a commander whose style had already been erased, the
phase-1 guard would swallow it silently, and no marker would fire. That silence is why
this is checked by eye rather than left to the runtime pass.

- [ ] **Step 4: Verify the call count**

```bash
cd /d/ck3/mods/battle_chronicles && grep -c "bc_reputation_effect" events/bc_aftermath_events.txt
```

Expected: **2** — one per grader.

- [ ] **Step 5: Validate, index, conflicts, deploy**

```bash
cd /d/ck3/tools && python ck3.py validate --strict && python ck3.py index && python ck3.py conflicts && python ck3.py deploy
```

Expected: all exit 0.

- [ ] **Step 6: Commit**

```bash
cd /d/ck3/mods/battle_chronicles
git add events/bc_aftermath_events.txt
git commit -m "feat: both graders now run the reputation chain

The loser grader gains a side_commander block it never had - style and terrain
grade either outcome. The nickname stays winner-only, carried by OUTCOME rather
than inferred from which event is running."
```

---

### Task 8: Localization

**Files:**
- Modify: `mods/battle_chronicles/localization/english/bc_l_english.yml`

- [ ] **Step 1: Check the BOM and record the baseline key count**

```bash
cd /d/ck3/mods/battle_chronicles
head -c 8 localization/english/bc_l_english.yml | cat -A
grep -c "^ bc_" localization/english/bc_l_english.yml
```

Expected: begins `M-oM-;M-?`. UTF-8 with BOM, one leading space per line.

**Write the key count down.** Step 3 checks that it rose by exactly 13, which is not a
check you can run without the number from before the edit.

- [ ] **Step 2: Write the thirteen keys**

Two titles and eleven descriptions — one description per trait, because
`bc_style_award_toast_effect` and `bc_terrain_award_toast_effect` build the desc key by
substituting `$TRAIT$`.

```
 bc_style_award_toast:0 "A Way of Fighting"
 bc_style_award_aggressive_attacker_desc:0 "[bc_award_subject.GetName] has won three battles by making the enemy pay for standing still. Men have started to say he does not fight so much as insist."
 bc_style_award_unyielding_defender_desc:0 "Three times now [bc_award_subject.GetName] has set his line and three times it has held. Whatever else is said of him, he does not move."
 bc_style_award_flexible_leader_desc:0 "[bc_award_subject.GetName] has won three battles on ground that did not suit him, and won them by not minding."
 bc_style_award_cautious_leader_desc:0 "[bc_award_subject.GetName] has taken three fields without spending men on any of them. The reckless captain he was is not the man who came back."
 bc_style_award_reckless_desc:0 "[bc_award_subject.GetName] has thrown himself into three battles without waiting to see the shape of them. It has worked three times."
 bc_style_award_organizer_desc:0 "Three battles, and not once has [bc_award_subject.GetName]'s line lost its shape. The men know where to be before he tells them."
 bc_terrain_award_toast:0 "He Knows This Ground"
 bc_terrain_award_desert_warrior_desc:0 "[bc_award_subject.GetName] has fought twice in the dry country and learned what it costs."
 bc_terrain_award_open_terrain_expert_desc:0 "Twice on open ground, and [bc_award_subject.GetName] has learned what open ground is for."
 bc_terrain_award_rough_terrain_expert_desc:0 "[bc_award_subject.GetName] has fought twice in broken country and stopped cursing it."
 bc_terrain_award_forest_fighter_desc:0 "Twice under the trees. [bc_award_subject.GetName] has stopped trying to make a forest into a field."
 bc_terrain_award_jungle_stalker_desc:0 "[bc_award_subject.GetName] has come out of the green twice. Not everyone does."
```

**`[bc_award_subject.GetName]` is why the toast effects save that scope**, and it is the
one thing here that will not fail loudly if it is wrong — a bad scope reference in a loc
string renders as broken text in game, not as a validation error.

- [ ] **Step 3: Verify**

```bash
cd /d/ck3/mods/battle_chronicles
grep -c "^ bc_" localization/english/bc_l_english.yml
head -c 8 localization/english/bc_l_english.yml | cat -A
cd /d/ck3/tools && python ck3.py validate --strict
```

The key count must have risen by exactly **13**. The BOM must still be present — editors
strip it silently, which is why it is checked after the edit as well as before.
`validate --strict` must exit 0 **with no missing-localization WARN naming any `bc_` key**.

That last condition is the real test of step 2: if a `$TRAIT$`-substituted desc key was
misspelled in task 4 or 5, this is the only check in the entire plan that catches it.

- [ ] **Step 4: Commit**

```bash
cd /d/ck3/mods/battle_chronicles
git add localization/english/bc_l_english.yml
git commit -m "feat: localize the eleven reputation awards"
```

---

### Task 9: Static verification

**Files:** none — this task only reads.

- [ ] **Step 1: Every trait B names actually exists**

```bash
cd /d/ck3/mods/battle_chronicles
grep -ohE "(add_trait|remove_trait|has_trait) = [a-z_]+" common/scripted_effects/bc_reputation_effects.txt \
  | awk '{print $3}' | sort -u > /tmp/bc_traits_used
while read t; do
  grep -q "^$t = {" "/d/SteamLibrary/steamapps/workshop/content/1158310/2962333032/common/traits/00_traits.txt" \
    || echo "MISSING: $t"
done < /tmp/bc_traits_used
```

Expected: **no `MISSING:` output**. Eleven distinct traits.

`validate` cannot do this — it has no knowledge of trait keys, so `add_trait = agressive_attacker`
would pass cleanly and silently do nothing forever.

- [ ] **Step 2: No parameter is compared without `flag:`**

```bash
cd /d/ck3/mods/battle_chronicles
grep -rn '\$[A-Z_]*\$ = [a-z]' common/scripted_effects/ | grep -v 'flag:\$'
```

Expected: **no output**. A hit is a `$PARAM$ = literal` comparison, which substitutes to an
unknown key and is a silent no-op. The only parameter comparison in B is
`flag:$OUTCOME$ = flag:win`.

**The `grep -v` is not optional and neither is `[A-Z_]`.** Without the filter this check
reports its own correct code as a failure — `flag:$OUTCOME$ = flag:win` contains
`$OUTCOME$ = f` and matches the pattern. A genuinely bad line reads `$OUTCOME$ = win` with
no `flag:` on it and survives the filter. `[A-Z]` alone would miss a parameter named
`$SOME_PARAM$`.

- [ ] **Step 2b: Every toast call names a TYPE**

```bash
cd /d/ck3/mods/battle_chronicles
grep -rc "bc_addressed_toast_effect = {" common/scripted_effects/ | grep -v ':0'
grep -rc "TYPE = event_toast_effect_" common/scripted_effects/ | grep -v ':0'
grep -n "TYPE = event_toast_effect_" common/scripted_effects/bc_reputation_effects.txt
```

The first two totals must be equal. The third must show **exactly two lines, both
`event_toast_effect_good`** — earning a trait is good news.

`TYPE` is a required parameter of `bc_addressed_toast_effect` as of plan 1 task 4, because
plans 4 and 5 route bad news through the same effect. **An omitted parameter is not an error
in CK3**: the literal text `type = $TYPE$` reaches `send_interface_toast` and `validate` sees
balanced braces. Only this count catches it.

- [ ] **Step 3: No missing-variable read**

Read `bc_reputation_effects.txt` end to end and check every `limit` block containing a
`var:` **comparison**. **Each one must be either nested inside an `exists` guard, or
reachable only where an unconditional write above it proves the variable exists.** A bare
`exists = var:X` row is not itself a comparison and needs no guard — `exists` on a missing
variable is safe. Only `var:X <op> Y` has to be protected.

There are **sixteen** such comparisons, and this is the full list. Tick each one:

| where | comparison | what makes it safe |
|---|---|---|
| `bc_style_streak_effect` arm 2 | `var:bc_style_last = var:bc_battle_style` | arm 1 already tested `NOT = { exists = var:bc_style_last }`, so arm 2 only runs when it exists; `bc_battle_style` is proven by the caller's phase-1 guard |
| `bc_terrain_streak_effect` arm 2 | `var:bc_terrain_last = var:bc_terrain_this` | same shape; `bc_terrain_this` proven by the caller's `exists` guard |
| chain phase 2a | `var:bc_style_streak >= 3` | nested inside `exists = var:bc_style_streak` |
| chain phase 2b | `var:bc_terrain_streak >= 2` | nested inside `exists = var:bc_terrain_streak` |
| chain phase 2c | `var:bc_notable_battles >= 3` | nested inside a limit carrying `exists = var:bc_notable_battles` |
| `bc_style_award_effect` | `var:bc_battle_style = flag:...` × **6** | see below |
| `bc_terrain_award_effect` | `var:bc_terrain_this = flag:...` × **5** | see below |

2 + 3 + 6 + 5 = 16. If your read finds a seventeenth, it is new and it is unguarded.

For the award ladders specifically: `var:bc_battle_style` is proven by phase 2a's outer
`exists = var:bc_style_streak` — phase 1 writes `bc_style_streak` only when
`bc_battle_style` existed, and never removes it — and `var:bc_terrain_this` by the explicit
`exists = var:bc_terrain_this` row in phase 2b's inner limit. **Write that reasoning as a
comment at the top of each ladder**, because it is the kind of invariant a later plan breaks
by moving a call site.

- [ ] **Step 4: The ledger variables are not cleared**

```bash
cd /d/ck3/mods/battle_chronicles
grep -n "bc_style_last\|bc_style_streak\|bc_terrain_last\|bc_terrain_streak" \
  common/scripted_effects/bc_ledger_effects.txt
```

Expected: **no output**. These four are ledger, not scratch. If `bc_clear_scratch_effect`
learned about any of them, every streak would reset at every combat end and B could never
award anything.

- [ ] **Step 5: Both scratch variables ARE dropped, and only inside the chain**

```bash
cd /d/ck3/mods/battle_chronicles
grep -n "bc_terrain_this\|bc_award_taken" common/scripted_effects/*.txt
```

Expected: hits only in `bc_reputation_effects.txt`. **No hit in `bc_ledger_effects.txt`** —
neither belongs in `bc_clear_scratch_effect`; their lifetime is one effect call, not one
battle.

Read the hits and confirm the shape of each:

| variable | written | read | removed |
|---|---|---|---|
| `bc_terrain_this` | once, in `bc_terrain_bucket_effect` (five arms) | `bc_terrain_streak_effect`, `bc_terrain_award_effect`, and phase 2b's `exists` row | `remove_variable` at the end of `bc_reputation_effect`, outside every branch |
| `bc_award_taken` | **only** in `bc_style_award_toast_effect` and `bc_terrain_award_toast_effect` — exactly two `set_variable` lines | phase 2b and phase 2c, via `NOT = { exists = ... }` | `remove_variable` at the end of `bc_reputation_effect`, outside every branch |

**Two `set_variable = { name = bc_award_taken` lines, no more.** A third means the marker
was also set in the chain, which would make it mean "an arm was entered" rather than "an
award was made" and would let a style ladder that fell through on `has_trait` block terrain
for nothing.

- [ ] **Step 6: Full static pass**

```bash
cd /d/ck3/tools && python ck3.py validate --strict && python ck3.py index && python ck3.py conflicts && python ck3.py deploy
```

Expected: all exit 0.

---

### Task 10: Run it

**This is the runtime checkpoint.**

- [ ] **Step 1: Clear the logs — game closed**

Delete `error.log` and `debug.log` from
`D:\Documents\Paradox Interactive\Crusader Kings III\logs`. Write any unrecorded findings
from the previous run into the README first.

- [ ] **Step 2: Fight**

B needs **notable** battles, which is a high bar — `bc_battle_is_notable_trigger` was
calibrated against 39 combat ends and most battles fail it. And a style award needs three
notable battles of the *same* style by the *same* commander.

**Do not expect to see `BC: style award` in one session.** What this run must show is that
the *bookkeeping* works. The award ladders are verified by the static checks in task 9 plus
the fact that they share their shape with the streak effects.

- [ ] **Step 3: Sweep the bookkeeping**

```bash
cd /d/ck3/tools
python ck3.py probe "BC: style"
python ck3.py probe "BC: terrain"
```

Expected: exit 0 on both, with `reset` lines and — if any commander fought two notable
battles the same way — `streak` lines.

| what came back | what it means |
|---|---|
| `BC: style reset` appears, `BC: style streak` never does | inconclusive if there were few notable battles; a red flag if there were many, because it means the comparison arm never matches. Check that `bc_battle_style` and `bc_style_last` are both flag values |
| neither appears, but `BC: win notable` / `BC: lose notable` did | **phase 1's `exists = var:bc_battle_style` guard is swallowing everything.** Either the seam is not writing style, or `bc_clear_scratch_effect` is running before the chain — check task 7 step 3 |
| `BC: terrain NONE MATCHED` appears | an unhandled `terrain =` key exists. Find it and add it to the right bucket before B ships |

- [ ] **Step 4: Sweep the blocked markers**

```bash
cd /d/ck3/tools
python ck3.py probe "BC: award blocked"
```

There are three distinct blocked markers and they mean different things:

| marker | emitted by | means |
|---|---|---|
| `BC: award blocked budget` | chain phase 2a | style threshold reached, `number_of_commander_traits < 3` failed |
| `BC: award blocked terrain` | chain phase 2b | terrain threshold reached and **one of three things** — style already awarded this battle, the budget gate failed, or the bucket did not resolve. It does not distinguish them |
| `BC: award blocked has trait` | either award ladder's `else` | the ladder ran and every arm's `NOT = { has_trait }` failed, or `bc_battle_style` held a KIND the ladder does not know |

**None of the three is a failure.** `budget` appearing often means Q1's verdict was
optimistic and the gate is tighter in live play than the sample suggested — revisit task 1
step 3. `has trait` appearing means commanders are re-reaching thresholds for traits they
hold, which is the treadmill the reset rule prevents; confirm the streak did reset by
checking that the same commander does not produce it on every subsequent battle.

`BC: award blocked terrain` is the ambiguous one. If it appears without any `BC: style
award` on the same commander, the cause was the budget gate or an unresolved bucket, not
precedence — cross-check against `BC: terrain NONE MATCHED` from step 3.

- [ ] **Step 5: Error sweep**

```bash
cd /d/ck3/tools && python ck3.py probe "bc_"
```

Plan 1's three-row pass condition, unchanged. **Watch specifically for missing-variable
reads naming `bc_style_last`, `bc_style_streak`, `bc_terrain_last`, `bc_terrain_streak`,
`bc_terrain_this`, `bc_award_taken` or `bc_notable_battles`.** All seven are guarded; a hit
means a guard was written as a sibling row rather than nested, which is the exact mistake
task 6 step 2 exists to prevent and which no static check in this plan can catch.

**`bc_notable_battles` is the one to watch hardest.** Its gate was safe by position in the
shipped code — the counter wrote it on the line above — and this plan moves it into an
effect the loser grader calls without the counter. If it appears here, the nesting in phase
2c was not written.

- [ ] **Step 6: Record and commit**

Write into `README.md`: Q1's verdict and the budget gate chosen; whether style streaks were
observed advancing; any `NONE MATCHED` terrain; and that `bc_style_last`,
`bc_style_streak`, `bc_terrain_last` and `bc_terrain_streak` are permanent ledger variables
that `bc_clear_scratch_effect` must never touch.

```bash
cd /d/ck3/mods/battle_chronicles
git add README.md
git commit -m "docs: record the plan 3 runtime findings"
```

---

## Done when

- `bc_reputation_effects.txt` holds both bookkeepers, both award ladders, both toast
  wrappers and the chain, and nothing else references B's variables.
- Task 9 step 1 reports no missing trait.
- Task 9 steps 4 and 5 report no output — the four ledger variables are never cleared and
  `bc_terrain_this` never escapes its file.
- Both graders call `bc_reputation_effect`, with `OUTCOME = win` and `OUTCOME = lose`
  respectively, inside the notability gate and before scratch clearing.
- 13 new loc keys, `validate --strict` exits 0 with no `bc_` localization WARN.
- A cleared-log run shows `BC: style reset` and `BC: terrain reset`, and no
  `BC: terrain NONE MATCHED`.
- The error sweep returns nothing outside plan 1's three whitelist rows, and in particular
  no missing-variable read naming any of B's five variables.

## Not in this plan

| thing | plan |
|---|---|
| the family-2 modifiers and the pacing curve | 2 — independent of this plan; either order |
| C, the named foe | 4 |
| D, the eve and the aftermath | 5 |
| family 3, the wounds | 6 |
| raising or replacing the budget gate | **task 1 step 3**, decided by Q1, before any code is written |
