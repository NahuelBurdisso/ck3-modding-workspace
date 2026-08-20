# Toast Priority Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a moment whose *effective* rank is major or decisive speak over a toast cooldown that a minor moment set, without editing any of the 444 templates.

**Architecture:** `bc_record_effective_tier_effect` already resolves the post-escalation rank and throws it away. Store it in `var:bc_last_moment_rank` on the same scope the toast gate evaluates on, let `bc_can_toast_trigger` accept rank 2+ against a second, scarcer flag, and spend that flag only on an actual interruption. Four definitions across three script files, plus four stale comments corrected in passing.

**Tech Stack:** CK3 Paradox script (`common/scripted_effects`, `common/scripted_triggers`), the `D:/ck3/tools/ck3.py` CLI, `grep -cF` over `debug.log`.

**Spec:** `docs/specs/2026-08-20-battle-chronicles-toast-priority-design.md`. Section numbers below (4.1, 4.2, …) refer to it. Read Sections 3, 4 and 7 before starting.

---

## Before you touch anything

**This plan is BLOCKED until Task 1 is complete.** Task 1 is a game run with none
of this design's code in the build. Its output — a single number, `p` — chooses a
constant in Task 5. Skipping it and guessing the constant means stacking two
unmeasured changes onto one measurement, which is the exact failure
`docs/battle-chronicles/bench.md` §5 was rewritten to prevent.

**Pre-flight, run it before Task 2 and it costs nothing:**

```bash
cd /d/ck3 && python tools/_planrehearse.py
```

It parses this file's own `Old:`/`New:` blocks, applies all eleven to scratch copies
of the real files, and runs every count assertion in Tasks 2-6 against the result.
Expected: `all edits applied cleanly`, `0 failing check(s)`. A failure here means an
anchor has drifted — fix the plan, not the mod. **The script is meaningless once the
edits have landed** (the anchors will no longer match) and should be deleted then.
It already caught two anchors that spanned into a line the source continues past.

Both repos are separate: `D:/ck3` is the workspace, `D:/ck3/mods/battle_chronicles`
is the mod, and `mods/` is gitignored by the workspace. **Script edits commit in the
mod repo; doc, plan and tool edits commit in the workspace repo.** Each task below
says which.

---

## Testing model — read this, it is not pytest

There is no unit-test harness for CK3 script and this plan does not build one.
The substitute, weakest to strongest, is:

| layer | command | catches |
|---|---|---|
| static | `python tools/ck3.py validate battle_chronicles --strict` | brace balance, BOM loss, duplicate top-level defs, broken `file.txt:NNN` citations |
| symbol | `Grep` for def/use counts | a name defined but never read, or read but never defined |
| compile | `python tools/ck3.py probe 'Compiling source'` after a boot | a scripted effect that failed to compile, killing every call site silently |
| behaviour | `grep -cF` over the final `debug.log` | which code paths ran, and in what proportion |
| the screen | a human playing a battle | what the player actually saw |

**`validate` passing means nothing about behaviour.** It has passed on every defect
this project has ever shipped. Treat it as a syntax gate only.

The TDD analogue is therefore: **for every code task, run the verification command
BEFORE the edit and record the output, then run it again after.** A number that did
not move is a failed task. Where the only honest check is a game run, the task says
so and defers to Task 8 — runs cost ~7 minutes each, so all code lands before the
second and last one.

Two traps that have each bitten this project more than once:

- **Read `debug.log` only after `ck3.exe` has left `tasklist`.** It is written live;
  a mid-session read undercounts by roughly half. This has put a wrong number into a
  document three separate times.
- **Archive `<user dir>/logs/` before `launch --clear-logs`** — it unlinks everything
  including `.bak`, with no backup.

`<user dir>` is `D:/Documents/Paradox Interactive/Crusader Kings III`.

---

## File structure

| file | repo | responsibility after this change |
|---|---|---|
| `common/scripted_effects/bc_ledger_effects.txt` | mod | writes `bc_last_moment_rank` in all three tier arms (4.1); clears it at combat end (4.4); four stale comment counts corrected — "nine"→"ten" at `:27` and `:542`, "eight of the eighteen"→465 at `:224` and `:271` (4.5) |
| `common/scripted_triggers/bc_scripted_triggers.txt` | mod | `bc_can_toast_trigger` gains the second, rank-gated arm (4.2) |
| `common/scripted_effects/bc_scripted_effects.txt` | mod | `bc_start_toast_cooldown_effect` spends the high budget and logs the preemption (4.3) |
| `docs/battle-chronicles/bench.md` | workspace | §3's flag table and clear line learn the new flag (4.6) |
| `tools/_bcorder.py` | workspace | header documents its two known limits |
| `docs/plans/2026-08-20-battle-chronicles-toast-priority.md` | workspace | this file; Task 1 and Task 8 record their results into it |

No template is edited. No new scripted-effect parameter is introduced — which is
deliberate, because a declared-but-unread parameter fails to compile and kills every
call site with no other symptom.

---

