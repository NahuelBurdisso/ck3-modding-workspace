# Battle Chronicles Aftermath Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Grade every battle at combat end, give each surviving knight on a notable field a forty-year memory of that province, and name the commander who won his third notable field from AGOT's own heroic nickname pool.

**Architecture:** Two new hidden `combat_side` events, `bc_chronicles.0091` on `on_combat_end_winner` and `.0092` on `on_combat_end_loser`, hooked through the existing `events = { }`-only on_action file. Both run the same `calc_true_if` grading trigger, log calibration buckets on every battle whether or not it clears the bar, and walk `every_side_knight` writing a memory. Only the winner's event increments the commander's cumulative counter and awards the nickname. Everything is additive to files the mod already owns, so the zero-collision property holds by construction.

**Tech Stack:** CK3 script (Jomini), AGOT 1.19.0.6 playset, `python tools/ck3.py` workspace CLI (`validate`, `deploy`, `conflicts`, `probe`, `launch`).

**Spec:** `docs/specs/2026-08-12-battle-chronicles-aftermath-design.md`

---

## How verification works here

CK3 script has no unit test framework, so the TDD loop is replaced by a two-layer check:

1. **Static, per task:** `python tools/ck3.py validate battle_chronicles` — must report `0 errors, 0 warnings` after every task. This is the "run the test" step.

   **Know what it does not catch.** It checks brace balance, the UTF-8 BOM, malformed localization lines, duplicate top-level definitions and stray root directories. It does **not** resolve references. `tools/ck3lib/validate.py:37` limits its loc cross-check to `LOC_EXPECTED = {common/traits, common/decisions, common/character_interactions}`, and even that is gated behind `--strict`. None of the categories this plan touches is in that set, so a typo in any of the 18 new localization keys passes every task silently and surfaces as a raw key name in game. Every task that adds a `desc = `, `title = ` or `type = ` reference therefore carries an explicit `ck3.py loc` check for each key it added.

   **Those checks must reindex first.** `ck3.py loc` reads the sqlite index at `index/ck3.sqlite3` (`tools/ck3lib/index.py:193-198, 231-242`), not the files on disk, and the index is only rebuilt by `ck3.py index`. Without a reindex every newly added key reports as missing and the check is noise. Each loop below therefore opens with `python tools/ck3.py index -q`. `ck3.py conflicts` reads the same index (`tools/ck3lib/index.py:245+`), so Task 9 reindexes before it too — otherwise it reports the file set as it stood *before* this plan's tasks ran, which is precisely the set with no collisions. It is also why Task 11 uses `grep` rather than `ck3.py find`.
2. **Dynamic, once at the end:** a single game run (Task 10). A restart costs about seven minutes, so the run is instrumented up front to answer every open question in one pass. `debug_log` markers are counted with `python tools/ck3.py probe 'BC:'`.

Tasks 1–9 build and land the feature. Task 10 runs it. Task 11 sets the real thresholds from what Task 10 measured and strips the instrumentation.

**Do not skip the marker code.** Thresholds in Tasks 3–4 are vanilla's numbers used as a placeholder; they are expected to be wrong for Westerosi host sizes. The markers are the only thing that will say by how much.

All paths below are relative to `D:/ck3`. All script files are tab-indented — match the surrounding file.

**The mod is its own git repository.** `D:/ck3/.gitignore` ignores `mods/`, so `git add mods/battle_chronicles/...` from the workspace root fails outright. Every commit step below therefore runs from `D:/ck3/mods/battle_chronicles` with paths relative to it. The plan document itself lives in the workspace repo and is committed separately.

---

## File structure

| Path | Responsibility | Change |
|---|---|---|
| `mods/battle_chronicles/common/game_rules/bc_game_rules.txt` | player-facing tuning switches | add `bc_aftermath` |
| `mods/battle_chronicles/common/character_memory_types/bc_memories.txt` | memory type definitions | add 2 types |
| `mods/battle_chronicles/common/script_values/bc_script_values.txt` | multiplied thresholds a trigger cannot express | add 2 live + 4 calibration values |
| `mods/battle_chronicles/common/scripted_triggers/bc_scripted_triggers.txt` | every situation gate | add the grading trigger |
| `mods/battle_chronicles/common/scripted_effects/bc_scripted_effects.txt` | every shared effect | add 3 effects |
| `mods/battle_chronicles/events/bc_events.txt` | all events | add `.0091`, `.0092` |
| `mods/battle_chronicles/common/on_action/bc_on_actions.txt` | hooks, `events = { }` only | add 2 entries |
| `mods/battle_chronicles/localization/english/bc_l_english.yml` | all display text | add 18 keys (8 + 8 + 2) |

No new files. No new nickname file — the nickname keys are AGOT's and are referenced, not redefined.

---

### Task 1: The game rule

Built first because everything else reads it, and because a game rule is baked into every save made with it — it has to ship with the feature, never be added afterwards.

**Files:**
- Modify: `mods/battle_chronicles/common/game_rules/bc_game_rules.txt` (append after line 35)
- Modify: `mods/battle_chronicles/localization/english/bc_l_english.yml` (append after line 42, inside the `--- game rules ---` block)

- [x] **Step 1: Add the rule**

Append to `bc_game_rules.txt`:

```
bc_aftermath = {
	categories = { flavor }

	default = bc_aftermath_default

	bc_aftermath_off = {}
	bc_aftermath_default = {}
	bc_aftermath_generous = {}
}
```

Option keys repeat the rule name because that is how the other two rules in this file are written and how `has_game_rule = <option>` reads them.

- [x] **Step 2: Add the eight localization keys**

Insert into `bc_l_english.yml` immediately after the `setting_bc_swing_dramatic_desc` line (line 42), before the `# --- commander chronicles ---` header. Note the single leading space on every entry — the file's syntax is exact.

```
 rule_bc_aftermath:0 "Battle Chronicles: Aftermath"
 rule_bc_aftermath_desc:0 "Whether a battle worth remembering leaves a mark on the men who fought it. Knights carry a memory of the field; a commander who wins several may be named for them."
 setting_bc_aftermath_off:0 "Off"
 setting_bc_aftermath_off_desc:0 "Battles leave nothing behind. The mod behaves as it did before this was added, and AGOT's own nickname system is left entirely alone."
 setting_bc_aftermath_default:0 "Default"
 setting_bc_aftermath_default_desc:0 "A battle must stand out in at least two ways — its size, its cost, the odds against, or how completely it was decided. Most fields do not."
 setting_bc_aftermath_generous:0 "Generous"
 setting_bc_aftermath_generous_desc:0 "One reason is enough. Notable fields and the names won on them become common."
```

- [x] **Step 3: Verify**

Run: `python tools/ck3.py validate battle_chronicles`
Expected: `0 errors, 0 warnings`

The validator will not check that these keys exist, so check them by hand:

```bash
cd /d/ck3 && python tools/ck3.py index -q && for k in rule_bc_aftermath rule_bc_aftermath_desc setting_bc_aftermath_off setting_bc_aftermath_off_desc setting_bc_aftermath_default setting_bc_aftermath_default_desc setting_bc_aftermath_generous setting_bc_aftermath_generous_desc; do python tools/ck3.py loc "$k" >/dev/null 2>&1 || echo "MISSING $k"; done
```

Expected: no output.

- [x] **Step 4: Commit**

```bash
cd /d/ck3/mods/battle_chronicles && git add common/game_rules/bc_game_rules.txt localization/english/bc_l_english.yml && git commit -m "feat(bc): add bc_aftermath game rule

Ships with the feature rather than after it: a modded game rule is baked
into every save made with it, so adding one later cannot reach saves that
already exist."
```

---

### Task 2: The two memory types

**Files:**
- Modify: `mods/battle_chronicles/common/character_memory_types/bc_memories.txt` (append after line 45)
- Modify: `mods/battle_chronicles/localization/english/bc_l_english.yml` (append in the `--- memories ---` block, after the `bc_shieldbrother_memory_desc_third_perspective` line)

