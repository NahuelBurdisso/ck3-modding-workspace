# Battle Chronicles Depth — Plan B: the prose fragments

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn ten fixed toast sentences into ten assembled ones, so that a battle in a swamp in winter against a brother no longer reads identically to a summer field battle against a stranger.

**Architecture:** Every moment's toast desc becomes a concatenation of `Custom()` calls against `type = character` customizable localizations. The arms compare only the three scratch flags Plan A writes — `bc_battle_ground`, `bc_battle_bond`, `bc_battle_size` — never terrain, culture or faith directly. Two of the four clause classes are per-moment (core, ground); two are shared across all ten (bond, scale).

**Tech Stack:** CK3 script (`common/customizable_localization`), YAML localization, `python tools/ck3.py validate --strict`.

**Spec:** `docs/specs/2026-08-15-battle-chronicles-depth-design.md` §3

**Depends on:** `docs/plans/2026-08-15-battle-chronicles-depth-plan-a-context.md`, all eleven tasks, **and on a game run that reports the spike rendered.** See task 1 — it is a gate, not a formality.

---

## AMENDMENT 2026-08-15 — the gate is split, and its safe half is now open

**Tasks 2, 3 and 4 are unblocked. Tasks 5-14 remain blocked on a run.** The line between them is
not a judgement about confidence; it is a property of the diffs.

**Why the split is safe.** Task 4 leaves every one of the ten literal sentences in place and
*appends* two calls to each. If a `Custom()` call fails to render, the toast shows exactly what it
shows today — the failure mode of tasks 2-4 is "no improvement", not "regression". Tasks 5-14 are
the opposite: they replace each literal with four calls and nothing else, so the same failure
produces an empty toast body. The gate exists for that second diff. It was never needed for the
first.

**What the gate asked, and how much of it static work has answered.** The premise was called
"unproven by anything static". Two thirds of it now are, by vanilla precedent:

| claim | status | proof |
|---|---|---|
| `Custom()` renders inside a `send_interface_toast` desc | **proven** | `common/court_positions/tasks/00_court_poet_tasks.txt:94-98` sends a toast whose `desc = court_poet_poetry_desc`; that key at `localization/english/court_positions_2_l_english.yml:150` is `"[court_poet_from_task.Custom('GeneratePoem_Outro_Rhyming')]"`, against a scope saved at `:47`. |
| custom-loc arms may read `var:X = flag:y` off the scope handed to `Custom()`, where that scope is a `save_scope_as` and the variable a `set_variable` | **proven** | `common/customizable_localization/00_ai_value_custom_loc.txt:1-10` is `type = character`, `random_valid = yes`, arms `var:strongest_ai_value = flag:positive_boldness`. Its one call site is `[debater.Custom('StrongestAIValueNoun')]` (`event_localization/lifestyle/statecraft/diplomacy_majesty_events_l_english.yml:153`). `debater` is `save_scope_as`'d at `events/activities/debate_activity/debate_events.txt:1520`; `strongest_ai_value` is `set_variable`'d at `common/scripted_effects/00_ai_value_effects.txt:31`. |
| the two **compose** — a var-reading definition called on a saved scope from inside a toast desc | **still unproven** | no vanilla site does both at once. This is the whole of what the run now settles. |

`00_artifact_custom_loc.txt:17-18` additionally ships the `exists = var:X` / nested-read arm shape
this plan mandates in rule 1, so that shape is precedent rather than invention.

**Do not read this amendment as permission to start task 5.** The residual risk is small but its
blast radius under tasks 5-14 is ten empty toasts, and the fix would be a rewrite of the same 110
keys into the `triggered_desc` fallback shape. Under tasks 2-4 the residual risk costs nothing at
all. Those are different bets and only one of them is worth taking without a run.

---

## Read this before task 1

**This plan is blocked until a human confirms one thing.** Plan A task 7 shipped a single fragment set on The Banner Falls precisely so that this plan is either unblocked or cancelled by one observation. Task 1 is that check. **Do not skip it because the code "looks right".** The premise it tests — that `[scope.Custom('key')]` renders inside a `send_interface_toast` desc with the arms reading the invoking character's variables — is unproven by anything static, and this plan writes about a hundred keys that all rest on it.

**And the gate gets stricter as this plan proceeds, which is why it is first.** Today every toast desc still holds its literal sentence and a failed `Custom()` degrades to that sentence. After tasks 5-14 the ten descs contain *no literal text at all* — they are four calls and nothing else — so the same failure produces a completely empty toast body. Task 1 is the only thing standing between this plan and that.

**Baseline is `0 errors, 2 warnings`,** from `cd /d/ck3 && python tools/ck3.py validate --strict battle_chronicles`. Both warnings are `namespace also defined in` false positives.

**Plan A's three validator checks are live and this plan leans on all of them.** They are the reason a plan that is 90% prose is verifiable at all:

| check | what it catches here |
|---|---|
| custom-loc arms resolve | a `localization_key` naming a loc key that was never written |
| `bc_` `Custom()` calls resolve | a toast calling a definition that does not exist, or a typo either side |
| ground partition complete | not used by this plan, but a break in it invalidates every ground arm |

Neither of the first two existed when the mod shipped its first custom loc. Without them, a typo in one of 110 keys shows in game as the raw key printed into the sentence — or, if the typo is on a `Custom()` call rather than a `localization_key`, as nothing at all — and in the toolchain as nothing at all either way.

**Four rules this plan repeats a hundred times, stated once here.**

1. **Every keyed arm is `exists` then a nested read, never a bare read.** `trigger_if` whose `limit` fails evaluates **true**, so the bare `exists` row is the row that actually rejects; and a read may not sit beside its own `exists`, because CK3 does not short-circuit and guarantees no evaluation order among siblings.
2. **Every keyed class ends in a trigger-less fallback arm, last.** It is load-bearing, not decorative: it is what a render after `bc_clear_scratch_effect` resolves to, and what a battle whose `combat.location` did not resolve resolves to. Each fallback must read as complete prose on its own.
3. **`bc_battle_ground` and `bc_battle_bond` are flags; `bc_battle_size` is a number.** Ground and bond arms compare `var:X = flag:y`. Scale arms compare `var:bc_battle_size = 3`. The size ladder inside `bc_battle_open_effect` (`bc_ledger_effects.txt`) writes it with `value = 3` / `2` / `1` — a flag comparison against it would be a silent no-match that `validate` passes.
4. **Every fragment string begins with a leading space, inside the quotes.** The toast concatenates `Custom()` calls with no separator of its own. A fragment that does not start with a space runs into the previous sentence. The fallback arms — which are usually empty strings — are the exception and are written `""`.

**The anchor is `bc_chronicle_subject`,** saved in `bc_battle_open_effect` (Plan A task 5). It is the only scope common to all ten call sites: the seven commander events save `bc_commander`, the three knight events save `bc_knight`, and neither reaches the other's toast.

**Naming rule, from Plan A:** every custom-loc definition ends in a class suffix — `_core`, `_ground`, or, for the two shared classes, `_clause`. `validate.py` records a key in `def_categories` only the first time it sees it, and `common/combat_phase_events` is scanned before `common/customizable_localization`, so a definition named `bc_banner_falls` would collide with the phase event of that name and every call to it would error falsely. The suffix is what prevents that, and a collision would also raise a third `also defined in` WARN, so it breaks the two-warning baseline as well as the call sites. Do not drop the suffix on a definition that happens not to collide today.

The shared classes are `bc_bond_clause` and `bc_scale_clause`, not `bc_bond` and `bc_scale`, for exactly this reason. Plan A stated the rule as `_bond` / `_scale` because at the time the classes were per-moment; they are shared, so the suffix moved to the front of the name and `_clause` carries the collision-proofing instead. Neither name collides in the playset today — `python tools/ck3.py find bc_bond_clause` returns nothing — but the suffix is what keeps that true when a future definition is added.