## Task 1: Run 1 — measure the 11/16 rungs with none of this code in the build

**Files:**
- Modify: `docs/plans/2026-08-20-battle-chronicles-toast-priority.md` (record results, workspace repo)

**Why first:** every volume figure in spec Section 6 rests on a 72/18/10 split that
is the *target* of the 11/16 rungs, not a measurement. The two shares actually
measured are 40/19/41 (rungs 4/6) and 61/21/18 (rungs 8/13). If the true rank-2+
share lands near 18%, preemption fires rarely enough to read as dead; if the rungs
undershoot, it fires constantly. The constant in Task 5 is chosen from this number.

- [ ] **Step 1: Confirm the working tree is clean and carries no code from this design**

```bash
cd /d/ck3/mods/battle_chronicles && git status --short
```

Expected: empty. If anything from Tasks 2-7 is present, stash it — Run 1 is only
valid against a build without it.

```bash
cd /d/ck3/mods/battle_chronicles && grep -c "bc_last_moment_rank" common/scripted_effects/bc_ledger_effects.txt common/scripted_triggers/bc_scripted_triggers.txt common/scripted_effects/bc_scripted_effects.txt
```

Expected: `0` for all three files.

- [ ] **Step 2: Confirm the rungs really are 11 and 16**

```bash
cd /d/ck3/mods/battle_chronicles && grep -n "bc_battle_moments >=" common/scripted_effects/bc_ledger_effects.txt
```

Expected: **three** lines — `>= 11`, `>= 16`, `>= 11`. The ladder is asymmetric by
construction, so three is correct and four would be wrong: the decisive arm is
`decisive OR (major AND >=11) OR (minor AND >=16)` and the major arm is
`major OR (minor AND >=11)`. If any line reads `8` or `13`, the 11/16 change was
never committed and this whole plan is premature — stop and surface it.

- [ ] **Step 3: Static gate**

```bash
cd /d/ck3 && python tools/ck3.py validate battle_chronicles --strict
```

Expected: 0 errors, and the 2 known `namespace` warnings. Anything else, fix before
spending a run.

- [ ] **Step 4: Confirm the mod is deployed and in the playset**

```bash
cd /d/ck3 && python tools/ck3.py deploy battle_chronicles && python tools/ck3.py playset list | grep -i "battle chronicles"
```

Expected: one line, `Battle Chronicles ... mod/battle_chronicles.mod`. Use
`playset list`, not `playset audit` — `audit` prints only problems and a
`N problem(s)` line, and never names a mod, so it cannot answer this question. A
workspace mod silently falls out
of `dlc_load.json` whenever the Paradox launcher runs, and a run against a build that
does not contain the mod looks exactly like a run where nothing fired.

- [ ] **Step 5: Archive the existing logs, then launch**

```bash
cd /d/ck3 && mv "/d/Documents/Paradox Interactive/Crusader Kings III/logs" "/d/Documents/Paradox Interactive/Crusader Kings III/logs-archive-$(date +%Y%m%d-%H%M)"
```

Then:

```bash
cd /d/ck3 && python tools/ck3.py launch --clear-logs
```

- [ ] **Step 6: Confirm the mod is live and compiled, before playing**

Once the main menu is up, in another shell:

```bash
cd /d/ck3 && grep -F "Battle Chronicles" "/d/Documents/Paradox Interactive/Crusader Kings III/logs/debug.log" | head -3
```

Expected: a launcher dump line of the form `<Name>|mod/<slug>.mod|Enabled`.

```bash
cd /d/ck3 && python tools/ck3.py probe 'Compiling source'
```

Expected: **no `bc_` symbol listed.** Any `bc_` name here means that effect failed to
compile and every one of its call sites is dead — the run would measure nothing.

- [ ] **Step 7: Play**

Personally command at least three long battles. `type = commander` roots on the
commander, so `is_ai = no` means the player is commanding in person, not merely
watching. Then **exit the game and wait for `ck3.exe` to leave `tasklist`** — it
lingers ~20 seconds at ~9 GB after the window closes.

```bash
tasklist | grep -i ck3.exe
```

Expected: no output before proceeding.

- [ ] **Step 8: Count the shares**

```bash
cd "/d/Documents/Paradox Interactive/Crusader Kings III/logs" && for m in "BC: moment minor" "BC: moment major" "BC: moment decisive" "BC: fired" "BC: combat end cleanup" "BC: wound gates passed"; do printf "%-28s %s\n" "$m" "$(grep -cF "$m" debug.log)"; done
```

Record all six numbers. Then compute:

- **`p = (major + decisive) ÷ (minor + major + decisive)`** — the number Task 5 needs.
- **moments per commander-side = `BC: fired` ÷ `BC: combat end cleanup`** — the
  denominator; the rungs are fitted per COMMANDER, not per battle.

- [ ] **Step 9: Judge the run**