- [x] **Step 1: Add both types**

Append to `bc_memories.txt`:

```

# --- the battle memory ------------------------------------------------------
#
# One field, remembered by every knight who stood on it. Two types rather than
# one so the polarity token in `categories` is right and the localization does
# not have to branch on the outcome.
#
# NO `participants` block on purpose. This memory is about a place, not a
# person - vanilla's `became_incapable_due_to_battle_concussion` is the
# precedent for a participant-free type carrying `battle_location`.
#
# `duration` is forty years and MUST NOT be `memory_default_duration`. The
# default is `value = 5` plus bonuses that only rulers, duchy-tier holders and
# the player's own circle collect, so a landless AI knight - precisely the man
# this feature exists for - would score 5 and forget the field inside five
# years. Same decision, same reason, as bc_shieldbrother_memory above.

bc_battle_memory_won = {
	categories = { positive martial war battle }
	icon = "battle.dds"

	description = {
		random_valid = {
			desc = bc_battle_memory_won_desc
		}
	}

	second_perspective_description = {
		random_valid = {
			desc = bc_battle_memory_won_desc_second_perspective
		}
	}

	third_perspective_description = {
		random_valid = {
			desc = bc_battle_memory_won_desc_third_perspective
		}
	}

	duration = {
		years = 40
	}
}

bc_battle_memory_lost = {
	categories = { negative martial war battle }
	icon = "battle.dds"

	description = {
		random_valid = {
			desc = bc_battle_memory_lost_desc
		}
	}

	second_perspective_description = {
		random_valid = {
			desc = bc_battle_memory_lost_desc_second_perspective
		}
	}

	third_perspective_description = {
		random_valid = {
			desc = bc_battle_memory_lost_desc_third_perspective
		}
	}

	duration = {
		years = 40
	}
}
```

- [x] **Step 2: Add the eight localization keys**

Append to the `--- memories ---` block of `bc_l_english.yml`:

```

# The title reads back the province with GetNameNoTooltip and the description
# with GetName. Vanilla's own battle-memory titles do the same: a title is
# already inside a memory-list entry, and GetName there nests a tooltip in a
# tooltip. `battle_location` is set on the memory by bc_battle_memory_effect.

 bc_battle_memory_won:0 "won a battle at [ROOT.Var('battle_location').GetProvince.GetNameNoTooltip]"
 bc_battle_memory_won_desc:0 "I stood in the line at [ROOT.Var('battle_location').GetProvince.GetName], and we were the ones still standing on it"
 bc_battle_memory_won_desc_second_perspective:0 "you stood in the line at [ROOT.Var('battle_location').GetProvince.GetName], and you were the ones still standing on it"
 bc_battle_memory_won_desc_third_perspective:0 "[owner.GetName] stood in the line at [ROOT.Var('battle_location').GetProvince.GetName], and was among those still standing on it"

 bc_battle_memory_lost:0 "lost a battle at [ROOT.Var('battle_location').GetProvince.GetNameNoTooltip]"
 bc_battle_memory_lost_desc:0 "I stood in the line at [ROOT.Var('battle_location').GetProvince.GetName], and the line did not hold"
 bc_battle_memory_lost_desc_second_perspective:0 "you stood in the line at [ROOT.Var('battle_location').GetProvince.GetName], and the line did not hold"
 bc_battle_memory_lost_desc_third_perspective:0 "[owner.GetName] stood in the line at [ROOT.Var('battle_location').GetProvince.GetName], and the line did not hold"
```

- [x] **Step 3: Verify**

Run: `python tools/ck3.py validate battle_chronicles`
Expected: `0 errors, 0 warnings`

Then check all eight keys resolve — six of these are the `desc = ` targets inside `bc_memories.txt`, and a typo in one of those renders as a raw key in the memory list with nothing else to warn you:

```bash
cd /d/ck3 && python tools/ck3.py index -q && for k in bc_battle_memory_won bc_battle_memory_won_desc bc_battle_memory_won_desc_second_perspective bc_battle_memory_won_desc_third_perspective bc_battle_memory_lost bc_battle_memory_lost_desc bc_battle_memory_lost_desc_second_perspective bc_battle_memory_lost_desc_third_perspective; do python tools/ck3.py loc "$k" >/dev/null 2>&1 || echo "MISSING $k"; done
```

Expected: no output.

- [x] **Step 4: Commit**

```bash
cd /d/ck3/mods/battle_chronicles && git add common/character_memory_types/bc_memories.txt localization/english/bc_l_english.yml && git commit -m "feat(bc): add battle memory types for won and lost fields

Forty years, not memory_default_duration - that default resolves to 5 for
a landless knight, which is the whole population this is for."
```

---

### Task 3: The odds script values

A trigger can compare one `side_max_army_size` against another but cannot multiply one first, so the threshold has to come from a script value. Four of the six added here are calibration-only and are deleted in Task 11.

**Files:**
- Modify: `mods/battle_chronicles/common/script_values/bc_script_values.txt` (append after line 26; also amend the file header)

- [x] **Step 1: Amend the file header**

The header currently describes only the two `scope:combat_side`-rooted values. Insert this paragraph on line 17 — the blank line between the last header comment (line 16) and `bc_outnumbered_threshold_value = {` (line 18):

```
# SCOPE WARNING: the two values below are written against `scope:combat_side`
# because they are read from phase events, where that scope exists. The
# aftermath values further down are written against `root`, because they are
# read from a combat_side-scoped event where the side IS root and
# `scope:combat_side` does not exist. Do not copy one style into the other's
# call site.
```

- [x] **Step 2: Add the two live values**

Append to `bc_script_values.txt`:

```

# --- aftermath: how lopsided were the hosts ---------------------------------
#
# Read from bc_chronicles.0091 / .0092, where the combat side is ROOT. The
# `root.` prefix is not decoration. Both call sites put a scope path on the
# left - `enemy_side.side_max_army_size >= bc_our_host_gap_value` - and if the
# engine resolves an unprefixed script value on the right in the LEFT operand's
# scope, this would evaluate as `enemy >= enemy * 1.5`: permanently false, on
# both sides, while still passing the winner-versus-loser symmetry check that
# exists to catch exactly this. That resolution rule is unverified. Anchoring
# means it never has to be known.
#
# multiply MUST stay strictly greater than 1. At exactly 1 the row degenerates
# to "the hosts were not identical", which is true in nearly every battle and
# donates a free calc_true_if point to both sides.
#
# side_max_army_size, not side_army_size or troops_ratio: at combat END a
# current-strength ratio measures the outcome, not the odds. Grand Remembrance
# corroborates the reading by computing casualties as
# `side_max_army_size - side_army_size` (zz_gr_memory_tracking.txt:74).

bc_our_host_gap_value = {
	value = root.side_max_army_size
	multiply = 1.5
}

bc_their_host_gap_value = {
	value = root.enemy_side.side_max_army_size
	multiply = 1.5
}
```

- [x] **Step 3: Add the four calibration values**

Append below. These exist only to bracket the live 1.5 and are deleted in Task 11.

```

# --- CALIBRATION ONLY - DELETE AFTER THE TUNING RUN -------------------------
# Bracket the live 1.5 so the marker ladder in .0091 / .0092 can report where
# the odds actually sit. Nothing but the debug_log ladders reads these.
#
# These are the reason the events also carry a PER-SIDE host size ladder: if
# every battle reports "odds even", these four cannot distinguish "the hosts
# really were matched" from "side_max_army_size does not work on the left of a
# comparison and all three rungs are silently false". The per-side ladder tests
# that construct against plain constants and is the control.

bc_cal_our_host_gap_2x = {
	value = root.side_max_army_size
	multiply = 2.0
}

bc_cal_their_host_gap_2x = {
	value = root.enemy_side.side_max_army_size
	multiply = 2.0
}

bc_cal_our_host_gap_12x = {
	value = root.side_max_army_size
	multiply = 1.2
}

bc_cal_their_host_gap_12x = {
	value = root.enemy_side.side_max_army_size
	multiply = 1.2
}
```

