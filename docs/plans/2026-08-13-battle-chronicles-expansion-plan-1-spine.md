# Battle Chronicles Expansion — Plan 1: The Spine (stages 0 and 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the mod's combat-end machinery, then add the one seam every future system reports through — so that at the end of this plan a battle writes down what happened in it, and a log proves it.

**Architecture:** Two stages. Stage 0 is behaviour-neutral: strip stale diagnostics, flatten and split files, and collapse three combat-end events into two so that grading provably runs before scratch clearing. Stage 1 adds `bc_battle_open_effect` (writes battle-scoped scratch at the top of every phase event) and `bc_record_moment_effect` (the seam every moment reports through), wires all eighteen existing moment sites to it, and ships a diagnostic pass that answers five open questions in one game run.

**Tech Stack:** CK3 script (Paradox clausewitz script), targeting CK3 1.19.0.6 under the AGOT playset. Workspace CLI is `python ck3.py` run from `D:/ck3/tools`.

**Spec:** `D:/ck3/docs/specs/2026-08-13-battle-chronicles-expansion-design.md`

---

## Read this before task 1

### There are no unit tests. This is what replaces them.

CK3 has no test harness. Nothing in this plan can be proven by running a command in
under a second. The verification loop is:

| step | command | pass condition |
|---|---|---|
| syntax | `cd /d/ck3/tools && python ck3.py validate --strict` | exit 0 |
| | **`validate` is syntax-only** — brace balance, BOM, loc keys, descriptor keys, structure. It has **no knowledge of trigger, effect or scope keys**, so a well-formed reference to a key that does not exist passes cleanly. Never gate a semantic question on `validate`. | |
| collisions | `python ck3.py index` then `python ck3.py conflicts` | exit 0. **`conflicts` reads a sqlite index that only `index` rebuilds — a stale index makes it always pass, so never run it alone** |
| deploy | `python ck3.py deploy` | exit 0 |
| runtime | launch the game, fight a battle, then `python ck3.py probe <pattern>` | see below |

**`--strict` adds almost nothing, and the plans that follow this one depend on knowing
exactly how little.** `ck3lib/validate.py:182-185` walks `def_categories` — the **top-level
definition keys** the parser collected — and warns for any whose key is absent from the
mod's localization. It does that only for the three categories in `LOC_EXPECTED` at `:37`:
`common/traits`, `common/decisions`, `common/character_interactions`.

**Battle Chronicles has none of those three directories, and no plan in this expansion
creates one.** `ls common/` in the mod returns `character_memory_types`,
`combat_phase_events`, `game_rules`, `modifiers`, `on_action`, `opinion_modifiers`,
`script_values`, `scripted_effects`, `scripted_triggers` — and `:182` is `--strict`'s only
effect in the whole file. **So `validate --strict` and `validate` do exactly the same thing
here.** Every plan writes `--strict` out of habit and because a later plan might add a
trait file; the flag is not currently buying anything.

Three consequences, all of which cost this expansion review time:

- **A loc key merely *referenced* is never checked.** Toast titles and descs, event `desc`
  branches, `$PARAM$`-substituted keys — all invisible. `--strict` is silent whether they
  exist or not, so its silence proves nothing about them.
- **`common/modifiers` and `common/game_rules` are not in the set.** A modifier with no loc
  key validates clean forever and renders its raw name in the player's battle UI.
- Therefore **never write a pass condition of the form "exit 0 with no missing-localization
  WARN naming X"** unless X is a top-level definition in one of those three directories.
  Everywhere else that phrasing describes a check that cannot fail. Pair the key against
  its call site instead; plans 2 through 6 each carry such a check.

**`ck3.py probe` exits 1 when nothing matches.** For a marker sweep, exit 0 is the pass
condition. For an error sweep, non-zero *would* be the pass condition — but read the next
paragraph before relying on that, because as of 2026-08-13 it cannot be reached.

**The error sweep does not work against an uncleared log, and this was measured, not
assumed.** `error.log` accumulates across sessions. Run today, before this plan changes
anything, `python ck3.py probe "bc_"` exits **0** with 225 matching lines already in it.
A sweep whose pass condition can never be met is not a gate. So:

1. **With the game closed**, delete `error.log` and `debug.log` from
   `D:\Documents\Paradox Interactive\Crusader Kings III\logs`. The game recreates both on
   launch. This is the only way to make the sweep falsifiable. Do it before every runtime
   checkpoint, and note that it discards the previous run's logs — if the previous run's
   findings are not yet written into the README, write them first.
2. Then run, then sweep.

**Even on a cleared log the sweep will not come back empty, and the noise is expected
rather than broken.** Two families recur, and neither is a defect:

- **Game-rule key references out of save files.** A modded game rule is baked into every
  save made with it, so a save read without those rule definitions available cannot
  resolve them. `bc_game_rules.txt:10-13` documents this exact error text and states
  plainly: "That is expected, not a bug." Do not go chasing it.
- **The launcher's mod-list dump**, one line in `debug.log`:
  `BC Spike|mod/bc_spike.mod|Disabled`. Rewritten on every launch.
- **The mod's own `debug_log` markers.** `probe` globs *every* `*.log` in the log
  directory (`ck3lib/launch.py:82-92`), `debug.log` included, and ten of the mod's
  permanent markers carry an event key in their text —
  `"BC: fired bc_banner_falls"` and six siblings in `bc_commander_phase_events.txt`,
  `"BC: fired bc_knight_holds_the_breach"` and two siblings in
  `bc_knight_phase_events.txt`. Task 1 step 2 deliberately **keeps** these, and task 15
  step 2 requires battles that fire them, so a run that satisfies the plan is a run whose
  sweep returns them. **This is the trap that a rotated `debug.log` hides:** measure the
  sweep on a log with no `BC:` lines in it and this whole family is invisible.

**Whitelist on the KEY NAME, not on the `in file:` suffix.** This matters and is easy to
get wrong. `probe` groups per *line*, and CK3 splits a key-reference error across several
lines, so the `in file:` suffix lands only on the last fragment — most groups do not carry
one at all, and one carries `in file: ""`. A whitelist phrased as "every group names a save
game" is therefore unsatisfiable. Worse, the bare fragment
`Failed to read key reference: <key>, near line: N` is **exactly the shape a real error in
a mod file takes**, so whitelisting that prefix would wave through the very thing the
sweep exists to catch. The key name, by contrast, is always on the matched line.

**Sweep pass condition.** Every group returned either:

1. is a `Failed to read key reference` naming one of the nine game-rule option keys —
   `bc_frequency_low` / `_default` / `_high`, `bc_swing_subtle` / `_default` / `_dramatic`,
   `bc_aftermath_off` / `_default` / `_generous` (`bc_game_rules.txt:22-44`); or
2. is the `BC Spike|mod/bc_spike.mod` line from `debug.log`; or
3. is a line **beginning** `BC: ` — one of the mod's own `debug_log` markers. That is the
   ten `BC: fired bc_<event>` lines, `BC: combat end cleanup`, `BC: win notable` /
   `BC: win not notable` / `BC: lose notable` / `BC: lose not notable`,
   `BC: nickname awarded`, `BC: moment minor` / `major` / `decisive`, the three
   `BC: popup ...` lines, and — during stage 1 only — any `BC: DIAG ...` line.

**A group that names a `bc_` key and is none of those three blocks the task.** Row 3 is
narrow on purpose: the marker text is *authored by this mod* and always starts `BC: `,
whereas an engine complaint about a mod file never does. Do not broaden it to "any line
mentioning `bc_`" — that is the whole sweep.

**Most of row 3 will not actually appear, and that is not a symptom.** `probe` compiles its
pattern with Python `re` and passes `re.IGNORECASE` **only** when `-i` is given
(`ck3lib/launch.py:81`), so the sweep pattern `bc_` is case-sensitive and matches a `BC: `
marker only when the marker's *text* also contains a lowercase `bc_`. Of the markers listed
in row 3 that is true of the `BC: fired bc_<event>` family and of nothing else — `BC: combat
end cleanup`, the four grading lines, `BC: nickname awarded`, the three `BC: moment` lines
and the `BC: popup` lines are all invisible to `probe "bc_"`. Row 3 lists them because it is
a *rule about what is allowed through*, and it stays correct if a future marker is renamed
into range. Seeing only the `fired` family means the sweep is working, not that markers are
missing; the marker sweeps are separate commands and each names its own text.

**`probe` patterns are Python regex, not grep regex.** `\t`, `\s`, `\d`, `+`, `?` and bare
`|` all work in a `probe` argument and none of them work in the `grep` calls elsewhere in
these plans, which are POSIX basic regex. Do not carry a pattern from one to the other
without rereading it.

**Never use `ck3.py errors`.** It tail-slices a ~500k-line log and mod script errors
appear near the top, so it cannot see them. `probe` reads end to end and groups by file.

**A game restart costs about seven minutes.** Batch runtime verification. This plan has
exactly two tasks that run the game — **task 2** (force-execute the nickname path) and
**task 15** (the DIAG run) — and that is deliberate. No other task launches it.

### TDD, adapted

The rhythm is preserved, but "write the failing test" means **write the `debug_log`
marker and confirm its absence in the current log** before writing the effect that
emits it. The marker is the assertion. A task is not done until its marker has been
seen, or until `validate --strict` and `conflicts` are clean for the tasks that ship no
marker.

### The mod is its own git repo

`D:/ck3/.gitignore` ignores `mods/`. **Mod commits run from
`D:/ck3/mods/battle_chronicles`**, spec and plan commits run from `D:/ck3`. Every
`git commit` in this plan is a mod commit unless it says otherwise.

### Non-negotiables

- **Zero file collisions.** Every new file is `bc_`-prefixed and additive. No vanilla or
  AGOT file is ever overridden.
- **Never force-kill the running game.**
- **Playset edits need the user's confirmation first.**
- Localization files are **UTF-8 with BOM**, one leading space per line.

---

## File structure

What this plan creates, moves and modifies. Stage 0 does all the moving so stage 1
writes into files that already exist.

| path | plan action | responsibility |
|---|---|---|
| `common/scripted_effects/bc_scripted_effects.txt` | modify (shrinks) | momentum ladder, `bc_clear_faltering_effect`, flattened `bc_cleanup_effect`, chronicle-mark effects, pop-up cooldown |
| `common/scripted_effects/bc_reward_effects.txt` | **create** (task 5) | everything on the reward path: `bc_addressed_toast_effect`, `bc_aftermath_nickname_effect`, `bc_notable_battle_counter_effect`, `bc_battle_memory_effect` |
| `common/scripted_effects/bc_ledger_effects.txt` | **create** (task 7) | `bc_battle_open_effect`, `bc_record_moment_effect` and its two helpers, `bc_clear_scratch_effect`. **Not** `bc_add_verb_effect`, which needs the family-2 modifiers and belongs to plan 2, and **not** the nemesis wipe, which has nothing to wipe until plan 4 |
| `common/scripted_triggers/bc_scripted_triggers.txt` | modify | unchanged except its header — **and task 17**, which rewrites the two ground triggers off bare `terrain =` keys onto AGOT's helpers. No other task opens this file, which is why task 17 can sit at the end of the plan without disturbing anything |
| `events/bc_events.txt` | modify (shrinks) | player-facing pop-ups only |
| `events/bc_aftermath_events.txt` | **create** (task 6) | the two consolidated combat-end graders |
| `events/bc_diag_events.txt` | **create** (task 14) | the DIAG pass. **Deleted at the end of stage 1** — unless Q2 passes, in which case it is renamed to `events/bc_combat_start_events.txt` and kept as plan 5's placeholder (task 16 step 2) |
| `common/on_action/bc_on_actions.txt` | modify | combat-end hooks now name one grader each; `on_combat_start` added |
| `common/combat_phase_events/bc_commander_phase_events.txt` | modify | `bc_battle_open_effect` + seam calls |
| `common/combat_phase_events/bc_knight_phase_events.txt` | modify | `bc_battle_open_effect` + seam calls, both inside `side_commander ?=` |
| `README.md` | modify (tasks 6, 15) | task 6 corrects two passages describing `.0090` as live; task 15 settles **Q4** here, next to the claim it contradicts (`:48-51`, `:158-159`). **Q1/Q2/Q3/Q5 go in the spec instead**, because they gate later plans — the split is task 15 step 7's, and it is two commits in two different repositories |

`bc_rivalry_effects.txt` and `bc_ledger_triggers.txt` are named in the spec's Files
table but hold nothing until plans 3 and 4. **Do not create empty files.**

---

# STAGE 0 — behaviour-neutral restructuring

Nothing in stage 0 changes what the mod does. That is the whole point: if the runtime
checkpoint after stage 1 finds a regression, stage 0 is not a suspect.

**Order inside stage 0 matters twice.** Task 1 (strip old markers) must precede task 14
(add new ones) or the log holds two interleaved generations. Task 2 (force-execute the
nickname path) must precede task 4 (refactor it), because that path has never run at
runtime and refactoring an unverified path makes an old bug indistinguishable from a
new one.

**One task pair is interleaved rather than sequential.** Task 13 adds the `on_combat_start`
hook and task 14 step 1 defines the only event that hook names. Neither is committable
alone — a hook naming a nonexistent event is a dangling reference — so task 13 reaches
forward into task 14 for one step and the two ship in a single commit. That is spelled out
in task 13 and is the only place in this plan where task boundaries do not match commit
boundaries.

---

### Task 1: Strip every stale DIAG marker

The mod carries diagnostics from a previous investigation. They are answered, and they
will pollute the stage-1 log.

**Files:**
- Modify: `mods/battle_chronicles/events/bc_events.txt`
- Modify: `mods/battle_chronicles/common/combat_phase_events/bc_knight_phase_events.txt:103-108`

- [x] **Step 1: Confirm what is there before removing it**

```bash
cd /d/ck3/mods/battle_chronicles
grep -rn "DIAG" --exclude-dir=.git common/ events/
grep -rn "toast body ran" --exclude-dir=.git common/ events/
```

Expected: **15 `DIAG` hits in `events/bc_events.txt`** — 11 `debug_log` lines plus 4
comment lines at `:153`, `:288`, `:293` and `:304` — and one
`"BC: toast body ran (knight breach)"` at
`common/combat_phase_events/bc_knight_phase_events.txt:108`.

The 11-versus-15 distinction matters: the markers to remove are 11, the grep hits are 15,
and the four extras are the comments that introduce them, which go too.

**Scope the grep to `common/` and `events/`.** A bare `grep -rn "DIAG" .` from the mod
root also matches `.git/COMMIT_EDITMSG`, and the toast grep also matches `README.md:159`.
Both are phantom hits that will make the counts look wrong.

If the counts still differ, **stop and re-read the files** — the plan was written against
a known state and a different one means someone else has edited the mod.

- [x] **Step 2: Remove the eleven markers in `bc_events.txt`**

Delete each `debug_log = "BC: DIAG ..."` line **and the comment block that introduces
it**. There are three such blocks. In `bc_chronicles.0090` remove the whole
`# DIAG, temporary.` comment at lines 153-158 and its `debug_log`. In
`bc_chronicles.0091` remove the DIAG comments and logs, and — critically — remove the
three diagnostic `if`/`else_if`/`else` ladders that exist only to report which gate
failed: the counter ladder, the nickname ladder and the martial ladder.

**Keep** these, which are not DIAG:
- `debug_log = "BC: combat end cleanup"`
- `debug_log = "BC: win notable"` / `"BC: win not notable"`
- `debug_log = "BC: lose notable"` / `"BC: lose not notable"`
- `debug_log = "BC: nickname awarded"` in `bc_scripted_effects.txt`

Those four are permanent instrumentation, not diagnostics.

**The `.0090` marker you are deleting asks a question the mod never wrote down an answer
to — answer it here, in the commit message, before it is gone.** Its comment says "Nothing
in the mod has ever proven that `side_commander` still resolves once combat is OVER", and
nothing in `README.md` records a result (grep it: no hit for `side_commander`, `scope
entered` or `DIAG`). The log that would have held the answer has rotated. Removal is
nonetheless safe, and the proof is in vanilla, not in our logs: `combat_event.0001`, which
is dispatched from `on_combat_end_winner`, opens `side_commander = { ... }` **unguarded**
at `events/war_events/combat_events.txt:84`. The scope resolves after combat ends.