| reading | verdict |
|---|---|
| shares near **~72 / ~18 / ~10** | on target, proceed |
| decisive share under 5% | regression, not a win — the rungs overshot; re-fit and re-run, do not proceed |
| `BC: wound gates passed` = 0 | the rungs went too far; re-fit and re-run |
| `BC: wound gates passed` nonzero and **below 55** | expected. The series is 96 at rungs 4/6 and 55 at 8/13, both counted off archived final logs |
| `BC: wound gates passed` **above 55** | the rungs did not bite; investigate before proceeding |

**55 and 96 are the numbers, not 62.** 62 appeared in `bench.md` and in workspace
memory until `3b52fb6`; it was a mid-session read. A run scored against 62 would read
a *rise* from 55 to 56-61 as the expected fall and pass a regression.

- [ ] **Step 10: Choose the constant**

> **p ≥ 0.20 → `high = 20` days. p < 0.20 → `high = 10` days.**

- [ ] **Step 11: Record the results in this plan and commit**

Append a `## Run 1 results` section to the bottom of this file containing: the date,
the six counts, `p`, moments per commander-side, and the chosen `high` value. Task 8
compares against these, so they must be written down, not remembered.

```bash
cd /d/ck3 && git add docs/plans/2026-08-20-battle-chronicles-toast-priority.md && git commit -m "docs: record Run 1 counts for the 11/16 rungs"
```

---

## Task 2: Store the effective rank, and clear it (4.1 + 4.4)

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_ledger_effects.txt`

**These two edits must land in the SAME commit.** 4.1 alone writes
`bc_last_moment_rank` on **every AI commander in the world** — `is_ai = no` gates the
toast, not the ledger — and without 4.4 it accumulates as a permanent save variable on
every character who has ever commanded.

- [ ] **Step 1: Record the before-state**

```bash
cd /d/ck3/mods/battle_chronicles && grep -c "bc_last_moment_rank" common/scripted_effects/bc_ledger_effects.txt
```

Expected: `0`.

- [ ] **Step 2: Write the rank in the decisive arm**

Insert after `debug_log = "BC: moment decisive"`, i.e. **above** the
`# Family 3 hangs here` comment block and above `bc_wound_effect`.

**Do not extend the anchor down into the `# Family 3 hangs here` line.** That line
continues `... ONLY here. This arm IS the effective tier: it is`, so an anchor ending
at `ONLY here.` followed by a newline matches nothing. The two lines below are
sufficient and unique — `RANK = 3` occurs once in the file.

Old:

```
		bc_write_style_effect = { RANK = 3 KIND = $KIND$ }
		debug_log = "BC: moment decisive"
```

New:

```
		bc_write_style_effect = { RANK = 3 KIND = $KIND$ }
		debug_log = "BC: moment decisive"

		# THE TOAST GATE'S ONLY INPUT. bc_can_toast_trigger reads this to decide
		# whether a moment may speak over a cooldown a minor moment set. It is
		# written here rather than passed as a parameter because this effect
		# already runs in the recipient's scope at every one of the 444 call
		# sites - proved mechanically by tools/_bcorder.py, not assumed.
		#
		# ABOVE bc_wound_effect, NOT APPENDED TO THE ARM. The wound call is last
		# on purpose so "BC: wound" can only ever follow the "BC: moment
		# decisive" that caused it; appending here would silently break that
		# ordering and the ratio the two counts are read as.
		set_variable = { name = bc_last_moment_rank value = 3 }
```

- [ ] **Step 3: Write the rank in the major arm**

Same rule as Step 2 — the `# THE MAJOR ARM WOUNDS TOO` line continues into `, AND IT
IS THE ARM THAT DOES THE WORK.`, so keep the anchor to the two lines below.
`RANK = 2` occurs once in the file.

Old:

```
		bc_write_style_effect = { RANK = 2 KIND = $KIND$ }
		debug_log = "BC: moment major"
```

New:

```
		bc_write_style_effect = { RANK = 2 KIND = $KIND$ }
		debug_log = "BC: moment major"

		# See the decisive arm above for why this is here and why it is above the
		# wound call.
		set_variable = { name = bc_last_moment_rank value = 2 }
```

- [ ] **Step 4: Write the rank in the else arm**

Old:

```
	else = {
		bc_write_style_effect = { RANK = 1 KIND = $KIND$ }
		debug_log = "BC: moment minor"
	}
```

New:

```
	else = {
		bc_write_style_effect = { RANK = 1 KIND = $KIND$ }
		debug_log = "BC: moment minor"

		# THE ELSE ARM MUST WRITE TOO, AND WRITING 1 IS NOT THE SAME AS WRITING
		# NOTHING. Leaving it unwritten would let the previous moment's rank
		# survive into this one, and every minor moment after a decisive one
		# would inherit the right to preempt.
		set_variable = { name = bc_last_moment_rank value = 1 }
	}
```

- [ ] **Step 5: Clear it at combat end**

In `bc_clear_scratch_effect`, add the remove **and fix the count in BOTH comments
that state it** — each says "nine" and this makes it ten. Leaving either would plant
exactly the stale number Task 3 exists to remove.