- [x] **Step 4: Verify**

Run: `python tools/ck3.py validate battle_chronicles`
Expected: `0 errors, 0 warnings`

- [x] **Step 5: Commit**

```bash
cd /d/ck3/mods/battle_chronicles && git add common/script_values/bc_script_values.txt && git commit -m "feat(bc): add host-gap script values for battle grading

Anchored to root, unlike the two existing values, which are read from
phase events where scope:combat_side is what exists. Four extra values
bracket the live 1.5 for the calibration run and come out afterwards."
```

---

### Task 4: The grading trigger

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_triggers/bc_scripted_triggers.txt` (amend header lines 6-7; append after line 93)

- [x] **Step 1: Amend the file header**

The header at lines 6-7 currently reads:

```
# All of these assume they are evaluated from a combat phase event, where
# `scope:combat_side` exists. They are not safe anywhere else.
```

Replace with:

```
# All of these assume they are evaluated from a combat phase event, where
# `scope:combat_side` exists. They are not safe anywhere else - EXCEPT
# bc_battle_is_notable_trigger at the bottom of the file, which takes the
# combat side as ROOT and is called from the combat-end events, where
# `scope:combat_side` does not exist. Check which one you are writing.
```

- [x] **Step 2: Add the trigger**

Append to `bc_scripted_triggers.txt`:

```

# --- was this battle worth remembering --------------------------------------
#
# ROOT is the combat side. This is the one trigger in the file that does not
# use scope:combat_side - see the header.
#
# calc_true_if is the engine's own points system and is what vanilla uses for
# this exact question, twice: combat_event.3000 for the map point-of-interest
# and historical_artifacts.0100 for naming an artifact after a battle. Both
# count direct children, so DO NOT wrap any of these rows in a nested scripted
# trigger - a nested trigger counts as one row no matter how many tests it
# holds.
#
# Five substantive rows plus the game rule. The two size rows nest, so the bar
# actually reads "huge, or big plus one other thing". Deliberate: thirty
# thousand men on a field is notable whatever else happened. It also means the
# blood, odds and warscore rows never decide the largest battles, so read their
# calibration ladders against the sub-huge population.
#
# The bar must be SYMMETRIC - both sides must reach the same verdict, or one
# side's knights get a memory of a battle the other side's knights do not.
# num_total_troops and warscore_value are combat-scoped and symmetric for free.
# Blood is made symmetric by the explicit OR across enemy_side. The odds row is
# symmetric because it asks "was either host much larger", not "were we
# outnumbered". The game rule is the same on both sides.
#
# PLACEHOLDER NUMBERS. Every threshold here is vanilla's, used as a starting
# guess. Westerosi hosts are larger than CK3's and these are expected to be too
# low. They are reset from the calibration run, which also replaces this
# comment.

bc_battle_is_notable_trigger = {
	calc_true_if = {
		amount >= 2

		combat = { num_total_troops >= 20000 }
		combat = { num_total_troops >= 30000 }
		OR = {
			percent_enemies_killed >= 75
			enemy_side.percent_enemies_killed >= 75
		}
		OR = {
			enemy_side.side_max_army_size >= bc_our_host_gap_value
			side_max_army_size >= bc_their_host_gap_value
		}
		combat = { warscore_value >= 25 }
		has_game_rule = bc_aftermath_generous
	}
}
```

Note: `side_max_army_size` as a trigger has no script precedent anywhere in vanilla, AGOT or the playset — every shipped occurrence is as a script value operand. It is documented as legal (`python tools/ck3.py api side_max_army_size` lists traits `<, <=, =, !=, >, >=` on scope `combat_side`). Unprecedented, not unsupported. Whether it works is settled by the **per-side host size ladder** in Tasks 6 and 7, not by the odds ladder — every rung of the odds ladder uses the same suspect construct, so if the construct is dead the odds ladder reports `even` on every battle and looks exactly like a world of evenly matched hosts. The per-side ladder compares `side_max_army_size` against plain constants, and the inference runs **one way only**: if that ladder never leaves its `else` while the size ladder shows large battles, the token does not resolve on the left of a comparison, the odds row is dead, and it should be dropped — nothing else depends on it. Leaving the `else` does *not* prove the odds row works, because the odds row also carries an `enemy_side.` prefix and a script value on the right. Those two are separately corroborated: the mod's own `bc_side_is_outnumbered_trigger` already compares a scope path against a script value, and `bc_script_values.txt:7-8` records that shape as verified in game on 2026-08-12.

- [x] **Step 3: Verify**

Run: `python tools/ck3.py validate battle_chronicles`
Expected: `0 errors, 0 warnings`

- [x] **Step 4: Commit**

```bash
cd /d/ck3/mods/battle_chronicles && git add common/scripted_triggers/bc_scripted_triggers.txt && git commit -m "feat(bc): add battle grading trigger

calc_true_if with amount >= 2, matching historical_artifacts.0100. Every
row is symmetric so winner and loser reach the same verdict. Thresholds
are vanilla's numbers as a placeholder until the calibration run."
```

---

### Task 5: The three scripted effects

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_scripted_effects.txt` (append after line 141)
- Modify: `mods/battle_chronicles/localization/english/bc_l_english.yml` (append after the `--- knight chronicles ---` block, before `--- memories ---`)

- [x] **Step 1: Add the memory effect**

Append to `bc_scripted_effects.txt`:

```

# --- aftermath: the knight's memory of the field ----------------------------
#
# Called from inside `every_side_knight`, so THIS is the knight. One effect
# parameterised by $TYPE$ rather than two, matching bc_add_momentum_effect
# above - the won/lost split is a localization decision, not a behavioural one.
#
# random_memory, NOT scope:new_memory. Both scope:new_memory idioms are well
# shipped - twenty-odd sites write it directly, four re-save it into a second
# scope first with a comment calling it "a dark pact with Code" - but every one
# of those twenty-four is a single-character call in an event immediate, an
# option or a toast. NONE is inside an iterator, which is the only place this
# effect is ever called, so none of them proves scope:new_memory rebinds on
# each pass rather than sticking to the first memory created.
#
# random_memory does not care. It searches the memories of the character
# currently in scope, and the newly created one is the only memory of that type
# without battle_location set - every earlier one got the variable when it was
# made. There is no cross-pass scope to rebind and nothing to leak between
# knights. The randomness is nominal: the limit matches exactly one memory.
#
# Direct precedent, from the mod we load under: AGOT's
# death_in_battle_memory_effect (death_management_events.txt:2308-2349) is a
# $TYPE$-parameterised effect that creates a battle memory and sets this same
# battle_location variable this same way.

bc_battle_memory_effect = {
	create_character_memory = {
		type = $TYPE$
	}
	random_memory = {
		limit = {
			has_memory_type = $TYPE$
			NOT = { has_variable = battle_location }
		}
		set_variable = {
			name = battle_location
			value = scope:bc_battle_province
		}
	}
}
```

- [x] **Step 2: Add the counter effect**

Append below:

```

# --- aftermath: the commander's tally ---------------------------------------
#
# Notable battles WON, on side commanders only. Never cleared - that is the
# point, and it is why it lives on commanders rather than on every participant,
# keeping the leak surface to one variable on characters who lead armies.
#
# Distinct from vanilla's combat_event_0001_tracker, which counts CONSECUTIVE
# wins and resets to 0 on any defeat. This one is cumulative: it survives a
# defeat, it just does not grow on one.
#
# The create-or-increment shape is vanilla's, from combat_events.txt:90-107.
# change_variable on a variable that was never set is not safe.

bc_notable_battle_counter_effect = {
	if = {
		limit = { NOT = { exists = var:bc_notable_battles } }
		set_variable = {
			name = bc_notable_battles
			value = 1
		}
	}
	else = {
		change_variable = {
			name = bc_notable_battles
			add = 1
		}
	}
}
```