This matters well beyond task 1. Task 12's `bc_clear_scratch_effect` and task 14's Q1 both
sit inside `side_commander ?=` in the graders. If that block were never entered, scratch
would never clear — the single most important runtime property in this plan — and Q1 would
return zero rows indistinguishable from "no battles happened".

**Do not remove the `exists = var:bc_notable_battles` guard** in the real nickname
`limit` block. It reads as belt-and-braces next to the ladders, but the ladders are
going and the guard is staying — the file's own comment explains why (CK3 guarantees no
evaluation order among siblings in a `limit`).

- [x] **Step 3: Remove the knight toast probe**

In `bc_knight_phase_events.txt`, delete the comment at `:103-107` and the
`debug_log = "BC: toast body ran (knight breach)"` at `:108`.

**Task 14's Q4 puts a better marker back at this same site.** That is intended. The site
was never the problem — it fires reliably, 14 times in the calibration run — but the
marker alone cannot distinguish an AI subject from a human one, which is why the result it
produced contradicts the mod's own design rule. Removing it here and restoring it there
keeps one generation of markers in the log instead of two.

- [x] **Step 4: Verify nothing else was caught**

```bash
cd /d/ck3/mods/battle_chronicles && grep -rn "DIAG\|toast body ran" --exclude-dir=.git common/ events/
```

Expected: **no output.** `README.md` is deliberately outside the search path — its record
of the earlier toast investigation is history and stays.

- [x] **Step 5: Validate**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
```

Expected: exit 0.

- [x] **Step 6: Commit**

```bash
cd /d/ck3/mods/battle_chronicles
git add events/bc_events.txt common/combat_phase_events/bc_knight_phase_events.txt
git commit -m "chore: strip answered DIAG markers ahead of the expansion"
```

---

### Task 2: Force-execute the nickname path

`bc_aftermath_nickname_effect` has **never run at runtime**. Its gates are
`has_any_nickname = no` + `var:bc_notable_battles >= 3` + `martial >= 14`, and no
observed battle has cleared all three. Task 4 refactors it. Refactoring code that has
never executed means a later failure has two possible causes.

**This task requires a game run and is the one place in stage 0 that does.**

**Files:**
- Modify (temporarily): `mods/battle_chronicles/events/bc_events.txt`

- [x] **Step 1: Temporarily weaken the gate**

In `bc_chronicles.0091`, delete these three rows from the nickname `limit` block, leaving
`has_any_nickname = no` as the only condition:

```
		exists = var:bc_notable_battles
		var:bc_notable_battles >= 3
		martial >= 14
```

**Delete only those three lines. Touch nothing else in the block.** The surrounding
`if`/`limit`/`save_scope_as` structure and — critically — the three rationale comment
blocks interleaved with it (`bc_events.txt:346-351`, `:357-363`, `:366-368`) must survive
untouched. They explain why `exists` is belt-and-braces, why the gate reads `martial` and
not `prowess`, and why the scope is saved. An earlier draft of this task told you to
re-paste the whole block from the plan, which would have silently deleted about fifteen
lines of load-bearing rationale.

**Leave `save_scope_as = bc_named_commander` exactly where it is.** The effect's toast
uses it for `left_icon`, and a scripted effect does not rebind ROOT — ROOT here is the
combat side, which `left_icon` does not accept.

Mark it so it cannot be forgotten:

```
# TEMPORARY — force-execution probe, task 2. REVERT BEFORE TASK 4.
```

- [x] **Step 2: Clear the logs, with the game closed**

Delete `error.log` and `debug.log` from
`D:\Documents\Paradox Interactive\Crusader Kings III\logs`. **`error.log` accumulates
across sessions** — skip this and step 3's sweep reports errors from runs that predate the
change, which is the failure mode the sweep procedure exists to prevent.

- [x] **Step 3: Deploy and run**

```bash
cd /d/ck3/tools && python ck3.py validate --strict && python ck3.py deploy
```

Then launch the game and fight until `BC: nickname awarded` appears.

**Expect to need several notable wins, not one.** Step 1 leaves `has_any_nickname = no`
in the gate, and roughly three in four AGOT commanders already hold a canon nickname —
this plan's own sampling found 3 of 4. A single notable win therefore clears the weakened
gate about a quarter of the time. If several wins produce `BC: win notable` and never
`nickname awarded`, that is the gate doing its job, not a failure: strike
`has_any_nickname = no` from the limit as well, under the same TEMPORARY marker, and fight
one more. Overwriting a canon nickname is harmless here — the save is disposable, and the
step 6 revert restores the mod regardless of what the save holds.

- [x] **Step 4: Confirm the path executed**

```bash
cd /d/ck3/tools && python ck3.py probe "nickname awarded"
```

Expected: **exit 0 with at least one hit.**

Then sweep for errors, using the procedure in "Read this before task 1":

```bash
python ck3.py probe "bc_"
```

Expected: every group satisfies the three-item whitelist in "Read this before task 1" — a
game-rule option key, the launcher's `BC Spike` line, or a `BC: ` marker the mod emitted
itself. A group naming a `bc_` key that is none of those means the nickname path is broken
and must be fixed here, before task 4, which is the entire reason this task exists.

- [x] **Step 5: Confirm the toast was addressed correctly**

Check whether the toast appeared in-game. If the commander who won the name was AI and
no toast appeared on his liege, that is a real bug in the shipped routing — record it
and fix it now.

- [x] **Step 6: Revert with git, not by re-typing**

```bash
cd /d/ck3/mods/battle_chronicles && git checkout -- events/bc_events.txt
```

**Do not hand-restore the deleted rows.** The file is under version control and the
change was never committed, so `git checkout --` restores it exactly, comments and all.
Re-typing is how the rationale blocks get lost.

Note that this discards *any* uncommitted change to `bc_events.txt`. Task 1 commits its
own edits to that same file, so at this point there should be nothing else in flight —
confirm with `git status --short events/bc_events.txt` first if unsure.

- [x] **Step 7: Verify the file is byte-identical to where task 1 left it**

```bash
cd /d/ck3/mods/battle_chronicles
git diff --exit-code events/bc_events.txt
grep -rn "TEMPORARY" --exclude-dir=.git common/ events/
```

Expected: `git diff --exit-code` exits **0** with no output, and the grep prints nothing.
The `--exclude-dir=.git` matters: without it the grep also matches `.git/COMMIT_EDITMSG`
and reports a phantom failure.

- [x] **Step 8: Record the result — there is no commit here**

This task deliberately ends with **no commit**. It made a temporary change and reverted
it, so the tree is unchanged and `git commit` would either be empty or, worse, capture a
botched restore. What this task produces is *knowledge*, and knowledge goes in the README:

Append to `mods/battle_chronicles/README.md` under the runs section, then commit **that**:

```markdown
- **Resolved:** `bc_aftermath_nickname_effect` executes. Forced by temporarily
  reducing the gate to `has_any_nickname = no`; `BC: nickname awarded` appeared,
  the toast was addressed to <who>, and the gate was restored with
  `git checkout --`.
```

```bash
git add README.md
git commit -m "docs: record that the nickname reward path executes

Its three gates had never been cleared by an observed battle, so the path was
unproven before task 4 refactors it. Forced it once with a weakened gate,
confirmed it runs, reverted the gate. No source change."
```

---

### Task 3: Flatten `bc_cleanup_effect`

Six hand-written guarded removals become a flat list. Family 2 adds four more in plan
2, and a ten-branch copy-paste ladder is where a modifier gets forgotten and leaks past
combat end.

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_scripted_effects.txt:101-115`

- [x] **Step 1: Confirm the no-op premise**

`remove_character_modifier` on an absent modifier must be a no-op, or flattening
introduces error spam. Verify against shipped code:

```bash
cd /d/ck3 && sed -n '2318,2335p' "/d/SteamLibrary/steamapps/common/Crusader Kings III/game/common/scripted_effects/00_diarchy_scripted_effects.txt"
```

Expected: an unguarded flat list of 16 `remove_character_modifier` lines, of which at
most 4 can ever be held. That is 12 guaranteed no-ops per call, shipped by Paradox, by
design.

- [x] **Step 2: Replace `bc_cleanup_effect`**

```
# --- cleanup ----------------------------------------------------------------
# Called from the combat-end graders. Without this, momentum earned in one
# battle bleeds into the next 20 days of the war.
#
# FLAT, NOT GUARDED. remove_character_modifier on an absent modifier is a no-op
# — vanilla's own vizierate_remove_extravagance_modifiers_effect
# (00_diarchy_scripted_effects.txt:2318-2335) is an unguarded list of 16 of
# which at most 4 are ever held. Guards here bought nothing and made the list a
# place where a new modifier gets forgotten.
#
# EVERY modifier the mod can apply during a battle must appear here. That is the
# one rule this effect exists to make easy to obey.
bc_cleanup_effect = {
	remove_character_modifier = bc_faltering_minor
	remove_character_modifier = bc_faltering_major
	remove_character_modifier = bc_faltering_decisive
	remove_character_modifier = bc_momentum_minor
	remove_character_modifier = bc_momentum_major
	remove_character_modifier = bc_momentum_decisive
}
```

- [x] **Step 3: Confirm `bc_clear_faltering_effect` was NOT touched**

```bash
cd /d/ck3/mods/battle_chronicles && grep -n "bc_clear_faltering_effect" -A 16 common/scripted_effects/bc_scripted_effects.txt | head -30
```

Expected: still three **guarded** `if` blocks, unchanged.

**This is load-bearing.** `bc_rally_effect` calls `bc_clear_faltering_effect`
*mid-battle* (`bc_scripted_effects.txt:92-95`). If it were flattened to the same
six-line list, every rally would strip the commander's momentum along with his setback.
The two effects look almost identical and must not be merged.

- [x] **Step 4: Confirm `bc_cleanup_effect` no longer calls it**

The old `bc_cleanup_effect` opened with `bc_clear_faltering_effect = yes`. The flat list
covers those three modifiers directly, so that call is now redundant and must be gone.

- [x] **Step 5: Validate and commit**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
cd /d/ck3/mods/battle_chronicles
git add common/scripted_effects/bc_scripted_effects.txt
git commit -m "refactor: flatten bc_cleanup_effect to an unguarded removal list"
```

---

### Task 4: Extract `bc_addressed_toast_effect`

Every award in this expansion needs the same routing: a toast about an AI subject is
raised on his liege instead. That routing exists once, buried in the nickname effect.

**Two independent reasons, and only one of them is in doubt.** The first is *addressing* —
a toast about a courtier knight belongs on his commander, because nobody is playing a
courtier knight and a toast raised on him reaches no one. That reason is not contested and
does not depend on any open question. The second is *reliability* — the belief that a
`send_interface_toast` body does not run at all for a character nobody is playing. **That
one is contradicted by the mod's own README** (`:158-159` versus `:48-51`) and is what
DIAG Q4 in task 14 exists to settle. Extract the routing on the strength of the first
reason. If Q4 comes back "bodies do run", this task does not get reverted — only its
comment gets corrected.

**Extract the routing, not the toast.** The routing is the `is_ai = no` /
`else_if exists = liege` fork at the end of `bc_aftermath_nickname_effect`.
`bc_aftermath_nickname_toast_effect` is only the body it calls twice, and it is **not**
reusable as-is because its `left_icon` is hardcoded to `scope:bc_named_commander`.

**Find both by name, not by line.** Task 3 rewrites `bc_cleanup_effect` earlier in the same
file, which shifts everything below it; any line number quoted here would already be off by
one by the time this task runs.

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_scripted_effects.txt` —
  the `bc_aftermath_nickname_effect` / `bc_aftermath_nickname_toast_effect` region

- [x] **Step 1: Write the new shared effect**

```
# --- addressed toasts -------------------------------------------------------
#
# A toast is ADDRESSED, not broadcast. Nearly every commander and every knight in
# the world is AI, and a toast raised on a man nobody is playing reaches nobody —
# so a toast ABOUT an AI subject is raised on somebody who might be human.
#
# Whether the toast BODY additionally fails to execute for an AI character is a
# separate and currently OPEN question - README.md:158-159 says it executes,
# README.md:48-51 says it does not. DIAG Q4 settles it. This effect is correct
# either way; only the strength of the "keep state out of toasts" rule depends on
# the answer.
#
# CALLED ON THE SUBJECT. Tests is_ai on THIS, raises on THIS or on `liege`.
#
# SUBJECT must be a SAVED SCOPE, never `this`. A scripted effect does not rebind
# ROOT, and in the liege arm the scope has already moved by the time left_icon is
# evaluated — so left_icon = $SUBJECT$ only names the right man if the caller
# saved him first.
#
# TYPE IS A PARAMETER AND IT IS REQUIRED. Not everything routed through here is
# good news: plan 4 announces the man who has beaten you twice and plan 5
# announces your dead knights. Hardcoding event_toast_effect_good would put a
# green tick on both. Callers pass event_toast_effect_good or
# event_toast_effect_bad - the mod already uses both (bc_banner_falls uses _bad).
#
# THERE IS NO DEFAULT. CK3 substitutes parameters textually and does not error on
# a missing one, so an omitted TYPE would emit the literal text `type = $TYPE$`
# and validate would pass it. Every call site names the type explicitly; the
# caller sweep in task 5 step 3 is what enforces it.
bc_addressed_toast_effect = {
	if = {
		limit = { is_ai = no }
		send_interface_toast = {
			type = $TYPE$
			title = $TITLE$
			desc = $DESC$
			left_icon = $SUBJECT$
		}
	}
	else_if = {
		limit = { exists = liege }
		liege = {
			send_interface_toast = {
				type = $TYPE$
				title = $TITLE$
				desc = $DESC$
				left_icon = $SUBJECT$
			}
		}
	}
}
```

- [x] **Step 2: Rewrite `bc_aftermath_nickname_effect` to call it**

Replace its routing fork (`:288-297`) with:

```
	bc_addressed_toast_effect = {
		TYPE = event_toast_effect_good
		TITLE = bc_aftermath_nickname_toast
		DESC = bc_aftermath_nickname_toast_desc
		SUBJECT = scope:bc_named_commander
	}
```

**`TYPE` first, and spelled out.** The old `bc_aftermath_nickname_toast_effect` hardcoded
`event_toast_effect_good`; winning a name is good news and the value is unchanged. It is
passed rather than defaulted because plans 4 and 5 pass `event_toast_effect_bad` through the
same effect.

Leave the `random_list` of 27 nicknames and the `debug_log = "BC: nickname awarded"`
exactly as they are.

- [x] **Step 3: Delete `bc_aftermath_nickname_toast_effect`**

It now has no callers.

- [x] **Step 4: Verify it has no callers**

```bash
cd /d/ck3/mods/battle_chronicles && grep -rn "bc_aftermath_nickname_toast_effect" --exclude-dir=.git .
```

Expected: **no output.** (The loc keys `bc_aftermath_nickname_toast` and
`..._desc` survive — they are keys, not the effect.)

**`--exclude-dir=.git`, for the reason task 1 gives.** A `grep -rn ... .` from the mod root
searches `.git/COMMIT_EDITMSG` and the packed objects too, and this expansion writes long
commit messages that name the symbols they change. Step 5's message happens not to contain
this one, so the flag changes nothing *today* — but "expected: no output" is a check whose
value is that it stays runnable later, and a bare form is one commit away from a false
failure. Today the bare form returns three lines in
`common/scripted_effects/bc_scripted_effects.txt` — two calls and the definition.

- [x] **Step 5: Validate and commit**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
cd /d/ck3/mods/battle_chronicles
git add common/scripted_effects/bc_scripted_effects.txt
git commit -m "refactor: extract bc_addressed_toast_effect from the nickname path

Four systems in the expansion need the same AI-subject-routes-to-liege rule.
Extracted the routing fork, not the toast body — the body's left_icon was
hardcoded. SUBJECT is a saved scope because a scripted effect does not rebind
ROOT and the liege arm has already changed scope."
```

---

### Task 5: Split the reward effects into their own file

`bc_scripted_effects.txt` holds two unrelated concerns: the momentum machinery that runs
*during* a battle, and the reward machinery that runs *after* one. They have different
lifecycles and the reward half is the half that grows under B, C and D.

**Files:**
- Create: `mods/battle_chronicles/common/scripted_effects/bc_reward_effects.txt`
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_scripted_effects.txt`