**Line numbers below are pre-edit.** Steps 2-4 insert ~21 lines at `:344` and above,
so by the time you run this step the second comment has moved from `:542` to about
`:564`. Both edits are content-anchored, so the shift does not matter — but do not
read `grep -n` output as a mismatch.

Old (`:27`, the file header — above every insertion, so it does not move):

```
# CLEARING MEANS remove_variable, NEVER set_variable value = 0. Six of the nine
# scratch variables cannot hold zero (enumerated at bc_clear_scratch_effect
```

New:

```
# CLEARING MEANS remove_variable, NEVER set_variable value = 0. Six of the ten
# scratch variables cannot hold zero (enumerated at bc_clear_scratch_effect
```

Old (`:542`, above the effect):

```
# remove_variable, NEVER set_variable value = 0. Six of the nine cannot hold
```

New:

```
# remove_variable, NEVER set_variable value = 0. Six of the ten cannot hold
```

Old:

```
	remove_variable = bc_battle_creed
}
```

New:

```
	remove_variable = bc_battle_creed

	# NOT here to stop a stale rank preempting - tools/_bcorder.py proves the
	# record always precedes the read, so the gate always sees the current
	# moment's rank. It is here because bc_record_effective_tier_effect runs for
	# EVERY AI COMMANDER IN THE WORLD (is_ai = no gates the toast, not the
	# ledger), and without this the variable accumulates permanently on every
	# character who has ever commanded. This effect runs under side_commander ?=
	# and OUTSIDE the aftermath gate, i.e. on both sides of every combat in the
	# world, so it does reap that accumulation.
	remove_variable = bc_last_moment_rank
}
```

- [ ] **Step 6: Verify def/use counts**

```bash
cd /d/ck3/mods/battle_chronicles && grep -c "bc_last_moment_rank" common/scripted_effects/bc_ledger_effects.txt
```

Expected: `4` — three writes and one remove. Not 3, not 5.

```bash
cd /d/ck3/mods/battle_chronicles && grep -c "Six of the nine" common/scripted_effects/bc_ledger_effects.txt
```

Expected: `0`. **Unanchored on purpose** — the string occurs twice, at `:27` and
`:542`, and an anchored grep would silently pass with one of them still stale.

- [ ] **Step 7: Static gate**

```bash
cd /d/ck3 && python tools/ck3.py validate battle_chronicles --strict
```

Expected: 0 errors, 2 known `namespace` warnings. This edit adds lines to
`bc_ledger_effects.txt`; `validate` resolves `file.txt:NNN` citations, so a citation
into this file that has shifted will surface here. (At time of writing no script
comment cites `bc_ledger_effects.txt:NNN`, so none is expected.)

- [ ] **Step 8: Commit**

```bash
cd /d/ck3/mods/battle_chronicles && git add common/scripted_effects/bc_ledger_effects.txt && git commit -m "feat: record the effective moment rank on the toast recipient

The rank was resolved in three arms and thrown away. Storing it lets the
toast gate rank moments without a parameter and without touching any of
the 444 templates. Cleared at combat end because this effect runs for
every AI commander in the world, not just the player."
```

---

## Task 3: Correct the stale call-site count (4.5)

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_ledger_effects.txt`

Separate commit because it is a documentation fix that happens to live in a script
file, and mixing it into Task 2 would hide it.

- [ ] **Step 1: Confirm the arithmetic before writing it**

```bash
cd /d/ck3/mods/battle_chronicles && grep -c "bc_record_moment_effect = {" common/combat_phase_events/bc_commander_phase_events.txt common/combat_phase_events/bc_knight_phase_events.txt events/bc_events.txt
```

Expected: `238`, `206`, `21` — summing to 465. Note `bc_events.txt` lives in the
top-level `events/`, not `common/events/`. If any count differs, use the measured
numbers, not the ones written below.

- [ ] **Step 2: Find every site, not just the one the spec cites**

```bash
cd /d/ck3/mods/battle_chronicles && grep -n "Eight of the eighteen" common/scripted_effects/bc_ledger_effects.txt
```

Expected: **two** hits, `:224` and `:271`. The spec cites only `:271`; fixing that
one alone leaves the identical stale count six screens above it, which is how this
number survived the 434-template batch in the first place. Both get fixed.

- [ ] **Step 3: Fix `:224` — a top-level comment, NO indentation**

Old:

```
# NO COMBAT SCOPE IS TOUCHED HERE. Eight of the eighteen call sites are pop-up
# options, and bc_events.txt records as an invariant that those character events
# hold no combat scope at all. Everything combat-scoped lives in
# bc_battle_open_effect instead.
```

New:

```
# NO COMBAT SCOPE IS TOUCHED HERE. Twenty-one of the four hundred and sixty-five
# call sites are pop-up options, and bc_events.txt records as an invariant that
# those character events hold no combat scope at all. Everything combat-scoped
# lives in bc_battle_open_effect instead.
```

- [ ] **Step 4: Fix `:271` — inside the effect body, EVERY LINE STARTS WITH A TAB**

The two lines below are tab-indented in the file. Copy the leading tab; an
unindented `old_string` will not match, and an unindented `new_string` would land
flush-left comments in the middle of a tab-indented body.

Old:

```
	# THE ABSENT CASE IS REAL, NOT DEFENSIVE PADDING. Eight of the eighteen call
	# sites are pop-up options, and a pop-up answered AFTER combat ended has had