**`bc_flavour.txt` carries a UTF-8 BOM.** Plan A task 7 created it with one. Appending with `Edit` preserves it. If you ever rewrite the file whole with `Write`, restore the BOM and check it — `validate` does **not** BOM-check script files (`has_bom` is called only from `_check_loc_file` in `tools/ck3lib/validate.py`, never on a script file).

---

## File structure

| file | state | responsibility |
|---|---|---|
| `mods/battle_chronicles/common/customizable_localization/bc_flavour.txt` | modify | all 22 definitions. Created by Plan A task 7 with one of them. |
| `mods/battle_chronicles/localization/english/bc_l_english.yml` | modify | 110 fragment keys — 103 written here, 7 already shipped by Plan A's spike — and the ten rewritten toast descs |
| `mods/battle_chronicles/README.md` | modify | task 1 adds a dated `## Spike gate run` section and removes the spike's pending entry; task 14 adds one "Not yet verified in game" entry |

**One file for all 22 definitions, not one per moment.** They share a shape and a set of rules, and a reader checking "does every keyed class end in a fallback" wants one file to check. The file will run to roughly 950 lines — a ground class is 67 of them and there are ten — which is acceptable for a file that is a table and is read one definition at a time.

**The loc keys interleave with the existing ones rather than appending in a block.** Each moment's fragments go directly under that moment's toast desc, so the assembled sentence and its parts are read together. The two shared classes get their own section at the end of the toast block.

---

### Task 1: the gate

**This task writes no code. Its output is a decision.**

- [ ] **Step 1: Read what Plan A recorded**

```bash
cd /d/ck3 && sed -n '/Not yet verified in game/,/^## /p' mods/battle_chronicles/README.md
```

Expected: an entry for **The spike fragment**, with a four-row table of markers-versus-toast outcomes.

- [ ] **Step 2: Get the observation**

Ask the user for the result of a game run in which a Banner Falls toast appeared. Two things are needed and neither can be inferred from the other:

1. What the toast said — specifically, whether the sentence *"The standard goes down in the press, and the men nearest it look for it and do not find it."* was followed by a clause naming the ground.
2. What `python tools/ck3.py probe 'BC: ground'` reports for that session.

If the user has no such run, **stop here.** This plan is blocked on a run, not on more analysis. Say so and offer to work on something else.

- [ ] **Step 3: Decide**

| markers | toast | what to do |
|---|---|---|
| a band | clause present, matches band | **proceed to task 2.** |
| a band | clause present, wrong band | **stop.** The arms read the variable off a character other than the one holding it. Re-derive the anchor before writing anything; the fault is in Plan A task 5, not here. |
| a band | no clause at all | **stop.** Either `Custom()` does not render in a toast desc or the anchor is not addressable from loc. Retry the spike once with `bc_commander` (`bc_commander_phase_events.txt:65`). If that renders, the anchor is wrong and fixable; if it does not, the mechanism is dead but **this plan is not cancelled**. A `send_interface_toast` does take a `desc = { ... }` block with `triggered_desc` arms inside it — vanilla does exactly that at `events/dlc/ach/ach_coronation_events.txt:3316-3324`, and `first_valid` inside a toast `title` at `common/scripted_effects/01_ep1_court_event_effects.txt:14-22`. The fallback is therefore the eve's own proven mechanism, written inline in the ten descs instead of in a shared definition: the same prose, the same triggers, but repeated per moment rather than shared, and with no `random_valid` — so the core class would be lost and the other three would survive. Expensive, local, and not a cancellation. Re-plan before writing it. |
| `BC: ground missing` | no clause | **stop, but this is not a spike failure.** `combat.location` did not resolve at a phase event. Fix `bc_write_ground_effect` and get another run. |
| nothing at all | — | the build the user ran did not contain Plan A. Confirm the mod deployed. |

- [ ] **Step 4: Record the decision**

The README has no "run log" section. Its convention is one `## <Kind> run, <date>`
heading per run, in chronological order, with `## Not yet verified in game`
always **last** (`README.md:558`). Follow it: insert a new

```
## Spike gate run, <date of the run> (Plan B task 1)
```

section immediately **above** `## Not yet verified in game`, naming which row of
the step-3 table the run landed on, what the toast actually said, and what
`probe 'BC: ground'` reported.

Then **delete the spike entry from `## Not yet verified in game`** — it has now
been verified, or it has failed, and either way it is no longer pending. Leaving
it there is how a later session is made to ask for the same run twice.

- [ ] **Step 5: Commit the record**

Do this even when step 3 said stop. The observation is the deliverable; losing it
costs another run.

```bash
cd /d/ck3/mods/battle_chronicles && git add README.md && git commit -m "$(cat <<'EOF'
docs: record the spike gate result

Plan B task 1. The one thing no static check can answer - whether a
Custom() call renders inside a send_interface_toast desc against the
invoking character's variables - and the answer decides whether the
remaining twenty-one definitions get written at all.
EOF
)"
```

---

### Task 2: the shared bond clause

Six keys and one definition. It is the smallest of the four classes and it exercises every rule in the preamble, so it goes first.

**Files:**
- Modify: `mods/battle_chronicles/common/customizable_localization/bc_flavour.txt`
- Modify: `mods/battle_chronicles/localization/english/bc_l_english.yml`

- [ ] **Step 1: Append the definition**

Append to `bc_flavour.txt`:

```

# --- the bond, shared by all ten moments -------------------------------------
#
# SHARED AND NOT PER-MOMENT, unlike the ground clauses. "against his own blood"
# reads the same after a banner falling as after a flank collapsing; "in the
# sand" does not - a standard goes down IN the sand, a flank collapses AMONG the
# trees. The verb has to agree with the ground and does not have to agree with
# the foe.
#
# FIVE VALUES PLUS A FALLBACK, matching bc_write_bond_effect exactly. The five
# are nemesis, kin, countryman, heathen, stranger. `stranger` gets a real clause
# rather than sharing the fallback, because "a man he has never heard of" is a
# fact worth saying and the fallback has to cover the case where NOTHING is
# known - which is a different thing.
#
# THE FALLBACK IS AN EMPTY STRING and that is deliberate. Every other class can
# say something generic when it knows nothing. This one cannot: any sentence
# about the foe presumes a foe, and the case this arm covers is precisely that
# there may not have been one. Silence is the only honest reading.
bc_bond_clause = {
	type = character

	text = {
		localization_key = bc_frag_bond_nemesis
		trigger = {
			exists = var:bc_battle_bond
			trigger_if = {
				limit = { exists = var:bc_battle_bond }
				var:bc_battle_bond = flag:nemesis
			}
		}
	}
	text = {
		localization_key = bc_frag_bond_kin
		trigger = {
			exists = var:bc_battle_bond
			trigger_if = {
				limit = { exists = var:bc_battle_bond }
				var:bc_battle_bond = flag:kin
			}
		}
	}
	text = {
		localization_key = bc_frag_bond_countryman
		trigger = {
			exists = var:bc_battle_bond
			trigger_if = {
				limit = { exists = var:bc_battle_bond }
				var:bc_battle_bond = flag:countryman
			}
		}
	}
	text = {
		localization_key = bc_frag_bond_heathen
		trigger = {
			exists = var:bc_battle_bond
			trigger_if = {
				limit = { exists = var:bc_battle_bond }
				var:bc_battle_bond = flag:heathen
			}
		}
	}
	text = {
		localization_key = bc_frag_bond_stranger
		trigger = {
			exists = var:bc_battle_bond
			trigger_if = {
				limit = { exists = var:bc_battle_bond }
				var:bc_battle_bond = flag:stranger
			}
		}
	}
	text = {
		localization_key = bc_frag_bond_any
	}
}
```

- [ ] **Step 2: Add the six keys**

In `bc_l_english.yml`, after the last moment toast desc (`bc_shieldbrother_forged_toast_desc`), add a section:

```

# --- shared fragments: the bond ---------------------------------------------

 bc_frag_bond_nemesis:0 " The man commanding here knew whose colours those were across the field before either host moved."
 bc_frag_bond_kin:0 " The man commanding here shares blood with whoever is giving the orders across the field."
 bc_frag_bond_countryman:0 " The men on both sides curse in the same words."
 bc_frag_bond_heathen:0 " Whatever the other side was praying to at dawn, the man commanding here was not."
 bc_frag_bond_stranger:0 " Nobody across the field is anybody to the man commanding here."
 bc_frag_bond_any:0 ""
```

Note the leading space inside each non-empty string, and that `bc_frag_bond_any` is empty rather than absent — the key must exist or Plan A's task 1 check errors on the arm that names it.

**Two prose rules the first draft of these strings broke, corrected in review 2026-08-15.**

**The foe is ONE character and may be a woman.** `bc_battle_bond` is computed against `var:bc_battle_foe`, a single enemy side commander, and the `kin` arm's test is `is_close_family_of`, whose members per the API dump are parents, children, siblings, grandparents and grandchildren — mothers, daughters, sisters and grandmothers all match. So no fragment may say "men on the other side" (plural against a single foe) or assume the foe's sex. The other four arms stay neutral by saying "the other side" or "nobody across the field"; the `kin` arm must too. It also has to be *about blood*, or it does not distinguish itself from `countryman`, which is the only reason the two arms are separate.

**No fragment may date itself to the start of the battle.** Phase events roll every five days, so these clauses append to toasts arriving on day 20 of a long fight. "at dawn" survives that; "all morning" presumes the battle began this morning.

**A third rule, added in the third review pass.** **No fragment may collide with the sentence it appends to, or with the eve.** A bond clause is appended to a moment toast and read in the same breath as it, and the same battle already showed the player the eve. Two collisions were caught this way: `nemesis` said "banner", which lands directly on `bc_banner_falls_toast_desc`'s falling standard and reads as if the nemesis's banner is the one going down — now "colours"; and `countryman` said "shouting in the same tongue", which is how the eve's `bc_chronicles.0011.desc_countryman` ends — now "curse in the same words". Check a new fragment against the ten toast descs **and** against `bc_chronicles.0011.desc_*` before shipping it.

**"The man commanding here", not "he", and this is not a style choice.** The bond is
computed commander-against-commander in `bc_write_bond_effect`; it is a fact about
the commander and about nobody else. But this clause is shared by all ten moments,
and three of them — tasks 12, 13 and 14 — are knight moments whose core and ground
clauses have already bound "he" to the **knight**. A bare pronoun there hands the
commander's kin and the commander's faith to a man who may share neither. Naming
the role costs four words and makes the clause true in both families, which is the
whole reason it can be one definition instead of two.

The same rule applies to any clause class added later that reads a
commander-scoped variable: **if it is shared, it may not say "he".**

- [ ] **Step 3: Validate**

```bash
cd /d/ck3 && python tools/ck3.py validate --strict battle_chronicles
```

Expected: `0 errors, 2 warnings`. An error naming `bc_frag_bond_*` means the arm and the key disagree — task 1's check catching exactly what it was built for.

- [ ] **Step 4: Prove the check would have caught a typo**

Not optional. This is the one moment in the plan where the safety net gets tested rather than trusted, and it costs one edit.

With `Edit`, change `localization_key = bc_frag_bond_kin` to `localization_key = bc_frag_bond_kinn`, then validate.

Expected: **exactly 1 error**, naming `bc_frag_bond_kinn`. Revert with `Edit`, re-validate, expect the baseline.

- [ ] **Step 5: Check the fallback is last and unguarded**

```bash
cd /d/ck3/mods/battle_chronicles && python -c "
import re
t = open('common/customizable_localization/bc_flavour.txt',encoding='utf-8-sig').read()
for name, body in re.findall(r'^(bc_\w+) = \{(.*?)^\}', t, re.M | re.S):
    arms = re.findall(r'text = \{(.*?)\n\t\}', body, re.S)
    unguarded = [i for i, a in enumerate(arms) if 'trigger' not in a]
    print(name, 'arms', len(arms), 'unguarded at', unguarded)
"
```

Expected for `bc_bond_clause`: `arms 6 unguarded at [5]`. Any other index means the fallback is not last, and a fallback that is not last **swallows every arm below it** — `Custom()` takes the first valid arm, and an unguarded arm is always valid.

- [ ] **Step 6: Commit**

```bash
cd /d/ck3/mods/battle_chronicles && git add common/customizable_localization/bc_flavour.txt localization/english/bc_l_english.yml && git commit -m "$(cat <<'EOF'
feat: add the shared bond clause

Five bond values plus a fallback, shared across all ten moments because
a clause about the foe does not have to agree with the moment's verb.
The fallback is an empty string: any sentence about the foe presumes
one, and the case it covers is that there may not have been one.
EOF
)"
```

---

### Task 3: the shared scale clause

Four keys and one definition. **The one class that compares a number, not a flag.**

**Files:**
- Modify: `mods/battle_chronicles/common/customizable_localization/bc_flavour.txt`
- Modify: `mods/battle_chronicles/localization/english/bc_l_english.yml`

- [ ] **Step 1: Append the definition**

Append to `bc_flavour.txt`:

```

# --- the scale, shared by all ten moments ------------------------------------
#
# bc_battle_size IS A NUMBER, NOT A FLAG. The size ladder inside
# bc_battle_open_effect, in bc_ledger_effects.txt, writes it with
# `value = 3` / `2` / `1`. Every other keyed class in this file compares
# `var:X = flag:y`; these three compare `var:bc_battle_size = 3`. A flag
# comparison here would be a silent no-match that validate passes clean, and the
# scale clause would simply never render - indistinguishable from a battle whose
# size never got written.
#
# THE BUCKETS ARE 10,000+ / 2,000+ / under. Measured over 143 battles per side:
# 5k+ 46, 3k 42, 2k 31, 1k 14, under-1k 4. Do not re-guess the boundaries here;
# they belong to bc_battle_open_effect and this file only names them.
bc_scale_clause = {
	type = character

	text = {
		localization_key = bc_frag_scale_huge
		trigger = {
			exists = var:bc_battle_size
			trigger_if = {
				limit = { exists = var:bc_battle_size }
				var:bc_battle_size = 3
			}
		}
	}
	text = {
		localization_key = bc_frag_scale_large
		trigger = {
			exists = var:bc_battle_size
			trigger_if = {
				limit = { exists = var:bc_battle_size }
				var:bc_battle_size = 2
			}
		}
	}
	text = {
		localization_key = bc_frag_scale_small
		trigger = {
			exists = var:bc_battle_size
			trigger_if = {
				limit = { exists = var:bc_battle_size }
				var:bc_battle_size = 1
			}
		}
	}
	text = {
		localization_key = bc_frag_scale_any
	}
}
```

- [ ] **Step 2: Add the four keys**

In `bc_l_english.yml`, after the bond section:

```

# --- shared fragments: the scale --------------------------------------------

 bc_frag_scale_huge:0 " On a field this size it will be an hour before anyone knows whether it mattered."
 bc_frag_scale_large:0 " The field is wide enough that half of it has not heard yet."
 bc_frag_scale_small:0 " There are few enough men here that every one of them sees it."
 bc_frag_scale_any:0 ""
```

- [ ] **Step 3: Validate and check the shape**

```bash
cd /d/ck3 && python tools/ck3.py validate --strict battle_chronicles
```

Expected: `0 errors, 2 warnings`. Then re-run task 2 step 5's arm check; expect `bc_scale_clause arms 4 unguarded at [3]`.

- [ ] **Step 4: Confirm the comparison form against the writer**

The one failure this class has that no other class has, checked mechanically:

```bash
cd /d/ck3/mods/battle_chronicles && python -c "
import re
f = open('common/customizable_localization/bc_flavour.txt',encoding='utf-8-sig').read()
b = f[f.index('bc_scale_clause = {'):]
b = b[:b.index('\n}')]
print('scale clause compares:', re.findall(r'var:bc_battle_size = (\S+)', b))
l = open('common/scripted_effects/bc_ledger_effects.txt',encoding='utf-8-sig').read()
print('writer values:', re.findall(r'name = bc_battle_size value = (\S+)', l))
"
```

