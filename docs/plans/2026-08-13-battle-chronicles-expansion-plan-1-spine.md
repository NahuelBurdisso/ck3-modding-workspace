# Battle Chronicles Expansion — Plan 1: The Spine (stages 0 and 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the mod's combat-end machinery, then add the one seam every future system reports through — so that at the end of this plan a battle writes down what happened in it, and a log proves it.

**Architecture:** Two stages. Stage 0 is behaviour-neutral: strip stale diagnostics, flatten and split files, and collapse three combat-end events into two so that grading provably runs before cleanup. Stage 1 adds `bc_battle_open_effect` (writes battle-scoped scratch at the top of every phase event) and `bc_record_moment_effect` (the seam every moment reports through), wires all eighteen existing moment sites to it, and ships a diagnostic pass that answers five open questions in one game run.

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
| collisions | `python ck3.py index` then `python ck3.py conflicts` | exit 0. **`conflicts` reads a sqlite index that only `index` rebuilds — a stale index makes it always pass, so never run it alone** |
| deploy | `python ck3.py deploy` | exit 0 |
| runtime | launch the game, fight a battle, then `python ck3.py probe <pattern>` | see below |

**`ck3.py probe` exits 1 when nothing matches.** For an error sweep, **non-zero exit is
the pass condition** — it means no `bc_` error was logged. For a marker sweep, exit 0 is
the pass condition. Read that twice; it inverts between the two uses.

**Never use `ck3.py errors`.** It tail-slices a ~500k-line log and mod script errors
appear near the top, so it cannot see them. `probe` reads end to end and groups by file.

**A game restart costs about seven minutes.** Batch runtime verification. This plan has
exactly two runtime checkpoints — after task 8 and after task 16 — and that is
deliberate.

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
| `common/scripted_effects/bc_ledger_effects.txt` | **create** (task 7) | `bc_battle_open_effect`, `bc_record_moment_effect`, `bc_add_verb_effect`, scratch clearing |
| `common/scripted_triggers/bc_scripted_triggers.txt` | modify | unchanged in this plan except its header |
| `events/bc_events.txt` | modify (shrinks) | player-facing pop-ups only |
| `events/bc_aftermath_events.txt` | **create** (task 6) | the two consolidated combat-end graders |
| `events/bc_diag_events.txt` | **create** (task 14) | the DIAG pass. **Deleted at the end of stage 1** |
| `common/on_action/bc_on_actions.txt` | modify | combat-end hooks now name one grader each; `on_combat_start` added |
| `common/combat_phase_events/bc_commander_phase_events.txt` | modify | `bc_battle_open_effect` + seam calls |
| `common/combat_phase_events/bc_knight_phase_events.txt` | modify | `bc_battle_open_effect` + seam calls, both inside `side_commander ?=` |

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

---

### Task 1: Strip every stale DIAG marker

The mod carries diagnostics from a previous investigation. They are answered, and they
will pollute the stage-1 log.

**Files:**
- Modify: `mods/battle_chronicles/events/bc_events.txt`
- Modify: `mods/battle_chronicles/common/combat_phase_events/bc_knight_phase_events.txt:103-108`

- [ ] **Step 1: Confirm what is there before removing it**

```bash
cd /d/ck3/mods/battle_chronicles
grep -rn "DIAG" . ; grep -rn "toast body ran" .
```

Expected: eleven `DIAG` hits in `events/bc_events.txt` and one
`"BC: toast body ran (knight breach)"` at
`common/combat_phase_events/bc_knight_phase_events.txt:108`.

If the counts differ, **stop and re-read the files** — the plan was written against a
known state and a different one means someone else has edited the mod.

- [ ] **Step 2: Remove the eleven markers in `bc_events.txt`**

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

**Do not remove the `exists = var:bc_notable_battles` guard** in the real nickname
`limit` block. It reads as belt-and-braces next to the ladders, but the ladders are
going and the guard is staying — the file's own comment explains why (CK3 guarantees no
evaluation order among siblings in a `limit`).

- [ ] **Step 3: Remove the knight toast probe**

In `bc_knight_phase_events.txt`, delete the comment at `:103-107` and the
`debug_log = "BC: toast body ran (knight breach)"` at `:108`. This question is superseded
by DIAG Q4 in task 14, which asks it properly.

- [ ] **Step 4: Verify nothing else was caught**