- [x] **Step 1: Create the new file with a header**

```
# Battle Chronicles - the reward path.
#
# Everything here runs at COMBAT END, from the two combat-end graders - which task 6
# gathers into bc_aftermath_events.txt, one task after this one. The one exception is
# bc_addressed_toast_effect: it is generic routing, and later plans call it from
# mid-battle contexts too.
#
# Nothing else here runs during a battle. That is the split from
# bc_scripted_effects.txt, which is the opposite: momentum, cooldowns and
# chronicle pacing, all of which run mid-battle and none of which persists.
#
# ROOT in every caller is a COMBAT SIDE, not a character. Effects here that need
# to name a character in a toast take it as a saved scope.
```

- [x] **Step 2: Move four effects across, verbatim**

Cut from `bc_scripted_effects.txt` and paste into `bc_reward_effects.txt`, **with their
comment blocks intact** — the comments carry the reasoning for `random_memory` over
`scope:new_memory`, for `give_nickname` over `set_nickname_effect`, and for the AGOT
nickname dependency, none of which is re-derivable:

1. `bc_battle_memory_effect`
2. `bc_notable_battle_counter_effect`
3. `bc_aftermath_nickname_effect`
4. `bc_addressed_toast_effect` (from task 4)

- [x] **Step 3: Confirm nothing was lost or duplicated**

```bash
cd /d/ck3/mods/battle_chronicles
for e in bc_battle_memory_effect bc_notable_battle_counter_effect bc_aftermath_nickname_effect bc_addressed_toast_effect; do
  echo "$e: $(grep -rc "^$e = {" common/scripted_effects/ | grep -v ':0' )"
done
```

Expected: each defined **exactly once**, all four in `bc_reward_effects.txt`.

A duplicate definition is silent in CK3 — one wins and nothing is logged — so this check
is not optional.

**Then sweep the `bc_addressed_toast_effect` callers for a missing `TYPE`:**

```bash
cd /d/ck3/mods/battle_chronicles
grep -c "bc_addressed_toast_effect = {" common/ -r
grep -rc "TYPE = event_toast_effect_" common/scripted_effects/ | grep -v ':0'
```

**The first number must be exactly one MORE than the second, not equal to it.** The pattern
`bc_addressed_toast_effect = {` matches the effect's own definition line as well as every
call site, and a definition does not pass a `TYPE` to itself. As of plan 1 the numbers are
**2** and **1** — the definition plus the nickname caller, and one `TYPE`. Plans 3, 4 and 5
each add call sites and each must preserve the gap of exactly one.

Equal, or a gap of two or more, both mean a caller is missing its `TYPE`.

**This check exists because nothing else can catch it.** An omitted parameter is not an
error in CK3 — the literal text `type = $TYPE$` reaches the toast, `validate` sees balanced
braces and passes, and the toast renders with no styling or fails silently at runtime. This
is the same class of failure as `$TIER$ = decisive`.

- [x] **Step 4: Validate, check collisions, commit**

```bash
cd /d/ck3/tools && python ck3.py validate --strict && python ck3.py index && python ck3.py conflicts
```

Expected: all exit 0. `conflicts` is run here rather than after every task because this
is the first task that adds a file.

```bash
cd /d/ck3/mods/battle_chronicles
git add common/scripted_effects/
git commit -m "refactor: split the reward path into bc_reward_effects.txt

Mid-battle machinery and combat-end machinery have different lifecycles, and the
combat-end half is the half that grows under the expansion."
```

---

### Task 6: Consolidate three combat-end events into two

`bc_chronicles.0090` (cleanup, both hooks), `.0091` (winner) and `.0092` (loser) become
one grader per hook.

**The reason is ordering, not efficiency.** `.0090` carries no `trigger` while
`.0091`/`.0092` do; all three fire from the same hooks; and the order between separate
events on one hook is undefined. Grading reads scratch variables that **scratch clearing**
will remove, so grading must provably run before the clearing. Separate events cannot
express that. One event per hook can, in written order.

**Be precise about which of the two "clears" this is about — they are different things
and only one of them constrains grading.** `bc_cleanup_effect` strips momentum
*modifiers*; `bc_clear_scratch_effect` (task 12) removes scratch *variables*. Grading
reads variables and no modifier, so cleanup is free to run first and does. The order is
cleanup → grading → scratch clearing, exactly as the file header states. Do not
"correct" the code to put grading first.

**Files:**
- Create: `mods/battle_chronicles/events/bc_aftermath_events.txt`
- Modify: `mods/battle_chronicles/events/bc_events.txt` (remove `.0090`, `.0091`, `.0092`)
- Modify: `mods/battle_chronicles/common/on_action/bc_on_actions.txt`
- Modify: `mods/battle_chronicles/README.md` (two passages describe `.0090` as live)

**Carry the rationale comments across — the code below is not the whole file.** The three
events being replaced carry substantial comment blocks explaining decisions that are still
live: why the grade runs in `immediate` rather than in the trigger, why the loser event
does not touch `bc_notable_battles`, and the belt-and-braces `exists` note above the
nickname gate. All three sit in the header comment of `bc_chronicles.0092` or in the body
of `.0091` — **find them by that text, not by line number**, because task 1 deletes the
DIAG ladders from this same file and shifts everything below them. Those survive the
consolidation. The listing below shows structure and the comments that are new or changed;
it is not a licence to drop everything it omits. Diff the old and new files before
committing and account for every removed comment line.

- [x] **Step 1: Create `bc_aftermath_events.txt`**

```
namespace = bc_chronicles

# Battle Chronicles - the combat-end graders.
#
# TWO events, one per hook. Not one: nothing in an event body can tell which of
# on_combat_end_winner / on_combat_end_loser invoked it. is_combat_side_pursuing
# is documented as "is this side the winner", but every use of it in vanilla and
# AGOT is DURING combat inside is_army_in_combat = yes, and its value at combat
# end is unproven. Two events makes the outcome structural instead of inferred.
#
# NEITHER CARRIES A `trigger`. The old cleanup event these two replace had none
# either, deliberately: it was the only caller of bc_cleanup_effect, and putting
# momentum stripping behind the aftermath off switch would leave `advantage +-10`
# modifiers bleeding twenty days into the next battle for any player who touched
# that setting. The game rule therefore lives on an INNER `if` around the grading
# branch only.
#
# BODY ORDER IS LOAD-BEARING and is part of the design:
#   1. cleanup, OUTSIDE the gate
#   2. grading, INSIDE the gate
#   3. scratch clearing, OUTSIDE the gate, and LAST
# Step 3 must follow step 2 because grading reads scratch. Writing the two-column
# split the natural way — all ungated work together — is exactly wrong.
#
# Scratch clearing arrives in task 12. Until then step 3 is absent, which is
# correct: there is no scratch yet.

# ---------------------------------------------------------------------------
# Winning side.
# ---------------------------------------------------------------------------
bc_chronicles.0091 = {
	hidden = yes
	scope = combat_side

	immediate = {
		debug_log = "BC: combat end cleanup"
		side_commander ?= {
			bc_cleanup_effect = yes
		}
		every_side_knight = {
			bc_cleanup_effect = yes
		}

		if = {
			limit = { NOT = { has_game_rule = bc_aftermath_off } }

			if = {
				limit = { bc_battle_is_notable_trigger = yes }
				debug_log = "BC: win notable"

				combat.location ?= {
					save_scope_as = bc_battle_province
				}

				if = {
					limit = { exists = scope:bc_battle_province }
					every_side_knight = {
						limit = {
							is_alive = yes
							trigger_if = {
								limit = { exists = root.side_commander }
								NOT = { this = root.side_commander }
							}
						}
						bc_battle_memory_effect = { TYPE = bc_battle_memory_won }
					}
				}

				side_commander ?= {
					if = {
						limit = { is_alive = yes }
						bc_notable_battle_counter_effect = yes

						if = {
							limit = {
								has_any_nickname = no
								exists = var:bc_notable_battles
								var:bc_notable_battles >= 3
								martial >= 14
							}
							save_scope_as = bc_named_commander
							bc_aftermath_nickname_effect = yes
						}
					}
				}
			}
			else = {
				debug_log = "BC: win not notable"
			}
		}
	}
}

# ---------------------------------------------------------------------------
# Losing side.
#
# Everything above except the two winner-only items: the cumulative notable-win
# counter and the nickname. The two events are NOT mirror images — the counter is
# wins only, deliberately.
# ---------------------------------------------------------------------------
bc_chronicles.0092 = {
	hidden = yes
	scope = combat_side

	immediate = {
		debug_log = "BC: combat end cleanup"
		side_commander ?= {
			bc_cleanup_effect = yes
		}
		every_side_knight = {
			bc_cleanup_effect = yes
		}

		if = {
			limit = { NOT = { has_game_rule = bc_aftermath_off } }

			if = {
				limit = { bc_battle_is_notable_trigger = yes }
				debug_log = "BC: lose notable"

				combat.location ?= {
					save_scope_as = bc_battle_province
				}

				if = {
					limit = { exists = scope:bc_battle_province }
					every_side_knight = {
						limit = {
							is_alive = yes
							trigger_if = {
								limit = { exists = root.side_commander }
								NOT = { this = root.side_commander }
							}
						}
						bc_battle_memory_effect = { TYPE = bc_battle_memory_lost }
					}
				}
			}
			else = {
				debug_log = "BC: lose not notable"
			}
		}
	}
}
```

Two details carried across from the originals that look like noise and are not:

- **`trigger_if`, not a bare `NOT = { this = root.side_commander }`.** A side can be
  leaderless. A bare comparison against a missing scope is an error-log line for every
  knight of every leaderless battle.
- **The province check is an enclosing `if`, not part of the knight `limit`.** It is a
  property of the battle; re-asking it once per knight is noise.

- [x] **Step 2: Delete `.0090`, `.0091` and `.0092` from `bc_events.txt`**

`bc_events.txt` keeps only `bc_chronicles.0001`, `.0002` and `.0003` — the three
player-facing pop-ups. Update its header comment: it currently describes a file holding
both pop-ups and hidden graders, and it now holds only pop-ups.

- [x] **Step 3: Rewrite the on_action hooks**

```
on_combat_end_winner = {
	events = {
		bc_chronicles.0091
	}
}

on_combat_end_loser = {
	events = {
		bc_chronicles.0092
	}
}
```

**Leave the file's header comment intact.** It records that an `effect = { }` in an
`on_action` does not merge across files, that the engine keeps exactly one chosen by
alphabetical filename, and that this bug ate a whole probe run. That warning is why this
file uses `events = { }`, and it applies again in task 13.

- [x] **Step 4: Update the two README passages that describe `.0090`**

`.0090` ceases to exist, and `README.md` documents it twice as live behaviour. Both are
load-bearing prose, not incidental mentions.

`README.md:41-42` currently reads:

```markdown
- **Momentum never outlives its battle.** `bc_chronicles.0090` strips it at
  combat end.
```

Replace with:

```markdown
- **Momentum never outlives its battle.** The combat-end graders
  `bc_chronicles.0091` and `.0092` strip it, before anything reads the scratch
  variables it was earned alongside.
```

`README.md:121-125` currently opens "Two events rather than one because
`bc_chronicles.0090` fires from both hooks and nothing in its body can tell which called
it." That sentence explains a *three*-event design that no longer exists. Rewrite the
paragraph so the reason survives the consolidation — the reason is still true, it is just
now the reason there is no shared event at all:

```markdown
One event per hook, not one shared event, because nothing in a combat-end event's
body can tell which hook invoked it. `is_combat_side_pursuing` is documented as
"is this side the winner", but every script use of it in vanilla and AGOT is
*during* combat; its value at combat end is unproven. A hook apiece makes the
outcome structural instead of inferred, and it is also what lets cleanup, grading
and scratch clearing run in a written, provable order within each one.
```

- [x] **Step 5: Confirm `.0090` is gone everywhere**

```bash
cd /d/ck3/mods/battle_chronicles && grep -rn "0090" --exclude-dir=.git common/ events/ README.md
```

Expected: **no output.** A dangling reference in an `events = { }` list is a runtime
error, not a validation error.

`--exclude-dir=.git` and an explicit path list, per this plan's own convention — a bare
`.` matches the git object store and every deployed copy.

**No `grep -v "#"` filter here, and that is deliberate.** Everywhere else in this plan a
verification grep whose pattern could appear in shipped comment text is filtered. Here the
opposite choice is made: nothing this task ships is allowed to name the old id at all, so
an unfiltered grep is both a stricter check and a simpler one. That is why step 1's header
comment says "the old cleanup event these two replace" rather than naming `.0090`, and why
step 4's two README replacements name only `.0091` and `.0092`. If you paste a comment
that mentions the old id, this step will fail — correctly. Reword the comment; do not add
a filter.

- [x] **Step 6: Validate, index, conflicts**

```bash
cd /d/ck3/tools && python ck3.py validate --strict && python ck3.py index && python ck3.py conflicts
```

Expected: all exit 0.

- [x] **Step 7: Commit**

```bash
cd /d/ck3/mods/battle_chronicles
git add events/ common/on_action/bc_on_actions.txt README.md
git commit -m "refactor: consolidate the three combat-end events into two graders

Not for efficiency — the graders still iterate every_side_knight twice. The order
between separate events on one hook is undefined, and grading must provably run
before scratch clearing removes the variables it reads. One event per hook
expresses that in written order; two could not. The game rule moves to an inner if
so that momentum stripping does not end up behind the aftermath off switch."
```

---

# STAGE 1 — the seam

Stage 1 ships **no new player-visible behaviour**, with one deliberate exception noted
in task 11. That is the point: the seam is proven by log before anything is built on it.

---

### Task 7: `bc_battle_open_effect`

Two scratch variables need a combat scope to write, and the seam cannot write them —
eight of the eighteen moment call sites are pop-up options, and those character events
hold no combat scope at all. So opening the battle is a second, separate effect, called
from the phase event where `scope:combat_side` does exist.

**Files:**
- Create: `mods/battle_chronicles/common/scripted_effects/bc_ledger_effects.txt`

- [x] **Step 1: Create the file with its header**

```
# Battle Chronicles - the ledger.
#
# ONE SEAM. Every moment in the mod — phase event or pop-up option — reports
# itself through bc_record_moment_effect and nothing else writes moment state.
# That is the only place the "state never lives inside a toast" rule has to be
# enforced, the only place the variable leak surface has to be audited, and the
# only place a future system has to hook.
#
# ALL WRITES LAND ON THE SIDE COMMANDER. The three `type = knight` events root on
# the knight, so they call in from inside scope:combat_side.side_commander ?= .
# NOTHING IN THIS MOD EVER WRITES A bc_ VARIABLE ONTO A KNIGHT. Per-character
# state on every participant has to be cleared on both sides or it leaks forever,
# and there are far more knights than commanders.
#
# THREE TIERS OF STATE:
#   momentum  character modifier  20 days, wiped at combat end
#   scratch   character variable  this battle only, cleared at combat end
#   ledger    character variable  forever
# Momentum must stay a modifier — it is what the engine reads for advantage.
# Scratch and ledger must be variables — bc_cleanup_effect strips every modifier
# at combat end, so anything modifier-shaped cannot persist by construction.
#
# CLEARING MEANS remove_variable, NEVER set_variable value = 0. Three scratch
# variables cannot hold zero, and absence-versus-zero is load-bearing: it is how
# the seam detects the first moment of a battle and which arm of the pacing floor
# fires.
```

- [x] **Step 2: Write `bc_battle_open_effect`**