Expected:

```
scale clause compares: ['3', '2', '1']
writer values: ['3', '2', '1']
```

Any `flag:` in the first list is the silent-no-op bug. Any mismatch between the two lists is an arm that can never match.

- [ ] **Step 5: Commit**

```bash
cd /d/ck3/mods/battle_chronicles && git add common/customizable_localization/bc_flavour.txt localization/english/bc_l_english.yml && git commit -m "$(cat <<'EOF'
feat: add the shared scale clause

Three size buckets plus a fallback. This is the only class in the file
that compares a number rather than a flag, because bc_battle_size is
written as one - a flag comparison would be a silent no-match that
validate passes.
EOF
)"
```

---

### Task 4: wire the two shared clauses into all ten toasts

The shared classes land on every moment in one commit, so that a partially-wired state never exists in the tree.

**Files:**
- Modify: `mods/battle_chronicles/localization/english/bc_l_english.yml` (the ten toast descs)

- [ ] **Step 1: Rewrite the ten toast descs**

Each keeps its existing sentence and gains two calls. Note `bc_banner_falls_toast_desc` already carries a third from Plan A's spike, and the ground call stays **between** the core sentence and the bond clause — ground, then foe, then scale, in that order everywhere.

```
 bc_banner_falls_toast_desc:0 "The standard goes down in the press, and the men nearest it look for it and do not find it.[bc_chronicle_subject.Custom('bc_banner_falls_ground')][bc_chronicle_subject.Custom('bc_bond_clause')][bc_chronicle_subject.Custom('bc_scale_clause')]"
 bc_rally_the_line_toast_desc:0 "A shouted order carries where it should not have, and the ranks close again.[bc_chronicle_subject.Custom('bc_bond_clause')][bc_chronicle_subject.Custom('bc_scale_clause')]"
 bc_horse_killed_toast_desc:0 "The horse goes down screaming. He comes up out of the mud on foot, and is seen to come up.[bc_chronicle_subject.Custom('bc_bond_clause')][bc_chronicle_subject.Custom('bc_scale_clause')]"
 bc_flank_collapses_toast_desc:0 "The outnumbered wing bends, and then it does not stop bending.[bc_chronicle_subject.Custom('bc_bond_clause')][bc_chronicle_subject.Custom('bc_scale_clause')]"
 bc_van_breaks_through_toast_desc:0 "The leading ranks find the seam, and open it.[bc_chronicle_subject.Custom('bc_bond_clause')][bc_chronicle_subject.Custom('bc_scale_clause')]"
 bc_ground_favours_us_toast_desc:0 "The slope, the trees, the narrow way in. They have to come to us across all of it.[bc_chronicle_subject.Custom('bc_bond_clause')][bc_chronicle_subject.Custom('bc_scale_clause')]"
 bc_lines_bogged_down_toast_desc:0 "Neither host can move. The battle becomes a matter of who tires of the mud last.[bc_chronicle_subject.Custom('bc_bond_clause')][bc_chronicle_subject.Custom('bc_scale_clause')]"
 bc_knight_holds_the_breach_toast_desc:0 "One man in the gap where the line failed, and the line has time to be made again behind him.[bc_chronicle_subject.Custom('bc_bond_clause')][bc_chronicle_subject.Custom('bc_scale_clause')]"
 bc_knight_shames_himself_toast_desc:0 "He throws down the shield and goes back through his own ranks. Every man he passes remembers it.[bc_chronicle_subject.Custom('bc_bond_clause')][bc_chronicle_subject.Custom('bc_scale_clause')]"
 bc_shieldbrother_forged_toast_desc:0 "They came through the same press back to back. Neither will speak of it well, and neither will forget it.[bc_chronicle_subject.Custom('bc_bond_clause')][bc_chronicle_subject.Custom('bc_scale_clause')]"
```

**No space before `[`.** The leading space lives inside each fragment. A space here as well would double up on every render and be invisible in the diff.

- [ ] **Step 2: Validate**

```bash
cd /d/ck3 && python tools/ck3.py validate --strict battle_chronicles
```

Expected: `0 errors, 2 warnings`. This is Plan A's task 2 check earning its place — twenty new `Custom()` call sites, each of which it resolves.

- [ ] **Step 3: Confirm all ten got both calls, and got them in the right order**

```bash
cd /d/ck3/mods/battle_chronicles && python -c "
import re
moments = ['bc_banner_falls','bc_rally_the_line','bc_horse_killed','bc_flank_collapses',
           'bc_van_breaks_through','bc_ground_favours_us','bc_lines_bogged_down',
           'bc_knight_holds_the_breach','bc_knight_shames_himself','bc_shieldbrother_forged']
t = open('localization/english/bc_l_english.yml',encoding='utf-8-sig').read()
for m in moments:
    line = re.search(r'^ %s_toast_desc:0 (.*)$' % m, t, re.M).group(1)
    calls = re.findall(r\"Custom\('(\w+)'\)\", line)
    tail = [c for c in calls if c.endswith('_clause')]
    print(m, calls, 'OK' if tail == ['bc_bond_clause','bc_scale_clause'] else 'WRONG')
"
```

Expected: ten lines, every one ending `OK`, and `bc_banner_falls` showing three calls with `bc_banner_falls_ground` first.

A `WRONG` means either a missing call or the two shared clauses in the wrong order. The order matters for reading, not for correctness — but it must be the same on all ten or the toasts will not feel like one system.

- [ ] **Step 4: Commit**

```bash
cd /d/ck3/mods/battle_chronicles && git add localization/english/bc_l_english.yml && git commit -m "$(cat <<'EOF'
feat: every moment toast now names the foe and the scale

Twenty call sites in one commit so that no partially-wired state exists
in the tree. Ground first, then foe, then scale, on all ten.
EOF
)"
```

---

## Tasks 5-14: the per-moment clauses

**Every one of these ten tasks has the same five steps.** They are written out in full for task 5 and referenced thereafter; the prose differs, the procedure does not.

### The shape, once

Each moment gains **two** definitions:

- **`<moment>_core`** — three arms, no triggers, `random_valid = yes`. A repetition-killer that needs no inputs at all: the same moment reads differently on consecutive firings. Vanilla ships this exact shape — `type = character`, `random_valid = yes`, every arm trigger-less — in `00_appropriate_generic_words.txt:1` (`GetSmallFood`), which is a two-arm match for the template below.
- **`<moment>_ground`** — six band arms plus a fallback, keyed on `var:bc_battle_ground`.

The core class **replaces** the fixed sentence in the toast desc rather than adding to it. After task 5 the assembled line is:

```
 bc_rally_the_line_toast_desc:0 "[bc_chronicle_subject.Custom('bc_rally_the_line_core')][bc_chronicle_subject.Custom('bc_rally_the_line_ground')][bc_chronicle_subject.Custom('bc_bond_clause')][bc_chronicle_subject.Custom('bc_scale_clause')]"
```

**The core fragments therefore do NOT begin with a leading space** — they are the first thing in the line. Every other class does. This is the one exception to preamble rule 4 and it is the mistake most likely to be made ten times.

**`random_valid = yes` goes on the core class only.** The keyed classes must pick by flag, and `random_valid` on a keyed class would pick randomly among the arms that match — which for a keyed class is one arm, making it a no-op, until the day two arms overlap and it becomes a silent randomiser. Spec §3 restricts it to toasts and this is the whole of that restriction.

### The template

```

# --- <moment name> -----------------------------------------------------------
bc_<moment>_core = {
	type = character
	random_valid = yes

	text = {
		localization_key = bc_frag_<moment>_core1
	}
	text = {
		localization_key = bc_frag_<moment>_core2
	}
	text = {
		localization_key = bc_frag_<moment>_core3
	}
}

bc_<moment>_ground = {
	type = character

	text = {
		localization_key = bc_frag_<moment>_desert
		trigger = {
			exists = var:bc_battle_ground
			trigger_if = {
				limit = { exists = var:bc_battle_ground }
				var:bc_battle_ground = flag:desert
			}
		}
	}
	# ... identical arms for open, rough, forest, jungle, winter ...
	text = {
		localization_key = bc_frag_<moment>_any
	}
}
```