```bash
cd /d/ck3/mods/battle_chronicles && grep -rn "DIAG\|toast body ran" .
```

Expected: **no output.**

- [ ] **Step 5: Validate**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
```

Expected: exit 0.

- [ ] **Step 6: Commit**

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

- [ ] **Step 1: Temporarily weaken the gate**

In `bc_chronicles.0091`, change the nickname `limit` block to fire on any notable win:

```
if = {
	limit = {
		has_any_nickname = no
	}
	save_scope_as = bc_named_commander
	bc_aftermath_nickname_effect = yes
}
```

**Leave `save_scope_as = bc_named_commander` exactly where it is.** The effect's toast
uses it for `left_icon`, and a scripted effect does not rebind ROOT — ROOT here is the
combat side, which `left_icon` does not accept.

Mark it so it cannot be forgotten:

```
# TEMPORARY — force-execution probe, task 2. REVERT BEFORE TASK 4.
```

- [ ] **Step 2: Deploy and run**

```bash
cd /d/ck3/tools && python ck3.py validate --strict && python ck3.py deploy
```

Then launch the game and fight until you win a battle that logs `BC: win notable`.

- [ ] **Step 3: Confirm the path executed**

```bash
cd /d/ck3/tools && python ck3.py probe "nickname awarded"
```

Expected: **exit 0 with at least one hit.**

Then sweep for errors:

```bash
python ck3.py probe "bc_"
```

Expected: **exit 1** (nothing matched — no `bc_` error was logged). If it exits 0, read
what it found; the nickname path is broken and must be fixed here, before task 4, which
is the entire reason this task exists.

- [ ] **Step 4: Confirm the toast was addressed correctly**

Check whether the toast appeared in-game. If the commander who won the name was AI and
no toast appeared on his liege, that is a real bug in the shipped routing — record it
and fix it now.

- [ ] **Step 5: Revert the gate**

Restore the original `limit` block verbatim:

```
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
```

- [ ] **Step 6: Verify the temporary marker is gone**

```bash
cd /d/ck3/mods/battle_chronicles && grep -rn "TEMPORARY" .
```

Expected: no output.

- [ ] **Step 7: Commit**

```bash
git add events/bc_events.txt
git commit -m "test: force-execute the nickname path before refactoring it

The gate needs three conditions no observed battle has cleared, so the reward
path had never run. Temporarily reduced to has_any_nickname = no, confirmed the
effect executes and the toast is addressed, then restored the gate verbatim."
```

---

### Task 3: Flatten `bc_cleanup_effect`

Six hand-written guarded removals become a flat list. Family 2 adds four more in plan
2, and a ten-branch copy-paste ladder is where a modifier gets forgotten and leaks past
combat end.

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_scripted_effects.txt:101-115`

- [ ] **Step 1: Confirm the no-op premise**

`remove_character_modifier` on an absent modifier must be a no-op, or flattening
introduces error spam. Verify against shipped code:

```bash
cd /d/ck3 && sed -n '2325,2341p' "/d/SteamLibrary/steamapps/common/Crusader Kings III/game/common/scripted_effects/00_diarchy_scripted_effects.txt"
```

Expected: an unguarded flat list of 16 `remove_character_modifier` lines, of which at
most 4 can ever be held. That is 12 guaranteed no-ops per call, shipped by Paradox, by
design.

- [ ] **Step 2: Replace `bc_cleanup_effect`**

```
# --- cleanup ----------------------------------------------------------------
# Called from the combat-end graders. Without this, momentum earned in one
# battle bleeds into the next 20 days of the war.
#
# FLAT, NOT GUARDED. remove_character_modifier on an absent modifier is a no-op
# — vanilla's own vizierate_remove_extravagance_modifiers_effect
# (00_diarchy_scripted_effects.txt:2325-2341) is an unguarded list of 16 of
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

- [ ] **Step 3: Confirm `bc_clear_faltering_effect` was NOT touched**

```bash
cd /d/ck3/mods/battle_chronicles && grep -n "bc_clear_faltering_effect" -A 16 common/scripted_effects/bc_scripted_effects.txt | head -30
```

Expected: still three **guarded** `if` blocks, unchanged.

**This is load-bearing.** `bc_rally_effect` calls `bc_clear_faltering_effect`
*mid-battle* (`bc_scripted_effects.txt:92-95`). If it were flattened to the same
six-line list, every rally would strip the commander's momentum along with his setback.
The two effects look almost identical and must not be merged.

- [ ] **Step 4: Confirm `bc_cleanup_effect` no longer calls it**

The old `bc_cleanup_effect` opened with `bc_clear_faltering_effect = yes`. The flat list
covers those three modifiers directly, so that call is now redundant and must be gone.

- [ ] **Step 5: Validate and commit**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
cd /d/ck3/mods/battle_chronicles
git add common/scripted_effects/bc_scripted_effects.txt
git commit -m "refactor: flatten bc_cleanup_effect to an unguarded removal list"
```