```
# --- opening the battle -----------------------------------------------------
#
# Called at the TOP of every commander and knight phase event's `effect` block,
# before bc_mark_chronicle_effect and before any trigger_event, where
# scope:combat_side always exists.
#
# UNCONDITIONAL, NOT WRITE-IF-UNSET. An earlier design skipped when the variables
# were already set. That was wrong for a reason outside this effect: scratch is
# cleared at combat end on `side_commander`, so a commander REPLACED mid-combat is
# never cleared — and under write-if-unset his stale values would freeze
# PERMANENTLY, not for one battle. A stale bc_battle_size of 3 would let a
# two-hundred-man skirmish maim people once family 3 ships.
#
# Overwriting is also MORE correct on the foe: capturing the current enemy
# commander at every phase event tracks a mid-battle replacement on the other
# side, which capture-once does not.
#
# CALL THIS AT MOST ONCE PER EVENT EXECUTION. The `?=` below leaves
# scope:bc_open_foe untouched when it fails rather than clearing it, so a second
# call in the same execution whose `?=` failed would find the FIRST call's scope
# still standing, pass the `exists` test, and write the wrong foe. No call site in
# plan 1 calls it twice — all ten call it once, at the top of an `effect` block —
# but plan 4 adds code to this same effect, so the constraint is written down
# rather than left to be rediscovered.
bc_battle_open_effect = {
	scope:combat_side.enemy_side.side_commander ?= {
		save_scope_as = bc_open_foe
	}
	if = {
		limit = { exists = scope:bc_open_foe }
		set_variable = {
			name = bc_battle_foe
			value = scope:bc_open_foe
		}
	}
	else = {
		# Self-contained: without this, a leaderless enemy side leaves the
		# PREVIOUS battle's foe in place. bc_clear_scratch_effect (task 12)
		# happens to cover this today, but that is a different effect in a
		# different task, and this one should not depend on it.
		remove_variable = bc_battle_foe
	}

	# A BUCKET, 1/2/3 — never a raw troop count.
	#
	# num_total_troops is a TRIGGER ONLY: triggers.log:9537-9540 gives it
	# comparison traits and scope `combat`, it appears in no value log, and all
	# four of its uses in the playset are left-hand trigger comparisons. There is
	# no way to read it into a set_variable value =. An earlier design wrote
	# `value = scope:combat_side.combat.num_total_troops`, which would simply not
	# have worked, and every size gate in the expansion rested on that one write.
	#
	# NOT side_strength, which IS readable and is therefore the trap:
	# bc_script_values.txt:15-16 records that the engine scales it down by 1000, so
	# reaching for it would make every battle read as "under 2,000".
	#
	# 10,000 is bc_battle_is_notable_trigger's own lower size row
	# (bc_scripted_triggers.txt:153). 2,000 is INVENTED — the calibration run
	# recorded `under 5k` as one undivided bucket and never subdivided it. DIAG Q3
	# measures it.
	if = {
		limit = { scope:combat_side.combat = { num_total_troops >= 10000 } }
		set_variable = { name = bc_battle_size value = 3 }
	}
	else_if = {
		limit = { scope:combat_side.combat = { num_total_troops >= 2000 } }
		set_variable = { name = bc_battle_size value = 2 }
	}
	else = {
		set_variable = { name = bc_battle_size value = 1 }
	}
}
```

**The nemesis-wipe housekeeping is NOT in this plan.** An earlier draft put a guarded
`remove_variable = bc_nemesis` at the top of this effect, on the grounds that this is the
one effect context guaranteed to run at every phase event while both of C's read sites
are pure trigger contexts. That reasoning still holds — but **nothing in plan 1 ever
writes `bc_nemesis`**, so the block would be untestable dead code shipped a plan early,
and the runtime checkpoint in task 15 could not falsify it. It belongs in plan 4, added
to this effect, and plan 4 must nest the two guard rows rather than making them siblings
in one `limit` for the same non-short-circuiting reason as `bc_write_style_effect`.

**Note the `save_scope_as` indirection — and note that it is a guard, not a necessity.**
`set_variable value =` *can* take a multi-link scope path directly. Vanilla does exactly
that, through these same two links, at `combat_on_actions.txt:39-44`:

```
set_variable = {
	name = cid_title_to_give
	value = prev.enemy_side.side_commander.primary_title
}
```

Both links are real: `event_targets.log:1409-1411` gives `enemy_side` (`combat_side` →
`combat_side`) and `:1415-1417` gives `side_commander` (`combat_side` → `character`). So
`value = scope:combat_side.enemy_side.side_commander` would work — **on a side that has a
commander.** The indirection buys the leaderless case: `?=` absorbs the failed link, and
the `exists` test then turns "no commander" into a branch instead of a broken read. Keep
it for that reason, not because the direct form is impossible.

**On `?=` for the foe:** a side can be leaderless. `bc_battle_foe` is then cleared rather
than left stale, and C never arms for that battle, which is correct.

- [x] **Step 3: Validate**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
```

Expected: exit 0. The effect has no callers yet, which is fine and intentional — task 9
wires it.

- [x] **Step 4: Check for collisions — this task creates a new filename**

```bash
cd /d/ck3/tools && python ck3.py index && python ck3.py conflicts
```

Expected: exit 0 for both. **This step is not optional here even though most tasks skip
it.** A new file in `common/scripted_effects/` is precisely when a collision can appear,
and `conflicts` reads a sqlite index that only `index` rebuilds — running `conflicts`
against yesterday's index would pass vacuously and prove nothing. `index` takes about two
minutes. Task 5 already does this, for the same reason, and task 6 does it again. **Tasks
5, 6 and 7 each create a permanent new filename and each run it.** Task 14's
`bc_diag_events.txt` is the one exception — it is temporary and is covered by task 16's
full sweep, which runs `index` and `conflicts` after it is deleted or renamed.

- [x] **Step 5: Commit**

```bash
cd /d/ck3/mods/battle_chronicles
git add common/scripted_effects/bc_ledger_effects.txt
git commit -m "feat: add bc_battle_open_effect, the battle-scoped scratch writer

bc_battle_size is a 1/2/3 bucket set by a trigger ladder, not a troop count:
num_total_troops is trigger-only and cannot be read into a variable. Unconditional
on every call, because scratch is only cleared on the man commanding at the end,
so write-if-unset would freeze a replaced commander's values permanently."
```

---

### Task 8: `bc_record_moment_effect` — the seam

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_ledger_effects.txt`

- [x] **Step 1: Write the marker first — this is the assertion**

The seam's correctness is proven by one log line per moment carrying the tier it
actually resolved to. Confirm the marker does not exist yet:

```bash
cd /d/ck3/tools && python ck3.py probe "BC: moment"
```

Expected: **exit 1** (no match). This is the failing test.

- [x] **Step 2: Write the seam**

```
# --- the seam ---------------------------------------------------------------
#
# bc_record_moment_effect = { TIER = minor|major|decisive  KIND = <kind>  SWING = up|down }
#
# TIER as passed is the REQUESTED tier. The escalation ladder below is a CEILING
# and can only lower it — a site asking for `minor` on the tenth moment still gets
# `minor`. That is why exactly two call sites request `decisive`: a ceiling cannot
# manufacture a tier nobody asks for.
#
# SWING exists because polarity is real in the shipped events and neither of the
# other two parameters carries it. bc_horse_killed_under_him and
# bc_van_breaks_through are both KIND `bloodied`, and one falters while the other
# gains. The wound gate in plan 6 is written against SWING = down.
#
# NO COMBAT SCOPE IS TOUCHED HERE. Eight of the eighteen call sites are pop-up
# options, and bc_events.txt records as an invariant that those character events
# hold no combat scope at all. Everything combat-scoped lives in
# bc_battle_open_effect instead.
bc_record_moment_effect = {
	if = {
		limit = { NOT = { exists = var:bc_battle_moments } }
		set_variable = { name = bc_battle_moments value = 1 }
	}
	else = {
		change_variable = { name = bc_battle_moments add = 1 }
	}

	bc_record_effective_tier_effect = { TIER = $TIER$ KIND = $KIND$ }
}
```

**The create-or-increment shape is not optional.** `change_variable` on a variable that
was never set is not safe — this is vanilla's own shape, from `combat_events.txt:90-107`,
and the mod already follows it in `bc_notable_battle_counter_effect`.

- [x] **Step 3: Write the ceiling and the style high-water mark**

```
# The ceiling, then the style write. Split out of the seam only because the
# ceiling has to resolve BEFORE the style comparison can use it — the style is
# keyed on EFFECTIVE tier, not requested.
#
# The ceiling is read AFTER bc_battle_moments is incremented, so the first moment
# of a battle sees 1, not 0, and there is no zero case.
#
#   moments 1-2  ->  minor
#   moments 3-4  ->  major
#   moments 5+   ->  decisive
#
# THE COMPARISON IS `flag:$TIER$ = flag:decisive`, NOT `$TIER$ = decisive`. A bare
# `$TIER$ = decisive` substitutes textually to `decisive = decisive`, and `decisive`
# is not a script value, trigger or scope anywhere in vanilla, AGOT or the playset —
# it is an unknown key, which is a silent no-op, not a validation failure. Wrapping
# both sides in `flag:` is the shipped idiom for comparing a parameter against a
# literal: vanilla 00_animal_effects.txt:1659 (`flag:$BONUS$ = flag:court_physician`)
# and :1778-1793 (`flag:$METHOD$ = flag:gift` and two siblings), AGOT
# 00_agot_character_data_effects.txt:1427-1463. Call sites are unaffected — they
# still pass TIER = decisive.
bc_record_effective_tier_effect = {
	if = {
		limit = {
			flag:$TIER$ = flag:decisive
			var:bc_battle_moments >= 5
		}
		bc_write_style_effect = { RANK = 3 KIND = $KIND$ }
		debug_log = "BC: moment decisive"
	}
	else_if = {
		limit = {
			OR = {
				flag:$TIER$ = flag:decisive
				flag:$TIER$ = flag:major
			}
			var:bc_battle_moments >= 3
		}
		bc_write_style_effect = { RANK = 2 KIND = $KIND$ }
		debug_log = "BC: moment major"
	}
	else = {
		bc_write_style_effect = { RANK = 1 KIND = $KIND$ }
		debug_log = "BC: moment minor"
	}
}

# bc_battle_style holds the KIND of the HIGHEST-TIER moment of the battle, ties
# broken by the LAST such moment. Not last-wins: a decisive stand on day five
# should name the battle even if a minor scuffle followed it.
#
# `>=` rather than `>` is exactly what makes ties break to the last moment. Do not
# "tidy" it to `>`.
#
# This needs a high-water mark, which is what bc_battle_tier is for. It cannot be
# derived from bc_battle_moments, because a call site may request `minor` at any
# rung of the ladder.
#
# THE ABSENCE CASE IS A SEPARATE BRANCH, NOT AN `OR` ROW. Writing it as
# `OR = { NOT = { exists = var:bc_battle_tier }  var:bc_battle_tier <= $RANK$ }`
# looks equivalent and is not: CK3 does not short-circuit, so on the first moment of
# every battle — when the variable does not exist yet — the second row still
# evaluates and logs a read of a missing variable, once per moment, forever. The
# mod already states this rule in its own source, in the imperative — see the
# comment above the nickname gate in `bc_chronicles.0091`: "Do not rely on
# evaluation order to make it safe - CK3 guarantees no order of evaluation among
# siblings, in a limit or anywhere else."
# The nested shape below is the same one `bc_notable_battle_counter_effect` uses.
#
# CITE BY SYMBOL, NOT BY LINE, in anything this plan SHIPS. Task 6 moves
# bc_chronicles.0091 out of bc_events.txt into bc_aftermath_events.txt and task 1
# shrinks both files, so a line citation baked into shipped source is wrong the
# moment the plan finishes and stays wrong forever. Line citations are fine in the
# plan's own prose, which is read once against the tree as it stands.
bc_write_style_effect = {
	if = {
		limit = { NOT = { exists = var:bc_battle_tier } }
		set_variable = { name = bc_battle_tier value = $RANK$ }
		set_variable = { name = bc_battle_style value = flag:$KIND$ }
	}
	else_if = {
		limit = { var:bc_battle_tier <= $RANK$ }
		set_variable = { name = bc_battle_tier value = $RANK$ }
		set_variable = { name = bc_battle_style value = flag:$KIND$ }
	}
}
```

**The two branches are byte-identical in body, and that is correct — do not "factor out"
the duplication.** The only thing that differs is the guard, and there is no way to write
one guard that covers both without reintroducing the non-short-circuiting read above. Two
duplicated lines is the price of not logging an error every moment of every battle.

- [x] **Step 4: Validate**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
```

Expected: exit 0.

**Do not read this as confirmation that the tier comparison works.** `validate` is
syntax-only and has no knowledge of trigger keys, so it would have passed the broken
`$TIER$ = decisive` form just as happily. The comparison form is settled by the vanilla
precedent cited in the code comment above, not by this command, and it is proven at
runtime in task 15 by all three of `BC: moment minor` / `major` / `decisive` appearing
in the log. If only `BC: moment minor` ever appears, the comparison is silently failing
and both upper arms are dead.

- [x] **Step 5: Commit**

```bash
cd /d/ck3/mods/battle_chronicles
git add common/scripted_effects/bc_ledger_effects.txt
git commit -m "feat: add bc_record_moment_effect, the one seam

Every moment reports tier, kind and swing through one effect. The escalation
ladder is a ceiling that only lowers the requested tier, and the style high-water
mark breaks ties to the last moment with >= rather than >."
```

---

### Task 9: Wire the commander phase events

Seven events. Each gains `bc_battle_open_effect` at the top of its `effect` block and one
or more seam calls.

**Files:**
- Modify: `mods/battle_chronicles/common/combat_phase_events/bc_commander_phase_events.txt`

- [x] **Step 1: Add `bc_battle_open_effect` to all seven**

In every one of the seven `effect` blocks, immediately after `save_scope_as = bc_commander`
and **before** `bc_mark_chronicle_effect`:

```
		bc_battle_open_effect = yes
```

The seven events are `bc_banner_falls`, `bc_rally_the_line`, `bc_horse_killed_under_him`,
`bc_flank_collapses`, `bc_van_breaks_through`, `bc_ground_favours_us`,
`bc_lines_bogged_down`.

**Before `bc_mark_chronicle_effect`, and before any `trigger_event`.** The ordering
matters for the pop-up branches: `bc_banner_falls` marks the chronicle and then
`trigger_event = bc_chronicles.0001`, so the seam is reached only from the option — and
by then `bc_battle_size` must already be written, because the option has no combat scope
to write it from.

- [x] **Step 2: Add seam calls to the four events with no pop-up branch**

| event | call |
|---|---|
| `bc_horse_killed_under_him` | `bc_record_moment_effect = { TIER = minor KIND = bloodied SWING = down }` |
| `bc_flank_collapses` | `bc_record_moment_effect = { TIER = decisive KIND = wild SWING = down }` |
| `bc_ground_favours_us` | `bc_record_moment_effect = { TIER = minor KIND = adapted SWING = up }` |
| `bc_lines_bogged_down` | `bc_record_moment_effect = { TIER = minor KIND = adapted SWING = down }` |

Place each **immediately after** the existing momentum call
(`bc_faltering_minor_effect = yes` and friends) and **before** the `send_interface_toast`.
State first, presentation second — the file's own header states this rule and explains
that the entire momentum system once lived inside toast blocks and reached almost nobody.

- [x] **Step 3: Add seam calls to the three events with a pop-up branch**

These fire the seam **only in the `else` branch**, the toast branch. The pop-up branch's
seam call lives in the option (task 10), because in that branch the option *is* the
outcome.

| event | `else` branch call |
|---|---|
| `bc_banner_falls` | `bc_record_moment_effect = { TIER = major KIND = wild SWING = down }` |
| `bc_rally_the_line` | `bc_record_moment_effect = { TIER = minor KIND = ordered SWING = up }` |
| `bc_van_breaks_through` | `bc_record_moment_effect = { TIER = major KIND = bloodied SWING = up }` |

- [x] **Step 4: Verify every effect block was reached**

```bash
cd /d/ck3/mods/battle_chronicles
grep -c "bc_battle_open_effect = yes" common/combat_phase_events/bc_commander_phase_events.txt
grep -c "bc_record_moment_effect" common/combat_phase_events/bc_commander_phase_events.txt
```

Expected: **7** and **7**.

- [x] **Step 5: Validate and commit**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
cd /d/ck3/mods/battle_chronicles
git add common/combat_phase_events/bc_commander_phase_events.txt
git commit -m "feat: wire the commander phase events to the seam"
```

