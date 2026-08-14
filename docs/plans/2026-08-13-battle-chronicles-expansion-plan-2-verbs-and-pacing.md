# Battle Chronicles Expansion — Plan 2: Verbs and Pacing (stage 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the seam *do* something — a battle whose moments were merely counted now
changes how the army fights — and make the rate of moments a property of the battle's
size rather than a flat 15-day cooldown.

**Architecture:** Two halves that share one variable. The **verb half** adds four
character modifiers (family 2) and a `(KIND, SWING)` ladder inside
`bc_record_moment_effect`, so no call site ever names a modifier. The **pacing half**
adds commander-only variants of the chronicle trigger and mark effect, scaling the
cooldown flag off `bc_battle_size`. Both read `var:bc_battle_size`, which plan 1 already
writes, so the two ladders cannot drift.

**Tech Stack:** CK3 script (Paradox clausewitz script), targeting CK3 1.19.0.6 under the
AGOT playset. Workspace CLI is `python ck3.py` run from `D:/ck3/tools`.

**Spec:** `D:/ck3/docs/specs/2026-08-13-battle-chronicles-expansion-design.md`, Sections 2 and 6.

**Depends on:** Plan 1 (`2026-08-13-battle-chronicles-expansion-plan-1-spine.md`)
**complete and its task 15 run**. This plan reads Q3's answer in task 1 and writes into
three files plan 1 creates.

---

## Read this before task 1

### Everything in "Read this before task 1" of plan 1 still applies

The verification loop, the `validate`-is-syntax-only warning, the cleared-log rule, the
`conflicts`-needs-`index` rule, the mod-is-its-own-git-repo rule and the non-negotiables
are all unchanged. **Read plan 1's preamble first.** What follows is only what is new or
different in plan 2.

### The sweep whitelist is a rule, not a list

Plan 1's sweep pass condition row 3 admits *any line beginning `BC: `*, and enumerates
the markers that existed when it was written. **That enumeration is now incomplete and
that is fine — row 3 is a rule.** This plan adds nine permanent markers, all of which
begin `BC: `:

| marker | emitted from | task |
|---|---|---|
| `BC: size 1` / `BC: size 2` / `BC: size 3` | `bc_battle_open_effect` | 1 |
| `BC: verb bloodied` | `bc_apply_verb_effect` | 4 |
| `BC: verb shieldwall` | `bc_apply_verb_effect` | 4 |
| `BC: verb spent horse` | `bc_apply_verb_effect` | 4 |
| `BC: verb pursuit` | `bc_apply_verb_effect` | 4 |
| `BC: chronicle mark commander` | `bc_mark_chronicle_commander_effect` | 9 |
| `BC: floor admitted` | `bc_mark_chronicle_commander_effect` | 9 |

Do not add a marker that does not begin `BC: `. That prefix is the only thing separating
this mod's own log output from an engine complaint about this mod's files.

### One runtime checkpoint

Plan 1 spent two game launches. This plan spends **one** — task 12. Nothing before it
launches the game. A restart costs about seven minutes.

### The known pre-existing hazard this plan does not fix

A pop-up option answered *after* combat has ended applies its momentum modifier with a
fresh 20-day duration, and `bc_cleanup_effect` has already run, so nothing removes it
until it expires. This is **pre-existing behaviour introduced by neither plan 1 nor plan
2**, it applies today to `bc_momentum_minor_effect` and friends in
`bc_chronicles.0001`–`.0003`, and the 60-day pop-up cooldown keeps the window narrow.

**Plan 2 does not fix it and does not make it worse.** Task 6's `exists = var:bc_battle_size`
guard means a late-answered option applies no *family-2* modifier, because
`bc_clear_scratch_effect` removed the variable at combat end. That guard is there for
correctness of the read, and the leak prevention is a free consequence — do not remove
the guard on the grounds that "the variable is always written", because at that call
site it is not.

Record this in the README when plan 2 lands so a later pass can decide whether to gate
the option-level momentum calls the same way.

---

## File structure

| path | plan action | responsibility |
|---|---|---|
| `common/modifiers/bc_battle_modifiers.txt` | **create** (task 2) | the four family-2 modifiers |
| `common/modifiers/bc_momentum_modifiers.txt` | untouched | family 1, unchanged |
| `common/scripted_effects/bc_ledger_effects.txt` | modify | `bc_add_verb_effect`, `bc_apply_verb_effect`, the size gate inside the seam, three markers in `bc_battle_open_effect` |
| `common/scripted_effects/bc_scripted_effects.txt` | modify | `bc_cleanup_effect` grows to ten; `bc_mark_chronicle_commander_effect` added beside `bc_mark_chronicle_effect` |
| `common/scripted_triggers/bc_scripted_triggers.txt` | modify | `bc_chronicle_ready_commander_trigger` added beside `bc_chronicle_ready_trigger` |
| `common/script_values/bc_script_values.txt` | modify | `bc_chronicle_flag_days_value` |
| `common/combat_phase_events/bc_commander_phase_events.txt` | modify | 14 call sites swapped to the commander-only variants |
| `common/combat_phase_events/bc_knight_phase_events.txt` | **untouched** | its 8 call sites keep the shared variants — this is the point of Section 6 |
| `localization/english/bc_l_english.yml` | modify | 8 new keys + 6 backfilled `_desc` |

**Do not create `bc_ledger_triggers.txt` or `bc_rivalry_effects.txt`.** They still hold
nothing until plans 3 and 4.

---

# STAGE 2 — the verbs

### Task 1: Apply Q3's measured boundary, and mark the buckets