---

### Task 4: Extract `bc_addressed_toast_effect`

Every award in this expansion needs the same routing: a toast about an AI subject has to
be raised on his liege, because a `send_interface_toast` body does not reliably run for
a character nobody is playing. That routing exists once, buried in the nickname effect.

**Extract the routing, not the toast.** The routing is the `is_ai = no` /
`else_if exists = liege` fork at `bc_scripted_effects.txt:288-297`.
`bc_aftermath_nickname_toast_effect` (`:302-309`) is only the body it calls twice, and
it is **not** reusable as-is because its `left_icon` is hardcoded to
`scope:bc_named_commander`.

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_scripted_effects.txt:242-309`

- [ ] **Step 1: Write the new shared effect**

```
# --- addressed toasts -------------------------------------------------------
#
# A send_interface_toast body only reliably runs for a character a player is
# actually playing, and nearly every commander in the world is AI. A toast about
# an AI subject therefore has to be raised on somebody who might be human.
#
# CALLED ON THE SUBJECT. Tests is_ai on THIS, raises on THIS or on `liege`.
#
# SUBJECT must be a SAVED SCOPE, never `this`. A scripted effect does not rebind
# ROOT, and in the liege arm the scope has already moved by the time left_icon is
# evaluated — so left_icon = $SUBJECT$ only names the right man if the caller
# saved him first.
bc_addressed_toast_effect = {
	if = {
		limit = { is_ai = no }
		send_interface_toast = {
			type = event_toast_effect_good
			title = $TITLE$
			desc = $DESC$
			left_icon = $SUBJECT$
		}
	}
	else_if = {
		limit = { exists = liege }
		liege = {
			send_interface_toast = {
				type = event_toast_effect_good
				title = $TITLE$
				desc = $DESC$
				left_icon = $SUBJECT$
			}
		}
	}
}
```

- [ ] **Step 2: Rewrite `bc_aftermath_nickname_effect` to call it**

Replace its routing fork (`:288-297`) with:

```
	bc_addressed_toast_effect = {
		TITLE = bc_aftermath_nickname_toast
		DESC = bc_aftermath_nickname_toast_desc
		SUBJECT = scope:bc_named_commander
	}