---

### Task 10: Wire the pop-up options

Eight options across three events. These are the call sites that cannot write combat
state, which is the whole reason `bc_battle_open_effect` exists.

**Files:**
- Modify: `mods/battle_chronicles/events/bc_events.txt`

- [x] **Step 1: Add one seam call per option**

| event | option | call |
|---|---|---|
| `.0001` | a — "Then I will carry it myself." | `{ TIER = minor KIND = entrenched SWING = up }` |
| `.0001` | b — fall back | `{ TIER = minor KIND = measured SWING = down }` |
| `.0001` | c — charge to it | `{ TIER = decisive KIND = wild SWING = down }` |
| `.0002` | a — rally by prowess | `{ TIER = major KIND = ordered SWING = up }` |
| `.0002` | b — pay them | `{ TIER = minor KIND = measured SWING = up }` |
| `.0002` | c — steady them | `{ TIER = minor KIND = entrenched SWING = up }` |
| `.0003` | a — press it | `{ TIER = major KIND = bloodied SWING = up }` |
| `.0003` | b — consolidate | `{ TIER = minor KIND = measured SWING = up }` |

The option labels are given so the right KIND lands on the right option **index** — do
not match on position alone, match on the `name = bc_chronicles.000X.y` key.

Place each after the existing momentum effect in that option.

- [x] **Step 2: Do NOT add `bc_battle_open_effect` here**

A pop-up is raised by a phase event that has already run it. Adding it here would be a
no-op at best; at worst an implementer would reach for a combat scope that does not exist
and write a silently-failing line. `bc_events.txt`'s header records the invariant in one
sentence — "Nothing in here touches combat scopes" — and task 6 rewrites the lines around
it, so quote it by that text rather than by line.

- [x] **Step 3: Verify the count**

```bash
cd /d/ck3/mods/battle_chronicles && grep -c "bc_record_moment_effect" events/bc_events.txt
```

Expected: **8**.

- [x] **Step 4: Validate and commit**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
cd /d/ck3/mods/battle_chronicles
git add events/bc_events.txt
git commit -m "feat: wire the pop-up options to the seam"
```

---

### Task 11: Wire the knight phase events

Three events, and this is the task with the sharp edges.

**Files:**
- Modify: `mods/battle_chronicles/common/combat_phase_events/bc_knight_phase_events.txt`

- [x] **Step 1: Read this before editing — one real behaviour change**

`bc_knight_holds_the_breach` and `bc_knight_shames_himself` already push momentum onto
the side commander through `scope:combat_side.side_commander ?= { ... }`, so a seam call
alongside is a pure addition of bookkeeping.

**`bc_shieldbrother_forged` applies no momentum at all today.** Its effect block
(`bc_knight_phase_events.txt:219-283`) does opinions and memories, and its only
`side_commander ?=` block wraps a toast. Wiring it to the seam per the KIND table
(`minor` / `ordered` / `up`) therefore does **change behaviour**: from plan 2 onward the
seam applies a family-2 modifier from `(KIND, SWING)`, and `ordered`/`up` maps to
`bc_pursuit`, so the commander starts gaining a modifier from an event that previously
gave him nothing.

This is a deliberate consequence of the KIND table, not an accident — a pair of knights
holding together *is* the battle staying ordered. **But it is the one place stage 1's
"no new player-visible behaviour" claim is not strictly true, and it must be recorded in
the commit message so a later bisect finds it.**

- [x] **Step 2: Add `bc_battle_open_effect` to all three**

It goes **inside** `scope:combat_side.side_commander ?= { ... }`, because every `bc_`
write lands on the commander and the effect's own writes assume `this` is him.
`scope:combat_side` is still resolvable inside that block — it is a saved scope, not a
relative link.

For `bc_knight_holds_the_breach` and `bc_knight_shames_himself`, add it as the first line
of the existing `side_commander ?=` block.

For `bc_shieldbrother_forged` there is no such block outside the toast, so add one at the
top of the `effect`, immediately after `save_scope_as = bc_knight`:

```
		scope:combat_side.side_commander ?= {
			bc_battle_open_effect = yes
		}
```

**This is the one exception to that event's own rule.** Its comment at `:213-218` says
nothing happens before the partner is found, because a wasted 15-day lockout is not free.
Opening the battle is not a lockout — it writes two variables that are overwritten on
every phase event anyway — so the rule is not violated in substance. Say so in a comment
at the call site, or someone will "fix" it later.

- [x] **Step 3: Add the seam calls**

| event | call | placement |
|---|---|---|
| `bc_knight_holds_the_breach` | `{ TIER = major KIND = entrenched SWING = up }` | in the `side_commander ?=` block, after `bc_momentum_minor_effect` |
| `bc_knight_shames_himself` | `{ TIER = minor KIND = wild SWING = down }` | in the `side_commander ?=` block, after `bc_faltering_minor_effect` |
| `bc_shieldbrother_forged` | `{ TIER = minor KIND = ordered SWING = up }` | **inside `if = { limit = { exists = scope:bc_shieldbrother } }`**, in a `side_commander ?=` block |

The third placement is load-bearing: outside that `if`, the seam would record a moment
for an event that produced no story, inflating `bc_battle_moments` and pushing the
escalation ladder up on nothing.

- [x] **Step 4: Verify no `bc_` variable can reach a knight**

```bash
cd /d/ck3/mods/battle_chronicles
grep -n "bc_record_moment_effect\|bc_battle_open_effect" common/combat_phase_events/bc_knight_phase_events.txt
```

Expected: **6 hits, every one of them indented inside a `side_commander ?=` block.**
Read the surrounding lines and confirm it by eye. A seam call that escapes that block
writes scratch onto a knight, which is the failure mode Section 1 of the spec exists to
prevent and which nothing at runtime will report.

- [x] **Step 5: Validate and commit**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
cd /d/ck3/mods/battle_chronicles
git add common/combat_phase_events/bc_knight_phase_events.txt
git commit -m "feat: wire the knight phase events to the seam

All six calls sit inside side_commander ?= — no bc_ variable is ever written onto
a knight.

BEHAVIOUR CHANGE, deliberate: bc_shieldbrother_forged previously applied nothing
to the commander. Per the KIND table it now records a minor/ordered/up moment, so
from plan 2 onward it will also apply bc_pursuit. This is the single exception to
stage 1 shipping no new player-visible behaviour."
```

---

### Task 12: Clear scratch at combat end

Five scratch variables now exist — `bc_battle_moments`, `_tier`, `_style`, `_size`,
`_foe`. Nothing removes them, so right now they leak into every subsequent battle.

The effect below clears **six**. The extra name is `bc_battle_wounded`, which nothing
writes until plan 6. That is deliberate and safe: `remove_variable` on a variable that was
never set is not a read and logs nothing, so the clear list can be written once, complete,
rather than being amended by a later plan that would have no reason to look here.

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_ledger_effects.txt`
- Modify: `mods/battle_chronicles/events/bc_aftermath_events.txt`

- [x] **Step 1: Write the clearing effect**

```
# --- scratch clearing -------------------------------------------------------
#
# remove_variable, NEVER set_variable value = 0. Three of the six cannot hold
# zero — bc_battle_style is a flag, bc_battle_foe is a character,
# bc_battle_wounded is a presence test — and absence-versus-zero is what the seam
# and the pacing floor both test.
#
# bc_battle_wounded is listed although nothing writes it until plan 6. Clearing a
# variable that does not exist is a no-op; forgetting to add it later is not.
bc_clear_scratch_effect = {
	remove_variable = bc_battle_moments
	remove_variable = bc_battle_tier
	remove_variable = bc_battle_style
	remove_variable = bc_battle_size
	remove_variable = bc_battle_wounded
	remove_variable = bc_battle_foe
}
```

- [x] **Step 2: Call it LAST in both graders, OUTSIDE the game-rule gate**

In both `bc_chronicles.0091` and `.0092`, as the final statement of `immediate`:

```
		side_commander ?= {
			bc_clear_scratch_effect = yes
		}
```

- [x] **Step 3: Confirm the placement by eye — this is the whole task**

Two properties, both of which will silently break things if wrong:

1. **Outside the `NOT = { has_game_rule = bc_aftermath_off }` gate.** Inside it, a player
   who turned aftermath off would accumulate scratch forever.
2. **After the grading branch, not before.** From plan 3 onward, B reads
   `bc_battle_style` and C reads `bc_battle_foe`, both scratch, from inside that branch.
   CK3 executes siblings in written order, so clearing first would leave them reading
   variables that had just been removed — they would silently never fire, and each would
   emit a missing-variable error line on every combat end in the world.

The natural way to write the two-column split — group all the ungated work together — is
exactly wrong. Add a comment saying so at the call site.

- [x] **Step 4: Record the one leak this does not close**

**A pop-up answered after the battle has already ended writes scratch that nothing will
clear.** `bc_chronicles.0001/0002/0003` are player events sitting in the queue. If the
combat resolves before the player clicks, the option's `bc_record_moment_effect` runs
*after* `bc_clear_scratch_effect` has run, leaving `bc_battle_moments`, `bc_battle_tier`
and `bc_battle_style` on the commander. `bc_battle_open_effect` overwrites `bc_battle_size`
and `bc_battle_foe` on the next battle, but **it does not touch those three** — so the next
battle starts with an inflated moment count and a stale style. That is precisely the
failure the "no `bc_battle_*` variable survives a battle" criterion claims cannot happen.

This is not fixed in plan 1, for two reasons: it only affects a human player who leaves a
pop-up unanswered through the end of a battle, and the clean fix — making
`bc_battle_open_effect` clear all three the way it already overwrites the other two — has
to be weighed against the pop-up legitimately arriving mid-battle, which is the normal
case and must keep working.

**Add this as a comment in `bc_ledger_effects.txt` next to `bc_clear_scratch_effect`**, so
whoever hits it does not rediscover it, and check for it in task 15 step 6.

- [x] **Step 5: Validate and commit**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
cd /d/ck3/mods/battle_chronicles
git add common/scripted_effects/bc_ledger_effects.txt events/bc_aftermath_events.txt
git commit -m "feat: clear battle scratch at combat end

Last statement of both graders and outside the game-rule gate. Order is
load-bearing: grading reads scratch, and CK3 runs siblings in written order."
```

---

### Task 13: Hook `on_combat_start`

Needed for DIAG Q2, and later for the eve pop-up in plan 5. The hook is **entirely
unclaimed** — AGOT's `combat_on_actions.txt:3-4` is a bare `on_combat_start = { }`.

**Files:**
- Modify: `mods/battle_chronicles/common/on_action/bc_on_actions.txt`
- Create: `mods/battle_chronicles/events/bc_diag_events.txt` — the hook's target. Written
  by reaching forward into task 14 step 1 (see step 4), because an `events = { }` entry
  pointing at an event that does not exist is a runtime error. The two commit together.

- [x] **Step 1: Add the hook**

```
# Root = Combat here, NOT a combat side — see event_scopes.log and the DIAG event
# this currently carries. `events = { }` for the same reason as the two hooks
# above: an `effect = { }` in an on_action does not merge across files.
on_combat_start = {
	events = {
		bc_chronicles.0900
	}
}
```

- [x] **Step 2: Do not add anything else to this file**

No `effect = { }`. The header comment records that the engine keeps exactly one
`effect` per on_action, chosen by alphabetical filename within `common/on_action`, and
that a mod loading dead last still loses to `combat_on_actions.txt`. This exact bug ate a
probe run on 2026-08-12.

- [x] **Step 3: Validate**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
```

Expected: exit 0.

**Step 4 is not "commit". Do task 14 step 1 now, before committing anything here.**
`bc_chronicles.0900` does not exist yet, and an `events = { }` list naming an event that
does not exist is a dangling reference — a runtime error, and a commit that leaves the
mod broken, which violates this plan's own rule that every task ends in a working state.
The hook and the event it points at are one atomic change and must be one commit.

- [x] **Step 4: Create `bc_chronicles.0900` — jump to task 14 step 1, then come back**

Task 14 step 1 creates `events/bc_diag_events.txt` containing `bc_chronicles.0900`. Do
that step now. Nothing else in task 14 depends on this ordering, and nothing in task 14
step 1 depends on the rest of task 13.

- [x] **Step 5: Validate again, now that the reference resolves**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
```

Expected: exit 0.

- [x] **Step 6: Commit the hook and the event together**

```bash
cd /d/ck3/mods/battle_chronicles
git add common/on_action/bc_on_actions.txt events/bc_diag_events.txt
git commit -m "feat: hook on_combat_start, which is unclaimed in the loaded playset

Committed together with bc_chronicles.0900, the event it dispatches. The hook
alone is a dangling reference. Both are provisional: the event is DIAG Q2, and
whether either survives is decided in task 16 by whether a scope = combat event
fires at all."
```

**On the scope of `on_combat_start`.** Vanilla and AGOT both comment `# Root = Combat` at
the top of `combat_on_actions.txt:1-2`, and this plan is written against that. Note that
`on_actions.log:10151-10153` disagrees, giving `Expected Scope: none`. The comment is more
likely right than the generated log, but if Q2's first marker never appears, **this
discrepancy is the first thing to suspect** — before concluding that `scope = combat`
events do not work.

---

### Task 14: The DIAG pass — five questions, one run

A restart costs about seven minutes, so one run must answer everything. Each question
independently invalidates a design decision in a later plan.

**Every question is a trigger ladder logging string constants.** `debug_log` takes a
string; it does not interpolate a variable or a script value. The mod's own existing DIAG
code was written this way for exactly this reason.

**Files:**
- Create: `mods/battle_chronicles/events/bc_diag_events.txt`
- Modify: `mods/battle_chronicles/events/bc_aftermath_events.txt` (Q1, Q3, Q5 hooks)
- Modify: `mods/battle_chronicles/common/combat_phase_events/bc_knight_phase_events.txt` (Q4)

- [x] **Step 1: Q2 — does a `scope = combat` event work at all?**

This is the riskiest question in the expansion. `scope = combat` is listed as a valid
event scope but **nothing in vanilla or AGOT declares it** — `scope = combat_side` is
universal. Two questions in one marker, because the second is meaningless without the
first.

Create `events/bc_diag_events.txt`:

```
namespace = bc_chronicles

# Battle Chronicles - DIAG. TEMPORARY. Deleted at the end of stage 1.
#
# Everything here is pure debug_log with no state. If any of it writes a variable
# or a modifier, it is wrong.

# ---------------------------------------------------------------------------
# Q2. Raised by on_combat_start, where Root is the Combat.
# ---------------------------------------------------------------------------
bc_chronicles.0900 = {
	hidden = yes
	scope = combat

	immediate = {
		debug_log = "BC: DIAG Q2 combat-scoped event fired"

		combat_attacker.side_commander ?= {
			debug_log = "BC: DIAG Q2 attacker commander resolved"
		}
		combat_defender.side_commander ?= {
			debug_log = "BC: DIAG Q2 defender commander resolved"
		}
	}
}
```

If the first marker never appears, the eve pop-up in plan 5 dies and nothing else moves —
that is the whole dependency.

- [x] **Step 2: Q1 — trait census**

A four-rung ladder. B gates on `number_of_commander_traits < 3`; if the median commander
already holds 3, B is dead on arrival, the same way `has_any_nickname = no` disqualified
3 of 4 sampled AGOT commanders.

**Placement: in BOTH graders, inside a `side_commander ?=` at the top of `immediate`,
OUTSIDE the notability gate** — the same placement as Q3, for the same reason. An earlier
draft put it in `bc_chronicles.0091` only and inside the gate, which samples exclusively
commanders who have just won a notable battle. That is precisely the population most
likely to be decorated, so it would overstate the trait count and kill B on a biased
sample. The mod already states this rule about its own instrumentation at
`bc_events.txt:180-184`: "the calibration markers below have to fire on EVERY combat end,
including the ones that fail the bar, or they measure only the battles that already
passed."