- [x] **Step 3: Add the nickname effect**

Append below. All 27 entries, transcribed from `agot_nicknames_events.txt:187-213`.

```

# --- aftermath: the name he wins --------------------------------------------
#
# The pool is exactly AGOT's heroic list, all 27 entries at weight 1, with NO
# null entry - the caller's gate has already decided the man deserves a name,
# so this list only decides which. Copying the whole list rather than a
# hand-picked subset keeps the mod out of the business of ruling on which of
# AGOT's names are martial enough, and the keys are REFERENCED, not redefined,
# so the pool tracks AGOT if AGOT changes it.
#
# This is the only place mod script names an AGOT key. The dependency is not
# new - descriptor.mod already declares `dependencies = { "A Game of Thrones" }`.
# The mod's no-hard-dependency stance was always about OPTIONAL playset mods
# such as Seasons of Ice and Fire, which is why the terrain triggers use plain
# vanilla keys.
#
# give_nickname runs OUTSIDE the toast. A send_interface_toast body only
# reliably runs for a character a player is playing, and nearly every commander
# in the world is AI. State first, presentation second - the mod's own rule.
#
# NOT set_nickname_effect: that deliberately overwrites any nickname flagged
# is_bad (00_nickname_effects.txt:8-11), and a Westeros playset is full of
# bad-sounding canon names worth keeping.
#
# left_icon MUST be scope:bc_named_commander, NOT `root`. A scripted effect does
# not rebind ROOT, and the only caller is bc_chronicles.0091, which is
# `scope = combat_side` - so `root` here is the COMBAT SIDE, and left_icon only
# accepts a character, artifact, title, dynasty or house. The caller saves the
# scope. Same reason the phase events use scope:bc_commander / scope:bc_knight.

bc_aftermath_nickname_effect = {
	random_list = {
		1 = { give_nickname = nick_agot_the_warrior }
		1 = { give_nickname = nick_agot_greysteel }
		1 = { give_nickname = nick_agot_fireball }
		1 = { give_nickname = nick_agot_hardstone }
		1 = { give_nickname = nick_agot_breakspear }
		1 = { give_nickname = nick_agot_oakenfist }
		1 = { give_nickname = nick_agot_greatheart }
		1 = { give_nickname = nick_agot_ironheart }
		1 = { give_nickname = nick_agot_the_neveryield }
		1 = { give_nickname = nick_agot_greycloak }
		1 = { give_nickname = nick_agot_longspear }
		1 = { give_nickname = nick_agot_shieldbreaker }
		1 = { give_nickname = nick_agot_shieldsmasher }
		1 = { give_nickname = nick_agot_thunderbolt }
		1 = { give_nickname = nick_agot_the_steelskin }
		1 = { give_nickname = nick_agot_the_woe }
		1 = { give_nickname = nick_agot_the_morningstar }
		1 = { give_nickname = nick_agot_oakenshield }
		1 = { give_nickname = nick_agot_blacksword }
		1 = { give_nickname = nick_agot_widowmaker }
		1 = { give_nickname = nick_agot_bloodborn }
		1 = { give_nickname = nick_agot_starfire }
		1 = { give_nickname = nick_agot_the_windrider }
		1 = { give_nickname = nick_agot_swiftspur }
		1 = { give_nickname = nick_agot_battleborn }
		1 = { give_nickname = nick_agot_swordbiter }
		1 = { give_nickname = nick_agot_the_painter }
	}

	debug_log = "BC: nickname awarded"

	# Field order matches every other toast in the mod.
	send_interface_toast = {
		type = event_toast_effect_good
		title = bc_aftermath_nickname_toast
		desc = bc_aftermath_nickname_toast_desc
		left_icon = scope:bc_named_commander
	}
}
```

- [x] **Step 4: Add the two toast localization keys**

Insert into `bc_l_english.yml` after the `bc_shieldbrother_forged_toast_desc` line, before the `# --- memories ---` header. The text names no number on purpose — `<N>` is retuned in Task 11 and nothing would catch a toast still saying "third" after it moved to five.

```

# --- aftermath --------------------------------------------------------------

 bc_aftermath_nickname_toast:0 "A Name Won on the Field"
 bc_aftermath_nickname_toast_desc:0 "He has won another great field, and enough of them now that men who were not there have started calling him something. It has stuck."
```

- [x] **Step 5: Verify**

Run: `python tools/ck3.py validate battle_chronicles`
Expected: `0 errors, 0 warnings`

Then:

```bash
cd /d/ck3 && python tools/ck3.py index -q && for k in bc_aftermath_nickname_toast bc_aftermath_nickname_toast_desc; do python tools/ck3.py loc "$k" >/dev/null 2>&1 || echo "MISSING $k"; done
```

Expected: no output.

- [x] **Step 6: Commit**

```bash
cd /d/ck3/mods/battle_chronicles && git add common/scripted_effects/bc_scripted_effects.txt localization/english/bc_l_english.yml && git commit -m "feat(bc): add aftermath memory, counter and nickname effects

Memory uses random_memory rather than scope:new_memory because it is the
only one of the three shipped idioms that is iterator-safe by
construction, and the call site is inside every_side_knight."
```

---

### Task 6: The loser's event, `bc_chronicles.0092`

Built before the winner's because it is the smaller of the two — grade, log, write knight memories, nothing else. Get it right, then extend the pattern.

**Files:**
- Modify: `mods/battle_chronicles/events/bc_events.txt` (append after line 159)

- [x] **Step 1: Add the event**

Append to `bc_events.txt`:

```

# ---------------------------------------------------------------------------
# Aftermath, losing side. Reached from on_combat_end_loser.
#
# Same shape as bc_chronicles.0090 and as vanilla's own combat-side graders:
# hidden, scope = combat_side, NO `type =`.
#
# TWO events rather than one because bc_chronicles.0090 fires from both hooks
# and nothing in its body can tell which one invoked it. is_combat_side_pursuing
# is documented as "is this side the winner", but every script use of it in
# vanilla and AGOT is DURING combat, inside is_army_in_combat = yes; its value
# at combat end is unproven. Two events makes the outcome structural instead of
# inferred, and costs nothing.
#
# The grade runs in `immediate`, not in the event trigger, even though the cited
# precedent historical_artifacts.0100 puts its calc_true_if in the trigger. The
# calibration markers below have to fire on EVERY combat end, including the ones
# that fail the bar, or they measure only the battles that already passed. The
# only thing in the trigger is the off switch.
#
# This event does NOT touch bc_notable_battles. The counter is wins only - see
# bc_notable_battle_counter_effect. The two events are not mirror images.
# ---------------------------------------------------------------------------
bc_chronicles.0092 = {
	hidden = yes
	scope = combat_side

	trigger = {
		NOT = { has_game_rule = bc_aftermath_off }
	}

	immediate = {
		# --- CALIBRATION ONLY - DELETE AFTER THE TUNING RUN -----------------
		# Every marker is tagged "lose" because .0091 fires on the same battle
		# and untagged markers would double-count the distribution - and worse,
		# would make the winner-versus-loser comparison impossible. That
		# comparison is the one test that catches an asymmetric bar.
		#
		# Buckets rather than interpolated numbers because `ck3.py probe`
		# tallies repeated markers, and a unique string per battle cannot be
		# counted.
		if = {
			limit = { combat = { num_total_troops >= 40000 } }
			debug_log = "BC: lose size 40k+"
		}
		else_if = {
			limit = { combat = { num_total_troops >= 30000 } }
			debug_log = "BC: lose size 30k"
		}
		else_if = {
			limit = { combat = { num_total_troops >= 20000 } }
			debug_log = "BC: lose size 20k"
		}
		else_if = {
			limit = { combat = { num_total_troops >= 10000 } }
			debug_log = "BC: lose size 10k"
		}
		else_if = {
			limit = { combat = { num_total_troops >= 5000 } }
			debug_log = "BC: lose size 5k"
		}
		else = {
			debug_log = "BC: lose size under 5k"
		}

		if = {
			limit = {
				OR = {
					percent_enemies_killed >= 75
					enemy_side.percent_enemies_killed >= 75
				}
			}
			debug_log = "BC: lose blood 75"
		}
		else_if = {
			limit = {
				OR = {
					percent_enemies_killed >= 50
					enemy_side.percent_enemies_killed >= 50
				}
			}
			debug_log = "BC: lose blood 50"
		}
		else_if = {
			limit = {
				OR = {
					percent_enemies_killed >= 25
					enemy_side.percent_enemies_killed >= 25
				}
			}
			debug_log = "BC: lose blood 25"
		}
		else = {
			debug_log = "BC: lose blood under 25"
		}

		if = {
			limit = { combat = { warscore_value >= 50 } }
			debug_log = "BC: lose warscore 50"
		}
		else_if = {
			limit = { combat = { warscore_value >= 25 } }
			debug_log = "BC: lose warscore 25"
		}
		else_if = {
			limit = { combat = { warscore_value >= 10 } }
			debug_log = "BC: lose warscore 10"
		}
		else = {
			debug_log = "BC: lose warscore under 10"
		}

		if = {
			limit = {
				OR = {
					enemy_side.side_max_army_size >= bc_cal_our_host_gap_2x
					side_max_army_size >= bc_cal_their_host_gap_2x
				}
			}
			debug_log = "BC: lose odds 2x"
		}
		else_if = {
			limit = {
				OR = {
					enemy_side.side_max_army_size >= bc_our_host_gap_value
					side_max_army_size >= bc_their_host_gap_value
				}
			}
			debug_log = "BC: lose odds 1.5x"
		}
		else_if = {
			limit = {
				OR = {
					enemy_side.side_max_army_size >= bc_cal_our_host_gap_12x
					side_max_army_size >= bc_cal_their_host_gap_12x
				}
			}
			debug_log = "BC: lose odds 1.2x"
		}
		else = {
			debug_log = "BC: lose odds even"
		}

		# The CONTROL for the odds ladder above. Every rung up there puts
		# side_max_army_size on the left of a comparison, which has no script
		# precedent anywhere in vanilla, AGOT or the playset. If that construct
		# does not work, all three rungs are silently false and the ladder
		# reports "even" on every battle - indistinguishable from a world of
		# evenly matched hosts. This ladder uses the same construct against
		# plain constants: if it ever leaves the else, the construct works.
		if = {
			limit = { side_max_army_size >= 20000 }
			debug_log = "BC: lose host 20k+"
		}
		else_if = {
			limit = { side_max_army_size >= 10000 }
			debug_log = "BC: lose host 10k"
		}
		else_if = {
			limit = { side_max_army_size >= 5000 }
			debug_log = "BC: lose host 5k"
		}
		else = {
			debug_log = "BC: lose host under 5k"
		}
		# --- end calibration ------------------------------------------------

		if = {
			limit = { bc_battle_is_notable_trigger = yes }
			debug_log = "BC: lose notable"

			combat.location ?= {
				save_scope_as = bc_battle_province
			}

			# The province check is an enclosing if, not part of the limit -
			# it is a property of the battle, and re-asking it once per knight
			# is noise.
			if = {
				limit = { exists = scope:bc_battle_province }
				every_side_knight = {
					limit = {
						# Knights die in the combat that just ended. Vanilla
						# guards its own post-battle knight handling the same
						# way (AGOT combat_events.txt:854, :1028; the
						# vanilla equivalents are :813 and :877).
						is_alive = yes
						# We never give a commander a battle memory - vanilla
						# already gives the loser's commander one, every time,
						# with no random gate. Nothing in the API says whether
						# every_side_knight includes him; this costs nothing if
						# it does not.
						#
						# NOTE, deviation from the spec: the spec writes this
						# as a bare `NOT = { this = root.side_commander }`.
						# trigger_if, not a bare NOT: a side can be leaderless,
						# which is why side_commander and combat.location are
						# reached with ?= everywhere else in this event. A bare
						# comparison against a missing scope is an error-log
						# line for every knight of every leaderless battle.
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
```

- [x] **Step 2: Verify**

Run: `python tools/ck3.py validate battle_chronicles`
Expected: `0 errors, 0 warnings`

- [x] **Step 3: Commit**

```bash
cd /d/ck3/mods/battle_chronicles && git add events/bc_events.txt && git commit -m "feat(bc): add bc_chronicles.0092, aftermath on the losing side

Grades the battle, logs the calibration ladders on every combat end
whether or not the bar is cleared, and gives each surviving knight a
memory of the field. Does not touch the counter - that is wins only."
```

---

### Task 7: The winner's event, `bc_chronicles.0091`

**Files:**
- Modify: `mods/battle_chronicles/events/bc_events.txt` (append after `.0092`)

- [x] **Step 1: Add the event**

Append to `bc_events.txt`. The calibration block is `.0092`'s with every `lose` replaced by `win` and nothing else changed — the ladders must be identical or the comparison is meaningless.