**The six band flags are `desert`, `open`, `rough`, `forest`, `jungle`, `winter`,** exactly as `bc_write_ground_effect` writes them. Not the terrain names, not the trigger names.

### The five steps, every time

1. **Append both definitions** to `bc_flavour.txt`.
2. **Add the ten keys** to `bc_l_english.yml`, directly under that moment's toast desc.
3. **Rewrite the toast desc** to open with the core call and follow with the ground call.
4. **Validate** — expect `0 errors, 2 warnings` — then run the arm-shape check from task 2 step 5 and confirm the new `_ground` entry reads `arms 7 unguarded at [6]` and the new `_core` entry reads `arms 3 unguarded at [0, 1, 2]`.
5. **Commit**, one moment per commit. Every one of these ten tasks touches the
   same two files and no others, so the stage line is the same every time — except task 14, which also stages `README.md`:

```bash
cd /d/ck3/mods/battle_chronicles && git add common/customizable_localization/bc_flavour.txt localization/english/bc_l_english.yml && git commit -m "<subject>"
```

**Step 4's counts are the only thing that catches three separate mistakes, so do not skip them because `validate` was clean.**

| what you see | what happened |
|---|---|
| `_core arms 3 unguarded at [0, 1, 2]` | correct |
| `_core` unguarded at anything else | a trigger got copied into a core arm, and a trigger in a `random_valid` class quietly biases the randomiser |
| `_core arms 0` | all three arms were written on one line each. Task 14 scores this as **passing** too, because `[] == list(range(0))`, and `arms 110` does not see it either — see the warning under task 5 step 1 |
| `_core arms 2` or `arms 1` | *some* arms were collapsed to one line. This one is nastier: the whole-file check in task 14 scores it as **passing**, and task 14's `arms 110` key count does not see it either, because that count scans `localization_key = X` regardless of line shape. The per-task `arms 3` is the only thing that catches a partial collapse. |
| `_ground arms 2 unguarded at [1]` | the template's `# ... identical arms for open, rough, forest, jungle, winter ...` placeholder line was left in place and the five middle arms were never written. Task 14 scores this as passing too — a two-arm keyed class with its fallback last is well-formed. Only `arms 7` here, and `arms 110` at the end, catch it. |

---

### Task 5: The Banner Falls

Its ground class already exists — Plan A task 7 wrote it as the spike. This task adds only the core, so it has **four** steps rather than the template's five: the toast-desc rewrite happens inside step 2, because the desc line and the three new keys are one contiguous edit.

**Files:**
- Modify: `mods/battle_chronicles/common/customizable_localization/bc_flavour.txt`
- Modify: `mods/battle_chronicles/localization/english/bc_l_english.yml`

- [ ] **Step 1: Append the core definition**

```

# --- the banner falls: the core ----------------------------------------------
#
# THE GROUND CLASS FOR THIS MOMENT IS ALREADY IN THIS FILE - it was the spike,
# written by Plan A task 7 and proven by a game run before any of the rest of
# this file existed. Do not write a second one.
bc_banner_falls_core = {
	type = character
	random_valid = yes

	text = {
		localization_key = bc_frag_banner_falls_core1
	}
	text = {
		localization_key = bc_frag_banner_falls_core2
	}
	text = {
		localization_key = bc_frag_banner_falls_core3
	}
}
```

**Each arm spans three lines. Do not collapse them to `text = { localization_key = X }`.**
The arm-shape check in task 2 step 5 matches on `text = {` … newline-tab-`}`, so a
one-line arm is invisible to it — and an invisible arm makes a `random_valid`
class report `arms 0 unguarded at []`, which the task 14 whole-file check scores
as **passing**. The check would then be watching nothing. Three lines per arm is
what keeps it honest.

- [ ] **Step 2: Add the three keys**

**Change exactly two things and delete nothing.** Plan A task 7 left a six-line
comment and seven `bc_frag_banner_falls_*` ground keys directly under this desc.
All of them must survive — they are the arms of `bc_banner_falls_ground`, and
removing them is 7 `has no loc entry` errors from Plan A's task 1 check.

With `Edit`, replace **only this one line**:

```
 bc_banner_falls_toast_desc:0 "The standard goes down in the press, and the men nearest it look for it and do not find it.[bc_chronicle_subject.Custom('bc_banner_falls_ground')][bc_chronicle_subject.Custom('bc_bond_clause')][bc_chronicle_subject.Custom('bc_scale_clause')]"
```

with these four:

```
 bc_banner_falls_toast_desc:0 "[bc_chronicle_subject.Custom('bc_banner_falls_core')][bc_chronicle_subject.Custom('bc_banner_falls_ground')][bc_chronicle_subject.Custom('bc_bond_clause')][bc_chronicle_subject.Custom('bc_scale_clause')]"
 bc_frag_banner_falls_core1:0 "The standard goes down in the press, and the men nearest it look for it and do not find it."
 bc_frag_banner_falls_core2:0 "The banner dips once, comes up crooked, and does not come up again."
 bc_frag_banner_falls_core3:0 "Whoever was carrying the standard is not carrying it now, and nobody has picked it up."
```

The lines that follow — `# SPIKE.` through `bc_frag_banner_falls_any:0 ""` — stay
exactly as they are. After the edit, confirm they did:

```bash
cd /d/ck3/mods/battle_chronicles && python -c "
import re
t = open('localization/english/bc_l_english.yml',encoding='utf-8-sig').read()
bands = ['desert','open','rough','forest','jungle','winter','any']
print('ground keys lost', [b for b in bands if 'bc_frag_banner_falls_%s:0' % b not in t])
print('core keys added', ['core%d' % n for n in (1,2,3) if 'bc_frag_banner_falls_core%d:0' % n in t])
"
```

Expected: `ground keys lost []` and `core keys added ['core1', 'core2', 'core3']`.

`core1` is the sentence the toast used to hold verbatim. Keeping it is not sentiment: it is the reading the one proven game run produced, and if the toast stops looking familiar there is no way to tell a rendering failure from a randomiser working.

- [ ] **Step 3: Validate and check the shape**

```bash
cd /d/ck3 && python tools/ck3.py validate --strict battle_chronicles
```

Expected: `0 errors, 2 warnings`. Then the arm-shape check from task 2 step 5; expect `bc_banner_falls_core arms 3 unguarded at [0, 1, 2]`.

- [ ] **Step 4: Commit**

```bash
cd /d/ck3/mods/battle_chronicles && git add common/customizable_localization/bc_flavour.txt localization/english/bc_l_english.yml && git commit -m "$(cat <<'EOF'
feat: three openings for The Banner Falls

random_valid picks among them, so the same moment reads differently on
consecutive firings without needing any input at all. The first arm is
the sentence the toast used to hold, so a failed render stays
distinguishable from a working randomiser.
EOF
)"
```

---

### Task 6: Rally the Line

Follow the five steps. Both definitions are new.

- [ ] **Step 1: Append both definitions** — the template, with `<moment>` = `rally_the_line`.

- [ ] **Step 2: Add the ten keys** under `bc_rally_the_line_toast_desc`:

```
 bc_frag_rally_the_line_core1:0 "A shouted order carries where it should not have, and the ranks close again."
 bc_frag_rally_the_line_core2:0 "He is heard over all of it, which no one expected, and the line stops going backwards."
 bc_frag_rally_the_line_core3:0 "Something is shouted that the men choose to obey, and the gap shuts."
 bc_frag_rally_the_line_desert:0 " The dust swallows the words a dozen paces out; the men who heard pass them on."
 bc_frag_rally_the_line_open:0 " There is nothing on the field to break the sound, and it reaches the far end of the line."
 bc_frag_rally_the_line_rough:0 " Half the line is above the other half and hears him twice."
 bc_frag_rally_the_line_forest:0 " Under the trees the order arrives in pieces, but enough of it arrives."
 bc_frag_rally_the_line_jungle:0 " The green eats the sound. What holds the line is the men who can see him."
 bc_frag_rally_the_line_winter:0 " His breath goes up white with every word of it."
 bc_frag_rally_the_line_any:0 ""
```