```
			if = {
				limit = { number_of_commander_traits >= 3 }
				debug_log = "BC: DIAG Q1 traits 3plus"
			}
			else_if = {
				limit = { number_of_commander_traits = 2 }
				debug_log = "BC: DIAG Q1 traits 2"
			}
			else_if = {
				limit = { number_of_commander_traits = 1 }
				debug_log = "BC: DIAG Q1 traits 1"
			}
			else = {
				debug_log = "BC: DIAG Q1 traits 0"
			}
```

- [x] **Step 3: Q3 — subdivide the `under 5k` bucket**

The 2,000 boundary between size buckets 1 and 2 is the one number in the expansion with
no evidence behind it. In **both** graders, at the top of `immediate`, outside every
gate — it must measure every battle, including the ones that fail notability, or it
measures only the battles that already passed:

```
		if = {
			limit = { combat = { num_total_troops >= 5000 } }
			debug_log = "BC: DIAG Q3 size 5k plus"
		}
		else_if = {
			limit = { combat = { num_total_troops >= 3000 } }
			debug_log = "BC: DIAG Q3 size 3k"
		}
		else_if = {
			limit = { combat = { num_total_troops >= 2000 } }
			debug_log = "BC: DIAG Q3 size 2k"
		}
		else_if = {
			limit = { combat = { num_total_troops >= 1000 } }
			debug_log = "BC: DIAG Q3 size 1k"
		}
		else = {
			debug_log = "BC: DIAG Q3 size under 1k"
		}
```

**Read from a trigger ladder, not from `var:bc_battle_size`.** It has to measure the
world, not the mod — a bug in `bc_battle_open_effect` would otherwise make the
measurement agree with itself and prove nothing.

- [x] **Step 4: Q4 — does a toast body run for an AI subject?**

**This question is not merely under-evidenced. The mod's own README already answers it,
and answers it the opposite way from the rule the whole mod is built on.** Both claims
are in that one file:

- `README.md:48-51`, the design rule: "No gameplay effect ever sits inside a
  `send_interface_toast`. A toast only reaches the player playing the scoped character,
  so anything nested in one is unreliable for the AI."
- `README.md:158-159`, the 2026-08-13 calibration result: "**Resolved:** a
  `send_interface_toast` body **does** run for an AI character — `fired
  bc_knight_holds_the_breach` 14 == `toast body ran` 14."

They cannot both be right, and the later one is marked Resolved. Vanilla sides with the
later one: `add_legitimacy = minor_legitimacy_loss` sits inside a toast body at
`combat_on_actions.txt:575`, under `on_combat_end_loser` within
`side_primary_participant`, which is usually AI.

**But the 14 == 14 result has a confound that invalidates it.** That probe was on
`bc_knight_holds_the_breach`, whose toast is raised on `scope:combat_side.side_commander`
(`bc_knight_phase_events.txt:94-109`). If every one of those 14 fires happened in a
battle the player was fighting, with the player as that side's commander, then the
subject was **human every time** and the run measured nothing about AI. Nothing in the
README records the AI/human split of those 14. The debug log that would settle it has
since rotated — `probe "BC:"` returns nothing today — so it cannot be recovered.

**Be honest about how strong that confound is: it is a live possibility, not a proof.**
`bc_knight_phase_events.txt:3-5` records, as established fact, that `type = knight` has no
`is_ai` gate and "fires for every knight on every side of every combat in the world — the
probe run saw 41 fires from a single battle". If that is right, a 14-fire sample very
probably did contain AI side commanders, and the 14 == 14 result is better evidence than
this section allows. The point stands anyway: *probably* is not a basis for a rule that
plans 3, 4 and 5 all build on, and the split costs one `if`. It also makes a prediction the
run itself tests — if the header is right, `subject AI` will be plentiful without any
special effort, and row 1 of the table below will not be reached.

So Q4 stands, but it must be instrumented to make the AI/human split explicit, which is
exactly what the original probe failed to do.

**Instrument the knight-breach toast, NOT `bc_addressed_toast_effect`.** This is the whole
difficulty of the question and the obvious placement is wrong. In plan 1
`bc_addressed_toast_effect` has exactly **one** caller — `bc_aftermath_nickname_effect` —
sitting behind `has_any_nickname = no` + `var:bc_notable_battles >= 3` + `martial >= 14`,
a gate that **no observed battle has ever cleared** (that is the entire premise of task 2).
Markers put there would return zero rows, land on the "inconclusive" row of the table below
by accident rather than by measurement, and burn the run.

`bc_knight_holds_the_breach` is the opposite: it fired **14 times** in the calibration run,
its toast is raised on the side commander, and it needs no gate weakened. It is the same
site the original probe used — it was never the site that was wrong, only the
instrumentation. So restore that probe with the split it lacked.

**Task 1 step 3 deletes this marker; this step puts back a better one.** That is
deliberate, not thrash — the old marker cannot answer the question and would otherwise
interleave two generations of output in one log.

In `bc_knight_phase_events.txt`, inside the existing
`scope:combat_side.side_commander ?= { ... }` block:

```
			if = {
				limit = { is_ai = no }
				debug_log = "BC: DIAG Q4 subject HUMAN"
			}
			else = {
				debug_log = "BC: DIAG Q4 subject AI"
			}

			send_interface_toast = {
				type = event_toast_effect_good
				title = bc_knight_holds_the_breach_toast
				desc = bc_knight_holds_the_breach_toast_desc
				left_icon = scope:bc_knight
				debug_log = "BC: DIAG Q4 body ran"
			}
```

**The two `subject` markers go OUTSIDE the toast** — that is the point. They count how
often the toast was *reached*, split by whether anyone was playing the subject. `body ran`
counts how often the inside of it executed. The comparison between those three numbers is
the answer.

**How to read the counts — this is the whole point of the split:**

Write down all three counts first — `subject HUMAN` (H), `subject AI` (A), `body ran` (B).
The rows are exhaustive over them:

| observation | conclusion |
|---|---|
| A == 0 | **The run proved nothing.** Every toast had a human subject, which is precisely the confound that invalidated the 14 == 14 result. Do not record a verdict. Keep playing until an AI side commander triggers the event. |
| A > 0 and B == H + A | Bodies **do** run for AI. The `README.md:48-51` rule is false as stated and `:158-159` was right. Correct the README, and relax "state never inside a toast" for plans 3-5. |
| A > 0 and B == H | Bodies are **skipped** for AI. The rule holds and every award in plans 3-5 must stay outside its toast. |
| A > 0 and H < B < H + A | Bodies run for AI **sometimes**. Treat this exactly as "skipped" — an effect that runs unpredictably is unusable for state either way — and record the partial counts, because this is the answer neither README claim anticipated. |
| B < H | **Not a Q4 answer at all.** Something other than AI-gating is suppressing the body, since it did not even run for every human subject. Do not record a Q4 verdict; find out what before plan 3 relies on any of this. |

The first row is not a formality; it is the failure mode that produced the contradiction in
the first place, and it must be checked before any verdict is written down. **The fourth
row is why all three raw counts get recorded rather than just a verdict.** The fifth exists
because "exhaustive" has to mean exhaustive: without it, `B < H` falls through the table
and gets read as whichever row it is closest to.

**Note what survives either answer.** `bc_addressed_toast_effect` does two things:
it keeps state out of toast bodies, and it addresses the toast to somebody who might be
human instead of broadcasting it at an AI courtier. Only the first depends on Q4. The
second is a presentation decision that stands regardless — a toast about an AI knight
still belongs on his commander. So a "bodies do run" answer **simplifies** task 4's
justification; it does not delete task 4.

- [x] **Step 5: Q5 — which terrain buckets do battles actually happen in?**

**Q5 used to ask a different question, and that question is now closed.** It asked whether
plain `terrain =` keys resolve in Westeros. They do not, and no run is needed to know it:
AGOT's `common/terrain_types/01_agot_terrains.txt` defines road variants as **distinct
terrain types** (`majorroad_hills` is not `hills`) and adds seven bases vanilla has no key
for. Of 7007 provinces in `common/province_terrain/00_province_terrain.txt`, 1036 sit on a
road variant and ~756 on an AGOT-only base — **~26% of the map is invisible to a bare
`terrain =` check**, silently. AGOT's own
`00_martial_lifestyle_effects.txt:45-52` and `:65-66` abandoned bare keys for exactly this
reason. Plan 3's ladder now calls AGOT's 23 `agot_is_<x>_terrain` helpers and the
already-shipped `bc_terrain_favours_us_trigger` / `bc_terrain_bogs_us_down_trigger` are
scheduled for the same repair.

**So this ladder must call the helpers too** — a DIAG written with bare keys would measure
the bug rather than the map, and would do it in the one place designed to catch bugs.

What is left to measure is the **distribution**: with the buckets resolving correctly, are
all six actually reached by battles? Plan 3 spends a trait arm, a toast, and a loc key on
each, and an arm for a bucket no battle ever lands in is dead weight. This is a census of
where wars are fought, not of what terrain exists — Dorne has desert and the Shivering Sea
has glacier, but armies may never fight in either.

**Placement: at the top of `immediate` in both graders, resolving the province directly —
NOT inside the `exists = scope:bc_battle_province` block.** That block sits inside both the
game-rule gate and `bc_battle_is_notable_trigger`, and the calibration run graded only
about 13% of battles notable, so one run would yield a handful of terrain samples across
six buckets. Q5 is a census of where battles happen, not of notable battles — and with six
buckets rather than five, sample size matters more, not less. Same rule as Q1 and Q3.

Resolve the province with `combat.location ?=`, which is what the graders already use to
populate `scope:bc_battle_province` further down:

**Indented two tabs, matching the top of `immediate`.** Q1's snippet is three tabs and this
one is two for a reason — the extra depth in the other snippets is a nested block this one
is deliberately not inside. If you paste this at five tabs you have put it back inside the
`exists = scope:bc_battle_province` block that the paragraph above forbids.

**The six arms below must be bucket-for-bucket identical to `bc_terrain_bucket_effect` in
plan 3 task 5.** That is the entire value of this measurement: if the two ladders disagree
by one helper, the census counts a bucket the mod will never award and misses one it will.
Diff them before running.

```
		combat.location ?= {
			if = {
				limit = {
					OR = {
						agot_is_jungle_terrain = yes
						agot_is_cloudforest_terrain = yes
					}
				}
				debug_log = "BC: DIAG Q5 terrain jungle"
			}
			else_if = {
				limit = {
					OR = {
						agot_is_drylands_terrain = yes
						agot_is_desert_terrain = yes
						agot_is_desert_mountains_terrain = yes
						agot_is_oasis_terrain = yes
						agot_is_canyon_terrain = yes
					}
				}
				debug_log = "BC: DIAG Q5 terrain desert"
			}
			else_if = {
				limit = {
					OR = {
						agot_is_frozen_flats_terrain = yes
						agot_is_glacier_terrain = yes
					}
				}
				debug_log = "BC: DIAG Q5 terrain winter"
			}
			else_if = {
				limit = {
					OR = {
						agot_is_forest_terrain = yes
						agot_is_taiga_terrain = yes
					}
				}
				debug_log = "BC: DIAG Q5 terrain forest"
			}
			else_if = {
				limit = {
					OR = {
						agot_is_hills_terrain = yes
						agot_is_mountains_terrain = yes
						agot_is_wetlands_terrain = yes
						agot_is_the_bog_terrain = yes
						agot_is_taiga_bog_terrain = yes
						agot_is_terraced_hills_terrain = yes
						agot_is_highlands_terrain = yes
					}
				}
				debug_log = "BC: DIAG Q5 terrain rough"
			}
			else_if = {
				limit = {
					OR = {
						agot_is_farmlands_terrain = yes
						agot_is_plains_terrain = yes
						agot_is_steppe_terrain = yes
						agot_is_floodplains_terrain = yes
						agot_is_urban_terrain = yes
					}
				}
				debug_log = "BC: DIAG Q5 terrain open"
			}
			else = {
				debug_log = "BC: DIAG Q5 terrain NONE MATCHED"
			}
		}
```

**The rare buckets are deliberately first.** `rough` and `forest` are the two commonest
terrains in Westeros — hills alone is 1465 provinces, taiga 824, forest 790 — so putting
them last costs nothing and putting `jungle`, `desert` and `winter` first means a rare hit
cannot be swallowed by an earlier broad arm. The arms are disjoint by construction, so the
order does not change any answer; it only makes the ladder easier to reason about.

**`NONE MATCHED` now means something much stronger than it used to.** The six arms are
exhaustive over all 23 AGOT terrain helpers — 5 + 5 + 7 + 2 + 2 + 2 = 23 — so this arm is
unreachable in principle. **Any hit at all means AGOT has changed its terrain list**, and
plan 3's ladder is stale in exactly the same way. Do not shrug it off as an unhandled key;
re-derive both ladders from
`common/scripted_triggers/00_agot_terrain_type_triggers.txt` before plan 3 starts.

**How to read the counts:**

| observation | conclusion |
|---|---|
| `NONE MATCHED` > 0 | Stop. AGOT's terrain list has changed; both ladders must be rebuilt before plan 3. |
| all six buckets > 0 | Ship all six arms. |
| `rough` and `forest` dominate, others thin but non-zero | Expected, and fine. A rare bucket is a rare reward, not a dead one — it does not need to be common to be worth an arm. |
| a bucket is 0 across the whole run | **Not yet a verdict.** A single run is a small sample and one war is fought in one corner of the map. Record the zero and keep the arm; only drop an arm if a second run in a different region also reports zero. |

That last row is deliberately conservative, and it is where this question differs from Q1
and Q3. Those measure properties of *every* battle, so a run is a fair sample. Terrain is
a property of *where the war is*, and a single campaign is not a sample of Westeros.

- [x] **Step 6: Validate, index, conflicts, deploy**

```bash
cd /d/ck3/tools && python ck3.py validate --strict && python ck3.py index && python ck3.py conflicts && python ck3.py deploy
```

Expected: all exit 0.

- [x] **Step 7: Commit**

```bash
cd /d/ck3/mods/battle_chronicles
git add events/bc_diag_events.txt events/bc_aftermath_events.txt \
        common/combat_phase_events/bc_knight_phase_events.txt
git commit -m "test: add the five-question DIAG pass

Each question independently invalidates a decision in a later plan. All are
trigger ladders logging string constants — debug_log does not interpolate values.
Q3 reads a trigger ladder rather than bc_battle_size so it measures the world
rather than the mod."
```

---

### Task 15: Run it

**This is the runtime checkpoint. Everything before it is unproven.**

- [x] **Step 1: Clear the logs — with the game closed**

Delete `error.log` and `debug.log` from
`D:\Documents\Paradox Interactive\Crusader Kings III\logs`.

**Skipping this makes step 2 unfalsifiable**, because `error.log` accumulates across
sessions and already holds 225 matching lines from earlier runs. See "Read this before
task 1". This also discards the previous run's `debug.log`, so if anything from it is
still unrecorded, write it into the README first.

- [x] **Step 2: Fight battles**

Launch the game. Fight several battles of visibly different sizes, and win at least one
and lose at least one. Let at least one battle run long enough to produce five or more
moments, so the `decisive` rung of the escalation ladder is exercised.

**Q4 additionally needs `bc_knight_holds_the_breach` to fire on a side whose commander is
AI** — watch an ally's or a vassal's army fight, not only your own. Without that, `subject
AI` is 0, Q4 lands on the inconclusive row, and the run reproduces exactly the all-human
sample that produced the contradiction it exists to resolve. The event needs a knight with
`prowess >= 10` on the side, so it is not rare — but it is not guaranteed in a short
session either.

**This is probably belt-and-braces, and costs nothing if it is.**
`bc_knight_phase_events.txt:3-5` records that `type = knight` has no `is_ai` gate and fires
"for every knight on every side of every combat in the world", which would make AI subjects
plentiful without going looking. Go looking anyway: that header has never been tested
against this specific question, and the cost of being wrong is a wasted seven-minute run.

- [x] **Step 3: Sweep for errors first**

```bash
cd /d/ck3/tools && python ck3.py probe "bc_"
```

Expected: every group satisfies the three-item whitelist in "Read this before task 1" — a
`Failed to read key reference` naming one of the nine game-rule option keys, the launcher's
`BC Spike` line, or a line beginning `BC: `. All three are expected noise, not defects.