```

# ---------------------------------------------------------------------------
# Aftermath, winning side. Reached from on_combat_end_winner.
#
# Everything .0092 does, plus the two things that only make sense for a winner:
# the cumulative notable-win counter, and the name won on the field.
#
# The counter is incremented BEFORE the nickname check, so <N> counts the
# battle just fought.
# ---------------------------------------------------------------------------
bc_chronicles.0091 = {
	hidden = yes
	scope = combat_side

	trigger = {
		NOT = { has_game_rule = bc_aftermath_off }
	}

	immediate = {
		# --- CALIBRATION ONLY - DELETE AFTER THE TUNING RUN -----------------
		# Identical ladders to .0092, tagged "win". They MUST stay identical:
		# comparing `probe 'BC: win notable'` against `probe 'BC: lose notable'`
		# is the only test that catches an asymmetric bar, and it only works if
		# both sides measure the same thing.
		if = {
			limit = { combat = { num_total_troops >= 40000 } }
			debug_log = "BC: win size 40k+"
		}
		else_if = {
			limit = { combat = { num_total_troops >= 30000 } }
			debug_log = "BC: win size 30k"
		}
		else_if = {
			limit = { combat = { num_total_troops >= 20000 } }
			debug_log = "BC: win size 20k"
		}
		else_if = {
			limit = { combat = { num_total_troops >= 10000 } }
			debug_log = "BC: win size 10k"
		}
		else_if = {
			limit = { combat = { num_total_troops >= 5000 } }
			debug_log = "BC: win size 5k"
		}
		else = {
			debug_log = "BC: win size under 5k"
		}

		if = {
			limit = {
				OR = {
					percent_enemies_killed >= 75
					enemy_side.percent_enemies_killed >= 75
				}
			}
			debug_log = "BC: win blood 75"
		}
		else_if = {
			limit = {
				OR = {
					percent_enemies_killed >= 50
					enemy_side.percent_enemies_killed >= 50
				}
			}
			debug_log = "BC: win blood 50"
		}
		else_if = {
			limit = {
				OR = {
					percent_enemies_killed >= 25
					enemy_side.percent_enemies_killed >= 25
				}
			}
			debug_log = "BC: win blood 25"
		}
		else = {
			debug_log = "BC: win blood under 25"
		}

		if = {
			limit = { combat = { warscore_value >= 50 } }
			debug_log = "BC: win warscore 50"
		}
		else_if = {
			limit = { combat = { warscore_value >= 25 } }
			debug_log = "BC: win warscore 25"
		}
		else_if = {
			limit = { combat = { warscore_value >= 10 } }
			debug_log = "BC: win warscore 10"
		}
		else = {
			debug_log = "BC: win warscore under 10"
		}

		if = {
			limit = {
				OR = {
					enemy_side.side_max_army_size >= bc_cal_our_host_gap_2x
					side_max_army_size >= bc_cal_their_host_gap_2x
				}
			}
			debug_log = "BC: win odds 2x"
		}
		else_if = {
			limit = {
				OR = {
					enemy_side.side_max_army_size >= bc_our_host_gap_value
					side_max_army_size >= bc_their_host_gap_value
				}
			}
			debug_log = "BC: win odds 1.5x"
		}
		else_if = {
			limit = {
				OR = {
					enemy_side.side_max_army_size >= bc_cal_our_host_gap_12x
					side_max_army_size >= bc_cal_their_host_gap_12x
				}
			}
			debug_log = "BC: win odds 1.2x"
		}
		else = {
			debug_log = "BC: win odds even"
		}

		# The control for the odds ladder - see .0092 for why it exists.
		if = {
			limit = { side_max_army_size >= 20000 }
			debug_log = "BC: win host 20k+"
		}
		else_if = {
			limit = { side_max_army_size >= 10000 }
			debug_log = "BC: win host 10k"
		}
		else_if = {
			limit = { side_max_army_size >= 5000 }
			debug_log = "BC: win host 5k"
		}
		else = {
			debug_log = "BC: win host under 5k"
		}
		# --- end calibration ------------------------------------------------

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
						# See .0092 for why this is trigger_if.
						trigger_if = {
							limit = { exists = root.side_commander }
							NOT = { this = root.side_commander }
						}
					}
					bc_battle_memory_effect = { TYPE = bc_battle_memory_won }
				}
			}

			# --- CALIBRATION ONLY - DELETE AFTER THE TUNING RUN -------------
			# Accounts for the notable wins that never reach the commander
			# branch at all. Without this, `nickname awarded` plus the four
			# other `nickname blocked` counts can fall short of `win notable`
			# with no explanation.
			if = {
				limit = { NOT = { exists = side_commander } }
				debug_log = "BC: nickname blocked no commander"
			}
			# --- end calibration --------------------------------------------

			side_commander ?= {
				if = {
					limit = { is_alive = yes }
					# NOTE, deviation from the spec: the spec puts is_alive in
					# the nickname limit only, which would let a commander who
					# died winning still take the tally. It is hoisted here
					# instead because the tally exists solely to gate the
					# nickname and a dead man will never command again, so the
					# difference is unobservable - and one gate is clearer than
					# two.
					bc_notable_battle_counter_effect = yes

					# `exists` is belt and braces. What actually makes the
					# var: read below safe is bc_notable_battle_counter_effect
					# immediately above, which always writes the variable
					# before anything reads it. Do not rely on evaluation
					# order to make it safe - CK3 guarantees no order of
					# evaluation among siblings, in a limit or anywhere else.
					if = {
						limit = {
							has_any_nickname = no
							exists = var:bc_notable_battles
							var:bc_notable_battles >= 3
							# martial, not prowess. This names a man for
							# commanding, and it is the same threshold the mod
							# already uses for its high-martial phase-event
							# bonus. Deliberately NOT AGOT's heroic gate of
							# prowess >= 25 plus bold AI: a man can be the
							# finest field commander in Westeros and a
							# mediocre swordsman, and that is who this is for.
							martial >= 14
						}
						# The toast inside the effect needs a character for
						# left_icon, and a scripted effect does not rebind
						# ROOT - ROOT is still the combat side. Save him here.
						save_scope_as = bc_named_commander
						bc_aftermath_nickname_effect = yes
					}
					# --- CALIBRATION ONLY - DELETE AFTER THE TUNING RUN -----
					# If `probe 'BC: nickname awarded'` comes back zero, these
					# say which gate ate it rather than leaving it unexplained.
					else_if = {
						limit = { has_any_nickname = yes }
						debug_log = "BC: nickname blocked already named"
					}
					else_if = {
						# No `exists` guard needed and none wanted:
						# bc_notable_battle_counter_effect ran unconditionally
						# before this whole chain and guarantees the variable.
						# An `OR = { NOT = { exists } ... }` here would be the
						# unsafe read the comment above warns about, since CK3
						# does not guarantee OR short-circuits.
						limit = { var:bc_notable_battles < 3 }
						debug_log = "BC: nickname blocked count"
					}
					else = {
						debug_log = "BC: nickname blocked martial"
					}
					# --- end calibration ------------------------------------
				}
				# --- CALIBRATION ONLY - DELETE AFTER THE TUNING RUN ---------
				else = {
					debug_log = "BC: nickname blocked dead commander"
				}
				# --- end calibration ----------------------------------------
			}
		}
		else = {
			debug_log = "BC: win not notable"
		}
	}
}
```

- [x] **Step 2: Verify**

Run: `python tools/ck3.py validate battle_chronicles`
Expected: `0 errors, 0 warnings`

- [x] **Step 3: Commit**

```bash
cd /d/ck3/mods/battle_chronicles && git add events/bc_events.txt && git commit -m "feat(bc): add bc_chronicles.0091, aftermath on the winning side

Adds the cumulative notable-win counter and the nickname on top of what
.0092 does. Counter increments before the nickname check so N counts the
battle just fought."
```

---

### Task 8: Wire the hooks

Left until last on purpose. Until this task the events exist and cannot fire, so every earlier task is inert on a live save.

**Files:**
- Modify: `mods/battle_chronicles/common/on_action/bc_on_actions.txt` (lines 17-27)

- [x] **Step 1: Add both entries**

Replace the two blocks with:

```
on_combat_end_winner = {
	events = {
		bc_chronicles.0090
		bc_chronicles.0091
	}
}

on_combat_end_loser = {
	events = {
		bc_chronicles.0090
		bc_chronicles.0092
	}
}
```

Do **not** add an `effect = { }` block — the warning at the top of this file explains why, and it cost a whole probe run once already. This hook is shared: AGOT: The Knighting Ceremony rolls a post-battle knighting on it and Grand Remembrance tracks battles on it, both through their own files. `events = { }` lists merge, so all three coexist.

- [x] **Step 2: Verify**

Run: `python tools/ck3.py validate battle_chronicles`
Expected: `0 errors, 0 warnings`

- [x] **Step 3: Commit**

```bash
cd /d/ck3/mods/battle_chronicles && git add common/on_action/bc_on_actions.txt && git commit -m "feat(bc): hook the aftermath events to combat end

events = { } only, as the file header demands - an effect block here is
discarded by alphabetical filename order regardless of load order."
```

---

### Task 9: Deploy and confirm zero collisions

**Files:** none modified.

- [x] **Step 1: Confirm no file collisions**

Run: `python tools/ck3.py index -q && python tools/ck3.py conflicts`
Expected: no line naming `battle_chronicles`. Every path this plan touched was already mod-owned, so this should be unchanged from before the work started — it is a regression check, not a discovery.

**The reindex is what makes it a check.** `conflicts` reads `index/ck3.sqlite3`, not the files on disk. Against a stale index it reports the file set as it stood before Task 1, which by construction has no collisions — it would pass no matter what these tasks did.

- [x] **Step 2: Deploy**

Run: `python tools/ck3.py deploy battle_chronicles`
Expected: confirmation that the `.mod` pointer was written.

- [x] **Step 3: Confirm the mod is in the playset**

Run: `python tools/ck3.py playset list`
Expected: `battle_chronicles` present, loading after AGOT. If absent, `python tools/ck3.py playset add battle_chronicles` — **ask the user before changing the playset.**

- [x] **Step 4: Final static check**

Run: `python tools/ck3.py validate battle_chronicles`
Expected: `0 errors, 0 warnings`

No commit — this task changes nothing under version control.

---

### Task 10: The calibration run

**Do not start this task without the user.** It needs the game launched and observed, and a restart costs about seven minutes, so this one run has to answer every open question at once — including the four still owed from the previous pass.