```

New:

```
	# THE ABSENT CASE IS REAL, NOT DEFENSIVE PADDING. Twenty-one of the four
	# hundred and sixty-five call sites are pop-up options - 238 commander phase
	# events, 206 knight, 21 in bc_events.txt, and all 21 of the bc_events.txt
	# sites sit inside `option` blocks while no phase-event site does. The old
	# "eight of the eighteen" predated the 434-template batch. A pop-up answered
	# AFTER combat ended has had
```

**The substance of the warning must survive the edit** — the sentence continues into
`bc_battle_size removed by bc_clear_scratch_effect`, and that is still correct.

- [ ] **Step 5: Verify no stale shape remains and the warning survived**

```bash
cd /d/ck3/mods/battle_chronicles && grep -c "Eight of the eighteen" common/scripted_effects/bc_ledger_effects.txt
```

Expected: `0` — **both** sites fixed. **Do not add `-i`.** The replacement at `:271`
deliberately quotes the old phrase in lowercase as `"eight of the eighteen"`, so a
case-insensitive grep returns `1` and reads as a failed edit on a correct one.

```bash
cd /d/ck3/mods/battle_chronicles && grep -A8 "THE ABSENT CASE IS REAL" common/scripted_effects/bc_ledger_effects.txt | grep -c "bc_battle_size"
```

Expected: `1` — the warning survived. `-A8`, not `-A2`: the replacement comment is
six lines long, so a narrower window returns `0` and reads as "the warning was
destroyed" on a correct edit.

- [ ] **Step 6: Static gate and commit**

```bash
cd /d/ck3 && python tools/ck3.py validate battle_chronicles --strict
```

```bash
cd /d/ck3/mods/battle_chronicles && git add common/scripted_effects/bc_ledger_effects.txt && git commit -m "docs: correct the pop-up call-site count, stale since the 434 batch"
```

---

## Task 4: Let the gate read the rank (4.2)

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_triggers/bc_scripted_triggers.txt`

Safe to land before Task 5: with nothing writing `bc_toast_cooldown_high`, the new
arm's `NOT = { has_character_flag = ... }` is always true and the gate widens
immediately. **That is a real behaviour change on its own** — it is Task 5 that makes
it a budget rather than a hole. Land Tasks 4 and 5 back to back; do not run the game
between them.

- [ ] **Step 1: Replace the trigger body**

Old:

```
bc_can_toast_trigger = {
	is_ai = no
	NOT = { has_character_flag = bc_toast_cooldown }
}
```

New:

```
bc_can_toast_trigger = {
	is_ai = no
	OR = {
		NOT = { has_character_flag = bc_toast_cooldown }
		AND = {
			NOT = { has_character_flag = bc_toast_cooldown_high }
			exists = var:bc_last_moment_rank
			trigger_if = {
				limit = { exists = var:bc_last_moment_rank }
				var:bc_last_moment_rank >= 2
			}
		}
	}
}
```

- [ ] **Step 2: Add the header note above the trigger**

Insert immediately above `bc_can_toast_trigger = {`, after the existing header:

```
# THE SECOND ARM IS A PRIORITY LANE, NOT A SECOND CHANCE. A moment whose
# EFFECTIVE rank is major or decisive may speak over a cooldown a minor moment
# set, and pays for it out of bc_toast_cooldown_high instead. The rank is on this
# scope already - see bc_record_effective_tier_effect - so this needs no parameter
# and no call site changes.
#
# `exists` SIBLING PLUS trigger_if, AND BOTH ARE LOAD-BEARING. CK3 does not
# short-circuit and guarantees no evaluation order among siblings, so a plain
# `exists = var:X` beside `var:X >= 2` still evaluates the comparison when the
# variable is absent and logs a read of a missing variable - the trap
# bc_record_moment_effect's own header documents, and bc_depth_rung_one_trigger is
# the shipped example of the correct shape. The `exists` sibling is needed a
# SECOND time because a trigger_if whose limit is FALSE evaluates to TRUE: without
# it the AND would pass vacuously whenever the variable is absent, and a rank-less
# toast would preempt.
#
# `is_ai = no` BEING FIRST DOES NOT MAKE THE REST CONDITIONAL. Every sibling is
# evaluated regardless of order, so the guard above is required for AI recipients
# too. Any argument of the form "row 1 already excluded that case" is invalid in
# this codebase.
```

- [ ] **Step 3: Verify the shape mechanically**

```bash
cd /d/ck3/mods/battle_chronicles && grep -c "bc_toast_cooldown_high" common/scripted_triggers/bc_scripted_triggers.txt
```

Expected: `2` — the `NOT` row in the trigger body, and the mention in the Step 2
header comment. A `1` means one of the two steps was skipped.