**Expect the third family to be large here.** This is the run that fires the mod's ten
`BC: fired bc_<event>` markers and every DIAG marker, all of which contain `bc_`, and all
of which `probe "bc_"` returns. Do not read that volume as breakage — read the *names*.

**A group naming a `bc_` key outside all three families — stop and fix before reading any
marker.** A missing-variable error
repeated once per knight per combat is the highest-volume failure this design can
produce, and every number below would be measured against a broken build.

- [x] **Step 4: Read the seam markers** — DONE on the second run, 2026-08-14.

The first run returned **zero** `BC: moment` lines: `bc_record_moment_effect` declared
`SWING` and read it nowhere, which stops the whole effect compiling and silently kills all
18 call sites. That is a **third** failure mode this step did not anticipate, and it looks
like nothing at all rather than like either signature below.

Second run, 143 combat ends, **707 moments**: minor 614, major 93, **decisive 0**. Swings
up 422 / down 285. Both totals equal 707, so every moment recorded exactly one tier and
exactly one swing.

**`decisive = 0` is a pacing result, not the broken-comparison signature described below.**
The two are distinguishable without a further run, and this is the technique to reuse:
`probe` groups by an `args#<hash>` that is unique per parameter set, so each call site can
be reconciled against its own `BC: fired` count.

| site | requested | fires | major | minor |
|---|---|---|---|---|
| `bc_knight_holds_the_breach` | major | 128 | 77 | 51 |
| `bc_van_breaks_through` | major | 53 | 8 | 45 |
| `bc_banner_falls` | major | 43 | 4 | 39 |
| `bc_flank_collapses` | **decisive** | 37 | **4** | 33 |

All four reconcile exactly. The decisive-requesting site logged `major` 4 times, and since
its `TIER` is `decisive`, those lines can only have come through the
`flag:$TIER$ = flag:decisive` arm of the OR — `flag:decisive = flag:major` is false. **The
comparison works.** Note that the 93 `major` lines alone would *not* have proven this: the
major arm is an OR, so it passes on `flag:major` even if the `decisive` row is dead. Only
the flank reconciliation settles it.

Why the top rung is empty: moments accumulate per side-commander, mean **707 / 286 ≈ 2.5**.
`decisive` needs `bc_flank_collapses` to fire on a commander already holding 4 moments, and
it is the only AI-reachable decisive site — the other (`bc_events.txt:61`) is a player
pop-up. **Recorded, deliberately not retuned:** this campaign lost every battle, and a
losing commander tends to die, be captured, or have his combat end early, so 2.5 may be a
losing-side artefact. Same reasoning this plan already applies to Q5's empty desert bucket.
Retune only if a second campaign that wins battles also reports zero.

```bash
python ck3.py probe "BC: moment"
```

**If `BC: moment minor` is the only marker that ever appears, do not write this off as a
short session.** That is the signature of the `flag:$TIER$` comparison failing: both upper
arms fall through to the `else`. Reconcile by `args#` as above rather than by eye.

- [x] **Step 5: Answer the five questions**

```bash
python ck3.py probe "DIAG Q1"
python ck3.py probe "DIAG Q2"
python ck3.py probe "DIAG Q3"
python ck3.py probe "DIAG Q4"
python ck3.py probe "DIAG Q5"
```

Record the counts. They gate the later plans:

| result | consequence |
|---|---|
| Q1 median is 3+ | plan 3's `number_of_commander_traits < 3` gate is dead — B must be redesigned before it ships |
| Q2 first marker absent | plan 5's eve pop-up dies. Nothing else is affected |
| Q3 | sets the real bucket-1/2 boundary. If `2k` and `3k` are both near-empty, move the boundary to where the mass is |
| Q4 | record all three raw counts and read them against the five-row table in task 14 step 4. If `subject AI` is 0 the run proved nothing and **no verdict is recorded**. A "bodies do run" verdict does not delete `bc_addressed_toast_effect` — it only relaxes the "state never inside a toast" rule for plans 3-5 |
| Q5 `NONE MATCHED` appears | **AGOT has changed its terrain list.** The six arms are exhaustive over all 23 `agot_is_<x>_terrain` helpers, so this is not "an unhandled terrain" — it is a stale ladder, in this DIAG and identically in plan 3 task 5. Rebuild both from `00_agot_terrain_type_triggers.txt` before plan 3 starts |
| a Q5 bucket is 0 | **record it, change nothing.** One campaign is fought in one corner of Westeros and is not a sample of the map. Drop an arm only if a second run in a different region also reports zero. See the four-row table in task 14 step 5 |

**If Q1 returns zero rows on a run that also logged `BC: win notable`, that — not the trait
census — is the finding.** Q1 sits inside `side_commander ?=` in the graders. Zero rows
alongside a notable win means the block was not entered, which would also mean task 12's
scratch clearing never runs. Vanilla says it should be entered (`combat_events.txt:84`
opens `side_commander` unguarded from an `on_combat_end_winner` event), so treat this as a
blocker on the whole plan and not as a Q1 answer. Zero rows with **no** `BC: win notable`
in the log is the ordinary case: too few notable battles, keep playing.

- [x] **Step 6: Confirm scratch does not leak** — DONE 2026-08-14, **statically**, because
  the method this step prescribed does not exist.

**`debug_show_variables` IS NOT A CK3 CONSOLE COMMAND.** It was invented while writing this
plan and never checked. The console answers `unknown command`, and there is no
`debug_show`-anything to autocomplete. Do not send anyone into the game to run it again.

**The claim below that "nothing static can catch it" was also wrong, and it is what made
this step look runtime-only.** Every `bc_battle_*` write in the mod lives in exactly four
effects in one file (`bc_ledger_effects.txt`), so auditing their call sites is *exhaustive*
where three sampled characters is not. Script the brace-depth walk over
`bc_knight_phase_events.txt`, `bc_commander_phase_events.txt`, `bc_events.txt` and
`bc_aftermath_events.txt`, printing each call site's enclosing-scope chain. Result on
2026-08-14, 31/31 sites:

1. **No `bc_` variable is ever written onto a knight** — knight events 6/6 inside
   `scope:combat_side.side_commander ?=`; commander events 14/14 and pop-ups 8/8 root on
   the commander (`type = commander` roots there, and a `trigger_event` with no `target =`
   inherits that scope); aftermath 3/3 inside `side_commander ?=`.
2. **Clearing is not gated by the game rule** — the ancestor chain of both
   `bc_clear_scratch_effect` calls is `event → immediate → side_commander ?=`, and the
   `bc_aftermath_off` `if` is not among the ancestors.
3. **Cleanup runs once per combat end** — `BC: combat end cleanup` logged 143× in each
   grader against 143 combat ends.

**One thing static analysis genuinely cannot reach, so it stays open:** a commander killed
or replaced mid-battle. The grader's `side_commander` then resolves to a different man and
the original keeps his scratch permanently. `bc_ledger_effects.txt` already anticipates
this in its own header comment. If a future run wants to measure it, the console command
that *does* exist is `effect`, and `every_living_character` is a global iterator
(`Supported Scopes: none`), so a one-line world sweep is possible:
`effect = { every_living_character = { limit = { is_knight = yes exists = var:bc_battle_moments } debug_log = "PROBE: leak" } }`.

- [x] **Step 7: Write the results down — two commits, two repos**

The numbers are the only record of how the later plans' thresholds were chosen. The
existing calibration header in `bc_scripted_triggers.txt` exists because the last set was
nearly lost.

Q1, Q2, Q3 and Q5 gate later plans, so they go in the spec — a **workspace** commit:

```bash
cd /d/ck3
git add docs/specs/2026-08-13-battle-chronicles-expansion-design.md
git commit -m "docs: record DIAG pass results"
```

Q4 settles a contradiction that lives in the mod's own README, so it goes there — a
**mod** commit. Correct or confirm `README.md:48-51` and `:158-159` in the same edit
rather than appending a third claim beside them:

```bash
cd /d/ck3/mods/battle_chronicles
git add README.md
git commit -m "docs: settle whether a toast body runs for an AI character

The 14 == 14 result recorded on 2026-08-13 could not distinguish an AI subject
from a human one, and contradicted the design rule stated earlier in the same
file. Re-measured with the split it lacked."
```

---

### Task 16: Remove the DIAG pass

Diagnostics that survive their question become noise that hides the next one. This is
exactly what task 1 had to clean up.

**Files:**
- Delete **or** rename: `mods/battle_chronicles/events/bc_diag_events.txt` — deleted if Q2
  failed, `git mv`'d to `events/bc_combat_start_events.txt` if it passed (step 2)
- Modify: `mods/battle_chronicles/events/bc_aftermath_events.txt` (Q1, Q3, Q5)
- Modify: `mods/battle_chronicles/common/combat_phase_events/bc_knight_phase_events.txt` (Q4)
- Modify: `mods/battle_chronicles/common/on_action/bc_on_actions.txt`
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_reward_effects.txt` (one comment, step 3)
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_ledger_effects.txt` (one comment, step 3)

- [x] **Step 1: Remove Q1, Q3, Q4 and Q5**

Strip every `debug_log = "BC: DIAG ..."` and the ladders that exist only to emit them.

**Keep** the permanent instrumentation: `"BC: combat end cleanup"`,
`"BC: win notable"` / `"BC: win not notable"`, `"BC: lose notable"` /
`"BC: lose not notable"`, `"BC: nickname awarded"`, and the three `"BC: moment ..."`
markers from the seam. The seam markers stay — they are how every later plan proves its
call sites fire.

- [x] **Step 2: Decide what happens to the `on_combat_start` hook**

Two cases:

- **Q2 passed.** Keep the hook and keep `bc_chronicles.0900`, but strip its body down to
  a single `debug_log = "BC: combat start"`. Plan 5 replaces the body with the eve
  dispatcher. Two things must happen alongside:
  - **Rename the file.** `git mv events/bc_diag_events.txt events/bc_combat_start_events.txt`,
    and update the `events = { }` reference if it names the file (it does not — CK3 resolves
    events by id — but check). A permanent file named for a diagnostic is a trap for plan 5.
  - **Rewrite the header.** Task 14 step 1 gives the file a header that says "DIAG.
    TEMPORARY. Deleted at the end of stage 1" and describes Q2. Every occurrence of `DIAG`
    must go, or step 3's grep fails on a file that is supposed to survive — and the grep is
    the only thing checking that the DIAG pass is really gone.
- **Q2 failed.** Delete the `on_combat_start` block from `bc_on_actions.txt` and delete
  `bc_diag_events.txt` entirely. Record the failure in the spec — plan 5's eve section
  needs rewriting before it can be executed.

- [x] **Step 3: Retire the two permanent comments that name a DIAG question**

**Two comments this plan ships are written in the future tense and will outlive the
questions they name.** They are not diagnostics and must not be deleted — they are the
justification for two invented constants — but they cannot keep saying a measurement is
pending after it has been taken. They are also what step 4's grep will trip over.

Both were written before the answers existed, so **substitute the numbers you actually
recorded in task 15 step 5**; the bracketed text below marks what varies.

In `common/scripted_effects/bc_reward_effects.txt` (shipped by task 5), the
`bc_addressed_toast_effect` header currently reads:

```
# Whether the toast BODY additionally fails to execute for an AI character is a
# separate and currently OPEN question - README.md:158-159 says it executes,
# README.md:48-51 says it does not. DIAG Q4 settles it. This effect is correct
# either way; only the strength of the "keep state out of toasts" rule depends on
# the answer.
```

Rewrite it as:

```
# Whether the toast BODY additionally executes for an AI character was an open
# question - README.md said both things in two places. It was measured at combat
# end across [N] toasts with a non-player subject: [the body ran / the body did
# not run]. README.md now records the answer next to the claim it corrects. This
# effect is correct either way; only the strength of the "keep state out of
# toasts" rule depended on it.
```

In `common/scripted_effects/bc_ledger_effects.txt` (shipped by task 7), the size ladder
currently reads:

```
	# (bc_scripted_triggers.txt:153). 2,000 is INVENTED - the calibration run
	# recorded `under 5k` as one undivided bucket and never subdivided it. DIAG Q3
	# measures it.
```

Rewrite it as:

```
	# (bc_scripted_triggers.txt:153). 2,000 was INVENTED - the calibration run
	# recorded `under 5k` as one undivided bucket and never subdivided it. It was
	# then measured over [N] battles: [the observed distribution], so the boundary
	# [stands / moved to X]. Do not re-guess it; re-derive it by restoring the
	# ladder from git history, the same rule the README states for the aftermath
	# thresholds.
```

**If Q4 recorded no verdict** — task 14 step 4's first row, `subject AI == 0` — say exactly
that in the first comment rather than inventing an answer: "measured once and the run
proved nothing; every toast had a human subject." A comment that overstates what was
measured is worse than one that admits the gap, and this is the specific failure the
five-row table exists to prevent.

- [x] **Step 4: Verify**

```bash
cd /d/ck3/mods/battle_chronicles && grep -rn "DIAG" --exclude-dir=.git common/ events/
```

Expected: **no output.**

**This grep is unfiltered on purpose and it is why step 3 exists.** It matches comment text
as readily as code, and after step 3 nothing shipped is allowed to contain the string
`DIAG` at all. Do not satisfy it by adding `| grep -v "#"` — the two comments were the
whole point, and filtering them out would leave stale prose in the mod forever while the
check reported clean.

**If Q2 failed and you deleted `bc_diag_events.txt`, delete the `on_combat_start` block in
the same commit.** Leaving the hook behind recreates exactly the dangling reference that
task 13 was restructured to avoid.

- [x] **Step 5: Full verification sweep** — deferred to task 17 step 4 and discharged
      there, so the index was built once over the final tree rather than over an
      intermediate one. `deploy` takes a mod name; see the correction in that step.

```bash
cd /d/ck3/tools && python ck3.py validate --strict && python ck3.py index && python ck3.py conflicts && python ck3.py deploy battle_chronicles
```

Expected: all exit 0.

- [x] **Step 6: Commit**

**Name the files. Do not use `git add -A`.** Task 15 is a runtime task run against a live
game, and the mod directory is the deploy target — a blanket add sweeps up whatever the
game or a stray deploy left behind.

```bash
cd /d/ck3/mods/battle_chronicles
git add events/bc_aftermath_events.txt \
        common/combat_phase_events/bc_knight_phase_events.txt \
        common/on_action/bc_on_actions.txt \
        common/scripted_effects/bc_reward_effects.txt \
        common/scripted_effects/bc_ledger_effects.txt
```

Then stage the DIAG event file according to the step 2 branch:

- **Q2 passed** — the file survives, renamed. `git mv` has already staged both halves of
  the rename, so add the content edit: `git add events/bc_combat_start_events.txt`
- **Q2 failed** — the file is gone: `git rm events/bc_diag_events.txt`

Confirm nothing else is staged before committing:

```bash
git status --short
```

Expected: only the files named above appear staged. If another file shows as modified or
untracked, look at it before you do anything else — the step 3 grep passed, so a stray
here is not a missed DIAG marker, it is something the game or a deploy wrote. Add it by
name only if it is genuinely part of this task.

```bash
git commit -m "chore: remove the DIAG pass now that all five questions are answered

Kept the permanent instrumentation and the three seam markers — every later plan
proves its call sites through those."
```

---

### Task 17: Repair the two shipped ground triggers

**This task is independent of tasks 1-16 and commutes with all of them.** It touches one
file that no other task in this plan opens. It is placed last only so that renumbering
does not invalidate the cross-references in the sixteen tasks above.

**Do it before task 15 anyway.** Task 15 is the one runtime run this plan gets, and these
two triggers gate two of the eleven moments. Running with them broken means the moment
distribution that plan 2 retunes against is measured on a bug.

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_triggers/bc_scripted_triggers.txt:32-61`

- [x] **Step 1: Confirm the bug is still there and measure it** — 5 bare keys found at
      lines 47, 48, 56, 57, 58 (plus a comment reference at 33), and all nine province
      counts measured against AGOT's `00_province_terrain.txt` matched the plan's table
      exactly.

```bash
cd /d/ck3/mods/battle_chronicles
grep -n "terrain = " common/scripted_triggers/bc_scripted_triggers.txt
```

Expected: **5 lines** — `hills`, `forest` in `bc_terrain_favours_us_trigger`, and
`wetlands`, `jungle`, `mountains` in `bc_terrain_bogs_us_down_trigger`. If this returns
0 lines the task is already done; skip to step 5.

Now measure what those five keys miss:

```bash
P="D:/SteamLibrary/steamapps/workshop/content/1158310/2962333032/common/province_terrain/00_province_terrain.txt"
for t in hills forest wetlands jungle mountains the_bog taiga_bog highlands; do
  echo "$t base=$(grep -c "= $t\$" "$P") major=$(grep -c "= majorroad_$t\$" "$P") minor=$(grep -c "= minorroad_$t\$" "$P")"