**Files:** none modified.

- [x] **Step 1: Launch, with the logs cleared**

Run: `python tools/ck3.py launch --clear-logs`

**The `--clear-logs` is not optional.** `probe` scans every `*.log` in the logs directory end to end (`launch.py:70-93`); it does not know about sessions. The logs on disk right now hold 3,884 `BC:` hits from the 2026-08-12 run — 858 cleanup calls, 439 `bc_knight_holds_the_breach`, 437 toast-body markers. Without clearing, every ladder is poisoned, the winner-versus-loser equality test is meaningless, and all four of the questions in Step 5 come back pre-answered by the previous run.

Set the `bc_aftermath` game rule to **Generous** at the start (see Step 3 — it is what makes a notable battle producible on demand, and it is the only test that option gets). Note the consequence for Step 2.

Play or observe until a meaningful number of battles have resolved. More battles is strictly better — the whole point is a distribution.

- [x] **Step 2: Collect the outcome markers**

Run: `python tools/ck3.py probe 'BC:'`

**Read every notable count as a Generous count.** The run is under `bc_aftermath_generous`, which adds a free `calc_true_if` point, so the effective bar for the whole run is "one real row", not `amount >= 2`. Consequences:

- the five **ladders** are unaffected — they fire on every combat end regardless of the bar, and they are what Task 11 sets thresholds from
- the **winner-versus-loser equality test** is unaffected — both sides read the same game rule
- the **notable rate**, `BC: nickname awarded` and every `blocked` count are inflated. The Default rate is strictly lower. Do **not** judge `amount >= 2` or `<N> = 3` from these numbers; derive them from the ladder distributions instead.

Record the full table. The counts that matter:

| Probe | What it answers |
|---|---|
| **the denominators, first** | `win notable + win not notable` against `lose notable + lose not notable`. **Read this before anything else.** If the two events did not fire the same number of times, the comparison in the next row means nothing. |
| `BC: win notable` vs `BC: lose notable` | given equal denominators, **these must match exactly.** Any divergence means the bar is asymmetric — one side's knights are getting a memory of a battle the other side's knights are not. |
| `BC: win notable` vs `BC: win not notable` | the notable rate. Says whether `amount >= 2` and `<N> = 3` describe a career or a formality. |
| `BC: win size *` ladder | sets `<SIZE_BIG>` and `<SIZE_HUGE>` from one distribution. Note this is `num_total_troops`, which is **both sides combined**. |
| `BC: win host *` ladder | the **per-side** distribution, and the control for the odds row. If this ladder never leaves `host under 5k` while the size ladder shows large battles, `side_max_army_size` does not work on the left of a comparison — the odds row is dead and must be dropped from `bc_battle_is_notable_trigger`. |
| `BC: win blood *` ladder | sets `<BLOOD>` |
| `BC: win warscore *` ladder | sets `<SCORE>`. The least trustworthy threshold — it is the only row whose scale is not troops, and AGOT's warscore is not obviously on vanilla's scale. |
| `BC: win odds *` ladder | sets `<ODDS>` — but only if the host ladder above proved the construct works. `odds even` on every battle is ambiguous on its own. |
| `BC: nickname awarded` | did a name ever land |
| `BC: nickname blocked *` | if awarded is zero, which gate ate it. The **five** blocked counts — `no commander`, `dead commander`, `already named`, `count`, `martial` — plus `awarded` should sum to `BC: win notable`; a shortfall means a path nothing is measuring. |

Read the size, blood, warscore and odds ladders against the **sub-huge** population — the two size rows nest, so those three rows never decide the largest battles.

- [ ] **Step 3: Check the memory in game, on two knights** — NOT DONE, and it is the one unverified thing left in the design. The calibration run was played on `bc_aftermath_default` (see the correction in Task 11 Step 1), which produced only 5 notable wins across the whole run with no guarantee any was the player's — so there was nothing to open a memories window on. Settling it needs one more run started on **Generous**, which would also give that rule option its only test.

This is the one thing a probe cannot answer, and nothing in the log says *which* knights in the world received a memory — so do not go looking for one. Make one instead:

1. Set the `bc_aftermath` game rule to **Generous** when starting the run. One real row then suffices, which makes notable battles common enough to produce one on demand. (This is also the only test the `generous` option gets.)
2. Fight a battle **as the player**, with your own knights on the field, and win or lose it.
3. Your own knights are reachable from the military screen. Open **two different ones** and read their memory lists.

Expected: both show a `bc_battle_memory_won` or `_lost` entry naming **the same province**, and that province is where the battle was fought.

Then hover the memory to read its description, which uses the other three localization keys and the `GetName` accessor rather than `GetNameNoTooltip`. The memory list only exercises the title.

Failure signatures to watch for:
- one knight has a correct memory and the rest have an empty province — the variable is not being written per pass
- every knight names the same wrong field — the province scope leaked
- the memory renders as its raw key name — the localization file lost its BOM

- [x] **Step 4: Read the error log**

Run: `python tools/ck3.py probe 'battle_chronicles|bc_chronicles|bc_aftermath|bc_battle|bc_notable'`

**Use `probe`, not `errors`, for this.** Script errors from a mod are logged when the file loads or when the event first fires — near the **top** of `error.log`, not the end. `errors` cannot reach them: `collect_errors` is `lines[-tail:]` (`tools/ck3lib/launch.py:96-103`), a tail slice with no head option, and `error.log` on an AGOT-stack run is hundreds of thousands of lines. `probe` reads each log end to end (`tools/ck3lib/launch.py:85-92`) and groups its output by file, so the `=== error.log ===` block is the whole answer.

Expected: **no `=== error.log ===` block at all.** If nothing anywhere matches, `probe` prints `no lines matching ...` and exits 1 — here that non-zero exit is the pass condition, not a failure. Ignore the `=== debug.log ===` and `=== game.log ===` blocks; those are this mod's own `debug_log` markers, which is the instrumentation working.

This only reads cleanly because Step 1 cleared the logs — one more reason that is not optional. Then, as a second pass on anything the pattern missed, run `python tools/ck3.py errors --tail 400` and read only the `=== error.log (N line(s)) ===` block for unattributed script errors at the end of the run.

`probe` only counts markers that fired. Every failure class in this feature that is *not* a missing marker lands here instead: an invalid `left_icon`, a comparison against a missing scope on a leaderless side, an unresolvable `var:` read, a mistyped memory type or localization key. This is the cheapest step in the run and the one that catches what the markers cannot.

- [x] **Step 5: Answer the four questions still owed from the previous pass**

Same run, no extra cost:

- `probe 'BC:'` — do `bc_knight_holds_the_breach` and `bc_knight_shames_himself` fire at all now, after the reweighting from `base = 40` to `base = 150`?
- does `bc_shieldbrother_memory` render, and does `[shieldbrother.GetFullName]` resolve to a name rather than a blank?
- do the retuned commander weights produce a sane distribution?
- compare the count of `"BC: toast body ran (knight breach)"` against `"BC: fired bc_knight_holds_the_breach"`. Fewer means a `send_interface_toast` body does **not** run for an AI character, which settles a standing rule. Nothing depends on the answer any more — this is to know it.

- [x] **Step 6: Write the results down**

Append the probe table, the error-log result and the two-knight result to `mods/battle_chronicles/README.md`, in the style of the existing "First live run (2026-08-12)" section.

```bash
cd /d/ck3/mods/battle_chronicles && git add README.md && git commit -m "docs(bc): record the aftermath calibration run"
```

---

### Task 11: Retune and strip the instrumentation