```bash
cd /d/ck3/mods/battle_chronicles && grep -A12 "^bc_can_toast_trigger = {" common/scripted_triggers/bc_scripted_triggers.txt | grep -c "exists = var:bc_last_moment_rank"
```

Expected: `2` — the sibling and the `trigger_if` limit. **A `1` here is the bug the
first draft of this design shipped**; go back to Step 1.

- [ ] **Step 4: Static gate**

```bash
cd /d/ck3 && python tools/ck3.py validate battle_chronicles --strict
```

Expected: 0 errors, 2 known `namespace` warnings. This edit adds lines to
`bc_scripted_triggers.txt`, which is cited at `:332` and `:340` from two comments
inside the same file — both are far above the edit point at `:584`, so neither
shifts. If `validate` reports a citation failure anyway, fix the citation rather
than reverting.

- [ ] **Step 5: Commit**

```bash
cd /d/ck3/mods/battle_chronicles && git add common/scripted_triggers/bc_scripted_triggers.txt && git commit -m "feat: let a major or decisive moment speak over a minor moment's cooldown"
```

---

## Task 5: Spend the high budget, and mark the preemption (4.3)

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_scripted_effects.txt`

**Uses the `high` value chosen in Task 1 Step 10.** Substitute the number; do not
leave a placeholder.

- [ ] **Step 1: Replace the effect body**

Old:

```
bc_start_toast_cooldown_effect = {
	add_character_flag = {
		flag = bc_toast_cooldown
		days = 10
	}
}
```

New — with `<HIGH>` replaced by `20` or `10` per Task 1:

```
bc_start_toast_cooldown_effect = {
	# READ BEFORE WRITE, so the OLD flag state is still visible. Every one of the
	# 444 call sites is the first statement inside a bc_can_toast_trigger gate, so
	# "base held at entry" is equivalent to "passed through the high arm while base
	# was held" - i.e. this branch IS the preemption, exactly. It is also the only
	# obtainable counter, because a trigger cannot log.
	#
	# THE HIGH FLAG IS SET ONLY BY A PREEMPTION, NEVER BY AN ORDINARY RANK-2+
	# TOAST, AND THE FEATURE DIES IF THAT IS GOT WRONG. Setting it whenever the
	# rank is 2+ is self-defeating in exactly the case this exists to serve: past
	# rung 16 every moment is rank 3, so every toast would refresh the high flag
	# while the 10-day base expires under it, the high arm could never pass again,
	# and preemption would become structurally impossible for the rest of the
	# battle. It would also make the verification undecidable - "preempt 0" would
	# be produced both by a feature that is unnecessary and by a correctly wired
	# one that over-refreshed itself. The high budget pays for INTERRUPTIONS, so
	# only an interruption spends it.
	if = {
		limit = { has_character_flag = bc_toast_cooldown }
		debug_log = "BC: toast preempt"
		add_character_flag = {
			flag = bc_toast_cooldown_high
			days = <HIGH>
		}
	}

	# UNCONDITIONAL, AND THE SUB-ADDITIVITY IS DELIBERATE. A preemption also resets
	# the ordinary clock, so an interruption costs the player a later routine
	# toast. Moving this into an `else` would "restore independence" and raise the
	# volume ceiling to the full additive bound - a real volume change dressed up
	# as a tidy-up.
	add_character_flag = {
		flag = bc_toast_cooldown
		days = 10
	}

	# THE DENOMINATOR, not a budget. How often a rank-2+ moment spoke at all, by
	# either arm. Without it, "preempt 0" cannot be told apart from "no rank-2+
	# moment ever reached the gate".
	#
	# NESTED, NOT TWO ROWS IN ONE `limit`, for the reason bc_can_toast_trigger
	# records: CK3 does not short-circuit.
	if = {
		limit = { exists = var:bc_last_moment_rank }
		if = {
			limit = { var:bc_last_moment_rank >= 2 }
			debug_log = "BC: toast rank2"
		}
	}
}
```

- [ ] **Step 2: Verify the placeholder is gone and the flag is written exactly once**

```bash
cd /d/ck3/mods/battle_chronicles && grep -c "<HIGH>" common/scripted_effects/bc_scripted_effects.txt
```

Expected: `0`.

```bash
cd /d/ck3/mods/battle_chronicles && grep -c "bc_toast_cooldown_high" common/scripted_effects/bc_scripted_effects.txt
```

Expected: `1`.

- [ ] **Step 3: Verify the high write is INSIDE the preemption branch**

This is the one check that catches the fatal wiring error.

```bash
cd /d/ck3/mods/battle_chronicles && grep -B4 "flag = bc_toast_cooldown_high" common/scripted_effects/bc_scripted_effects.txt | grep -c "limit = { has_character_flag = bc_toast_cooldown }"
```

Expected: `1`. A `0` means the high flag is being set outside the preemption branch —
**stop and fix; the feature is dead if this ships.**

- [ ] **Step 4: Static gate**

```bash
cd /d/ck3 && python tools/ck3.py validate battle_chronicles --strict
```

Expected: 0 errors, 2 known `namespace` warnings. `bc_scripted_effects.txt:231-234`
is cited from `bc_flavour.txt:2304`; this edit is at `:353` and below, so that
citation does not shift.

- [ ] **Step 5: Commit**

```bash
cd /d/ck3/mods/battle_chronicles && git add common/scripted_effects/bc_scripted_effects.txt && git commit -m "feat: give preemptive toasts a scarcer budget of their own