done
```

Expected, as of AGOT at workshop id `2962333032`:

| terrain | base | majorroad | minorroad |
|---|---|---|---|
| `hills` | 1465 | 94 | 139 |
| `forest` | 790 | 36 | 155 |
| `wetlands` | 160 | 4 | 14 |
| `jungle` | 69 | 0 | 1 |
| `mountains` | 437 | 8 | 24 |
| `the_bog` | 125 | 14 | 0 |
| `taiga_bog` | 78 | 1 | 0 |
| `highlands` | 146 | 5 | 11 |

**`bc_terrain_favours_us_trigger` misses 94 + 139 + 36 + 155 = 424 provinces** it should
match — 15.8% of the ground it is meant to describe. `bc_terrain_bogs_us_down_trigger`
misses 51. Neither failure is visible: a province on `majorroad_hills` simply does not
match `terrain = hills`, no error is logged, and the event silently does not fire.

- [x] **Step 2: Replace both triggers and their comment**

The comment block above them is as wrong as the code and must go with it. Replace
`bc_scripted_triggers.txt:32-61` — from the `# --- ground` header through the closing
brace of `bc_terrain_bogs_us_down_trigger` — with:

```
# --- ground -----------------------------------------------------------------
# scope:combat_side.combat.location is a province scope, so a terrain check works
# there directly. Proven in game (probe 4).
#
# NEVER `terrain = X`. ALWAYS `agot_is_X_terrain = yes`. AGOT's
# common/terrain_types/01_agot_terrains.txt defines road variants as DISTINCT
# terrain types - `majorroad_hills` is not `hills` - and adds seven bases vanilla
# has no key for. These two triggers shipped with bare keys and so missed 424 and
# 51 provinces respectively, silently, from the first live run onward. AGOT's 23
# helpers in common/scripted_triggers/00_agot_terrain_type_triggers.txt each fold
# a base key together with its two road variants; that is the only correct way to
# ask what ground a battle is on.
#
# The helpers are base AGOT, not Seasons of Ice and Fire. An earlier version of
# this comment justified the bare keys as avoiding a hard dependency on a submod.
# That was the wrong file: 2962333032 is `name="A Game of Thrones"` itself, and
# descriptor.mod already declares `dependencies = { "A Game of Thrones" }`.
#
# `mountains` used to appear in BOTH lists, so in the mountains the ground
# simultaneously favoured you and bogged you down and the two events fought over
# the same roll. It belongs to the bogging list: hills and forest already carry
# "good defensive ground".
#
# the_bog and taiga_bog are new to the bogging list and are the point of it. The
# old comment argued that wetlands and jungle alone are "close to nonexistent in
# Westeros - the Neck and nothing else". That was right about the Neck and wrong
# about the key: AGOT models the Neck as `the_bog`, 139 provinces including road
# variants, which the old trigger did not match at all. highlands and
# terraced_hills join the favouring list for the same reason - they are AGOT's own
# variations on hills. terraced_hills currently has zero provinces on the map; it
# is listed anyway so the pair stays exhaustive over what "hill-like" means if
# AGOT ever places one.

bc_terrain_favours_us_trigger = {
	scope:combat_side.combat.location = {
		OR = {
			agot_is_hills_terrain = yes
			agot_is_forest_terrain = yes
			agot_is_highlands_terrain = yes
			agot_is_terraced_hills_terrain = yes
		}
	}
}

bc_terrain_bogs_us_down_trigger = {
	scope:combat_side.combat.location = {
		OR = {
			agot_is_wetlands_terrain = yes
			agot_is_jungle_terrain = yes
			agot_is_mountains_terrain = yes
			agot_is_the_bog_terrain = yes
			agot_is_taiga_bog_terrain = yes
		}
	}
}
```

**The two lists stay disjoint.** That was a bug once already — `mountains` in both — and
adding four terrains is exactly when it recurs. `highlands` and `terraced_hills` are
hill-like, `the_bog` and `taiga_bog` are bog-like, and no helper appears twice.

- [x] **Step 3: Verify the replacement**

```bash
cd /d/ck3/mods/battle_chronicles
grep -cE '^[[:space:]]+terrain = [a-z_]+[[:space:]]*$' common/scripted_triggers/bc_scripted_triggers.txt
grep "agot_is_" common/scripted_triggers/bc_scripted_triggers.txt | grep -vc "#"
grep -n "agot_is_" common/scripted_triggers/bc_scripted_triggers.txt | grep -v "#"
```

The first must be **0**. The second must be **9**. The third must list **9 lines**, four
under `bc_terrain_favours_us_trigger` and five under `bc_terrain_bogs_us_down_trigger`,
with no key appearing twice. **All three came out right: 0, 9, and the nine lines at
68-71 and 79-83, no key twice.**

**The first count is the one that matters and it must be exactly 0, not "lower".** A
single surviving bare key is the entire bug, and it validates clean.

**RUN CORRECTION, 2026-08-14 — the first grep was originally written `grep -c "terrain =
[a-z]"` and CANNOT return 0 on a correctly fixed file.** It returned **10**. The plan
argued the comment line ``# NEVER `terrain = X`.`` is safe because `X` is uppercase. True
of that half of the line — but the *same line* ends `ALWAYS agot_is_X_terrain = yes`, and
so does every one of the nine helper calls the fix introduces. `[a-z]` matches the `y` of
`yes`. 9 helpers + 1 comment = 10. The check was counting the cure, not the disease, and
would have read 10 forever while looking like a failure.

The anchored form above is the correct check. It matches only the bare vanilla shape — a
line that is nothing but indentation, `terrain = `, and a lowercase key — which is exactly
what this task deletes, and which no helper call can resemble because a helper call has
text before `terrain`. Before the fix it returns 5 (the five bare keys; the old comment's
`terrain = x` example sat inline after `#` and never matched an anchored pattern). After,
0.

**The second command filters comments and a plain `grep -c` would not.** The replacement
comment contains the line ``# NEVER `terrain = X`. ALWAYS `agot_is_X_terrain = yes`.``, so
an unfiltered `grep -c "agot_is_"` returns **10** on a correct file. That line is doing real
work — it is the instruction a future editor needs at the moment they are looking at these
two triggers — so the grep gives way, not the comment.

Then confirm the helpers this file now depends on all exist:

```bash
for h in hills forest highlands terraced_hills wetlands jungle mountains the_bog taiga_bog; do
  grep -q "agot_is_${h}_terrain = {" "D:/SteamLibrary/steamapps/workshop/content/1158310/2962333032/common/scripted_triggers/00_agot_terrain_type_triggers.txt" || echo "MISSING: agot_is_${h}_terrain"
done
```

Expected: **no output** — and that is what it gave; all nine helpers exist.

One caveat found on the run: the `= {` in that grep is load-bearing only if AGOT's
formatting never varies. It held here, but the safer form drops it and greps the bare name.
`validate` cannot do this — it does not resolve references, so a
misspelled `agot_is_hils_terrain` passes cleanly and the trigger silently never matches,
which is the same class of failure being fixed here.

**No `^` anchor in that grep, deliberately.** AGOT ships a UTF-8 BOM on 2945 of its 3117
`common/*.txt` files, and `agot_is_farmlands_terrain` is on line 1 of this one — a
`^`-anchored version would report it missing.

- [x] **Step 4: Full sweep and deploy**

```bash
cd /d/ck3/tools && python ck3.py validate --strict && python ck3.py index && python ck3.py conflicts && python ck3.py deploy battle_chronicles
```

Expected: all exit 0. `conflicts` reads the index, so it must run after `index` — on a
stale index it can only ever report a pass.

**RUN CORRECTION, 2026-08-14: `deploy` takes a mod name and the plan omitted it.** Bare
`python ck3.py deploy` exits 2 with `error: the following arguments are required: mods`,
which in a `&&` chain reads as the sweep failing at the last step. The argument is
`battle_chronicles`.

All four passed. `index` covered 48 sources / 31502 files and lists `[45] Battle
Chronicles: 16 files, 71 defs, 107 loc`. `conflicts` reports 300 colliding files across the
playset and **Battle Chronicles appears in none of the chains** — which is the only part of
that report this mod is answerable for. This step also discharges task 16 step 5, whose
index/conflicts sweep was deferred to here.

- [x] **Step 5: Commit** — `2bd7f13`.

```bash
cd /d/ck3/mods/battle_chronicles
git add common/scripted_triggers/bc_scripted_triggers.txt
git commit -m "fix: the two ground triggers missed 26% of the map

Both shipped with bare vanilla terrain keys. AGOT defines road variants as
distinct terrain types, so `terrain = hills` does not match `majorroad_hills`:
bc_terrain_favours_us_trigger missed 424 provinces and bc_terrain_bogs_us_down
missed 51, silently, since the first live run. Both now call AGOT's
agot_is_<x>_terrain helpers.

Adds four terrains the bare keys could not name at all. the_bog is the Neck,
139 provinces, which the bogging trigger was written to describe and never
matched; highlands and terraced_hills are AGOT's variations on hills. The two
lists remain disjoint."
```

**No runtime step.** The fire rates of `ground_favours_us` and `lines_bogged_down` are
measured by task 15's run, which is why this task belongs before it. Plan 2 retunes their
weights against those numbers, and a weight tuned against a broken trigger is worse than
no tuning.

---

## Done when

- [x] Three combat-end events are two, and grading provably runs before scratch clearing.
      Verified structurally: `bc_chronicles.0091` opens at line 51, grades at 65, clears at
      152; `.0092` opens at 164, grades at 178, clears at 226. Both gradings sit at a
      shallower ancestor depth than their clear, so no game-rule branch can skip one and
      keep the other.
- [x] `bc_addressed_toast_effect` exists and the nickname path has executed at runtime —
      `BC: nickname awarded` ×6 in the run log.
- [x] All eighteen moment call sites reach `bc_record_moment_effect`. Reconciled through
      the `args#` hash: every `BC: fired` count matches its site's swing/tier lines exactly.
- [x] A battle's log shows N moment markers with tiers that respect the ceiling — 707
      moments logged, no tier above its site's ceiling.
- [x] No `bc_battle_*` variable exists on any commander at the start of a new battle.
      **Ledger variables persist by design** — `bc_notable_battles` is deliberately never
      cleared ("Never cleared - that is the point", `bc_scripted_effects.txt`), and task 12
      correctly leaves it out of the clear list. A criterion phrased "no `bc_` variable"
      would fail on a correct build.
      **Established by exhaustive static audit, not by console inspection** — see task 15
      step 6: all 31 write sites live in 4 effects in one file, every one is cleared, and
      the clear sits outside the game-rule gate. The one residual leak static analysis
      cannot reach is a commander killed or replaced mid-battle, which
      `bc_ledger_effects.txt`'s own header already anticipates.
- [x] No `bc_` variable of any kind exists on any knight, ever. Knights hold no ledger, so
      here the broad phrasing is the right one. Same audit.
- [x] `validate --strict`, `index`, `conflicts` and `deploy` all exit 0 — task 17 step 4.
- [x] On a **cleared** log, every group returned by `probe "bc_"` satisfies the three-item
      whitelist: a game-rule option key, the launcher's `BC Spike` line, or a line
      beginning `BC: `. No group names any other `bc_` key.
      **Two engine-emitted groups are not in that whitelist and never could be**: the
      `>=== NAMESPACE > 'bc_chronicles' is set to #3830000` line and one
      `Loaded [N] events from 'events/bc_*.txt'` line per event file. Both are the engine
      reporting on the mod rather than the mod logging, and both appear on any healthy
      build. The whitelist as written was a three-item list of *mod* output and should be
      read that way.
- [x] All three of `BC: moment minor` / `major` / `decisive` have appeared. If only
      `minor` ever appears, the `flag:$TIER$` comparison is silently failing and both
      upper arms of the ceiling are dead.
      **MET on the 2026-08-14 checkpoint run** — `BC: moment decisive` fired once. It
      had been the last unmet criterion on this plan.
      The history is worth keeping. At the DIAG run this read **NOT MET, AND
      DELIBERATELY LEFT SO**: `minor` and `major` both appeared; `decisive` was 0 across
      707 moments. That was **not** the failure the criterion was written to catch — the
      `flag:$TIER$` comparison was already proven working, by reconciling
      `bc_flank_collapses` (37 fires = 4 major + 33 minor) through its `args#` hash: those
      4 `major` lines can only have come through the decisive arm of the OR. `decisive = 0`
      was pacing, not logic — 707 moments over 286 side-commanders is a mean of 2.5, and
      the decisive rung needs a longer run of moments than a 2.5-mean battle produces. It
      was also measured entirely on a campaign that **lost every battle**. The decision to
      record rather than retune was the right one: the rung was reachable all along and a
      run with wins in it found it. **Do not retune the ladder on the strength of one
      `decisive`, either** — n=1 says reachable, not correctly paced.
- [x] All five DIAG answers are recorded — **Q1/Q2/Q3/Q5 in the spec**, Q4 in the mod's
      README next to the claim it corrects or confirms. That is the split task 15 step 7
      commits, and **Q2 belongs in it**: plan 5 gates its entire eve on Q2's verdict, and
      the only other record of that verdict is whether `events/bc_combat_start_events.txt`
      exists — a fact about the filesystem that says nothing about *why*. An earlier draft
      of this checklist listed only Q1/Q3/Q5 and left Q2 with no written home at all.
- [x] Q4 was answered on a run in which `BC: DIAG Q4 subject AI` appeared at least once.
      If that count is 0, the run only ever named a human subject and the question is
      untouched — record no verdict. **It appeared 131 times; human 0.**
- [x] No DIAG marker remains in `common/` or `events/`.
- [x] `grep -cE '^[[:space:]]+terrain = [a-z_]+[[:space:]]*$' common/scripted_triggers/bc_scripted_triggers.txt`
      returns **0**, and the file names nine `agot_is_<x>_terrain` helpers across two
      disjoint lists. Exactly 0, not "fewer" — one surviving bare key is the whole bug and
      it validates clean. **The unanchored `grep -c "terrain = [a-z]"` this criterion
      originally named is defective and can never return 0 after a correct fix; see the
      run correction in task 17 step 3.**

## What comes next

| plan | ships | gated on |
|---|---|---|
| 2 | family-2 modifiers, pacing curve | Q3 |
| 3 | B — reputation | Q1, Q4 |
| 4 | C — rivalry | this plan |
| 5 | D — eve, wipe, dead knights | Q2 for the eve only |
| 6 | family 3 — wounds | this plan |

**Every feature plan depends on this one and on nothing else.** Plan 6 was previously
listed as downstream of plan 2; that was wrong. Everything plan 6 needs — the
`bc_record_effective_tier_effect` ceiling ladder, `var:bc_battle_size` and its measured
bucket boundaries, `bc_battle_wounded` in the clear list, `bc_addressed_toast_effect` with
its `TYPE` parameter, and `SWING` in the seam's signature — comes from tasks 4, 7, 8, 11,
12 and 14 of this plan. Plan 6's own dependency table says so.

So all five may ship in any order once the DIAG run is in. Plan 4 does not even need the
DIAG run, because `bc_battle_foe` is written by `bc_battle_open_effect` and not by the eve.

Two pieces of scheduled work are deliberately **not** plans of their own:

| work | where it lives | why not a plan |
|---|---|---|
| repairing the two shipped ground triggers | task 17 of this plan | one file, no other task touches it, and it must land before task 15's run |
| a second `wounded` rank, recovery, knight wounds | nowhere yet | listed in plan 6's "what this plan deliberately does not do", pending a first look at how rank 1 actually plays |