**Do not start until Task 10 has produced numbers.** Setting thresholds without the distribution is exactly the guessing this whole apparatus exists to avoid.

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_triggers/bc_scripted_triggers.txt`
- Modify: `mods/battle_chronicles/common/script_values/bc_script_values.txt`
- Modify: `mods/battle_chronicles/events/bc_events.txt`
- Modify: `mods/battle_chronicles/localization/english/bc_l_english.yml` — only if `<N>` moves far enough that `bc_aftermath_nickname_toast_desc` reads wrong
- Modify: `mods/battle_chronicles/README.md`

`bc_scripted_effects.txt` is deliberately not on this list — its one marker, `"BC: nickname awarded"`, is permanent.

- [x] **Step 1: Set the five thresholds**

In `bc_battle_is_notable_trigger`, replace the placeholder numbers with values read off the ladders:

- `<SIZE_BIG>` — around the 75th percentile of battle size
- `<SIZE_HUGE>` — the genuinely rare tail, a bucket that fires on a handful of battles across the whole run
- `<BLOOD>` — a bucket that fires on a minority of sub-huge battles
- `<SCORE>` — likewise, and expect this to move furthest from vanilla's 25
- `<ODDS>` — in `bc_our_host_gap_value` and `bc_their_host_gap_value`. **Must stay strictly greater than 1.** If the host ladder showed `side_max_army_size` does not work as a trigger operand, delete the odds row from `bc_battle_is_notable_trigger` and both live script values instead.

Replace the `# PLACEHOLDER NUMBERS` comment block above the trigger with what the run actually showed and where the numbers came from, so the next reader is not told they are still guesses.

**`amount` and `<N>` come off the ladders, not off the notable counts.** **CORRECTION, 2026-08-13:** the run was played under `bc_aftermath_default`, not Generous — Step 1 asked for Generous and it was not set, and nothing in the log reports the active rule, so this was only caught afterwards by arithmetic (under Generous one real row suffices and `odds >= 1.5x` alone fired on 21 of 39, so notable would have been ≥21; it was 5, which is an exact fit for the two-row Default bar). The ladders are unaffected, which is exactly why they exist, and they remain the only sound basis for both numbers. The consequence is that **`bc_aftermath_generous` was never exercised at all** — record it as untested rather than treating the notable counts as a generous sample. If the thresholds alone cannot bring the rate somewhere sensible, adjust `amount >= 2` — but the spec's judgement is that above 2 the bar starts requiring coincidences rather than significance, so prefer moving thresholds.

If `<N> = 3` proved to be a formality rather than a career, raise it in `bc_chronicles.0091` (both the `var:bc_notable_battles >= 3` gate and the matching `< 3` in the calibration `else_if`, though that one is about to be deleted), and reread `bc_aftermath_nickname_toast_desc` to check it still says nothing a new `<N>` contradicts.

- [x] **Step 2: Delete the four calibration script values**

Remove `bc_cal_our_host_gap_2x`, `bc_cal_their_host_gap_2x`, `bc_cal_our_host_gap_12x`, `bc_cal_their_host_gap_12x` and the `--- CALIBRATION ONLY ---` header above them from `bc_script_values.txt`.

- [x] **Step 3: Delete every calibration marker**

In `bc_events.txt`, remove **every** block bracketed by `--- CALIBRATION ONLY ---` / `--- end calibration ---`. There are five of them:

| Where | What |
|---|---|
| `.0092`, top of `immediate` | the five ladders — size, blood, warscore, odds, per-side host |
| `.0091`, top of `immediate` | the same five ladders |
| `.0091`, before `side_commander ?=` | the `no commander` marker |
| `.0091`, inside the nickname `if` chain | the three `blocked` markers — already named, count, martial |
| `.0091`, the `else` on the `is_alive` `if` | the `blocked dead commander` marker |

**Keep** these four, which are permanent observability rather than calibration:
- `debug_log = "BC: win notable"` and `"BC: lose notable"` — the asymmetry check must remain runnable
- `debug_log = "BC: win not notable"` and `"BC: lose not notable"` — the rate is meaningless without the denominator

**Keep** `debug_log = "BC: nickname awarded"` in `bc_aftermath_nickname_effect`.

NOTE, deviation from the spec: the spec's Calibration section says "all markers are stripped once the numbers are set". These five stay. The asymmetric-bar test is the only check that catches a whole class of silent failure, and a test that cannot be rerun after the next tuning pass is not a test.

- [x] **Step 4: Verify**

Run: `python tools/ck3.py validate battle_chronicles`
Expected: `0 errors, 0 warnings`

Then confirm nothing is left behind:

```bash
cd /d/ck3 && grep -rn --exclude-dir=.git --exclude-dir=.vscode 'bc_cal_\|CALIBRATION\|end calibration\|PLACEHOLDER' mods/battle_chronicles/
```

Expected: no output. `PLACEHOLDER` is in the pattern because Step 1 is also told to replace the `# PLACEHOLDER NUMBERS` comment above the trigger, and nothing else would catch forgetting it. The `--exclude-dir` flags matter: this mod has its own `.git`, whose loose objects and `COMMIT_EDITMSG` are in scope of a recursive grep.

**Do not use `ck3.py find` for this.** `find` resolves to `find_key()` in `tools/ck3lib/index.py:215`, which queries the index's `defs` table — **definitions only**. The instant Step 2 deletes the definition it returns nothing no matter how many references survive, so it reports success precisely when the bug exists. The index is also only rebuilt by `ck3.py index`, which this task never runs. `validate` will not catch it either: it checks braces, BOM and loc-line syntax, never references.

- [x] **Step 5: Update the README**

Record the final thresholds and the reasoning, in the style of the existing "Changes made after that run" section. Three specific edits:

1. Add a run write-up for this run with its own `**Resolved:**` bullet, in the style of the existing "First live run (2026-08-12)" block, recording what the two-knight check showed about a memory written inside `every_side_knight`. There is no standing "memory-in-an-iterator" bullet to move — the question lived in the spec, not the README.
2. Strike the `bc_shieldbrother_memory` bullet from "Not yet verified in game" (`README.md:110-118`) if Step 5 of the run answered it, along with whichever of the other two bullets that run settled.
3. Fix `README.md:18`, which names a mod — "Battlefield Duel+" — that is not in the playset. `ck3.py playset list` is the authority for what to replace it with.

- [x] **Step 6: Deploy and commit**

```bash
cd /d/ck3 && python tools/ck3.py deploy battle_chronicles && python tools/ck3.py validate battle_chronicles
```

```bash
cd /d/ck3/mods/battle_chronicles && git add . && git commit -m "tune(bc): set aftermath thresholds from the calibration run, strip markers

Vanilla's numbers were placeholders for Westerosi host sizes. The
notable/not-notable markers stay - the winner-versus-loser count is the
only test that catches an asymmetric bar and it has to stay runnable."
```

---

## Things that will look like bugs and are not

- **`bc_chronicles.0090` still walks `every_side_knight` calling `bc_cleanup_effect`, and that walk was a no-op** before this feature: the knight chronicles apply momentum to the side commander, not to the knight. Leave it. It is correct code that had nothing to do.
- **The knight loop excludes the side commander even though `every_side_knight` may already exclude him.** Vanilla runs `every_side_knight` and `every_side_commander` back to back without deduplicating, which hints they are disjoint but does not prove it. The guard costs nothing if they are.
- **Nothing gives the side commander a memory.** Deliberate. Vanilla already does — every time he lost, and on a 10% roll when he won. A second memory of the same field would be noise.
- **The nickname closes AGOT's entire nickname system for that character, dynastic pools included.** Every AGOT dynastic event gates on `has_any_nickname = no` independently. This is accepted, not mitigated; the controls are rarity and `bc_aftermath_off`.
- **`amount >= 2` with a nesting pair of size rows.** The bar reads "huge, or big plus one other thing". Intended.

## Variable names not to use

All live in the playset and would collide: `battle_poi_*`, `epic_*`, `artifact_battles_won_var`, `combat_event_0001_tracker`, and `battle_province` / `battle_memory` as scope names. Everything this plan adds is `bc_`-prefixed except the memory-scoped `battle_location`, which is namespaced by living on the memory and must keep that exact name because vanilla's localization accessor reads it.