Set only on an actual interruption, never on a rank-2+ toast that took a
free slot - otherwise past rung 16 every toast would refresh the high flag
and preemption would become impossible for the rest of the battle."
```

---

## Task 6: Teach the bench the new flag (4.6)

**Files:**
- Modify: `docs/battle-chronicles/bench.md:117` and the table at `:119-124` (workspace repo)

**Load-bearing for the verification, not tidiness.** §3 claims to enumerate every
throttle in the mod and currently lists exactly the four `bc_` flags that exist. A
20-day flag that survives the bench's cooldown clear makes preemption impossible for
the remainder of the test session, producing exactly the `preempt 0` reading Task 8
instructs the reader to revert on — the feature would be reverted on the strength of
a bench that failed to clear it.

- [ ] **Step 1: Add the flag to the clear line**

Old:

```
    effect = { remove_character_flag = bc_eve_cooldown remove_character_flag = bc_toast_cooldown remove_character_flag = bc_chronicle_recent remove_character_flag = bc_popup_cooldown }
```

New:

```
    effect = { remove_character_flag = bc_eve_cooldown remove_character_flag = bc_toast_cooldown remove_character_flag = bc_toast_cooldown_high remove_character_flag = bc_chronicle_recent remove_character_flag = bc_popup_cooldown }
```

- [ ] **Step 2: Add the row to the table**

Insert after the `bc_toast_cooldown` row, using the `high` value from Task 1:

```
| `bc_toast_cooldown_high` | <HIGH> | whether a major or decisive moment may speak OVER `bc_toast_cooldown`. Set only by an actual preemption. **Clearing `bc_toast_cooldown` alone leaves this one holding**, and a session that forgets it will measure zero preemptions and conclude the feature is dead |
```

- [ ] **Step 3: Verify**

```bash
cd /d/ck3 && grep -c "bc_toast_cooldown_high" docs/battle-chronicles/bench.md
```

Expected: `2` — the clear line and the table row.

```bash
cd /d/ck3 && grep -c "<HIGH>" docs/battle-chronicles/bench.md
```

Expected: `0`.

- [ ] **Step 4: Commit**

```bash
cd /d/ck3 && git add docs/battle-chronicles/bench.md && git commit -m "docs: bench must clear bc_toast_cooldown_high or it measures zero preemptions"
```

---

## Task 7: Document `_bcorder.py`'s two known limits

**Files:**
- Modify: `tools/_bcorder.py` (workspace repo)

The spec leans on this script's output as proof that the record call always precedes
the toast gate in the same scope. Its limits belong in its own header, where the next
person to run it will see them.

- [ ] **Step 1: Add a header comment at the top of the file**

Insert above `import re, sys`:

```python
# Proves the invariant the toast-priority design rests on: in every phase-event
# template, bc_record_moment_effect precedes the bc_can_toast_trigger gate, and the
# toast `if` sits exactly one brace deeper - i.e. inside the same enclosing scope.
# That is what lets the gate read var:bc_last_moment_rank with no parameter.
# Re-run after any bulk edit to the phase-event files.
#
# TWO KNOWN LIMITS:
#   1. The SIDE constant is dead. It was going to check the knight wrapper
#      explicitly and the depth check subsumed it; it is left as documentation of
#      what the depth column is really measuring.
#   2. Brace counting does not strip comments, so an unbalanced brace inside a
#      comment would skew the depth column. No template currently has one.
```

- [ ] **Step 2: Verify the script still runs and still reports clean**

```bash
cd /d/ck3 && python tools/_bcorder.py
```

Expected, unchanged from the spec:

```
bc_commander_phase_events.txt
  pairs: 238  events: 476
  out-of-order pairs: 0
  depth mismatches: 0
bc_knight_phase_events.txt
  pairs: 206  events: 412
  out-of-order pairs: 0
  depth mismatches: 0