- [ ] **Step 3: Rewrite the toast desc:**

```
 bc_rally_the_line_toast_desc:0 "[bc_chronicle_subject.Custom('bc_rally_the_line_core')][bc_chronicle_subject.Custom('bc_rally_the_line_ground')][bc_chronicle_subject.Custom('bc_bond_clause')][bc_chronicle_subject.Custom('bc_scale_clause')]"
```

- [ ] **Step 4: Validate and check the shape.** Expect the baseline, `bc_rally_the_line_core arms 3 unguarded at [0, 1, 2]`, `bc_rally_the_line_ground arms 7 unguarded at [6]`.

- [ ] **Step 5: Commit** — `feat: ground-aware prose for Rally the Line`.

---

### Task 7: The Horse Killed Under Him

**Note the key is `bc_horse_killed_*`, not `bc_horse_killed_under_him_*`** — the event is `bc_horse_killed_under_him` but its toast key is `bc_horse_killed_toast_desc`. Match the **loc key**, not the event name, or task 2's naming rule stops protecting you.

- [ ] **Step 1: Append both definitions** — template, `<moment>` = `horse_killed`.

- [ ] **Step 2: Add the ten keys:**

```
 bc_frag_horse_killed_core1:0 "The horse goes down screaming. He comes up off the ground on foot, and is seen to come up."
 bc_frag_horse_killed_core2:0 "The animal folds under him. He is on his feet before anyone can reach him."
 bc_frag_horse_killed_core3:0 "He loses the horse and does not lose the ground, which the men nearest him notice."
 bc_frag_horse_killed_desert:0 " He is out of the sand with half of it still on him."
 bc_frag_horse_killed_open:0 " On open ground a man on foot is visible from everywhere, and he knows it."
 bc_frag_horse_killed_rough:0 " On this ground the horse was becoming a liability anyway."
 bc_frag_horse_killed_forest:0 " Among the trees he is no worse off on foot than he was mounted."
 bc_frag_horse_killed_jungle:0 " Nothing in this green was ever going to be crossed at a gallop."
 bc_frag_horse_killed_winter:0 " The cold gets into him the moment he is out of the saddle, and does not leave."
 bc_frag_horse_killed_any:0 ""
```

- [ ] **Step 3: Rewrite the toast desc** to the four calls, with `bc_horse_killed_core` and `bc_horse_killed_ground`.

- [ ] **Step 4: Validate and check the shape.**

- [ ] **Step 5: Commit** — `feat: ground-aware prose for The Horse Killed Under Him`.

---

### Task 8: The Flank Collapses

- [ ] **Step 1: Append both definitions** — template, `<moment>` = `flank_collapses`.

- [ ] **Step 2: Add the ten keys:**

```
 bc_frag_flank_collapses_core1:0 "The outnumbered wing bends, and then it does not stop bending."
 bc_frag_flank_collapses_core2:0 "One end of the line gives, and what was a line becomes two crowds."
 bc_frag_flank_collapses_core3:0 "The wing that was holding is not holding, and everyone on that side can see where it ends."
 bc_frag_flank_collapses_desert:0 " There is nowhere on this ground for them to fall back to."
 bc_frag_flank_collapses_open:0 " On open ground a broken wing keeps breaking; there is nothing to stop against."
 bc_frag_flank_collapses_rough:0 " They fall back into the broken ground, and the pursuit slows in it too."
 bc_frag_flank_collapses_forest:0 " They go into the trees, which ends the pursuit and ends the wing."
 bc_frag_flank_collapses_jungle:0 " They go into the green and stop being an army."
 bc_frag_flank_collapses_winter:0 " Men who fall back through this cold do not all come back."
 bc_frag_flank_collapses_any:0 ""
```

- [ ] **Steps 3-5** as the template. Commit — `feat: ground-aware prose for The Flank Collapses`.

---

### Task 9: The Van Breaks Through

- [ ] **Step 1: Append both definitions** — template, `<moment>` = `van_breaks_through`.

- [ ] **Step 2: Add the ten keys:**

```
 bc_frag_van_breaks_through_core1:0 "The leading ranks find the seam, and open it."
 bc_frag_van_breaks_through_core2:0 "The van goes into a gap that was not there a moment ago and makes it a road."
 bc_frag_van_breaks_through_core3:0 "The front rank does not stop where it was expected to stop."
 bc_frag_van_breaks_through_desert:0 " The dust of it is visible from the far wing."
 bc_frag_van_breaks_through_open:0 " With open ground beyond, there is nothing to slow what comes through."
 bc_frag_van_breaks_through_rough:0 " The gap is one gap on this ground, and everything now goes through it."
 bc_frag_van_breaks_through_forest:0 " Beyond the gap the trees close again, and the breakthrough narrows to a path."
 bc_frag_van_breaks_through_jungle:0 " What comes through goes straight into the green and is lost to everyone behind."
 bc_frag_van_breaks_through_winter:0 " The ground they take is frozen hard enough to run on."
 bc_frag_van_breaks_through_any:0 ""
```

- [ ] **Steps 3-5** as the template. Commit — `feat: ground-aware prose for The Van Breaks Through`.

---

### Task 10: The Ground Favours Us

**This moment's fixed sentence already names the ground** — *"The slope, the trees, the narrow way in."* — and it names two things at once. The moment's own gate guarantees one of them, not both.

**Two of the six bands are reachable here and four are not.** `bc_ground_favours_us` carries `bc_terrain_favours_us_trigger` in its `is_valid` (`bc_commander_phase_events.txt`), and that trigger (`bc_scripted_triggers.txt:65-74`) is `OR = { agot_is_hills_terrain agot_is_forest_terrain agot_is_highlands_terrain agot_is_terraced_hills_terrain }`. Through Plan A task 3's bands that is **rough** (hills, highlands, terraced_hills) and **forest**, and nothing else. The moment cannot fire on sand, plains, jungle or ice.

**Write all six bands anyway.** The four dead arms cost four loc lines and they are the difference between "this is safe if the gate changes" and "this silently renders the fallback the day someone widens the trigger". Do not treat their absence from a run as a bug — and do not count this moment as 3 × 7; it is 3 × 3, three core arms times rough, forest and the fallback.

- [ ] **Step 1: Append both definitions** — template, `<moment>` = `ground_favours_us`.

- [ ] **Step 2: Add the ten keys.** The core arms are deliberately rewritten to say nothing specific about terrain; the ground class now says it, and says it truthfully:

```
 bc_frag_ground_favours_us_core1:0 "They have to come to him, and they have to come across all of it."
 bc_frag_ground_favours_us_core2:0 "Whatever they intended, the field has made the decision for them."
 bc_frag_ground_favours_us_core3:0 "He picked this place, and it is turning out to be worth having picked."
 bc_frag_ground_favours_us_desert:0 " They will cross open sand to reach him, in the heat, carrying their own water."
 bc_frag_ground_favours_us_open:0 " There is little enough here to hold, but he is holding the better half of it."
 bc_frag_ground_favours_us_rough:0 " The slope, the rocks, the one narrow way up. Every part of it is his."
 bc_frag_ground_favours_us_forest:0 " The treeline is behind him and the open ground is in front of them."
 bc_frag_ground_favours_us_jungle:0 " He holds the one path through, and there is no other."
 bc_frag_ground_favours_us_winter:0 " They will cross the snow to reach him, and arrive out of breath."
 bc_frag_ground_favours_us_any:0 ""
```