```

Leave the `random_list` of 27 nicknames and the `debug_log = "BC: nickname awarded"`
exactly as they are.

- [ ] **Step 3: Delete `bc_aftermath_nickname_toast_effect`**

It now has no callers.

- [ ] **Step 4: Verify it has no callers**

```bash
cd /d/ck3/mods/battle_chronicles && grep -rn "bc_aftermath_nickname_toast_effect" .
```

Expected: **no output.** (The loc keys `bc_aftermath_nickname_toast` and
`..._desc` survive — they are keys, not the effect.)

- [ ] **Step 5: Validate and commit**

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

- [ ] **Step 1: Create the new file with a header**

```
# Battle Chronicles - the reward path.
#
# Everything here runs at COMBAT END, from the graders in bc_aftermath_events.txt.
# Nothing here runs during a battle. That is the split from
# bc_scripted_effects.txt, which is the opposite: momentum, cooldowns and
# chronicle pacing, all of which run mid-battle and none of which persists.
#
# ROOT in every caller is a COMBAT SIDE, not a character. Effects here that need
# to name a character in a toast take it as a saved scope.
```

- [ ] **Step 2: Move four effects across, verbatim**

Cut from `bc_scripted_effects.txt` and paste into `bc_reward_effects.txt`, **with their
comment blocks intact** — the comments carry the reasoning for `random_memory` over
`scope:new_memory`, for `give_nickname` over `set_nickname_effect`, and for the AGOT
nickname dependency, none of which is re-derivable:

1. `bc_battle_memory_effect`
2. `bc_notable_battle_counter_effect`
3. `bc_aftermath_nickname_effect`
4. `bc_addressed_toast_effect` (from task 4)

- [ ] **Step 3: Confirm nothing was lost or duplicated**

```bash
cd /d/ck3/mods/battle_chronicles
for e in bc_battle_memory_effect bc_notable_battle_counter_effect bc_aftermath_nickname_effect bc_addressed_toast_effect; do
  echo "$e: $(grep -rc "^$e = {" common/scripted_effects/ | grep -v ':0' )"
done
```

Expected: each defined **exactly once**, all four in `bc_reward_effects.txt`.

A duplicate definition is silent in CK3 — one wins and nothing is logged — so this check
is not optional.

- [ ] **Step 4: Validate, check collisions, commit**

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
events on one hook is undefined. Grading reads scratch that cleanup will later clear, so
grading must provably run first. Two events cannot express that. One can, in written
order — CK3 executes sibling effects in the order written.

**Files:**
- Create: `mods/battle_chronicles/events/bc_aftermath_events.txt`
- Modify: `mods/battle_chronicles/events/bc_events.txt` (remove `.0090`, `.0091`, `.0092`)
- Modify: `mods/battle_chronicles/common/on_action/bc_on_actions.txt`

- [ ] **Step 1: Create `bc_aftermath_events.txt`**

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
# NEITHER CARRIES A `trigger`. The old .0090 deliberately had none because it is
# the only caller of bc_cleanup_effect, and putting momentum stripping behind the
# aftermath off switch would leave `advantage +-10` modifiers bleeding twenty days
# into the next battle for any player who touched that setting. The game rule
# therefore lives on an INNER `if` around the grading branch only.
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

- [ ] **Step 2: Delete `.0090`, `.0091` and `.0092` from `bc_events.txt`**

`bc_events.txt` keeps only `bc_chronicles.0001`, `.0002` and `.0003` — the three
player-facing pop-ups. Update its header comment: it currently describes a file holding
both pop-ups and hidden graders, and it now holds only pop-ups.

- [ ] **Step 3: Rewrite the on_action hooks**

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

- [ ] **Step 4: Confirm `.0090` is gone everywhere**

```bash
cd /d/ck3/mods/battle_chronicles && grep -rn "0090" .
```

Expected: **no output.** A dangling reference in an `events = { }` list is a runtime
error, not a validation error.

- [ ] **Step 5: Validate, index, conflicts**

```bash
cd /d/ck3/tools && python ck3.py validate --strict && python ck3.py index && python ck3.py conflicts
```

Expected: all exit 0.

- [ ] **Step 6: Commit**

```bash
cd /d/ck3/mods/battle_chronicles
git add events/ common/on_action/bc_on_actions.txt
git commit -m "refactor: consolidate the three combat-end events into two graders

Not for efficiency — the graders still iterate every_side_knight twice. The order
between separate events on one hook is undefined, and grading must provably run
before cleanup touches the same state. One event per hook expresses that in
written order; two could not. The game rule moves to an inner if so that momentum
stripping does not end up behind the aftermath off switch."
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

- [ ] **Step 1: Create the file with its header**

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

- [ ] **Step 2: Write `bc_battle_open_effect`**

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
bc_battle_open_effect = {
	# Housekeeping for C, which does not ship until plan 4. Kept here because this
	# is the ONE effect context guaranteed to run at every phase event: both
	# named read sites for bc_nemesis are pure TRIGGER contexts, and no effect
	# runs in a trigger, so a "wipe on failed read" rule is unimplementable.
	#
	# It lags the read by one phase event — is_valid runs before effect — and that
	# is harmless: the read guard is `exists` PLUS `is_alive`, and CK3 keeps dead
	# characters as real objects, so is_alive on one is a clean `no`, not an
	# error. This wipe stops the variable living on a commander forever; it is not
	# what makes the read safe.
	if = {
		limit = {
			exists = var:bc_nemesis
			NOT = { var:bc_nemesis = { is_alive = yes } }
		}
		remove_variable = bc_nemesis
		remove_variable = bc_nemesis_losses
	}

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

**On `?=` for the foe:** a side can be leaderless. The variable is then simply left
unset and C never arms for that battle, which is correct.

**Note the `save_scope_as` indirection.** `set_variable value =` needs a resolvable
target; reaching through `?=` and saving first keeps the write out of the arm where the
scope does not resolve. Do not collapse it into a single `set_variable` with a `?=` path
— that path is a *scope link*, not a value expression.

- [ ] **Step 3: Validate**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
```

Expected: exit 0. The effect has no callers yet, which is fine and intentional — task 9
wires it.

- [ ] **Step 4: Commit**

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

- [ ] **Step 1: Write the marker first — this is the assertion**

The seam's correctness is proven by one log line per moment carrying the tier it
actually resolved to. Confirm the marker does not exist yet:

```bash
cd /d/ck3/tools && python ck3.py probe "BC: moment"
```

Expected: **exit 1** (no match). This is the failing test.

- [ ] **Step 2: Write the seam**

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

- [ ] **Step 3: Write the ceiling and the style high-water mark**

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
bc_record_effective_tier_effect = {
	if = {
		limit = {
			$TIER$ = decisive
			var:bc_battle_moments >= 5
		}
		bc_write_style_effect = { RANK = 3 KIND = $KIND$ }
		debug_log = "BC: moment decisive"
	}
	else_if = {
		limit = {
			OR = { $TIER$ = decisive  $TIER$ = major }
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
bc_write_style_effect = {
	if = {
		limit = {
			OR = {
				NOT = { exists = var:bc_battle_tier }
				var:bc_battle_tier <= $RANK$
			}
		}
		set_variable = { name = bc_battle_tier value = $RANK$ }
		set_variable = { name = bc_battle_style value = flag:$KIND$ }
	}
}
```

**On the `$TIER$ = decisive` comparison.** CK3 substitutes `$TIER$` textually, so this
resolves to `decisive = decisive`, which is not a valid trigger. **Verify this before
relying on it** — if `validate --strict` rejects it, switch the parameter to a numeric
rank at every call site (`TIER = 1|2|3`) and compare integers, which is unambiguous.
Prefer the numeric form if there is any doubt; the KIND table in the spec maps cleanly
onto 1/2/3.

- [ ] **Step 4: Validate**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
```

Expected: exit 0. **If it complains about the `$TIER$` comparison, take the numeric-rank
branch above now** rather than deferring it — every call site in tasks 9-11 depends on
which form is chosen.

- [ ] **Step 5: Commit**

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

- [ ] **Step 1: Add `bc_battle_open_effect` to all seven**

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

- [ ] **Step 2: Add seam calls to the four events with no pop-up branch**

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

- [ ] **Step 3: Add seam calls to the three events with a pop-up branch**

These fire the seam **only in the `else` branch**, the toast branch. The pop-up branch's
seam call lives in the option (task 10), because in that branch the option *is* the
outcome.

| event | `else` branch call |
|---|---|
| `bc_banner_falls` | `bc_record_moment_effect = { TIER = major KIND = wild SWING = down }` |
| `bc_rally_the_line` | `bc_record_moment_effect = { TIER = minor KIND = ordered SWING = up }` |
| `bc_van_breaks_through` | `bc_record_moment_effect = { TIER = major KIND = bloodied SWING = up }` |

- [ ] **Step 4: Verify every effect block was reached**

```bash
cd /d/ck3/mods/battle_chronicles
grep -c "bc_battle_open_effect = yes" common/combat_phase_events/bc_commander_phase_events.txt
grep -c "bc_record_moment_effect" common/combat_phase_events/bc_commander_phase_events.txt
```

Expected: **7** and **7**.

- [ ] **Step 5: Validate and commit**

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

- [ ] **Step 1: Add one seam call per option**

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

- [ ] **Step 2: Do NOT add `bc_battle_open_effect` here**

A pop-up is raised by a phase event that has already run it. Adding it here would be a
no-op at best; at worst an implementer would reach for a combat scope that does not exist
and write a silently-failing line. `bc_events.txt:10-12` records the invariant.

- [ ] **Step 3: Verify the count**

```bash
cd /d/ck3/mods/battle_chronicles && grep -c "bc_record_moment_effect" events/bc_events.txt
```

Expected: **8**.

- [ ] **Step 4: Validate and commit**

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

- [ ] **Step 1: Read this before editing — one real behaviour change**

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

- [ ] **Step 2: Add `bc_battle_open_effect` to all three**

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

- [ ] **Step 3: Add the seam calls**

| event | call | placement |
|---|---|---|
| `bc_knight_holds_the_breach` | `{ TIER = major KIND = entrenched SWING = up }` | in the `side_commander ?=` block, after `bc_momentum_minor_effect` |
| `bc_knight_shames_himself` | `{ TIER = minor KIND = wild SWING = down }` | in the `side_commander ?=` block, after `bc_faltering_minor_effect` |
| `bc_shieldbrother_forged` | `{ TIER = minor KIND = ordered SWING = up }` | **inside `if = { limit = { exists = scope:bc_shieldbrother } }`**, in a `side_commander ?=` block |

The third placement is load-bearing: outside that `if`, the seam would record a moment
for an event that produced no story, inflating `bc_battle_moments` and pushing the
escalation ladder up on nothing.

- [ ] **Step 4: Verify no `bc_` variable can reach a knight**

```bash
cd /d/ck3/mods/battle_chronicles
grep -n "bc_record_moment_effect\|bc_battle_open_effect" common/combat_phase_events/bc_knight_phase_events.txt
```

Expected: **6 hits, every one of them indented inside a `side_commander ?=` block.**
Read the surrounding lines and confirm it by eye. A seam call that escapes that block
writes scratch onto a knight, which is the failure mode Section 1 of the spec exists to
prevent and which nothing at runtime will report.

- [ ] **Step 5: Validate and commit**

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

Six scratch variables now exist. Nothing removes them, so right now they leak into every
subsequent battle.

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_ledger_effects.txt`
- Modify: `mods/battle_chronicles/events/bc_aftermath_events.txt`

- [ ] **Step 1: Write the clearing effect**

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

- [ ] **Step 2: Call it LAST in both graders, OUTSIDE the game-rule gate**

In both `bc_chronicles.0091` and `.0092`, as the final statement of `immediate`:

```
		side_commander ?= {
			bc_clear_scratch_effect = yes
		}
```

- [ ] **Step 3: Confirm the placement by eye — this is the whole task**

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

- [ ] **Step 4: Validate and commit**

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

- [ ] **Step 1: Add the hook**

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

- [ ] **Step 2: Do not add anything else to this file**

No `effect = { }`. The header comment records that the engine keeps exactly one
`effect` per on_action, chosen by alphabetical filename within `common/on_action`, and
that a mod loading dead last still loses to `combat_on_actions.txt`. This exact bug ate a
probe run on 2026-08-12.

- [ ] **Step 3: Validate**

```bash
cd /d/ck3/tools && python ck3.py validate --strict
```

Expected: exit 0. `bc_chronicles.0900` does not exist yet — task 14 writes it. **Do not
deploy between this task and the next**; a dangling event reference in an `events = { }`
list is a runtime error.

- [ ] **Step 4: Commit**

```bash
cd /d/ck3/mods/battle_chronicles
git add common/on_action/bc_on_actions.txt
git commit -m "feat: hook on_combat_start, which is unclaimed in the loaded playset"
```

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
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_reward_effects.txt` (Q4)

- [ ] **Step 1: Q2 — does a `scope = combat` event work at all?**

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

- [ ] **Step 2: Q1 — trait census**

In `bc_chronicles.0091`'s `side_commander ?=` block, as a four-rung ladder. B gates on
`number_of_commander_traits < 3`; if the median commander already holds 3, B is dead on
arrival, the same way `has_any_nickname = no` disqualified 3 of 4 sampled AGOT commanders.

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

- [ ] **Step 3: Q3 — subdivide the `under 5k` bucket**

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

- [ ] **Step 4: Q4 — does a toast body run for an AI subject?**

The whole of `bc_addressed_toast_effect` rests on the answer being no. The claim is
well-supported but under-evidenced: the mod's own comments hedge with "only *reliably*
runs", and **vanilla puts real state inside toast bodies on AI-reachable paths** —
`add_legitimacy = minor_legitimacy_loss` at `combat_on_actions.txt:587`, inside
`side_primary_participant`, which is usually AI.

In `bc_addressed_toast_effect`, add a marker outside the toast and one inside it, in the
`is_ai` arm that is **not** taken — i.e. instrument the liege arm:

```
	else_if = {
		limit = { exists = liege }
		debug_log = "BC: DIAG Q4 liege arm entered"
		liege = {
			send_interface_toast = {
				type = event_toast_effect_good
				title = $TITLE$
				desc = $DESC$
				left_icon = $SUBJECT$
				debug_log = "BC: DIAG Q4 toast body ran on liege"
			}
		}
	}
```

If "entered" appears without "toast body ran", the routing rule is confirmed and every
award in plans 3-5 must stay outside its toast.

- [ ] **Step 5: Q5 — do the vanilla terrain keys resolve in Westeros?**

Plan 3's terrain traits read plain `terrain =` keys. **AGOT deliberately abandoned them
in one place**: `00_martial_lifestyle_effects.txt:45-52` comments out
`terrain = desert / desert_mountains / oasis / drylands` in favour of
`agot_is_desert_terrain = yes`, and `:65-66` does the same for `terrain = jungle`. It did
*not* do this in `commander_trait_leveling_leveling_effect`, which is where plan 3's table
comes from — so the citation is sound, but `desert_warrior` and `jungle_stalker` may be
unreachable in a Westeros playset.

In both graders, inside the `exists = scope:bc_battle_province` block:

```
					scope:bc_battle_province = {
						if = {
							limit = { terrain = jungle }
							debug_log = "BC: DIAG Q5 terrain jungle"
						}
						else_if = {
							limit = {
								OR = {
									terrain = drylands
									terrain = desert
									terrain = desert_mountains
									terrain = oasis
								}
							}
							debug_log = "BC: DIAG Q5 terrain desert"
						}
						else_if = {
							limit = {
								OR = { terrain = forest  terrain = taiga }
							}
							debug_log = "BC: DIAG Q5 terrain forest"
						}
						else_if = {
							limit = {
								OR = { terrain = hills  terrain = mountains  terrain = wetlands }
							}
							debug_log = "BC: DIAG Q5 terrain rough"
						}
						else_if = {
							limit = {
								OR = { terrain = farmlands  terrain = plains  terrain = steppe }
							}
							debug_log = "BC: DIAG Q5 terrain open"
						}
						else = {
							debug_log = "BC: DIAG Q5 terrain NONE MATCHED"
						}
					}
```

The `NONE MATCHED` arm is the important one: it is how a terrain key the mod does not
know about announces itself.

- [ ] **Step 6: Validate, index, conflicts, deploy**

```bash
cd /d/ck3/tools && python ck3.py validate --strict && python ck3.py index && python ck3.py conflicts && python ck3.py deploy
```

Expected: all exit 0.

- [ ] **Step 7: Commit**

```bash
cd /d/ck3/mods/battle_chronicles
git add events/ common/scripted_effects/bc_reward_effects.txt
git commit -m "test: add the five-question DIAG pass

Each question independently invalidates a decision in a later plan. All are
trigger ladders logging string constants — debug_log does not interpolate values.
Q3 reads a trigger ladder rather than bc_battle_size so it measures the world
rather than the mod."
```

---

### Task 15: Run it

**This is the runtime checkpoint. Everything before it is unproven.**

- [ ] **Step 1: Fight battles**

Launch the game. Fight several battles of visibly different sizes, and win at least one
and lose at least one. Let at least one battle run long enough to produce five or more
moments, so the `decisive` rung of the escalation ladder is exercised.

- [ ] **Step 2: Sweep for errors first**

```bash
cd /d/ck3/tools && python ck3.py probe "bc_"
```

Expected: **exit 1** — nothing matched, so no `bc_` error was logged.

If it exits 0, **stop and fix before reading any marker.** A missing-variable error
repeated once per knight per combat is the highest-volume failure this design can
produce, and every number below would be measured against a broken build.

- [ ] **Step 3: Read the seam markers**

```bash
python ck3.py probe "BC: moment"
```

Expected: minor markers common, major markers present, decisive markers rare or absent in
a short session. **If `decisive` appears in a battle with fewer than five moments the
ceiling is inverted** — check the `>=` in `bc_record_effective_tier_effect`.

- [ ] **Step 4: Answer the five questions**

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
| Q4 "entered" without "toast body ran" | routing rule confirmed. If **both** appear, `bc_addressed_toast_effect` is unnecessary and plans 3-5 simplify |
| Q5 `NONE MATCHED` appears | an unhandled terrain exists — find it before plan 3 |
| Q5 desert/jungle never appear | drop `desert_warrior` and `jungle_stalker` from plan 3 |

- [ ] **Step 5: Confirm scratch does not leak**

The single most important runtime property of this plan. In the console, on a commander
who has just finished a battle:

```
debug_show_variables
```

Expected: **no `bc_battle_*` variable present.** If any remain, task 12's placement is
wrong — check that clearing is outside the game-rule gate.

- [ ] **Step 6: Write the results down**

Append the counts to the spec under a new `## DIAG results 2026-08-13` heading. This is a
workspace commit, not a mod commit:

```bash
cd /d/ck3
git add docs/specs/2026-08-13-battle-chronicles-expansion-design.md
git commit -m "docs: record DIAG pass results"
```

The numbers are the only record of how the later plans' thresholds were chosen, and the
existing calibration header in `bc_scripted_triggers.txt` exists because the last set was
nearly lost.

---

### Task 16: Remove the DIAG pass

Diagnostics that survive their question become noise that hides the next one. This is
exactly what task 1 had to clean up.

**Files:**
- Delete: `mods/battle_chronicles/events/bc_diag_events.txt`
- Modify: `mods/battle_chronicles/events/bc_aftermath_events.txt`
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_reward_effects.txt`
- Modify: `mods/battle_chronicles/common/on_action/bc_on_actions.txt`

- [ ] **Step 1: Remove Q1, Q3, Q4 and Q5**

Strip every `debug_log = "BC: DIAG ..."` and the ladders that exist only to emit them.

**Keep** the permanent instrumentation: `"BC: combat end cleanup"`,
`"BC: win notable"` / `"BC: win not notable"`, `"BC: lose notable"` /
`"BC: lose not notable"`, `"BC: nickname awarded"`, and the three `"BC: moment ..."`
markers from the seam. The seam markers stay — they are how every later plan proves its
call sites fire.

- [ ] **Step 2: Decide what happens to the `on_combat_start` hook**

Two cases:

- **Q2 passed.** Keep the hook and keep `bc_chronicles.0900`, but strip its body down to
  a single `debug_log = "BC: combat start"`. Plan 5 replaces the body with the eve
  dispatcher. Note in the file that the event is a placeholder.
- **Q2 failed.** Delete the `on_combat_start` block from `bc_on_actions.txt` and delete
  `bc_diag_events.txt` entirely. Record the failure in the spec — plan 5's eve section
  needs rewriting before it can be executed.

- [ ] **Step 3: Verify**

```bash
cd /d/ck3/mods/battle_chronicles && grep -rn "DIAG" .
```

Expected: **no output.**

- [ ] **Step 4: Full verification sweep**

```bash
cd /d/ck3/tools && python ck3.py validate --strict && python ck3.py index && python ck3.py conflicts && python ck3.py deploy
```

Expected: all exit 0.

- [ ] **Step 5: Commit**

```bash
cd /d/ck3/mods/battle_chronicles
git add -A
git commit -m "chore: remove the DIAG pass now that all five questions are answered

Kept the permanent instrumentation and the three seam markers — every later plan
proves its call sites through those."
```

---

## Done when

- [ ] Three combat-end events are two, and grading provably runs before cleanup.
- [ ] `bc_addressed_toast_effect` exists and the nickname path has executed at runtime.
- [ ] All eighteen moment call sites reach `bc_record_moment_effect`.
- [ ] A battle's log shows N moment markers with tiers that respect the ceiling.
- [ ] No `bc_` variable exists on any commander at the start of a new battle.
- [ ] No `bc_` variable exists on any knight, ever.
- [ ] `validate --strict`, `index`, `conflicts` and `deploy` all exit 0.
- [ ] `probe "bc_"` exits **1**.
- [ ] All five DIAG answers are recorded in the spec.
- [ ] No DIAG marker remains in the mod.

## What comes next

| plan | ships | gated on |
|---|---|---|
| 2 | family-2 modifiers, pacing curve | Q3 |
| 3 | B — reputation | Q1, Q4 |
| 4 | C — rivalry | this plan |
| 5 | D — eve, wipe, dead knights | Q2 for the eve only |
| 6 | family 3 — wounds | plan 2 |

Plans 2, 3 and 5 all unblock on the same DIAG run and may ship in any order. Plan 4 needs
only this one, because `bc_battle_foe` is written by `bc_battle_open_effect` and not by
the eve. Only plan 6 is strictly downstream of another feature plan.