```

**Any nonzero in either zero column invalidates Task 2's parameterless approach** —
stop and surface it, do not proceed to Task 8.

- [ ] **Step 3: Commit**

```bash
cd /d/ck3 && git add tools/_bcorder.py && git commit -m "docs: record _bcorder.py's dead SIDE constant and comment-brace limit"
```

---

## Task 8: Run 2 — verify on the screen and in the log

**Files:**
- Modify: `docs/plans/2026-08-20-battle-chronicles-toast-priority.md` (record results, workspace repo)

- [ ] **Step 1: Static gates before spending a run**

```bash
cd /d/ck3 && python tools/ck3.py validate battle_chronicles --strict && python tools/_bcorder.py
```

Expected: 0 errors, 2 known `namespace` warnings, and all four zero columns still zero.

- [ ] **Step 2: Archive, deploy, launch**

Same as Task 1 Steps 4-5.

- [ ] **Step 3: Compile sweep before playing**

```bash
cd /d/ck3 && python tools/ck3.py probe 'Compiling source'
```

Expected: **no `bc_` symbol.** No new parameter was introduced, so the
declared-but-unread compile failure should not apply — sweep anyway, because that
failure is silent at every call site and this is the only thing that finds it.

- [ ] **Step 4: Play at least three long battles, personally commanding**

**Count toasts on screen, per battle.** There is no marker for a toast; the log
cannot answer this question. Note also whether each extra message *read as the
battle turning* or as one more line of noise — that judgement is Step 8 and it is
the real verdict.

Then exit, and wait for `ck3.exe` to leave `tasklist`.

- [ ] **Step 5: Count**

```bash
cd "/d/Documents/Paradox Interactive/Crusader Kings III/logs" && for m in "BC: toast preempt" "BC: toast rank2" "BC: moment minor" "BC: moment major" "BC: moment decisive" "BC: fired" "BC: combat end cleanup"; do printf "%-28s %s\n" "$m" "$(grep -cF "$m" debug.log)"; done
```

**The first two will be single digits and that is expected, not a fault.**
`is_ai = no` is the first row of the gate, so `bc_start_toast_cooldown_effect` never
runs for AI. Unlike every other `BC:` marker, which counts the whole world, these two
are player-only. A zero is weak evidence, which is why three long battles is the floor.

- [ ] **Step 6: Regression guard**

`BC: fired` and the three `BC: moment` shares must be **unchanged from Run 1**. This
design touches only the toast gate. Movement there is an accident, not a result —
diagnose it before reading anything else in the table below.

- [ ] **Step 7: Verdict**

| reading | verdict |
|---|---|
| `BC: toast preempt` > 0, screen shows **up to 6** toasts per 30-day battle | **pass**. 6 is the volume ceiling, not a fitted band — the pre-change baseline is an n=1 on-screen count and cannot support a lower bound |
| preempt 0, and `BC: moment major` + `decisive` also ~0 | not this feature — the rungs undershot. Re-fit and repeat Task 1 |
| preempt 0, `BC: toast rank2` > 0 | rank-2+ moments spoke, but always into a free slot; the base budget never collides. The feature is **unnecessary, not broken** — revert it |
| preempt 0, `BC: toast rank2` 0, world-wide `BC: moment major`+`decisive` healthy | the rank is not reaching the gate scope. Re-run `tools/_bcorder.py` first. Note this row crosses a **world-wide** count against **player-only** counters; at the three-battle floor the expected player rank-2 count is ~6, so a 0 is meaningful rather than merely small |
| screen shows **7 or more** toasts per 30-day battle | above the ceiling of 6, so the volume model is wrong, not merely mistuned. Diagnose before turning anything; if it is only mistuned, turn `high` and **never** the base |

- [ ] **Step 8: The judgement no log can make**

No log line can say the toast the player saw was the turn of the battle. **If the
extra messages read as noise, this design is wrong and the answer is not a smaller
cooldown.** It means the in-battle toast is the wrong surface for narrative weight,
and the effort belongs in the combat-end chronicle instead — one pop-up that narrates
the battle from the depth, style, ground, foe and wound already recorded. That is the
intended follow-on design either way; this outcome would promote it from *next* to
*instead*.

Write the judgement down in plain words, not just the counts.

- [ ] **Step 9: Record and commit**

Append a `## Run 2 results` section to this file: the counts, the on-screen toast
count per battle, the verdict row that matched, and the Step 8 judgement.

```bash
cd /d/ck3 && git add docs/plans/2026-08-20-battle-chronicles-toast-priority.md && git commit -m "docs: record Run 2 results for the toast priority lane"
```

- [ ] **Step 10: Update the workspace memory**

`C:/Users/nahue/.claude/projects/D--Claude/memory/project_battle_chronicles.md` still
lists "unmeasured since 2026-08-15" as a standing risk. Replace it with what Run 1
and Run 2 measured, and record `bc_toast_cooldown_high` as a fifth throttle. Memory is
not in git; no commit.

---

## What this plan deliberately does not do

- **No template is edited.** Parameterising `bc_can_toast_trigger = { RANK = $TIER$ }`
  would touch all 444 call sites for information already on the scope, and every
  parameter added is a chance to hit the declared-but-unread compile failure.
- **No flag is used in place of the variable.** Day-granular flags linger for the rest
  of the day, so a rank-1 moment later the same day would inherit a rank-2 grant.
- **The base cooldown and the `chance` weights are not touched.** Weights decide
  *which* moment speaks, not how often the player hears one, and changing two dials at
  once makes the next run unreadable.
- **No new physical moments are written.** That is the larger and better idea, and it
  is deferred rather than dismissed: a new major moment competing for a slot allocated
  by a timer is a new major moment nobody sees. This is its precondition.