Plan 1 shipped `bc_battle_size` with an **invented** 2,000 boundary between buckets 1 and
2, and DIAG Q3 exists to measure it. Everything in this plan reads that variable, so it
gets settled first.

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_ledger_effects.txt`

- [ ] **Step 1: Read Q3's counts out of the plan-1 run**

Q3's five buckets were written into the spec by plan 1 task 16. Find them:

```bash
cd /d/ck3 && grep -n "Q3" docs/specs/2026-08-13-battle-chronicles-expansion-design.md
```

You need five numbers: how many battles logged `under 1k`, `1k`, `2k`, `3k`, `5k plus`.

**If they are not in the spec, stop.** Plan 1 task 16 was not completed and the boundary
cannot be set from nothing. Do not guess it a second time — go run plan 1 task 15.

- [ ] **Step 2: Decide the boundary**

The rule is: **put the bucket-1/2 boundary where the mass divides**, so that bucket 1 is
the ordinary skirmish and bucket 2 is a real field battle.

| what Q3 shows | boundary |
|---|---|
| `2k` and `3k` together hold a meaningful share (say ≥ 20% of battles) | **keep 2000** — the invented number was right |
| `2k` and `3k` are both near-empty and nearly everything is `under 1k` / `1k` | **lower to 1000** |
| `under 1k` is near-empty and the mass sits at `3k` / `5k plus` | **raise to 3000** |

Record the decision and the counts it rests on as a comment at the ladder, replacing the
"2,000 is INVENTED" paragraph.

- [ ] **Step 3: Edit the ladder and add the three markers**

In `bc_battle_open_effect`, find the bucket ladder by its `set_variable = { name = bc_battle_size`
lines — **not by line number**, because plan 1 shipped this file and the surrounding
comment block is being rewritten in the same step.

```
	if = {
		limit = { scope:combat_side.combat = { num_total_troops >= 10000 } }
		set_variable = { name = bc_battle_size value = 3 }
		debug_log = "BC: size 3"
	}
	else_if = {
		limit = { scope:combat_side.combat = { num_total_troops >= 2000 } }
		set_variable = { name = bc_battle_size value = 2 }
		debug_log = "BC: size 2"
	}
	else = {
		set_variable = { name = bc_battle_size value = 1 }
		debug_log = "BC: size 1"
	}
```

Substituting the boundary chosen in step 2 for `2000` if it changed.

**The markers are what makes the rest of this plan falsifiable.** DIAG Q3 is deleted at
the end of plan 1, so without them there is no way at runtime to tell a size-1 battle
from a size-3 one, and every claim in this plan about "big battles produce more moments"
becomes unmeasurable. They are permanent, and plans 3–6 get them for free.

**They log the bucket the mod actually chose, not the troop count.** That is the point —
Q3 measured the *world*, these measure the *mod*, and the whole risk in Section 6 is that
those two disagree.

- [ ] **Step 4: Verify**

```bash
cd /d/ck3/mods/battle_chronicles && grep -c "BC: size" common/scripted_effects/bc_ledger_effects.txt
cd /d/ck3/tools && python ck3.py validate --strict
```

Expected: **3**, then exit 0.

- [ ] **Step 5: Commit**

```bash
cd /d/ck3/mods/battle_chronicles
git add common/scripted_effects/bc_ledger_effects.txt
git commit -m "fix: set the bucket-1/2 boundary from measurement, and mark the buckets

The 2,000 threshold was invented in plan 1 and flagged as the one number in the
expansion with no evidence behind it. DIAG Q3 measured it. The three size markers
replace Q3 permanently, so every later plan can tell battle sizes apart at runtime."
```

---

### Task 2: The four family-2 modifiers

**Files:**
- Create: `mods/battle_chronicles/common/modifiers/bc_battle_modifiers.txt`

- [ ] **Step 1: Confirm the four modifier tags exist**

`validate` cannot check this — it has no knowledge of modifier tags — so check the API
dump directly:

```bash
cd /d/ck3 && grep -n "^Tag: \(army_damage_mult\|army_toughness_mult\|knight_effectiveness_mult\|army_pursuit_mult\)$" -A 1 docs/api/1.19.0.6/modifiers.log
```

Expected: four hits, each followed by `Use areas: character`. If any is missing, the
modifier will silently do nothing and no tool in this workspace will tell you.

- [ ] **Step 2: Write the file**

```
# Battle Chronicles - family 2, the character of the fight.
#
# Family 1 (bc_momentum_modifiers.txt) is the TIDE: pure `advantage`, one axis,
# up or down. Family 2 is the CHARACTER of the fight: what kind of battle this
# turned into. Every one of these is a trade, not a bonus - the army fights
# differently, not better.
#
# NO CALL SITE NAMES ONE. They are selected by bc_apply_verb_effect from the
# (KIND, SWING) an event already passes to the seam. If you find yourself adding
# `bc_bloodied` to an event, the KIND table is wrong, not the event.
#
# NO `stacking = yes` ON ANY OF THESE, deliberately. stacking is opt-in in CK3 -
# see 00_activity_tour_modifiers.txt:4 and 00_activity_hunt_modifiers.txt:286,
# which set it explicitly - so re-applying one of these inside the same battle
# REFRESHES its 20 days rather than doubling the effect. That is what we want: a
# battle that goes bloody twice is still one bloody battle, and stacking would
# make a long siege battle grotesque.
#
# These are `army_*` and `knight_*` tags, so unlike the momentum modifiers they
# do NOT appear in the combat advantage breakdown. They appear in the army stat
# breakdown and in the character's modifier list. Both render the localized name
# and, if present, the _desc.
#
# EVERY ONE OF THESE MUST APPEAR IN bc_cleanup_effect. That is the one rule.

# Traded blood for ground. He is winning the exchange and paying for it.
bc_bloodied = {
	icon = martial_positive
	army_damage_mult = 0.15
	army_toughness_mult = -0.10
}

# Dug in and refused to move. Nothing gets through and nothing gets done.
bc_shieldwall = {
	icon = martial_positive
	army_toughness_mult = 0.15
	army_damage_mult = -0.10
}

# The knights went in hard and early and the horses are blown.
bc_spent_horse = {
	icon = martial_negative
	knight_effectiveness_mult = -0.20
}

# They are running and we are on them.
bc_pursuit = {
	icon = martial_positive
	army_pursuit_mult = 0.15
}
```

`icon = martial_positive` and `martial_negative` are proven keys — `bc_momentum_modifiers.txt`
ships both.

- [ ] **Step 3: Validate, index, conflicts**

```bash
cd /d/ck3/tools && python ck3.py validate --strict && python ck3.py index && python ck3.py conflicts
```

Expected: all exit 0, and **no output about the four keys at all**.

**`--strict` will NOT warn that these modifiers are unlocalized, and it is important not
to expect it to.** Its missing-localization check is scoped to
`LOC_EXPECTED = {"common/traits", "common/decisions", "common/character_interactions"}`
(`D:/ck3/tools/ck3lib/validate.py:37`, applied at `:184`). **`common/modifiers` is not in
that set.** A modifier with no loc key validates perfectly clean, at `--strict`, forever.

That matters more here than it would elsewhere. This mod's whole presentation rests on
modifier names being prose — `README.md`'s "Modifier names are prose. The combat advantage
breakdown prints them verbatim next to `Commander Martial Skill`." An unlocalized family-2
modifier does not vanish; it renders its raw key, `bc_bloodied`, in the middle of the
player's battle UI. Nothing in the toolchain will tell you.

So task 3's static grep is not a formality that `--strict` also covers. **It is the only
automated check that exists for these four keys**, and the in-game look at the advantage
breakdown in task 12 is the only real one.

- [ ] **Step 4: Commit**

```bash
cd /d/ck3/mods/battle_chronicles
git add common/modifiers/bc_battle_modifiers.txt
git commit -m "feat: add the four family-2 battle modifiers

Family 1 is the tide, one axis. Family 2 is what kind of battle this turned into,
and every one of them is a trade rather than a bonus. No stacking key, so
re-application inside a battle refreshes rather than doubles."
```

---

### Task 3: Localization

**Files:**
- Modify: `mods/battle_chronicles/localization/english/bc_l_english.yml`

- [ ] **Step 1: Confirm the file's encoding before touching it**

```bash
cd /d/ck3/mods/battle_chronicles && head -c 8 localization/english/bc_l_english.yml | cat -A
```

Expected: the line starts `M-oM-;M-?` — UTF-8 **with BOM**. Every line is one leading
space then `KEY:0 "text"`. Writing this file without the BOM makes every key in it fail
to load, and `validate` checks for exactly this.

- [ ] **Step 2: Append the eight family-2 keys**

Add beneath the six momentum keys:

```
 bc_bloodied:0 "Blood for Ground"
 bc_bloodied_desc:0 "They have paid for every step they have taken, and they mean to be paid back."
 bc_shieldwall:0 "The Shields Are Locked"
 bc_shieldwall_desc:0 "They have set their feet. Nothing is getting through, and nothing is getting done."
 bc_spent_horse:0 "The Horses Are Blown"
 bc_spent_horse_desc:0 "The knights went in hard and went in early. There is nothing left in the animals."
 bc_pursuit:0 "Hard on Their Heels"
 bc_pursuit_desc:0 "The enemy is giving ground, and there is no order left in the giving."
```

- [ ] **Step 3: Backfill the six momentum descriptions**

The six family-1 modifiers ship with a name and no `_desc`, so their tooltips render the
stat line and nothing else. A missing `_desc` is legal — vanilla's
`befriend_scheme_modifiers_l_english.yml` has 28 names and zero descriptions — but
shipping family 2 with flavour and leaving family 1 without it puts two conventions in
one file for no reason, in a mod whose entire product is the flavour.

```
 bc_momentum_minor_desc:0 "The shouting has changed. They are listening again."
 bc_momentum_major_desc:0 "The line is moving forward and it is moving together."
 bc_momentum_decisive_desc:0 "It is over. They have not all worked that out yet."
 bc_faltering_minor_desc:0 "Men are looking over their shoulders. Not many. Enough."
 bc_faltering_major_desc:0 "The banner is where the line should be, and the line is not there."
 bc_faltering_decisive_desc:0 "It is not a battle any more. It is a crowd running in one direction."
```

**This is beyond the letter of the spec, which specifies eight keys.** It is six lines in
a file this task already opens, it removes an inconsistency rather than documenting one,
and it is committed separately so it can be dropped without touching anything else.

- [ ] **Step 4: Verify the count and the encoding survived**

```bash
cd /d/ck3/mods/battle_chronicles
grep -c "^ bc_" localization/english/bc_l_english.yml
head -c 8 localization/english/bc_l_english.yml | cat -A
cd /d/ck3/tools && python ck3.py validate --strict
```

The key count must have gone up by exactly **14**. The BOM must still be there — some
editors strip it silently on save, which is why this is checked after the edit and not
only before. `validate --strict` must exit 0.

**Do not gate this step on the absence of a missing-localization WARN.** There was never
going to be one: `--strict`'s loc cross-check is scoped to
`LOC_EXPECTED = {"common/traits", "common/decisions", "common/character_interactions"}`
(`ck3lib/validate.py:37`), and `common/modifiers` is not in it. A gate phrased "no WARN
for any `bc_` modifier" is satisfied by a run that produced no such WARN because it could
not produce one, and it would pass just as cleanly with all fourteen keys missing.

**So pair each of the four modifier keys with its definition explicitly instead:**

```bash
cd /d/ck3/mods/battle_chronicles
for m in bc_bloodied bc_shieldwall bc_spent_horse bc_pursuit; do
  d=$(grep -c "^$m = {" common/modifiers/bc_battle_modifiers.txt)
  l=$(grep -c "^ $m:" localization/english/bc_l_english.yml)
  echo "$m def=$d loc=$l"
done
```

Expected: **`def=1 loc=1` on all four rows.** A `def=1 loc=0` row is the failure this
whole step exists to catch, and it is invisible to every other check in this plan — the
modifier applies correctly, the battle is affected correctly, and the advantage breakdown
prints the raw key `bc_bloodied` at the player.

The `^ ` in the loc pattern is the required single leading space of the yml format, and
the `:` stops `bc_pursuit` matching a `bc_pursuit_desc` that does not exist yet. Task 12's
in-game look at the advantage breakdown is still the authoritative check; this is the one
that can run without launching the game.

- [ ] **Step 5: Commit — two commits, so do steps 2 and 3 as two cycles**

`git add` stages whole files, so two commits against one file require two edit-then-commit
cycles. **Do step 2, commit, then do step 3, commit.** If you already wrote both blocks in
one edit, make one commit and say so in its message rather than claiming a split that did
not happen.

After step 2:

```bash
cd /d/ck3/mods/battle_chronicles
git add localization/english/bc_l_english.yml
git commit -m "feat: localize the four family-2 modifiers"
```

After step 3:

```bash
cd /d/ck3/mods/battle_chronicles
git add localization/english/bc_l_english.yml
git commit -m "feat: give the family-1 momentum modifiers descriptions

They shipped with names only, so their tooltips rendered the stat line and
nothing else. Beyond the spec's letter; separable."
```

Run step 4's verification once, after both commits.

---

### Task 4: `bc_add_verb_effect` and `bc_apply_verb_effect`

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_ledger_effects.txt`

- [ ] **Step 1: Confirm the markers do not exist yet**

```bash
cd /d/ck3/tools && python ck3.py probe "BC: verb"
```

Expected: **exit 1** (no match). This is the failing test.

- [ ] **Step 2: Write both effects**

Append to `bc_ledger_effects.txt`:

```
# --- family 2: the character of the fight -----------------------------------
#
# The leaf, mirroring bc_add_momentum_effect in bc_scripted_effects.txt so that
# duration lives in exactly one place per family. 20 days, the same as momentum:
# both families are wiped at combat end by bc_cleanup_effect, so the duration
# only matters for the pre-existing case of a pop-up answered after the battle
# ended - see "the known pre-existing hazard" in this plan's preamble.
bc_add_verb_effect = {
	add_character_modifier = {
		modifier = $MODIFIER$
		days = 20
	}
}

# The (KIND, SWING) -> modifier table. THIS IS THE ONLY PLACE THE MAPPING LIVES.
#
#   bloodied    either  ->  bc_bloodied
#   entrenched  either  ->  bc_shieldwall
#   wild        either  ->  bc_spent_horse
#   ordered     up      ->  bc_pursuit
#   ordered     down    ->  nothing
#   adapted     either  ->  nothing
#   measured    either  ->  nothing
#
# NO `else` ARM. adapted and measured are the KINDs that describe how the
# commander READ the battle rather than what the battle DID to the army, and
# there is no army modifier that means "he judged it well". FIVE of the eighteen
# call sites are adapted or measured - bc_ground_favours_us, bc_lines_bogged_down,
# and the three pop-up options .0001b, .0002b and .0003b - and all five are
# supposed to fall through.
#
# THE COMPARISON IS `flag:$KIND$ = flag:bloodied`, NOT `$KIND$ = bloodied`. A bare
# `$KIND$ = bloodied` substitutes textually to `bloodied = bloodied`, an unknown
# key, which is a SILENT NO-OP that validate passes cleanly - the whole ladder
# would be dead and nothing would say so. Same rule and same reason as the tier
# comparison in bc_record_effective_tier_effect; the precedents are cited there.
#
# `ordered`/`down`, `entrenched`/`down` and `wild`/`up` are unreachable from the
# eighteen call sites that ship today. They are written anyway because SWING is a
# parameter of the seam, not of this table, and plan 6's wound gate reads SWING on
# every KIND. Do not delete the rows as dead code.
bc_apply_verb_effect = {
	if = {
		limit = { flag:$KIND$ = flag:bloodied }
		bc_add_verb_effect = { MODIFIER = bc_bloodied }
		debug_log = "BC: verb bloodied"
	}
	else_if = {
		limit = { flag:$KIND$ = flag:entrenched }
		bc_add_verb_effect = { MODIFIER = bc_shieldwall }
		debug_log = "BC: verb shieldwall"
	}
	else_if = {
		limit = { flag:$KIND$ = flag:wild }
		bc_add_verb_effect = { MODIFIER = bc_spent_horse }
		debug_log = "BC: verb spent horse"
	}
	else_if = {
		limit = {
			flag:$KIND$ = flag:ordered
			flag:$SWING$ = flag:up
		}
		bc_add_verb_effect = { MODIFIER = bc_pursuit }
		debug_log = "BC: verb pursuit"
	}
}
```

**The marker strings are literals, not `$KIND$`.** `bc_scripted_effects.txt`'s header
records that `$PARAM$` substitution inside a quoted string eats the space in front of it
(`"applied $MODIFIER$"` prints `appliedbc_momentum_major`). More importantly, a literal
per branch is what proves the *branch* was taken — a substituted marker would print the
same text whether the ladder worked or fell through, which is the exact failure this
marker exists to catch.

- [ ] **Step 3: Validate**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
```

Expected: exit 0.

**This proves nothing about the ladder.** `validate` would pass the broken
`$KIND$ = bloodied` form just as happily. The ladder is proven at runtime in task 12 by
at least three of the four `BC: verb` markers appearing. If none appears, the comparison
form is wrong and the entire family is dead.

- [ ] **Step 4: Commit**

```bash
cd /d/ck3/mods/battle_chronicles
git add common/scripted_effects/bc_ledger_effects.txt
git commit -m "feat: add the (KIND, SWING) -> family-2 modifier ladder

Nothing calls it yet. No call site will ever name a modifier - the mapping lives
here and only here, keyed on the parameters the seam already carries."
```

---

### Task 5: Extend `bc_cleanup_effect` — before anything applies a modifier

**This task must land before task 6.** Task 6 makes the seam apply family-2 modifiers.
If cleanup does not know about them first, then between the two commits every battle
leaves four modifiers on the commander for 20 days, and a bisect landing between them
looks like a serious regression.

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_scripted_effects.txt`

- [ ] **Step 1: Find it by name**

```bash
cd /d/ck3/mods/battle_chronicles && grep -n "^bc_cleanup_effect" -A 10 common/scripted_effects/bc_scripted_effects.txt
```

Plan 1 task 3 flattened it to six unguarded `remove_character_modifier` lines. If it
still has `if` blocks in it, plan 1 task 3 was not done — stop and do it.

- [ ] **Step 2: Add the four**

```
	remove_character_modifier = bc_bloodied
	remove_character_modifier = bc_shieldwall
	remove_character_modifier = bc_spent_horse
	remove_character_modifier = bc_pursuit
```

Appended to the existing six, inside `bc_cleanup_effect`. The result is a flat list of
ten.

- [ ] **Step 3: Confirm `bc_clear_faltering_effect` was NOT touched**

```bash
cd /d/ck3/mods/battle_chronicles && grep -n "^bc_clear_faltering_effect" -A 16 common/scripted_effects/bc_scripted_effects.txt
```

Expected: still three guarded `if` blocks covering only the three `bc_faltering_*`
modifiers, unchanged.

**This is load-bearing and it is the single most likely mistake in this plan.**
`bc_rally_effect` calls `bc_clear_faltering_effect` **mid-battle**. The two effects look
almost identical, and adding the four family-2 removals to the wrong one means every
rally strips the character of the fight along with the setback — silently, with no error
and no marker.

- [ ] **Step 4: Verify the count**

```bash
cd /d/ck3/mods/battle_chronicles
grep -n "^bc_cleanup_effect" -A 12 common/scripted_effects/bc_scripted_effects.txt | grep -c "remove_character_modifier"
```

Expected: **10**.

- [ ] **Step 5: Validate and commit**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
cd /d/ck3/mods/battle_chronicles
git add common/scripted_effects/bc_scripted_effects.txt
git commit -m "feat: strip the family-2 modifiers at combat end

Lands before anything applies them, so no commit in history leaks them."
```

---

### Task 6: Wire the ladder into the seam

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_ledger_effects.txt`

- [ ] **Step 1: Add the size gate to `bc_record_moment_effect`**

Find `bc_record_moment_effect` by name. Append, **after** the existing
`bc_record_effective_tier_effect` call and inside the effect's braces:

```

	# Family 2 needs a real battle. Size 1 is a skirmish and gets the tide only -
	# spec Section 6, "verb families gate on size".
	#
	# NESTED, NOT TWO SIBLING ROWS IN ONE `limit`. CK3 does not short-circuit and
	# guarantees no evaluation order among siblings, so
	# `limit = { exists = var:bc_battle_size  var:bc_battle_size >= 2 }` would
	# still evaluate the comparison when the variable is absent and log a read of
	# a missing variable.
	#
	# THE ABSENT CASE IS REAL, NOT DEFENSIVE PADDING. Eight of the eighteen call
	# sites are pop-up options, and a pop-up answered AFTER combat ended has had
	# bc_battle_size removed by bc_clear_scratch_effect. Without this guard that
	# option would log an error - and if the comparison somehow passed, it would
	# apply a 20-day modifier that bc_cleanup_effect has already run past and will
	# never remove.
	if = {
		limit = { exists = var:bc_battle_size }
		if = {
			limit = { var:bc_battle_size >= 2 }
			bc_apply_verb_effect = { KIND = $KIND$ SWING = $SWING$ }
		}
	}
```

- [ ] **Step 2: Confirm `$SWING$` now has a consumer**

```bash
cd /d/ck3/mods/battle_chronicles && grep -n "SWING" common/scripted_effects/bc_ledger_effects.txt
```

Expected: the seam's header comment, the seam's `bc_apply_verb_effect` call, and
`bc_apply_verb_effect`'s own `flag:$SWING$` row. Plan 1 accepted `SWING` and never read
it; this is where that ends.

- [ ] **Step 3: Confirm no call site was changed**

```bash
cd /d/ck3/mods/battle_chronicles
git status --short
```

Expected: **one modified file**, `common/scripted_effects/bc_ledger_effects.txt`. If any
event file appears, someone reached for a modifier at a call site. Revert it — the KIND
table is the interface.

**`git status`, not `git diff HEAD~1`.** Nothing in this task is committed yet, so a diff
against `HEAD~1` would show task 5's committed changes as well and the "one file" check
would be meaningless.

- [ ] **Step 4: Validate and commit**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
cd /d/ck3/mods/battle_chronicles
git add common/scripted_effects/bc_ledger_effects.txt
git commit -m "feat: the seam now applies a family-2 modifier

Gated on bc_battle_size >= 2, nested rather than sibling so a pop-up answered
after combat end - which has no bc_battle_size - does not read a missing variable.

BEHAVIOUR CHANGE: every moment in a battle of 2,000 or more now changes how the
army fights. bc_shieldbrother_forged in particular applied nothing to the
commander before plan 1 and now applies bc_pursuit; plan 1's task 11 commit
message flagged this as the one place its no-new-behaviour claim was not true."
```

---

# STAGE 2 — the pacing curve

### Task 7: `bc_chronicle_flag_days_value`

**Files:**
- Modify: `mods/battle_chronicles/common/script_values/bc_script_values.txt`

- [ ] **Step 1: Read the file's standing scope warning first**

```bash
cd /d/ck3/mods/battle_chronicles && sed -n '1,30p' common/script_values/bc_script_values.txt
```

The header records that this file holds **two** scope conventions — `scope:combat_side`
for the phase-event values, `root` for the aftermath values — and that new values must
not copy one into the other's call site. **This value belongs to neither.** It is
evaluated inside `bc_mark_chronicle_commander_effect`, which runs on the commander, so
`var:bc_battle_size` is a bare read of `this` with no scope prefix at all. Amend the
header to say there are now three conventions and which value uses the third.

- [ ] **Step 2: Write the value**

```
# The chronicle cooldown, in days, scaled by battle size.
#
#   size 3 (10,000+)  ->  10 days   a moment every other phase roll
#   size 2 (2,000+)   ->  20 days
#   size 1 (skirmish) ->  40 days
#
# Phase events roll every 5 days (COMBAT_EVENT_DAYS), so the flag length IS the
# pacing. The old flat 15 gave a two-month siege battle a constant stream and a
# skirmish nothing at all.
#
# SCOPE: `this`, a character - the commander. NOT scope:combat_side, NOT root.
# This is the third convention in this file; see the header.
#
# SHAPE: every branch is a bare `value = X` and there is NO base value outside
# the ladder. That is vanilla's own shape for a pure lookup - see
# swing_scales_discounts_multiplier_value in 00_diarchy_values.txt, an
# if/else_if/else where all three branches are bare `value =`. Nesting an if
# inside an if with no scope change is likewise shipped, in
# swing_scales_influence_cost_value in the same file.
#
# THE `exists` GUARD IS THE OUTER BRANCH, NOT A SIBLING ROW, for the reason
# stated at the seam's size gate: CK3 does not short-circuit, so a sibling
# `exists` would not stop the comparison from evaluating and logging a read of a
# missing variable.
#
# The 15 in the else arm is the old flat duration. It is unreachable if the call
# ordering in task 10 holds - bc_battle_open_effect writes bc_battle_size before
# bc_mark_chronicle_commander_effect is reached in all seven events - and it is
# there so that a future call site that breaks that ordering degrades to the
# shipped behaviour instead of to zero days, which would mean no cooldown at all.
bc_chronicle_flag_days_value = {
	if = {
		limit = { exists = var:bc_battle_size }
		if = {
			limit = { var:bc_battle_size >= 3 }
			value = 10
		}
		else_if = {
			limit = { var:bc_battle_size >= 2 }
			value = 20
		}
		else = {
			value = 40
		}
	}
	else = {
		value = 15
	}
}
```

- [ ] **Step 3: Validate and commit**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
cd /d/ck3/mods/battle_chronicles
git add common/script_values/bc_script_values.txt
git commit -m "feat: add bc_chronicle_flag_days_value

40/20/10 days by battle size. The else arm is the old flat 15, unreachable given
the call ordering, and there so a broken ordering degrades to shipped behaviour
rather than to no cooldown."
```

---

### Task 8: `bc_chronicle_ready_commander_trigger`

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_triggers/bc_scripted_triggers.txt`

- [ ] **Step 1: Confirm the shared trigger is what you think it is**

```bash
cd /d/ck3/mods/battle_chronicles && grep -n "^bc_chronicle_ready_trigger" -A 4 common/scripted_triggers/bc_scripted_triggers.txt
```

Expected: a single `NOT = { has_character_flag = bc_chronicle_recent }`.

- [ ] **Step 2: Add the commander variant beside it — do not modify it**

```
# The commander-only variant. The knight events keep bc_chronicle_ready_trigger
# above, unchanged, and that is the entire point of this pair.
#
# WHY NOT JUST EDIT THE SHARED ONE: no bc_ variable is ever written onto a knight
# (spec Section 1), so `NOT = { exists = var:bc_battle_moments }` is ALWAYS TRUE
# on a knight. Rewriting the shared trigger in place would therefore disable the
# knight cooldown entirely - and `type = knight` has no is_ai gate and fires for
# every knight on every side of every combat in the world, 41 fires from a single
# battle in the calibration run. That is the mod's largest event-spam surface and
# this is the one line holding it back.
#
# THE SECOND ARM IS THE FLOOR, not defensive padding. It lets a battle that has
# produced nothing yet always produce its first moment, no matter how long the
# size-scaled flag runs. A 40-day flag on a skirmish would otherwise mean most
# skirmishes are silent, which is the failure the pacing curve exists to fix.
#
# ONE `exists` ARM, NOT A VALUE COMPARISON. Scratch is cleared with
# remove_variable, so bc_battle_moments is either absent or >= 1 and there is no
# zero case to test. A `var:bc_battle_moments = 0` arm would read a missing
# variable on the first roll of every battle for every commander in the world -
# the highest-volume error source this expansion could possibly introduce.
bc_chronicle_ready_commander_trigger = {
	OR = {
		NOT = { has_character_flag = bc_chronicle_recent }
		NOT = { exists = var:bc_battle_moments }
	}
}
```

**Both arms of an `OR` are evaluated** — CK3 does not short-circuit — but neither arm
here reads a variable's *value*, and `exists` on a missing variable is a test, not a
read. That is why the floor is written as `exists` and not as a comparison.

- [ ] **Step 3: Do NOT touch the "Five substantive rows" comment**

Further down the file, above `bc_battle_is_notable_trigger`, a comment reads "Five
substantive rows plus the game rule". **That counts `calc_true_if` rows inside that one
trigger — size, blood, odds, warscore and the game rule — not triggers in the file.**
Adding a trigger to this file does not make it six. The comment immediately above it says
why the count matters: `calc_true_if` counts direct children, so the number is load-bearing
for that trigger's threshold and changing it changes what "notable" means.

This is called out because the comment reads like a file census and is not one.

- [ ] **Step 4: Validate and commit**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
cd /d/ck3/mods/battle_chronicles
git add common/scripted_triggers/bc_scripted_triggers.txt
git commit -m "feat: add bc_chronicle_ready_commander_trigger

A commander-only variant with a floor arm. The shared trigger is left alone
because its exists-arm would be always-true on a knight, which would un-gate the
mod's largest event-spam surface."
```

---

### Task 9: `bc_mark_chronicle_commander_effect`

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_scripted_effects.txt`

- [ ] **Step 1: Confirm the marker does not exist yet**

```bash
cd /d/ck3/tools
python ck3.py probe "BC: chronicle mark commander"
python ck3.py probe "BC: floor admitted"
```

Expected: **exit 1** on both. This is the failing test.

- [ ] **Step 2: Add the variant beside `bc_mark_chronicle_effect`**

```
# The commander-only variant. bc_mark_chronicle_effect above stays exactly as it
# is, at a flat 15 days, because the knight events call it - including
# bc_shieldbrother_forged, which calls it TWICE on two different characters. Do
# not collapse those two calls and do not point them here: a knight has no
# bc_battle_size, so bc_chronicle_flag_days_value would fall to its 15-day else
# arm on every single knight in every combat in the world. It would happen to
# produce the right number and would log a read of nothing, but it would be a
# lie about why.
#
# THE FLOOR DIAG IS FIRST, AND THAT IS LOAD-BEARING. It has to read both pieces
# of state BEFORE add_character_flag rewrites one of them. Every commander event
# calls this effect near the top of its `effect` block - after
# bc_battle_open_effect, before any bc_record_moment_effect, before any
# trigger_event - so here bc_battle_moments still holds the state from BEFORE
# this moment. Put this block below add_character_flag and it is always false.
#
# WHAT THE LIMIT MEANS: is_valid has already passed
# bc_chronicle_ready_commander_trigger. If the cooldown flag is set, that
# trigger's first arm was FALSE, so the only thing that let this event through
# was the floor arm. The two rows below re-test exactly that pair, so the marker
# fires when and only when the floor did work the cooldown would have blocked -
# and reading it needs no attribution of log lines to a particular battle.
bc_mark_chronicle_commander_effect = {
	if = {
		limit = {
			has_character_flag = bc_chronicle_recent
			NOT = { exists = var:bc_battle_moments }
		}
		debug_log = "BC: floor admitted"
	}

	add_character_flag = {
		flag = bc_chronicle_recent
		days = bc_chronicle_flag_days_value
	}
	debug_log = "BC: chronicle mark commander"
}
```

**`add_character_flag` accepts a script value for `days`.** The API dump does not say so
— `effects.log` gives the form and says only "a value or value interval" — but two
shipped call sites do it: `court_physician_search_max` in `20_health_effects.txt` and
`stress_threshold_cooldown_duration` in `00_stress_effects.txt`, three times in the
latter. **Cited by symbol, not line:** the spec cites `20_health_effects.txt:2264` for
this and the actual call is at `:2101`, which is exactly the drift symbol citations avoid.

Confirm both before relying on it:

```bash
cd "/d/SteamLibrary/steamapps/common/Crusader Kings III/game/common/scripted_effects"
grep -n "days = court_physician_search_max" 20_health_effects.txt
grep -n "days = stress_threshold_cooldown_duration" 00_stress_effects.txt
```

Expected: at least one hit each.

- [ ] **Step 3: Note what the two markers do and do not prove**

`BC: chronicle mark commander` proves the new effect is **reached** — that the call-site
swap in task 10 landed. It does **not** prove the duration resolved correctly; a script
value's result cannot be logged, because `debug_log` does not interpolate.

`BC: floor admitted` proves the **floor arm fires**, and it is the one claim in this plan
that survives the log's total lack of battle attribution, because its meaning is carried
entirely by the character's own state at the instant it is written and not by which lines
sit near it.

**Neither marker verifies the duration, and nothing in this plan does.** An earlier draft
of this step said the duration "is verified indirectly in task 12 by counting `BC: moment`
lines against the `BC: size` marker for the same battle." That is the exact procedure task
12 step 6 forbids — `type = commander` has no `is_ai` gate, so *the same battle* is not a
thing this log can identify. The claim is withdrawn. Tuning 40/20/10 needs a purpose-built
DIAG, not this run.

**`BC: floor admitted` is one-directional and step 6 says so.** Its presence proves the
floor lives. Its absence proves nothing, because the state it tests may simply never have
arisen.

- [ ] **Step 4: Validate and commit**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
cd /d/ck3/mods/battle_chronicles
git add common/scripted_effects/bc_scripted_effects.txt
git commit -m "feat: add bc_mark_chronicle_commander_effect

Size-scaled cooldown flag. Nothing calls it yet."
```

---

### Task 10: Swap the fourteen commander call sites

**Files:**
- Modify: `mods/battle_chronicles/common/combat_phase_events/bc_commander_phase_events.txt`

- [ ] **Step 1: Count what you are about to change**

```bash
cd /d/ck3/mods/battle_chronicles
grep -c "bc_chronicle_ready_trigger = yes" common/combat_phase_events/bc_commander_phase_events.txt
grep -c "bc_mark_chronicle_effect = yes" common/combat_phase_events/bc_commander_phase_events.txt
grep -c "bc_chronicle_ready_trigger = yes" common/combat_phase_events/bc_knight_phase_events.txt
grep -c "bc_mark_chronicle_effect = yes" common/combat_phase_events/bc_knight_phase_events.txt
```

Expected: **7, 7, 4, 4**.

**The ` = yes` is load-bearing, not decoration.** Dropping it gives **8, 7, 5, 5** —
both files open with a header comment naming these helpers in prose
(`bc_commander_phase_events.txt:13` names `bc_chronicle_ready_trigger`;
`bc_knight_phase_events.txt:8` names both). Those are the extra hits. Anchoring on the
call syntax counts call sites and only call sites, which is what this step is for.

The asymmetry in the unfiltered numbers is real rather than a miscount: the commander
header names only the trigger, so its bare counts are 8 and 7, while the knight header
names both, so its bare counts are 5 and 5. A reader who "corrects" one of those to make
the four agree has introduced an error, not removed one.

If the commander counts are not 7 and 7, plan 1 changed the event count and this task's
verification numbers are stale — recount before proceeding rather than forcing the
expected number.

- [ ] **Step 2: Swap, in the commander file only**

Replace every `bc_chronicle_ready_trigger` with `bc_chronicle_ready_commander_trigger`
and every `bc_mark_chronicle_effect` with `bc_mark_chronicle_commander_effect`, **in
`bc_commander_phase_events.txt` only**.

The two name pairs are safe for a blind replace-all *within that file*: neither new name
contains the old name as a substring, so a second pass cannot double-substitute.

**Let it rewrite the header comment at line 13 too.** That comment explains why the
trigger, not the weights, is what stops these events firing, and after this task it is the
commander variant doing that job — leaving the old name there would make the file's own
documentation name a helper it no longer calls. This is why step 1 counts with ` = yes`
and step 3 does not need to care: the comment moves with the code.

- [ ] **Step 3: Confirm ordering — this is what makes the script value work**

In each of the seven `effect` blocks, `bc_battle_open_effect = yes` must appear **before**
`bc_mark_chronicle_commander_effect`. Plan 1 task 9 step 1 placed it there deliberately.
It matters more now than it did then: `bc_battle_open_effect` is what writes
`bc_battle_size`, and the mark effect is what reads it.

```bash
cd /d/ck3/mods/battle_chronicles
grep -n "bc_battle_open_effect = yes\|bc_mark_chronicle_commander_effect = yes\|bc_record_moment_effect = {" \
  common/combat_phase_events/bc_commander_phase_events.txt
```

**Anchored on call syntax on purpose.** This file's header is prose that names its own
helpers — line 13 does it today and step 2 above rewrites that line — so an unanchored
pattern here counts documentation as if it were code. That is the same trap step 1 of this
task documents at length, and it is worth avoiding twice.

Expected: 21 lines — **open, then mark, then record**, in that order, seven times. All
seven events carry a `record` line in this file: four record directly (plan 1 task 9 step
2) and three record inside their `else` branch (step 3), which is later in the block
either way. The three pop-up branches record from an option in `bc_events.txt` instead,
which is later still and not in this grep. **Read them in order and confirm it by eye.**

Two different things depend on that order, and neither reports its own failure at runtime:

- **open before mark.** `bc_battle_open_effect` writes `bc_battle_size`; the mark reads it
  through `bc_chronicle_flag_days_value`. A mark that precedes its open falls to the
  15-day `else` arm silently — the flag still gets written, just with the wrong number.
- **mark before record.** `bc_record_moment_effect` creates `bc_battle_moments`, and the
  floor DIAG inside the mark effect tests that variable's *absence*. A record that precedes
  its mark makes `BC: floor admitted` permanently unreachable, and step 6 of task 12 would
  then read an instrumentation bug as an inconclusive result.

- [ ] **Step 4: Confirm the knight file is untouched**

```bash
cd /d/ck3/mods/battle_chronicles
git diff --stat HEAD
grep -c "commander_trigger\|commander_effect" common/combat_phase_events/bc_knight_phase_events.txt
```

Expected: **one file** in the diffstat, and **0** commander-variant references in the
knight file.

This is the whole design of Section 6. A single leaked swap in the knight file un-gates
the mod's largest event-spam surface and makes a script value read a variable that
cannot exist.

- [ ] **Step 5: Validate, index, conflicts, deploy**

```bash
cd /d/ck3/tools && python ck3.py validate --strict && python ck3.py index && python ck3.py conflicts && python ck3.py deploy
```

Expected: all exit 0. `conflicts` reads a sqlite index that only `index` rebuilds — never
run it alone.

- [ ] **Step 6: Commit**

```bash
cd /d/ck3/mods/battle_chronicles
git add common/combat_phase_events/bc_commander_phase_events.txt
git commit -m "feat: point the commander phase events at the size-scaled pacing

Fourteen call sites in the commander file. The knight file's eight keep the
shared flat-15 variants deliberately - see the comment on
bc_chronicle_ready_commander_trigger."
```

---

### Task 11: Static verification of the whole plan

Everything before this is unproven at runtime, but several claims can be settled without
launching the game. Do them before spending seven minutes on a restart.

**Files:** none — this task only reads.

- [ ] **Step 1: Every modifier the mod can apply is stripped at combat end**

```bash
cd /d/ck3/mods/battle_chronicles
grep -hoE "^[a-z_]+ = \{" common/modifiers/bc_*.txt | sed 's/ = {//' | sort > /tmp/bc_mods_defined
grep -oE "remove_character_modifier = [a-z_]+" common/scripted_effects/bc_scripted_effects.txt \
  | sed 's/remove_character_modifier = //' | sort -u > /tmp/bc_mods_stripped
diff /tmp/bc_mods_defined /tmp/bc_mods_stripped
```

Expected: **no output**. Ten modifiers defined, ten stripped.

This is the one rule `bc_battle_modifiers.txt`'s header states, and it is the rule most
likely to be broken by a later plan adding a fifth modifier. A non-empty diff means a
modifier leaks past combat end for 20 days and nothing at runtime will say so.

**A line only in `bc_mods_stripped` is also a failure** — it means cleanup names a
modifier that does not exist, which is a silent no-op rather than an error.

- [ ] **Step 2: No call site names a family-2 modifier**

```bash
cd /d/ck3/mods/battle_chronicles
grep -rn "bc_bloodied\|bc_shieldwall\|bc_spent_horse\|bc_pursuit" \
  common/combat_phase_events/ events/
```

Expected: **no output**. The `(KIND, SWING)` table is the interface.

- [ ] **Step 3: Every seam parameter is consumed**

```bash
cd /d/ck3/mods/battle_chronicles
grep -n "TIER\|KIND\|SWING" common/scripted_effects/bc_ledger_effects.txt
```

Expected: all three appear on a right-hand side that is actually read —
`flag:$TIER$` in the tier ladder, `flag:$KIND$` in the verb ladder and as `$KIND$` passed
through the tier ladder to `bc_write_style_effect`, `flag:$SWING$` in the verb ladder's
`ordered` row.

- [ ] **Step 4: Nothing compares a parameter without `flag:`**

```bash
cd /d/ck3/mods/battle_chronicles
grep -rn '\$[A-Z]*\$ = [a-z]' common/scripted_effects/ common/scripted_triggers/
```

Expected: **no output**. Any hit is a `$PARAM$ = literal` comparison, which substitutes
to an unknown key and is a silent no-op that `validate` passes. This is the single
highest-consequence class of error in this mod and it is invisible to every other check
in this plan.

- [ ] **Step 5: Full static pass**

```bash
cd /d/ck3/tools && python ck3.py validate --strict && python ck3.py index && python ck3.py conflicts && python ck3.py deploy
```

Expected: all exit 0.

- [ ] **Step 6: Nothing to commit**

This task changes no files. If `git status --short` is not clean, something in steps 1–4
was "fixed" in passing — review it as its own change.

---

### Task 12: Run it

**This is the runtime checkpoint. Everything before it is unproven.**

- [ ] **Step 1: Clear the logs — with the game closed**

Delete `error.log` and `debug.log` from
`D:\Documents\Paradox Interactive\Crusader Kings III\logs`.

Skipping this makes every sweep below unfalsifiable — `error.log` accumulates across
sessions. This also discards plan 1's run, so if anything from it is still unrecorded,
write it into the README or the spec first.

- [ ] **Step 2: Fight battles of different sizes**

Launch. Fight at least one battle you can see is small (a few hundred men) and at least
one large one (several thousand). **Both halves of this plan are about the difference
between them, so a run with only one size proves nothing.**

Let at least one large battle run long enough to produce several moments.

- [ ] **Step 3: Sweep the size markers**

```bash
cd /d/ck3/tools && python ck3.py probe "BC: size"
```

Expected: exit 0, with **at least two distinct sizes** among the results.

**Expect a lot of lines.** Phase events have no `is_ai` gate, so this marker fires for
every commander in every combat in the world, not only yours. That makes "two distinct
sizes" an easy bar — it is testing that the *ladder* is live, not that your battle was
read correctly, and nothing in this log can tell you the latter.

If only `BC: size 1` appears no matter what the world is doing, the bucket ladder is
misreading `num_total_troops` and every gate in this plan is dead. That is a blocker on
the whole plan, not a tuning question.

- [ ] **Step 4: Sweep the verb markers**

```bash
cd /d/ck3/tools && python ck3.py probe "BC: verb"
```

Expected: exit 0, with **at least two distinct verbs**.

| what came back | what it means |
|---|---|
| two or more distinct verbs | the `flag:$KIND$` comparison works and the ladder is live |
| exactly one verb, repeatedly | inconclusive — you may simply have fought one kind of battle. Fight more before concluding anything |
| nothing at all, but `BC: size 2` or `3` appeared | **the ladder is dead.** Check the `flag:` wrapping in `bc_apply_verb_effect` first, then the nested size gate in the seam |
| nothing at all, and only `BC: size 1` appeared | not a failure — size 1 gets no family-2 modifier by design. Go fight a bigger battle |

- [ ] **Step 5: Sweep the pacing marker**

```bash
cd /d/ck3/tools && python ck3.py probe "BC: chronicle mark commander"
```

Expected: exit 0. Its absence alongside any `BC: fired bc_` line means the task-10 swap
did not land — the events are firing and marking through the old shared effect.

- [ ] **Step 6: Check the floor — and understand what cannot be checked**

**You cannot attribute markers to a battle from this log.** `type = commander` has no
`is_ai` gate — `bc_commander_phase_events.txt`'s header records 59 commander fires in one
session and `type = knight` produced 41 fires from a single battle — so every combat in
the world writes into the same `debug.log`, interleaved. Counting `BC: moment` lines
"between two `BC: size` lines" attributes one battle's moments to another. Do not do it,
and do not report a number derived that way.

That constraint is why task 9 put the floor's evidence inside a **single line's own
meaning** instead of inside a count:

```bash
cd /d/ck3/tools && python ck3.py probe "BC: floor admitted"
```

`BC: floor admitted` is written only when, at the instant the event's effect began, the
commander already carried `bc_chronicle_recent` **and** `bc_battle_moments` did not exist.
`is_valid` had already passed `bc_chronicle_ready_commander_trigger`, and a live cooldown
flag makes that trigger's first arm false, so the floor arm is the only thing that could
have admitted the event. **One such line anywhere in the log proves the floor works.** It
does not matter which battle wrote it, who wrote it, or what surrounds it, and that is the
entire reason the marker is shaped this way rather than as a count.

**Read it one-directionally:**

| result | conclusion |
|---|---|
| at least one `BC: floor admitted` | **the floor works.** Done — no further floor testing this run |
| none, and `BC: chronicle mark commander` is present | **inconclusive, not a failure.** The tested state may never have arisen. Go to the retry below |
| none, and `BC: chronicle mark commander` is absent too | not a floor result at all — the task-10 swap did not land. Step 5 already caught this |

**The retry, if it came back empty.** The state the marker needs is a commander starting a
battle while a cooldown from an *earlier* battle is still running. Nothing about that
requires log attribution, so you can go make it happen directly: fight a second battle
within a few in-game days of the first, with the same commander, and re-run the probe.
Two battles back to back with one leader is the whole recipe. If a long run with several
such back-to-back pairs still yields nothing, treat it as a failure and look at the two
likely causes — the `OR` in `bc_chronicle_ready_commander_trigger` written as two `AND`
rows, or `bc_battle_moments` surviving combat end, which makes the floor arm permanently
false from the second battle onward. For the second cause the thing to check is
`bc_clear_scratch_effect` and its two call sites in `bc_chronicles.0091` and `.0092` — not
`bc_cleanup_effect`, which strips modifiers and does not touch scratch.

For context only, these two should both be non-empty and neither is a floor result:

```bash
cd /d/ck3/tools
python ck3.py probe "BC: size 1"
python ck3.py probe "BC: moment"
```

**The 40/20/10 durations themselves are not verified by this run, and this plan does not
claim they are.** A script value's result cannot be logged. What is verified is that the
value is *reached* (step 5's marker) and that the floor can override it (this step's
marker). Whether 40 days is the right number for a large battle is untested and untestable
from this log; it needs a purpose-built DIAG.

- [ ] **Step 7: Error sweep**

```bash
cd /d/ck3/tools && python ck3.py probe "bc_"
```

Apply plan 1's three-row pass condition unchanged. Row 3 — "a line beginning `BC: `" —
now legitimately covers this plan's nine new markers.

**Watch specifically for a missing-variable read naming `bc_battle_size` or
`bc_battle_moments`.** Those are the two variables this plan added readers for, and both
readers are guarded; a hit means a guard is written as a sibling row somewhere instead of
nested.

- [ ] **Step 8: Record the findings**

Write into `README.md`:

- the Q3 boundary chosen in task 1 and the counts behind it;
- which verbs were observed, and which were not. **All four are reachable** from the
  shipped call sites — `bc_bloodied` from three, `bc_shieldwall` from three,
  `bc_spent_horse` from four, `bc_pursuit` from three — so a verb that never appears
  after several varied battles is worth investigating rather than shrugging at. What is
  unreachable is three `(KIND, SWING)` *pairs*: `wild`/`up`, `entrenched`/`down` and
  `ordered`/`down`;
- the pre-existing late-pop-up modifier hazard from this plan's preamble;
- that `bc_mark_chronicle_effect` and `bc_chronicle_ready_trigger` are now knight-only,
  and why;
- whether `BC: floor admitted` appeared, **and if it did not, that the floor is untested
  rather than broken.** Write the distinction down. It is the one result in this run that
  a later reader is likely to misremember as a failure, because every other empty probe in
  this plan is one.

```bash
cd /d/ck3/mods/battle_chronicles
git add README.md
git commit -m "docs: record the plan 2 runtime findings"
```

- [ ] **Step 9: Record the Q3 boundary in the spec — a workspace commit**

The boundary gates plan 6's wound gate as well, so it belongs in the spec, not only in
the mod's README. Section 6's "Risk" paragraph says the threshold is invented and must be
measured; replace it with what was measured.

```bash
cd /d/ck3
git add docs/specs/2026-08-13-battle-chronicles-expansion-design.md
git commit -m "docs: record the measured battle-size boundary"
```

---

## Done when

- `common/modifiers/bc_battle_modifiers.txt` defines four modifiers and
  `bc_cleanup_effect` strips all ten. Task 11 step 1's diff is empty.
- No file under `common/combat_phase_events/` or `events/` names a family-2 modifier.
- `bc_commander_phase_events.txt` holds 7 `bc_chronicle_ready_commander_trigger = yes` and
  7 `bc_mark_chronicle_commander_effect = yes`, and 0 of the shared variants **including in
  its header comment**, which task 10 step 2 rewrites along with the code.
- `bc_knight_phase_events.txt` holds 4 and 4 `= yes` call sites of the **shared** variants
  and 0 of the commander variants. Its header comment still names the shared variants,
  correctly, so an unfiltered count there is 5 and 5 — count with ` = yes`.
- `validate --strict`, `index`, `conflicts` and `deploy` all exit 0.
- A cleared-log run returns at least two distinct `BC: size` markers, at least two
  distinct `BC: verb` markers, and `BC: chronicle mark commander`.
- The floor is **either** proven by at least one `BC: floor admitted` line, **or** recorded
  in the README as untested with the back-to-back-battle retry noted for a later run.
  Both outcomes close this plan; only a run that never produced
  `BC: chronicle mark commander` at all leaves it open. **Not** "an isolated battle
  produced a moment" — no battle is isolated in an interleaved log.
- The error sweep returns nothing outside plan 1's three whitelist rows, and in
  particular no missing-variable read naming `bc_battle_size` or `bc_battle_moments`.

## Not in this plan

| thing | plan |
|---|---|
| family 3, the wounds | 6 — **gated on plan 1, not on this plan.** Plan 6 hangs the wound off `bc_record_effective_tier_effect`'s decisive arm and reads `var:bc_battle_size`, both of which plan 1 ships. It can run before this plan, after it, or instead of it |
| B, the reputation traits | 3 — gated on Q1 and Q4 |
| C, the named foe | 4 — `bc_battle_foe` is written by plan 1 and read by nobody until then |
| D, the eve and the aftermath | 5 |
| gating the pop-up options' momentum calls on `exists = var:bc_battle_size` | unscheduled — recorded in the preamble as a pre-existing hazard |