- [ ] **Steps 3-5** as the template. Commit — `feat: The Ground Favours Us stops asserting terrain it may not have`.

---

### Task 11: The Lines Bog Down

**Two of the six bands are reachable here too, and they are not the same two.** `bc_terrain_bogs_us_down_trigger` (`bc_scripted_triggers.txt:76-86`) is `OR = { agot_is_wetlands_terrain agot_is_jungle_terrain agot_is_mountains_terrain agot_is_the_bog_terrain agot_is_taiga_bog_terrain }` — bands **rough** (wetlands, mountains, the_bog, taiga_bog) and **jungle**. The `_forest` arm below is dead: forest terrain does not bog anyone down under this trigger. Write all six for the same reason as task 10.

- [ ] **Step 1: Append both definitions** — template, `<moment>` = `lines_bogged_down`.

- [ ] **Step 2: Add the ten keys.** As with task 10, the core sentence currently names mud; the rewritten arms let the ground class decide what the men are standing in:

```
 bc_frag_lines_bogged_down_core1:0 "Neither host can move. The battle becomes a matter of which host tires first."
 bc_frag_lines_bogged_down_core2:0 "The two lines have found each other and neither can get past."
 bc_frag_lines_bogged_down_core3:0 "Nothing is happening except that men are dying, which is the worst kind of battle to be in."
 bc_frag_lines_bogged_down_desert:0 " They are standing in the sand long enough that the water is running out."
 bc_frag_lines_bogged_down_open:0 " Two lines on open ground with nowhere to be but where they are."
 bc_frag_lines_bogged_down_rough:0 " Nobody can outflank anybody; the ground will not let them."
 bc_frag_lines_bogged_down_forest:0 " Between the trees there is no room to do anything but push."
 bc_frag_lines_bogged_down_jungle:0 " The heat is doing as much as the fighting is."
 bc_frag_lines_bogged_down_winter:0 " It is cold enough that standing still is its own kind of wound."
 bc_frag_lines_bogged_down_any:0 ""
```

- [ ] **Steps 3-5** as the template. Commit — `feat: ground-aware prose for The Lines Bog Down`.

---

### Task 12: The Knight Holds the Breach

**The three knight moments read their scratch off `bc_chronicle_subject`, the commander — not off the knight.** No `bc_` variable is ever written onto a knight, and the fragments must not be written as though the knight held them. `scope:bc_knight` stays where it is and is not needed here: it is the toast's `left_icon` (`bc_knight_phase_events.txt:109`, `:177`, `:293`) and nothing else — no fragment renders the knight's name. The ground and bond come from the commander who was on that side. Both are true of the same battle, so the prose is consistent — but do not "fix" a fragment by pointing it at `bc_knight`, and see task 2 on why the shared bond clause names the role instead of saying "he".

- [ ] **Step 1: Append both definitions** — template, `<moment>` = `knight_holds_the_breach`.

- [ ] **Step 2: Add the ten keys:**

```
 bc_frag_knight_holds_the_breach_core1:0 "One man in the gap where the line failed, and the line has time to be made again behind him."
 bc_frag_knight_holds_the_breach_core2:0 "The breach stays one man wide for longer than one man should manage."
 bc_frag_knight_holds_the_breach_core3:0 "Somebody stands where the line broke and is still standing there when it is mended."
 bc_frag_knight_holds_the_breach_desert:0 " He holds it in the heat, in armour, for as long as it takes."
 bc_frag_knight_holds_the_breach_open:0 " There is no cover for him and he does not appear to want any."
 bc_frag_knight_holds_the_breach_rough:0 " The ground narrows the gap for him, which is the only help he gets."
 bc_frag_knight_holds_the_breach_forest:0 " Two trees and one man, and that is the whole of the line there."
 bc_frag_knight_holds_the_breach_jungle:0 " In this green they come at him one and two at a time, which is the only reason it works."
 bc_frag_knight_holds_the_breach_winter:0 " The cold is in his hands and he holds the sword anyway."
 bc_frag_knight_holds_the_breach_any:0 ""
```

- [ ] **Steps 3-5** as the template. Commit — `feat: ground-aware prose for The Knight Holds the Breach`.

---

### Task 13: The Knight Shames Himself

- [ ] **Step 1: Append both definitions** — template, `<moment>` = `knight_shames_himself`.

- [ ] **Step 2: Add the ten keys:**

```
 bc_frag_knight_shames_himself_core1:0 "He throws down the shield and goes back through his own ranks. Every man he passes remembers it."
 bc_frag_knight_shames_himself_core2:0 "He turns, and keeps turning, and goes out through the men behind him."
 bc_frag_knight_shames_himself_core3:0 "Whatever he was going to be today, he is not going to be it."
 bc_frag_knight_shames_himself_desert:0 " He goes out into open sand where everyone can watch him go."
 bc_frag_knight_shames_himself_open:0 " There is nowhere on this field to do that unseen."
 bc_frag_knight_shames_himself_rough:0 " He goes back down the slope faster than he came up it."
 bc_frag_knight_shames_himself_forest:0 " The trees take him quickly, which is the only mercy in it."
 bc_frag_knight_shames_himself_jungle:0 " The green closes behind him and nobody follows to bring him back."
 bc_frag_knight_shames_himself_winter:0 " His tracks in the snow say exactly which way he went."
 bc_frag_knight_shames_himself_any:0 ""
```

- [ ] **Steps 3-5** as the template. Commit — `feat: ground-aware prose for The Knight Shames Himself`.

---

### Task 14: The Shieldbrother Forged

The last one. Its ground fragments are about two men rather than one, which is the only thing that makes it different from the other nine.

- [ ] **Step 1: Append both definitions** — template, `<moment>` = `shieldbrother_forged`.

- [ ] **Step 2: Add the ten keys**, directly under `bc_shieldbrother_forged_toast_desc` and therefore **above** the two shared-fragment sections that tasks 2 and 3 appended after it. Key order in a yml is irrelevant to the engine; this only keeps the file reading the way the File structure section describes.

```
 bc_frag_shieldbrother_forged_core1:0 "They came through the same press back to back. Neither will speak of it well, and neither will forget it."
 bc_frag_shieldbrother_forged_core2:0 "Two men who did not know each other this morning spent the afternoon keeping each other alive."
 bc_frag_shieldbrother_forged_core3:0 "Whatever the two of them were before today, they are something else after it."
 bc_frag_shieldbrother_forged_desert:0 " They shared what water there was, which in this heat is the whole of it."
 bc_frag_shieldbrother_forged_open:0 " There was nowhere to hide and neither of them went looking."
 bc_frag_shieldbrother_forged_rough:0 " On this ground a man's footing is his neighbour's problem too."
 bc_frag_shieldbrother_forged_forest:0 " Under the trees a man can only see the one beside him, and that turns out to be enough."
 bc_frag_shieldbrother_forged_jungle:0 " In the green they lost the army and did not lose each other."
 bc_frag_shieldbrother_forged_winter:0 " They were cold together for a long time before any of it started."
 bc_frag_shieldbrother_forged_any:0 ""
```

- [ ] **Step 3: Rewrite the toast desc** as the template.

- [ ] **Step 4: Validate and check the whole file at once**

```bash
cd /d/ck3 && python tools/ck3.py validate --strict battle_chronicles
```

Expected: `0 errors, 2 warnings`. Then the full shape check:

```bash
cd /d/ck3/mods/battle_chronicles && python -c "
import re
t = open('common/customizable_localization/bc_flavour.txt',encoding='utf-8-sig').read()
defs = re.findall(r'^(bc_\w+) = \{(.*?)^\}', t, re.M | re.S)
print('definitions', len(defs))
bad = []
for name, body in defs:
    arms = re.findall(r'text = \{(.*?)\n\t\}', body, re.S)
    unguarded = [i for i, a in enumerate(arms) if 'trigger' not in a]
    rv = 'random_valid = yes' in body
    if rv:
        ok = unguarded == list(range(len(arms)))
    else:
        ok = unguarded == [len(arms) - 1]
    if not ok:
        bad.append((name, len(arms), unguarded, rv))
print('malformed', bad)
"
```

Expected:

```
definitions 22
malformed []
```

**22 is the whole design:** ten `_core`, ten `_ground`, `bc_bond_clause`, `bc_scale_clause`. A different number means a definition is missing or one got written twice.

A non-empty `malformed` list is one of exactly two faults. In a `random_valid` class, an arm that carries a trigger — which biases the randomiser silently. In a keyed class, a fallback that is not last — which swallows every arm below it, because `Custom()` takes the first valid arm and an unguarded arm is always valid.

Then the BOM, which nothing else in this plan or in `validate` can see:

```bash
cd /d/ck3 && python -c "
import pathlib
p = pathlib.Path('mods/battle_chronicles/common/customizable_localization/bc_flavour.txt')
print(p.read_bytes()[:3])
"
```

Expected: `b'\xef\xbb\xbf'`.

**This is the plan's one unrecoverable silent failure and it has to be checked by
hand.** If any task rewrote `bc_flavour.txt` with `Write` instead of appending
with `Edit`, the BOM is gone and CK3 ignores the entire file — all 22
definitions, every toast falling back to a raw key. And every other check in
this plan still passes clean, because they all open the file with `utf-8-sig`,
which does not care whether the BOM was there. `validate` cannot catch it either:
`has_bom` is called only from `_check_loc_file`, never on a script file.

If it prints anything else, restore it:

```bash
cd /d/ck3 && python -c "
import pathlib
p = pathlib.Path('mods/battle_chronicles/common/customizable_localization/bc_flavour.txt')
b = p.read_bytes()
if not b.startswith(b'\xef\xbb\xbf'): p.write_bytes(b'\xef\xbb\xbf' + b)
print(p.read_bytes()[:3])
"
```

- [ ] **Step 5: Count the keys**

```bash
cd /d/ck3/mods/battle_chronicles && python -c "
import re
t = open('common/customizable_localization/bc_flavour.txt',encoding='utf-8-sig').read()
y = open('localization/english/bc_l_english.yml',encoding='utf-8-sig').read()
named = re.findall(r'localization_key = (\S+)', t)
have = set(re.findall(r'^ (\S+):0', y, re.M))
print('arms', len(named), 'distinct', len(set(named)))
print('missing keys', sorted(set(named) - have))
print('unused bc_frag keys', sorted(k for k in have if k.startswith('bc_frag_') and k not in named))
"
```

Expected:

```
arms 110 distinct 110
missing keys []
unused bc_frag keys []
```

`missing keys` duplicates Plan A's task 1 check and should always be empty by the time `validate` is clean; it is here because this is the last chance to catch it. **`unused bc_frag keys` is the one nothing else checks** — a key written into the yml that no arm names. It renders nowhere, `validate` is silent about it, and it is almost always a typo on the arm side that the missing-keys check already reported and someone "fixed" by adding a second key.

- [ ] **Step 6: Record what the run must show**

Append to `mods/battle_chronicles/README.md`, under "Not yet verified in game":

```markdown
- **The assembled toasts.** All ten moments now read
  `core + ground + bond + scale`. The spike proved one ground clause on one
  moment; nothing proves the other nine, the two shared classes, or
  `random_valid`. The next run should show:

  | what to look at | pass | fail |
  |---|---|---|
  | any moment toast | one sentence, then up to three clauses, no double spaces and no run-together words | a missing leading space in a fragment, or a stray one before a `[` |
  | the same moment three or more times across a session | not always the same opening sentence | `random_valid` is not picking, or a trigger got into a core arm |
  | a moment in a battle whose `probe 'BC: bond'` says `nofoe` | the **stranger** clause — "Nobody across the field is anybody to the man commanding here." | anything else, including silence |
  | a moment whose `BC: ground` band is known | a clause matching that band | the flag names in the arms do not match what bc_write_ground_effect writes |
  | The Ground Favours Us, any firing | a clause naming slope-and-rocks or a treeline — never sand, snow or jungle | the core arms were not rewritten, or the ground band disagrees with the moment's own gate |
  | any knight moment with a bond clause | the clause says "the man commanding here", not "he" | a shared clause is attributing the commander's kin or faith to the knight |
```

**`nofoe` renders the stranger clause, not silence,** and that row is easy to get
backwards. `bc_write_bond_effect`'s `else` — the leaderless-enemy-side arm —
writes `value = flag:stranger` and *then* logs `BC: bond nofoe`. So a `nofoe`
battle has a bond flag like any other. `bc_frag_bond_any` is reachable only from
a render after `bc_clear_scratch_effect`, or from a stale anchor; if it shows up
in a live battle, something upstream is wrong.

- [ ] **Step 7: Commit**

```bash
cd /d/ck3/mods/battle_chronicles && git add common/customizable_localization/bc_flavour.txt localization/english/bc_l_english.yml README.md && git commit -m "$(cat <<'EOF'
feat: ground-aware prose for The Shieldbrother Forged, and close the set

Twenty-two definitions and 110 keys, against ten fixed sentences before.
Cost is additive and coverage is multiplicative: a moment now has three
openings times up to seven grounds times six bonds times four scales.
Two of the ten reach only three grounds, because their own is_valid
gates the terrain they can fire on.

The two whole-file checks in this commit's task are the ones nothing in
the toolchain does - that every keyed class ends in its fallback and
every random_valid class carries no triggers at all.
EOF
)"
```

---

## What Plan B does not do

- **New moments.** Still deferred, and now more clearly so: with three core arms each, ten moments already read as thirty openings. Whether the mod needs an eleventh moment is a question to ask *after* a run measures how repetitive thirty feels, not before.
- **Season, war type, troop composition.** Designed as inputs in the spec, written by nothing. Adding one is now a small job — a writer effect beside `bc_write_ground_effect`, a flag, and one more clause class — and that is the point of having done it this way.
- **Anything on the eve.** Plan A task 10 finished the eve. It uses `first_valid` in an event `desc`, not `Custom()`, and the two mechanisms stay separate on purpose: the eve is read once and carefully, a toast is read in passing.
- **`bc_battle_creed`.** Plan A task 6 writes it — `same` or `heathen`, on an independent chain from the bond ladder — and nothing here reads it. The bond class's `heathen` arm is the *ladder* value, which is a narrower thing: it only reaches a foe who is neither nemesis, nor kin, nor countryman. A clause class on the creed is the cheapest possible next increment, and it is deliberately not in this plan, because thirteen prose tasks in one plan is already the limit of what can be reviewed at once.
- **Localisation beyond English.** The mod ships English only.

## Where this plan departs from the spec

Two deliberate divergences, recorded so that a later reader does not treat them as drift.

- **The spec's assembled example puts a space between the `Custom()` calls** (§3, the assembled form). This plan mandates the opposite: no space before `[`, and a leading space inside every non-core fragment. The spec's form leaves a **trailing space** on every render whose scale fallback is empty, and empty fallbacks are the common case. This plan's form is also what Plan A's spike already shipped, so changing it now would invalidate the one thing task 1 is gating on.
- **The two shared classes are named `bc_bond_clause` and `bc_scale_clause`**, not `_bond` and `_scale` as Plan A's naming rule reads. See the preamble; the suffix does the same collision-proofing job under a different spelling.

## The one thing this plan cannot check

**Whether the prose is any good.** Every check here is structural: keys resolve, fallbacks are last, arms are counted. None of them can tell that `bc_frag_rally_the_line_jungle` reads awkwardly after `core2`, because eight moments have 3 × 7 = 21 core-plus-ground readings and the two gated ones have 3 × 3 = 9, which is 186 across the ten, and no way to see any of them without playing.

The mitigation is the shape, not a check: every fragment is a **complete clause that stands alone**, and the classes are concatenated in a fixed order — what happened, where, against whom, at what scale. A reading assembled from four independently sensible clauses in a fixed order is at worst flat. It cannot be ungrammatical, which is the failure that would actually matter.
