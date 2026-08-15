# Battle Chronicles Depth — Plan A: tooling, context, and the spike

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Teach every combat moment what ground it is fought on, who the foe is to the commander, and whether the two share a faith — then prove one prose fragment reads it back.

**Architecture:** Classification happens in script, never in a localization arm. Three writes land in `bc_battle_open_effect` (ground, bond, creed) as scratch variables on the side commander. Prose fragments are `type = character` customizable localizations whose arms only compare those flags. Because `validate` is blind to both custom-loc definitions and `Custom()` call sites, three new checks land in the toolchain *before* any fragment is written.

**Tech Stack:** CK3 script (`common/scripted_triggers`, `common/scripted_effects`, `common/customizable_localization`, `events`), YAML localization, Python 3 (`tools/ck3lib/validate.py`).

**Spec:** `docs/specs/2026-08-15-battle-chronicles-depth-design.md`

---

## Read this before task 1

**There are no unit tests in this repo.** There is no `tests/` directory, no pytest, no test runner. The only automated verification available is:

```
python tools/ck3.py validate --strict battle_chronicles
```

run from `D:/ck3`. **Its baseline is `0 errors, 2 warnings`** — both warnings are `namespace also defined in` false positives. Any other line is new and is yours.

`validate` is a *syntax and reference* checker. It proves braces balance, that loc files parse and carry a BOM (loc files only — see below), and — after tasks 1, 2 and 4 — that custom-loc arms and `Custom()` calls resolve and that the terrain partition is complete. **It cannot prove a trigger evaluates true in game.** It never will. Do not write a step that claims otherwise.

**No step in this plan requires launching CK3.** That is a hard constraint on this plan. Every step's expected output is either a `validate` result, a `git` result, or a `python -c` result. The one thing that genuinely needs a game run is task 7's spike, and task 7 only *writes* the spike — reading its result is Plan B's problem.

**Every bare `python tools/ck3.py ...` in this plan runs from `D:/ck3`.** The shell is git-bash on Windows, so that is `cd /d/ck3`. Steps that need a different directory say so on the command line. If a `validate` invocation reports `mod folder does not exist`, you are in the wrong directory, not looking at a real failure.

**Two git repos.** Docs live in `D:/ck3`. The mod lives in `D:/ck3/mods/battle_chronicles`, which is **its own repository**. `git status` from `D:/ck3` will not show mod changes. Every mod commit in this plan runs with `cd D:/ck3/mods/battle_chronicles` first; every tooling commit runs from `D:/ck3`.

**Every script `.txt` in the mod carries a UTF-8 BOM** (`ef bb bf`). The `Write` tool does not add one. Every task that creates a new `.txt` under `mods/battle_chronicles` has an explicit BOM step and a `read_bytes()[:3]` check, and **that check is the only one there is**: `has_bom` is called from `_check_loc_file` only (`validate.py:116`), never from `_check_script_file` (`:93-108`). A script file with no BOM passes `validate` clean and is ignored by the game. Do not skip the byte check on the grounds that `validate` would catch it.

**Two script rules this plan depends on and that are easy to get wrong:**

1. **`flag:$PARAM$ = flag:literal`, never bare `$PARAM$ = literal`.** The bare form substitutes to an unknown key: a silent no-op that `validate` passes.
2. **CK3 does not short-circuit and guarantees no evaluation order among siblings.** A `var:` read in a `limit` evaluates even when the variable is absent. Reads must be nested behind an `exists`; bare `exists` rows *are* safe as siblings.

---

## File structure

| file | state | responsibility |
|---|---|---|
| `tools/ck3lib/validate.py` | modify | three new static checks (tasks 1, 2, 4) |
| `mods/battle_chronicles/common/scripted_triggers/bc_ground_triggers.txt` | **create** | the six ground-band triggers, and nothing else — task 4's check reads this file whole |
| `mods/battle_chronicles/common/scripted_effects/bc_reputation_effects.txt` | modify | `bc_terrain_bucket_effect` rewritten onto the six triggers |
| `mods/battle_chronicles/common/scripted_effects/bc_context_effects.txt` | **create** | `bc_write_ground_effect`, `bc_write_bond_effect` |
| `mods/battle_chronicles/common/scripted_effects/bc_ledger_effects.txt` | modify | anchor scope + three calls in `bc_battle_open_effect`; three removals in `bc_clear_scratch_effect` |
| `mods/battle_chronicles/common/customizable_localization/bc_flavour.txt` | **create** | the spike fragment (Plan B fills this file out) |
| `mods/battle_chronicles/common/modifiers/bc_battle_modifiers.txt` | modify | one new family-2 modifier, `bc_ground_held` |
| `mods/battle_chronicles/common/scripted_effects/bc_scripted_effects.txt` | modify | register `bc_ground_held` in `bc_cleanup_effect` |
| `mods/battle_chronicles/common/scripted_effects/bc_eve_effects.txt` | modify | save `scope:bc_eve_ground` |
| `mods/battle_chronicles/events/bc_eve_events.txt` | modify | foe + ground paragraphs, two contextual options |
| `mods/battle_chronicles/events/bc_aftermath_events.txt` | modify | the foe-relative award in `.0091` |
| `mods/battle_chronicles/common/scripted_triggers/bc_scripted_triggers.txt` | modify | comment only — `bc_facing_nemesis_trigger`'s header gains a caveat once task 6 calls it outside a weight block |
| `mods/battle_chronicles/localization/english/bc_l_english.yml` | modify | fragment keys, eve paragraphs, option text, modifier name |
| `mods/battle_chronicles/README.md` | modify | the "Not yet verified in game" list — tasks 7 and 10. Under this plan's no-testing constraint it is the only handoff channel to the session that does run the game. |

`bc_ground_triggers.txt` is a **new file rather than an append to `bc_scripted_triggers.txt`** for one concrete reason: task 4's validator check counts every `agot_is_*_terrain` mention in the file it reads. A file that contains only the six band triggers makes that check a two-line regex instead of a brace parser. Keep it that way — do not add unrelated triggers to it.

**A naming rule, and it starts here.** `validate.py:174-178` records a key in `def_categories` only the **first** time it sees it, so a customizable-localization definition whose key collides with an earlier-scanned script key would be omitted from task 2's `custom_loc_defs` and every `Custom()` call to it would error falsely — on top of the duplicate-definition warning. `common/customizable_localization` sorts after `common/combat_phase_events` under `iter_files`, so the phase event would win the race. **Every custom-loc definition in this mod ends in a class suffix** — `_core`, `_ground`, `_bond`, `_scale` — which no phase event, effect or trigger key uses. `bc_banner_falls_ground` versus the phase event `bc_banner_falls` is the first instance. Plan B writes about a hundred more; the rule is what keeps them from colliding.

---

### Task 1: validator — custom-loc arms must resolve

`common/customizable_localization/` entries name loc keys with `localization_key = X`. Nothing today checks that `X` exists. This plan is about to create roughly a hundred of them, so the check lands first.

**Files:**
- Modify: `tools/ck3lib/validate.py`

- [ ] **Step 1: Confirm the baseline before touching anything**

Run from `D:/ck3`:

```bash
cd /d/ck3 && python tools/ck3.py validate --strict battle_chronicles
```

Expected: `0 errors, 2 warnings`. If it is not, stop and find out why before continuing — every later step in this plan compares against this number.

- [ ] **Step 2: Add the regex constants**

In `tools/ck3lib/validate.py`, after the `LOC_EXPECTED` line (currently line 37), add:

```python

# Customizable localization: `localization_key = X` inside an arm names a loc
# key that must exist, and `[scope.Custom('name')]` inside a loc value names a
# customizable_localization definition that must exist. CK3 reports neither.
# A missing loc key renders as the raw key; a missing definition renders as
# nothing at all, which is indistinguishable from an arm that did not match.
CUSTOM_LOC_DIR = "common/customizable_localization/"
# `[^\s#]+` and not `\S+`: `localization_key = bc_x# note` is a legal comment
# with no space before it, and `\S+` would capture `bc_x# note`'s first token
# as the key and false-error on it.
LOC_ARM_RE = re.compile(r"^\s*localization_key\s*=\s*([^\s#]+)", re.M)
CUSTOM_CALL_RE = re.compile(r"\.Custom2?\(\s*'([^']+)'")
```

> **RUN CORRECTION, 2026-08-15.** The capture group was `(\S+)` when this task
> was written and the code-quality review caught it: a trailing `#` comment with
> no space before it would be captured as part of the key. The block above is
> what shipped.

- [ ] **Step 3: Add the two scan helpers**

In the same file, immediately after `_check_loc_file` (it ends with `return list(seen)` at line 146), add:

```python


def _scan_matches(path: Path, pattern: re.Pattern[str]) -> list[tuple[int, str]]:
    """Yield (line, capture-group-1) for every match in the file."""
    text = read_text(path)
    return [(text.count("\n", 0, m.start()) + 1, m.group(1)) for m in pattern.finditer(text)]
```

- [ ] **Step 4: Accumulate the arm keys inside `validate_mod`**

In `validate_mod`, the declarations block currently reads:

```python
    defs_by_key: dict[str, tuple[str, int]] = {}
    def_categories: list[tuple[str, str]] = []
    loc_keys: set[str] = set()
    vanilla_overrides: list[str] = []
```

Add two lists to it:

```python
    defs_by_key: dict[str, tuple[str, int]] = {}
    def_categories: list[tuple[str, str]] = []
    loc_keys: set[str] = set()
    vanilla_overrides: list[str] = []
    custom_loc_arms: list[tuple[str, int, str]] = []
    custom_calls: list[tuple[str, int, str]] = []
```

Then, inside the `for relpath, path in iter_files(mod_root):` loop, in the `if ext in (".txt", ...)` branch, **before** the `for key, line in _check_script_file(...)` line, add:

```python
            if relpath.startswith(CUSTOM_LOC_DIR):
                for line, key in _scan_matches(path, LOC_ARM_RE):
                    custom_loc_arms.append((relpath, line, key))
```

- [ ] **Step 5: Emit the errors**

In `validate_mod`, immediately **before** the `if strict:` block, add:

```python
    for relpath, line, key in custom_loc_arms:
        if key not in loc_keys:
            issues.append(
                Issue(ERROR, relpath, line, f"`localization_key = {key}` has no loc entry in this mod")
            )

```

- [ ] **Step 6: Confirm the baseline is unchanged**

The mod has no `common/customizable_localization/` directory yet, so the new code must find nothing.

```bash
cd /d/ck3 && python tools/ck3.py validate --strict battle_chronicles
```

Expected: `0 errors, 2 warnings` — identical to step 1.

- [ ] **Step 7: Prove the check fires by breaking the mod on purpose**

Create the directory and a deliberately broken definition:

```bash
cd /d/ck3 && mkdir -p mods/battle_chronicles/common/customizable_localization
cd /d/ck3 && printf '\xef\xbb\xbfbc_probe_check = {\n\ttype = character\n\ttext = {\n\t\tlocalization_key = bc_this_key_does_not_exist\n\t}\n}\n' > mods/battle_chronicles/common/customizable_localization/zz_probe.txt
python tools/ck3.py validate --strict battle_chronicles
```

Expected: exactly one new ERROR, reading

```
ERROR common/customizable_localization/zz_probe.txt:4: `localization_key = bc_this_key_does_not_exist` has no loc entry in this mod
```

If it does not appear, the check is not wired up — most likely the `if relpath.startswith(CUSTOM_LOC_DIR)` block landed outside the `.txt` branch.

- [ ] **Step 8: Remove the probe and confirm the baseline returns**

```bash
cd /d/ck3 && rm mods/battle_chronicles/common/customizable_localization/zz_probe.txt
python tools/ck3.py validate --strict battle_chronicles
```

Expected: `0 errors, 2 warnings`.

Leave the now-empty `common/customizable_localization/` directory in place; task 7 fills it. Git will not track an empty directory, which is fine.

- [ ] **Step 9: Commit**

```bash
cd /d/ck3 && git add tools/ck3lib/validate.py && git commit -m "$(cat <<'EOF'
tools: validate custom-loc localization_key resolution

Customizable localization arms name loc keys that CK3 renders as the raw
key when missing. The depth work multiplies these tenfold, so the check
lands before the fragments do.
EOF
)"
```

---

### Task 2: validator — `bc_` `Custom()` calls must resolve

The other half of the same blind spot. A `Custom('name')` whose definition is missing renders as *nothing*, which reads exactly like an arm that legitimately did not match — the single worst failure mode for this design, because it is invisible in game as well as in the toolchain.

**Files:**
- Modify: `tools/ck3lib/validate.py`

- [ ] **Step 1: Accumulate the call sites**

In `validate_mod`, the loc branch currently reads:

```python
        elif ext == ".yml" and relpath.startswith("localization/"):
            loc_keys.update(_check_loc_file(relpath, path, issues))
```

Replace it with:

```python
        elif ext == ".yml" and relpath.startswith("localization/"):
            loc_keys.update(_check_loc_file(relpath, path, issues))
            for line, key in _scan_matches(path, CUSTOM_CALL_RE):
                custom_calls.append((relpath, line, key))
```

- [ ] **Step 2: Emit the errors**

Directly after the `custom_loc_arms` loop added in task 1 step 5, add:

```python
    # Only this mod's own keys. A Custom() call naming a vanilla or AGOT
    # definition is legitimate and unresolvable from the mod root alone.
    custom_loc_defs = {key for category, key in def_categories if category.rstrip("/") == CUSTOM_LOC_DIR.rstrip("/")}
    for relpath, line, key in custom_calls:
        if key.startswith("bc_") and key not in custom_loc_defs:
            issues.append(
                Issue(ERROR, relpath, line, f"`Custom('{key}')` has no customizable_localization definition in this mod")
            )

```

The `bc_` filter is load-bearing and is **not** a shortcut. `validate_mod` iterates the mod root only; a call to an AGOT or vanilla definition is correct and would be flagged with no way to satisfy it.

- [ ] **Step 3: Confirm the baseline is unchanged**

```bash
cd /d/ck3 && python tools/ck3.py validate --strict battle_chronicles
```

Expected: `0 errors, 2 warnings`. The mod's loc contains no `Custom(` calls yet.

- [ ] **Step 4: Prove the check fires**

Append a broken call to the loc file — temporarily:

```bash
cd /d/ck3 && printf ' bc_probe_broken_call:0 "[ROOT.Char.Custom('"'"'bc_no_such_fragment'"'"')]"\n' >> mods/battle_chronicles/localization/english/bc_l_english.yml
python tools/ck3.py validate --strict battle_chronicles
```

Expected: exactly one new ERROR, reading

```
ERROR localization/english/bc_l_english.yml:276: `Custom('bc_no_such_fragment')` has no customizable_localization definition in this mod
```

(The line number is whatever line the append landed on.)

- [ ] **Step 5: Remove the probe line and confirm the baseline returns**

Delete the appended line with the `Edit` tool — do not truncate the file with a shell redirect, and do not use `sed -i`, which strips the BOM on some Windows Python/git-bash combinations and would silently make CK3 ignore the whole file.

```bash
cd /d/ck3 && python tools/ck3.py validate --strict battle_chronicles
```

Expected: `0 errors, 2 warnings`. If you see `missing UTF-8 BOM; CK3 will ignore the entire file`, restore the file with `git checkout -- localization/english/bc_l_english.yml` from the mod repo and redo the removal with `Edit`.

- [ ] **Step 6: Commit**

```bash
cd /d/ck3 && git add tools/ck3lib/validate.py && git commit -m "$(cat <<'EOF'
tools: validate bc_ Custom() call resolution

A Custom() whose definition is missing renders as nothing, which is
indistinguishable in game from an arm that did not match. Restricted to
bc_ keys because validate_mod only sees the mod root.
EOF
)"
```

---

### Task 3: extract the six ground-band triggers

`bc_terrain_bucket_effect` (`common/scripted_effects/bc_reputation_effects.txt:267-339`) already contains an **exhaustive six-band partition** over all 23 AGOT terrain helpers. The moments need the same vocabulary. Rather than inventing a second one, extract the six `limit` bodies into named triggers and rewrite the effect onto them.

**This task is behaviour-preserving.** Nothing about `bc_terrain_bucket_effect` changes except that its `limit` bodies move.

**Files:**
- Create: `mods/battle_chronicles/common/scripted_triggers/bc_ground_triggers.txt`
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_reputation_effects.txt:267-339`

- [ ] **Step 1: Create the six triggers**

Write `mods/battle_chronicles/common/scripted_triggers/bc_ground_triggers.txt`:

```
# Battle Chronicles - the six ground bands.
#
# EXTRACTED, NOT INVENTED. These six bodies were the six `limit` blocks of
# bc_terrain_bucket_effect, which had already been verified exhaustive over all
# 23 AGOT terrain helpers - 5 + 5 + 7 + 2 + 2 + 2 = 23, every helper exactly
# once. The reputation streak and the moment prose therefore speak one
# vocabulary by construction rather than by anyone remembering to keep two
# ladders in step.
#
# NEVER `terrain = X` UNDER AGOT. AGOT defines road variants as DISTINCT terrain
# types - `majorroad_hills` is not `hills` - plus nine AGOT-only bases vanilla
# has no key for. ~26% of the map is INVISIBLE to a bare `terrain =` check and
# it fails silently. See bc_reputation_effects.txt:246-254.
#
# THIS FILE HOLDS THESE SIX TRIGGERS AND NOTHING ELSE. tools/ck3lib/validate.py
# checks the partition by counting every `agot_is_*_terrain` mention in this
# file and comparing the multiset against the 23 base helpers. Adding an
# unrelated trigger here that happens to mention a terrain will break that
# check, correctly and confusingly.
#
# SCOPE: PROVINCE. Every caller enters a province scope first - the bucket
# effect via scope:bc_battle_province, the moment writer via
# scope:combat_side.combat.location.

bc_ground_is_desert_trigger = {
	OR = {
		agot_is_drylands_terrain = yes
		agot_is_desert_terrain = yes
		agot_is_desert_mountains_terrain = yes
		agot_is_oasis_terrain = yes
		agot_is_canyon_terrain = yes
	}
}

bc_ground_is_open_trigger = {
	OR = {
		agot_is_farmlands_terrain = yes
		agot_is_plains_terrain = yes
		agot_is_steppe_terrain = yes
		agot_is_floodplains_terrain = yes
		agot_is_urban_terrain = yes
	}
}

bc_ground_is_rough_trigger = {
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

bc_ground_is_forest_trigger = {
	OR = {
		agot_is_forest_terrain = yes
		agot_is_taiga_terrain = yes
	}
}

bc_ground_is_jungle_trigger = {
	OR = {
		agot_is_jungle_terrain = yes
		agot_is_cloudforest_terrain = yes
	}
}

bc_ground_is_winter_trigger = {
	OR = {
		agot_is_frozen_flats_terrain = yes
		agot_is_glacier_terrain = yes
	}
}
```

- [ ] **Step 2: Add the BOM**

```bash
cd /d/ck3 && python -c "import pathlib; p=pathlib.Path('mods/battle_chronicles/common/scripted_triggers/bc_ground_triggers.txt'); b=p.read_bytes(); p.write_bytes(b'\xef\xbb\xbf'+b) if not b.startswith(b'\xef\xbb\xbf') else None"
cd /d/ck3 && python -c "import pathlib; print(pathlib.Path('mods/battle_chronicles/common/scripted_triggers/bc_ground_triggers.txt').read_bytes()[:3])"
```

Expected second line: `b'\xef\xbb\xbf'`.

- [ ] **Step 3: Rewrite the six limits in `bc_terrain_bucket_effect`**

In `mods/battle_chronicles/common/scripted_effects/bc_reputation_effects.txt`, replace each of the six `limit = { OR = { ... } }` blocks inside `bc_terrain_bucket_effect` with a single call. The effect body becomes:

```
bc_terrain_bucket_effect = {
	save_scope_as = bc_terrain_subject
	scope:bc_battle_province = {
		if = {
			limit = { bc_ground_is_desert_trigger = yes }
			scope:bc_terrain_subject = { set_variable = { name = bc_terrain_this value = flag:desert } }
		}
		else_if = {
			limit = { bc_ground_is_open_trigger = yes }
			scope:bc_terrain_subject = { set_variable = { name = bc_terrain_this value = flag:open } }
		}
		else_if = {
			limit = { bc_ground_is_rough_trigger = yes }
			scope:bc_terrain_subject = { set_variable = { name = bc_terrain_this value = flag:rough } }
		}
		else_if = {
			limit = { bc_ground_is_forest_trigger = yes }
			scope:bc_terrain_subject = { set_variable = { name = bc_terrain_this value = flag:forest } }
		}
		else_if = {
			limit = { bc_ground_is_jungle_trigger = yes }
			scope:bc_terrain_subject = { set_variable = { name = bc_terrain_this value = flag:jungle } }
		}
		else_if = {
			limit = { bc_ground_is_winter_trigger = yes }
			scope:bc_terrain_subject = { set_variable = { name = bc_terrain_this value = flag:winter } }
		}
		else = {
			debug_log = "BC: terrain NONE MATCHED"
		}
	}
}
```

**Do not touch the comment block above it** (lines 228-266). It documents why the ladder is exhaustive and why the unreachable `else` logs — all still true.

- [ ] **Step 4: Update one line of that comment so it points at the new home**

Replace the sentence

```
# THE LADDER IS EXHAUSTIVE OVER ALL 23 HELPERS - verified against AGOT's
# 00_agot_terrain_type_triggers.txt, 5 + 5 + 7 + 2 + 2 + 2 = 23, every helper
# once. So the `else` is unreachable in principle, which is exactly why it logs.
```

with

```
# THE LADDER IS EXHAUSTIVE OVER ALL 23 HELPERS - 5 + 5 + 7 + 2 + 2 + 2 = 23,
# every helper once. The six bands now live in bc_ground_triggers.txt and
# tools/ck3.py validate enforces the count. So the `else` is unreachable in
# principle, which is exactly why it logs.
```

- [ ] **Step 5: Verify the extraction lost nothing**

The refactor is only safe if **two** orderings survived: the terrain names inside the six bands, and the six `flag:` values the effect writes. Both matter and they fail differently — a transposed terrain name moves one province, a transposed flag value re-bands every province in two whole categories and silently changes which commander trait `bc_reputation_effect` awards.

```bash
cd /d/ck3/mods/battle_chronicles && python -c "
import re, subprocess
old = subprocess.run(['git','show','HEAD:common/scripted_effects/bc_reputation_effects.txt'],
                     capture_output=True, encoding='utf-8').stdout
cur = open('common/scripted_effects/bc_reputation_effects.txt',encoding='utf-8-sig').read()
new = open('common/scripted_triggers/bc_ground_triggers.txt',encoding='utf-8-sig').read()

def bucket(text):
    b = text[text.index('bc_terrain_bucket_effect = {'):]
    return b[:b.index('bc_terrain_streak_effect')]

a = re.findall(r'agot_is_(\w+)_terrain', bucket(old))
b = re.findall(r'agot_is_(\w+)_terrain', new)
print('terrain names  old', len(a), 'new', len(b), '| identical order:', a == b)

fo = re.findall(r'bc_terrain_this value = flag:(\w+)', bucket(old))
fn = re.findall(r'bc_terrain_this value = flag:(\w+)', bucket(cur))
tn = re.findall(r'limit = \{ bc_ground_is_(\w+)_trigger = yes \}', bucket(cur))
print('flag order     ', fo == fn, '| trigger order matches flags:', tn == fn)
"
```

Expected:

```
terrain names  old 23 new 23 | identical order: True
flag order      True | trigger order matches flags: True
```

The third comparison is the one that catches a transposition: it asserts that the `n`th `limit` in the rewritten ladder calls the trigger named after the `n`th flag it writes.

- [ ] **Step 6: Validate**

```bash
cd /d/ck3 && python tools/ck3.py validate --strict battle_chronicles
```

Expected: `0 errors, 2 warnings`.

- [ ] **Step 7: Commit**

```bash
cd /d/ck3/mods/battle_chronicles && git add common/scripted_triggers/bc_ground_triggers.txt common/scripted_effects/bc_reputation_effects.txt && git commit -m "$(cat <<'EOF'
refactor: extract the six ground bands into named triggers

bc_terrain_bucket_effect already carried an exhaustive partition over the
23 AGOT terrain helpers. The moment prose needs the same vocabulary, so it
becomes six triggers rather than a second, drifting ladder. Behaviour is
unchanged: same names, same order, same bands.
EOF
)"
```

---

### Task 4: validator — the ground partition stays complete

Task 3's partition is only safe while it stays exhaustive, and it can stop being exhaustive from **two directions**: the mod can drop a band, or AGOT can add a terrain. Either way, every province on the orphaned helper falls to an `else` and loses its band, silently. The check therefore has two halves.

**Files:**
- Modify: `tools/ck3lib/validate.py`

- [ ] **Step 1: Add the expected helper list and the mod-side check**

In `tools/ck3lib/validate.py`, after `_scan_matches` (added in task 1 step 3), add:

```python


# The 23 AGOT base terrain helpers, in band order. Held as an explicit list and
# not globbed: the `agot_is_*_terrain` glob matches 26 names, because AGOT also
# ships agot_is_majorroad_terrain, agot_is_minorroad_terrain and
# agot_is_location_valid_vanilla_terrain, which are cross-cutting or
# character-scoped and must not be banded.
BC_GROUND_BASES = [
    "drylands", "desert", "desert_mountains", "oasis", "canyon",
    "farmlands", "plains", "steppe", "floodplains", "urban",
    "hills", "mountains", "wetlands", "the_bog", "taiga_bog", "terraced_hills", "highlands",
    "forest", "taiga",
    "jungle", "cloudforest",
    "frozen_flats", "glacier",
]
BC_GROUND_NON_BASES = {"majorroad", "minorroad", "location_valid_vanilla"}
BC_GROUND_FILE = "common/scripted_triggers/bc_ground_triggers.txt"
AGOT_TERRAIN_FILE = "common/scripted_triggers/00_agot_terrain_type_triggers.txt"
TERRAIN_HELPER_RE = re.compile(r"agot_is_(\w+)_terrain")
TERRAIN_DEF_RE = re.compile(r"^agot_is_(\w+)_terrain\s*=\s*\{", re.M)


def _check_ground_partition(cfg: Config, mod_root: Path, issues: list[Issue]) -> None:
    """Mod-specific: the six ground bands must cover every AGOT base exactly once."""
    path = mod_root / BC_GROUND_FILE
    if not path.is_file():
        return

    found = TERRAIN_HELPER_RE.findall(read_text(path))
    for name in BC_GROUND_BASES:
        if name not in found:
            issues.append(Issue(ERROR, BC_GROUND_FILE, None, f"terrain `{name}` is in no ground band"))
    for name in found:
        if name not in BC_GROUND_BASES:
            issues.append(
                Issue(ERROR, BC_GROUND_FILE, None, f"`agot_is_{name}_terrain` is not a base terrain helper")
            )
    for name in sorted({n for n in found if found.count(n) > 1}):
        issues.append(Issue(ERROR, BC_GROUND_FILE, None, f"terrain `{name}` is in more than one ground band"))

    # THE OTHER HALF: has AGOT grown a terrain the bands do not know about?
    # BC_GROUND_BASES above is a frozen literal and can only ever catch drift on
    # the mod's side. Resolved through the playset the way `ck3.py api` and
    # `ck3.py find` do, last source wins.
    #
    # IT SKIPS LOUDLY, NEVER SILENTLY. A validate run on a machine with no
    # playset configured must say that the cross-check did not happen, because a
    # silent skip is indistinguishable from a pass and this check exists
    # precisely for the case nobody is looking.
    agot: Path | None = None
    for source in playset_sources(cfg):
        candidate = source.root / AGOT_TERRAIN_FILE
        if candidate.is_file():
            agot = candidate
    if agot is None:
        issues.append(
            Issue(WARN, BC_GROUND_FILE, None, f"SKIPPED the AGOT-side check: no enabled source provides {AGOT_TERRAIN_FILE}")
        )
        return
    shipped = {n for n in TERRAIN_DEF_RE.findall(read_text(agot))} - BC_GROUND_NON_BASES
    for name in sorted(shipped - set(BC_GROUND_BASES)):
        issues.append(
            Issue(ERROR, BC_GROUND_FILE, None, f"AGOT ships `agot_is_{name}_terrain`, which is in no ground band")
        )
    for name in sorted(set(BC_GROUND_BASES) - shipped):
        issues.append(
            Issue(ERROR, BC_GROUND_FILE, None, f"band uses `agot_is_{name}_terrain`, which AGOT no longer defines")
        )
```

- [ ] **Step 2: Add the import and call it**

At the top of the file, the import currently reads:

```python
from .sources import SCAN_DIRS, iter_files
```

Change it to:

```python
from .sources import SCAN_DIRS, iter_files, playset_sources
```

Then in `validate_mod`, after `_check_structure(mod_root, issues)`, add:

```python
    _check_ground_partition(cfg, mod_root, issues)
```

- [ ] **Step 3: Confirm the baseline is unchanged**

```bash
cd /d/ck3 && python tools/ck3.py validate --strict battle_chronicles
```

Expected: `0 errors, 2 warnings`. Task 3's file is complete and AGOT's 23 bases match it exactly.

**If you instead see `3 warnings` with `SKIPPED the AGOT-side check`,** the playset is not resolving on this machine. That is a real result, not a failure of this task — record it and continue; the mod-side half still works. Do not "fix" it by removing the warning.

**Steps 4 to 7 prove the four arms.** Note carefully which half of the check each break reaches: the **mod-side** arms compare the trigger file against the frozen `BC_GROUND_BASES` literal, and the **AGOT-side** arms compare that same literal against the AGOT file. So editing `bc_ground_triggers.txt` alone can only ever fire mod-side arms — the AGOT-side ones need `BC_GROUND_BASES` edited instead. Step 7 exists because nothing else in this plan fires them at all.

- [ ] **Step 4: Prove the "no band" arm fires**

With `Edit`, delete the `agot_is_glacier_terrain = yes` line from `bc_ground_is_winter_trigger`, then:

```bash
cd /d/ck3 && python tools/ck3.py validate --strict battle_chronicles
```

Expected: **exactly 1 error** — `` terrain `glacier` is in no ground band ``. Mod-side only; `BC_GROUND_BASES` is untouched, so the AGOT-side comparison still balances.

Revert:

```bash
cd /d/ck3/mods/battle_chronicles && git checkout -- common/scripted_triggers/bc_ground_triggers.txt
```

- [ ] **Step 5: Prove the "not a base" arm fires**

With `Edit`, change `agot_is_taiga_terrain` to `agot_is_majorroad_terrain` in `bc_ground_is_forest_trigger`, then validate.

Expected: **exactly 2 errors** — `` terrain `taiga` is in no ground band `` and `` `agot_is_majorroad_terrain` is not a base terrain helper ``.

Revert as in step 4.

- [ ] **Step 6: Prove the "more than one band" arm fires**

With `Edit`, add `agot_is_hills_terrain = yes` to `bc_ground_is_open_trigger`'s `OR`, then validate.

Expected: **exactly 1 error** — `` terrain `hills` is in more than one ground band ``.

Revert as in step 4.

- [ ] **Step 7: Prove both AGOT-side arms fire**

These are the arms that catch AGOT changing under the mod, and no edit to the mod can reach them. Break the literal instead. With `Edit`, in `tools/ck3lib/validate.py`, add `"marshland"` to the end of `BC_GROUND_BASES` and delete `"glacier"` from it, then:

```bash
cd /d/ck3 && python tools/ck3.py validate --strict battle_chronicles
```

Expected: **exactly 4 errors** —

```
terrain `marshland` is in no ground band
`agot_is_glacier_terrain` is not a base terrain helper
AGOT ships `agot_is_glacier_terrain`, which is in no ground band
band uses `agot_is_marshland_terrain`, which AGOT no longer defines
```

**Two of those four are mod-side**, and that is the point of doing the break this way — one edit reaches all four arms. `BC_GROUND_BASES` feeds both halves of the function, so adding `marshland` to it makes the mod-side "in no ground band" loop fire too (the trigger file does not name `marshland`), and deleting `glacier` from it makes the mod-side "not a base" loop fire (the trigger file still names `glacier`). Do not read the two mod-side lines as noise; if either is missing, the corresponding loop is broken.

**If instead you see `SKIPPED the AGOT-side check`,** the playset does not resolve on this machine. You then get **2 errors and 3 warnings** — the two mod-side lines and the skip warning, with the two AGOT-side lines absent. That is the loud skip working; record it and move on.

Revert **with `Edit`**, restoring `"glacier"` and deleting `"marshland"`. Do not `git checkout -- tools/ck3lib/validate.py` — steps 1 and 2 of this task are not committed yet and that would discard them.

- [ ] **Step 8: Confirm the baseline returns**

```bash
cd /d/ck3 && python tools/ck3.py validate --strict battle_chronicles
```

Expected: `0 errors, 2 warnings`.

- [ ] **Step 9: Commit**

```bash
cd /d/ck3 && git add tools/ck3lib/validate.py && git commit -m "$(cat <<'EOF'
tools: check the Battle Chronicles ground partition stays complete

A terrain helper that falls out of the six bands loses its band silently,
on every province that carries it. Two halves: the 23 bases as an
explicit list, because the agot_is_*_terrain glob also matches three
non-base helpers, and a cross-check against whatever AGOT the playset
actually resolves to, which skips loudly when there is no playset.
EOF
)"
```

---

### Task 5: write the ground onto the commander

Every moment now runs on a commander who knows what he is standing on.

**Files:**
- Create: `mods/battle_chronicles/common/scripted_effects/bc_context_effects.txt`
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_ledger_effects.txt:52-53` and `:507-514`

- [ ] **Step 1: Create the context effects file with the ground writer**

Write `mods/battle_chronicles/common/scripted_effects/bc_context_effects.txt`:

```
# Battle Chronicles - what a moment knows about its battle.
#
# CLASSIFICATION HAPPENS HERE, NEVER IN A LOCALIZATION ARM. A loc arm cannot be
# instrumented: it renders or it does not, and a mis-scoped read renders as
# nothing, which reads exactly like an arm that legitimately did not match.
# Script can log. So script decides which situation obtains and writes a flag,
# and the prose only ever compares flags.
#
# EVERYTHING HERE IS SCRATCH, on the SIDE COMMANDER, cleared by
# bc_clear_scratch_effect at combat end. Nothing here is a saved scope carrying
# meaning: a saved scope is not cleared when a combat ends, so a stale one would
# make the NEXT battle read the LAST battle's ground. Scratch that is missing
# resolves to a fallback arm, which is the correct failure.
#
# CALLED FROM bc_battle_open_effect, on the commander, at the top of every phase
# event. See bc_ledger_effects.txt:28-51 for why that call is unconditional.

# --- the ground -------------------------------------------------------------
#
# THE REMOVE COMES FIRST so that a failure cannot leave the previous phase
# event's band standing. Every path below either writes a band or logs why it
# did not, and an unwritten variable is a fallback arm rather than a lie.
#
# scope:bc_chronicle_subject IS NOT OPTIONAL. Inside
# scope:combat_side.combat.location the scope is a PROVINCE and the variable has
# to land on the COMMANDER. `root` will not do it - a phase event roots on the
# commander for `type = commander` but on the KNIGHT for `type = knight`, and no
# bc_ variable is ever written onto a knight. Same lesson as
# bc_reputation_effects.txt:238-244.
#
# MARKERS, and what each one means on its own:
#   BC: ground <band>       classified. Six of these should sum to the moment
#                           count, minus the two below.
#   BC: ground NONE MATCHED the province matched no band. Impossible while the
#                           partition holds - tools/ck3.py validate enforces it -
#                           so this means AGOT changed under us.
#   BC: ground missing      combat.location did not resolve. A different fix
#                           entirely: the read site, not the bands.
bc_write_ground_effect = {
	remove_variable = bc_battle_ground
	if = {
		limit = { exists = scope:combat_side.combat.location }
		scope:combat_side.combat.location = {
			if = {
				limit = { bc_ground_is_desert_trigger = yes }
				scope:bc_chronicle_subject = { set_variable = { name = bc_battle_ground value = flag:desert } }
				debug_log = "BC: ground desert"
			}
			else_if = {
				limit = { bc_ground_is_open_trigger = yes }
				scope:bc_chronicle_subject = { set_variable = { name = bc_battle_ground value = flag:open } }
				debug_log = "BC: ground open"
			}
			else_if = {
				limit = { bc_ground_is_rough_trigger = yes }
				scope:bc_chronicle_subject = { set_variable = { name = bc_battle_ground value = flag:rough } }
				debug_log = "BC: ground rough"
			}
			else_if = {
				limit = { bc_ground_is_forest_trigger = yes }
				scope:bc_chronicle_subject = { set_variable = { name = bc_battle_ground value = flag:forest } }
				debug_log = "BC: ground forest"
			}
			else_if = {
				limit = { bc_ground_is_jungle_trigger = yes }
				scope:bc_chronicle_subject = { set_variable = { name = bc_battle_ground value = flag:jungle } }
				debug_log = "BC: ground jungle"
			}
			else_if = {
				limit = { bc_ground_is_winter_trigger = yes }
				scope:bc_chronicle_subject = { set_variable = { name = bc_battle_ground value = flag:winter } }
				debug_log = "BC: ground winter"
			}
			else = {
				debug_log = "BC: ground NONE MATCHED"
			}
		}
	}
	else = {
		debug_log = "BC: ground missing"
	}
}
```

- [ ] **Step 2: Add the BOM**

```bash
cd /d/ck3 && python -c "import pathlib; p=pathlib.Path('mods/battle_chronicles/common/scripted_effects/bc_context_effects.txt'); b=p.read_bytes(); p.write_bytes(b'\xef\xbb\xbf'+b) if not b.startswith(b'\xef\xbb\xbf') else None"
cd /d/ck3 && python -c "import pathlib; print(pathlib.Path('mods/battle_chronicles/common/scripted_effects/bc_context_effects.txt').read_bytes()[:3])"
```

Expected: `b'\xef\xbb\xbf'`.

- [ ] **Step 3: Anchor the commander and call the writer**

In `bc_ledger_effects.txt`, `bc_battle_open_effect` currently opens:

```
bc_battle_open_effect = {
	scope:combat_side.enemy_side.side_commander ?= {
		save_scope_as = bc_open_foe
	}
```

Replace with:

```
bc_battle_open_effect = {
	# THE ANCHOR. Every context writer below reaches into a province or reads a
	# foe, and both rebind the scope. This is the only handle on the commander
	# that survives those hops. It carries no meaning of its own - it is an
	# address, not a fact - so it is exempt from the "no saved scope carries
	# meaning" rule in the spec, and a stale one is harmless because it is
	# rewritten in every phase event, before anything reads it. NOT literally at
	# the top of every effect block: the seven commander events call this effect
	# at the top, but the three knight events call it nested inside their
	# `scope:combat_side.side_commander ?=` block (bc_knight_phase_events.txt:101,
	# :169, :232). Upstream of every read is what matters, not the line number.
	save_scope_as = bc_chronicle_subject

	scope:combat_side.enemy_side.side_commander ?= {
		save_scope_as = bc_open_foe
	}
```

- [ ] **Step 4: Call the ground writer**

Still in `bc_battle_open_effect`, immediately **after** the size ladder's closing `else = { ... "BC: size 1" ... }` block and **before** the `# --- housekeeping: drop a dead nemesis` comment, add:

```

	# --- context: what this battle is ---------------------------------------
	#
	# AFTER the size ladder and BEFORE the eve raise at the bottom. The eve reads
	# what these write, and the size ladder writes what one of them reads.
	bc_write_ground_effect = yes
```

- [ ] **Step 5: Clear it at combat end**

In `bc_clear_scratch_effect`, add one line:

```
	remove_variable = bc_battle_foe
	remove_variable = bc_battle_ground
}
```

- [ ] **Step 6: Validate**

```bash
cd /d/ck3 && python tools/ck3.py validate --strict battle_chronicles
```

Expected: `0 errors, 2 warnings`.

- [ ] **Step 7: Confirm the call order by eye**

```bash
cd /d/ck3 && python -c "
import re
t = open('mods/battle_chronicles/common/scripted_effects/bc_ledger_effects.txt',encoding='utf-8-sig').read()
b = t[t.index('bc_battle_open_effect = {'):t.index('# --- the seam')]
for name in ['save_scope_as = bc_chronicle_subject','BC: size 1','bc_write_ground_effect','bc_eve_offer_effect']:
    print(b.index(name), name)
"
```

Expected: four increasing numbers, in that order. If `bc_write_ground_effect` sorts before `BC: size 1` or after `bc_eve_offer_effect`, the insert landed in the wrong place.

- [ ] **Step 8: Confirm both ladders still cover all six bands**

There are now two ladders over the same six triggers — `bc_terrain_bucket_effect` (task 3) and `bc_write_ground_effect` (this task). Task 4's validator check proves the *triggers* partition the terrain space; nothing yet proves either *ladder* still asks all six. A ladder missing an arm silently routes a whole band to its `else`, and `validate` sees nothing wrong.

```bash
cd /d/ck3/mods/battle_chronicles && python -c "
import re
six = ['desert','open','rough','forest','jungle','winter']
for f, name in [('common/scripted_effects/bc_reputation_effects.txt','bc_terrain_bucket_effect'),
                ('common/scripted_effects/bc_context_effects.txt','bc_write_ground_effect')]:
    t = open(f,encoding='utf-8-sig').read()
    b = t[t.index(name + ' = {'):]
    b = b[:b.index('\n}')]
    called = re.findall(r'bc_ground_is_(\w+)_trigger', b)
    print(name, 'calls', called, 'missing', [s for s in six if s not in called])
"
```

Expected:

```
bc_terrain_bucket_effect calls ['desert', 'open', 'rough', 'forest', 'jungle', 'winter'] missing []
bc_write_ground_effect calls ['desert', 'open', 'rough', 'forest', 'jungle', 'winter'] missing []
```

A non-empty `missing` list is a band with no arm. A duplicate in `calls` is a band asked twice, where the second ask is dead code the first arm already swallowed.

- [ ] **Step 9: Commit**

```bash
cd /d/ck3/mods/battle_chronicles && git add common/scripted_effects/bc_context_effects.txt common/scripted_effects/bc_ledger_effects.txt && git commit -m "$(cat <<'EOF'
feat: every moment knows what ground it is fought on

bc_write_ground_effect classifies the combat province into one of the six
bands and writes it as scratch on the side commander. Classification is in
script rather than in a loc arm so that its failures can be logged: three
markers separate "no band matched" from "no province resolved".
EOF
)"
```

---

### Task 6: write the bond and the creed

Who the foe is to the commander, and whether they pray to the same gods.

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_context_effects.txt`
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_ledger_effects.txt`
- Modify: `mods/battle_chronicles/common/scripted_triggers/bc_scripted_triggers.txt` (comment only, step 7)

- [ ] **Step 1: Append the bond writer**

Append to `bc_context_effects.txt`:

```

# --- the foe, and the creed -------------------------------------------------
#
# TWO INDEPENDENT QUESTIONS, TWO INDEPENDENT CHAINS, and that is the whole point
# of the shape below.
#
# bc_battle_bond is an ORDERED, MUTUALLY EXCLUSIVE ladder: a man is a nemesis
# first, kin second, a countryman third. An ordered ladder SWALLOWS every
# question below the arm that matched - so a nemesis of another faith would
# never reach a `heathen` arm, and the faith question would be answerable only
# for foes who are nothing else. Faith therefore gets its OWN if/else beside the
# ladder, not an arm inside it.
#
# THE LADDER HAS A TERMINAL ARM AND IT IS NOT DECORATION. A foe of a different
# culture and the same faith - a Reachman against a Westerman, both of the Seven,
# which is the largest match-up class on the AGOT map - matches nemesis no, kin
# no, countryman no, heathen no. Without the `else` he would leave bc_battle_bond
# unwritten and emit no marker at all, and the single most common case in the
# game would be invisible in the logs.
#
# NESTED, NOT SIBLING, on every read. CK3 does not short-circuit and guarantees
# no evaluation order among siblings, so `exists = var:bc_battle_foe` beside a
# read of var:bc_battle_foe is a missing-variable read on every leaderless enemy
# side. The outer `if` is the guard; everything inside it may read freely.
#
# MARKERS: SIX bond markers for five bond values, plus two creed markers.
# `stranger` is written from two sites and marked differently at each - the
# inner else logs `BC: bond stranger`, the outer else logs `BC: bond nofoe` and
# NOT `BC: bond stranger`. The six are DISJOINT and the SIX sum to the moment
# count. Do not read `nofoe` as a subset of `stranger`; it is the other half of
# it, and treating it as a subset double-counts every leaderless enemy side.
#
# The two creed markers sum to the moment count MINUS `BC: bond nofoe`, because
# a battle with no enemy commander has no creed to compare.
bc_write_bond_effect = {
	if = {
		limit = { exists = var:bc_battle_foe }

		# bc_facing_nemesis_trigger, NOT a hand-rolled comparison.
		# bc_scripted_triggers.txt:244-255 already nests both reads behind their
		# own `exists` in a trigger_if AND carries the `is_alive = yes` row. A
		# hand-rolled `limit = { exists = var:bc_nemesis  var:bc_battle_foe =
		# var:bc_nemesis }` would read var:bc_nemesis as a SIBLING of its own
		# exists, which is the rule at the top of this file, and would drop the
		# liveness row on top of it.
		if = {
			limit = { bc_facing_nemesis_trigger = yes }
			set_variable = { name = bc_battle_bond value = flag:nemesis }
			debug_log = "BC: bond nemesis"
		}
		else_if = {
			limit = { var:bc_battle_foe = { is_close_family_of = scope:bc_chronicle_subject } }
			set_variable = { name = bc_battle_bond value = flag:kin }
			debug_log = "BC: bond kin"
		}
		else_if = {
			limit = { var:bc_battle_foe = { culture = scope:bc_chronicle_subject.culture } }
			set_variable = { name = bc_battle_bond value = flag:countryman }
			debug_log = "BC: bond countryman"
		}
		else_if = {
			limit = { NOT = { var:bc_battle_foe = { faith = scope:bc_chronicle_subject.faith } } }
			set_variable = { name = bc_battle_bond value = flag:heathen }
			debug_log = "BC: bond heathen"
		}
		else = {
			set_variable = { name = bc_battle_bond value = flag:stranger }
			debug_log = "BC: bond stranger"
		}

		# A SEPARATE CHAIN, deliberately. See the header.
		if = {
			limit = { NOT = { var:bc_battle_foe = { faith = scope:bc_chronicle_subject.faith } } }
			set_variable = { name = bc_battle_creed value = flag:heathen }
			debug_log = "BC: creed heathen"
		}
		else = {
			set_variable = { name = bc_battle_creed value = flag:same }
			debug_log = "BC: creed same"
		}
	}
	else = {
		# A leaderless enemy side. `stranger` rather than absent: the prose has a
		# stranger arm and it is the right one to read here, and an absent flag
		# would fall to a fallback that says nothing about the foe at all.
		set_variable = { name = bc_battle_bond value = flag:stranger }
		debug_log = "BC: bond nofoe"
		remove_variable = bc_battle_creed
	}
}
```

- [ ] **Step 2: Confirm `is_close_family_of` exists in the playset**

```bash
cd /d/ck3 && python tools/ck3.py api is_close_family_of
```

Expected: a trigger entry with scope `character` taking a character target. **Do not substitute a name the dump does not contain** — a nonexistent trigger inside a `limit` is not caught by `validate`.

`is_close_family_of` and not the wider `is_close_or_extended_family_of`, which the dump also lists: the wider one reaches cousins, uncles, aunts, nephews and nieces, and `kin` sits directly **above** `countryman` in an ordered ladder. Widening `kin` starves the band below it, and a second cousin across the field is a countryman, not a brother. This is the spec's choice; do not quietly upgrade it.

The other two comparisons in the ladder use the bare-field form — `culture = scope:X.culture`, `faith = scope:X.faith` — rather than a named trigger. That form is what vanilla itself uses; see **vanilla's** `common/scripted_triggers/00_councillor_triggers.txt:402-407` (`same_faith_or_culture_as_councillor_trigger`), which compares `culture` and `faith` against a scoped character's field in exactly this shape. **The vanilla file, not AGOT's** — AGOT overrides the whole file and wins load order, and its own `:402-407` is a different trigger body. Confirm with `python tools/ck3.py find same_faith_or_culture_as_councillor_trigger`, which resolves script keys rather than filenames. Do not swap the form for `has_same_culture_as` / `has_same_faith_as` on instinct: those are separate triggers with their own semantics, and a wrong guess here is a silent no-match, not an error.

- [ ] **Step 3: Call the bond writer**

In `bc_battle_open_effect`, directly after the `bc_write_ground_effect = yes` line added in task 5:

```
	bc_write_ground_effect = yes

	# AFTER the foe block at the top of this effect - it reads var:bc_battle_foe,
	# which that block writes or removes. AFTER the dead-nemesis housekeeping
	# would be better still, but the housekeeping sits below and moving it is a
	# larger change than this needs: bc_facing_nemesis_trigger carries its own
	# `is_alive = yes` row, so a dangling reference fails to match and falls
	# through to the next arm. The consequence is one phase event of a dead man's
	# grudge reading as `countryman` or `stranger` rather than `nemesis`, which is
	# the correct answer anyway.
	bc_write_bond_effect = yes
```

- [ ] **Step 4: Clear both at combat end**

In `bc_clear_scratch_effect`:

```
	remove_variable = bc_battle_ground
	remove_variable = bc_battle_bond
	remove_variable = bc_battle_creed
}
```

- [ ] **Step 5: Validate**

```bash
cd /d/ck3 && python tools/ck3.py validate --strict battle_chronicles
```

Expected: `0 errors, 2 warnings`.

- [ ] **Step 6: Confirm every scratch variable written is also cleared**

```bash
cd /d/ck3 && python -c "
import re
d = 'mods/battle_chronicles/common/scripted_effects/'
ctx = open(d+'bc_context_effects.txt',encoding='utf-8-sig').read()
led = open(d+'bc_ledger_effects.txt',encoding='utf-8-sig').read()
written = set(re.findall(r'set_variable = \{ name = (bc_battle_\w+)', ctx))
clear = led[led.index('bc_clear_scratch_effect = {'):]
clear = clear[:clear.index('}')]
cleared = set(re.findall(r'remove_variable = (bc_battle_\w+)', clear))
print('written', sorted(written))
print('leaked ', sorted(written - cleared))
"
```

Expected:

```
written ['bc_battle_bond', 'bc_battle_creed', 'bc_battle_ground']
leaked  []
```

A non-empty `leaked` list means a scratch variable outlives its battle and the next one reads the last one's answer.

- [ ] **Step 7: Annotate the two claims this task half-falsifies**

`bc_facing_nemesis_trigger` gains its first caller outside a weight block, and its header (`bc_scripted_triggers.txt:227-243`) makes two statements that are now only true of the *other* call sites. Neither is wrong about the trigger's body; both are wrong as blanket statements. Append a fourth paragraph rather than rewriting the first two — the original reasoning still explains why the body looks the way it does:

```
# SINCE bc_write_bond_effect, ONE CALLER IS NOT A WEIGHT BLOCK. That effect - in
# bc_context_effects.txt, called from bc_battle_open_effect - asks this in the
# `limit` of its first `if`. Still a trigger context, so the safety argument
# above holds unchanged, but two things above are now local to the weight call
# sites and not to this trigger:
#   - "TRIGGER contexts only - weight multipliers and is_valid blocks" now also
#     means the limit of an if in an effect.
#   - "IT MISSES THE FIRST ROLL OF EVERY BATTLE" is true of weights and FALSE
#     from bc_write_bond_effect, which runs after the foe block in the same
#     effect and therefore sees bc_battle_foe on the very first moment.
# The second one matters: do not "fix" the first-roll gap by moving the foe
# write, because the bond ladder already depends on the write being upstream.
```

- [ ] **Step 8: Validate again after the comment edit**

```bash
cd /d/ck3 && python tools/ck3.py validate --strict battle_chronicles
```

Expected: `0 errors, 2 warnings`. A comment cannot break a parse, but this file is one an unterminated `#` block would take down quietly, so the check is cheap.

- [ ] **Step 9: Commit**

```bash
cd /d/ck3/mods/battle_chronicles && git add common/scripted_effects/bc_context_effects.txt common/scripted_effects/bc_ledger_effects.txt common/scripted_triggers/bc_scripted_triggers.txt && git commit -m "$(cat <<'EOF'
feat: every moment knows who the foe is and whether they share a faith

bc_battle_bond is an ordered ladder with a terminal stranger arm; the
creed is a separate if/else beside it rather than an arm inside it,
because an ordered ladder swallows every question below the arm that
matched and the faith question has to be answerable for a nemesis too.
EOF
)"
```

---

### Task 7: the spike — one fragment, one moment

The whole prose design rests on one unproven premise: that `[scope.Custom('key')]` renders inside a `send_interface_toast` desc, with the flag comparisons in the arms evaluating against the invoking character. Plan B writes roughly a hundred fragments. This task writes **one**, so that a single game run either retires the premise or kills the design before ninety-nine more keys exist.

**Files:**
- Create: `mods/battle_chronicles/common/customizable_localization/bc_flavour.txt`
- Modify: `mods/battle_chronicles/localization/english/bc_l_english.yml:78`

- [ ] **Step 1: Write the fragment definition**

Write `mods/battle_chronicles/common/customizable_localization/bc_flavour.txt`:

```
# Battle Chronicles - prose fragments.
#
# THE ARMS ONLY COMPARE FLAGS. Every classification decision was made in
# bc_context_effects.txt, where it could be logged. Nothing here decides
# anything; it selects a sentence for a decision already recorded. If a
# fragment renders wrong, the marker in the log says which of the two it was.
#
# type = character ON EVERY DEFINITION, and invoked on a SAVED SCOPE, never on a
# variable-held character. Vanilla's Custom2 second argument is always a saved
# scope or ROOT.Char - a variable-held character has zero uses in vanilla or
# AGOT - so the mod does not use Custom2 at all.
#
# THE FALLBACK ARM IS LAST AND HAS NO TRIGGER. CK3 takes the first matching arm
# in order, so a trigger-less arm anywhere but last would swallow the ones below
# it. The fallback is not decoration: it is what renders when the ground is
# unknown, which is the correct output for a battle whose province did not
# resolve.
#
# NESTED, NOT SIBLING, on the variable read. The bare `exists` row and the
# trigger_if are safe as siblings - only the READ has to be nested, which is
# what the trigger_if does. A `trigger_if` whose `limit` fails evaluates TRUE,
# so the bare `exists` beside it is the row that actually rejects.

# --- SPIKE. The only fragment until a run proves this shape renders. ---------
bc_banner_falls_ground = {
	type = character

	text = {
		localization_key = bc_frag_banner_falls_desert
		trigger = {
			exists = var:bc_battle_ground
			trigger_if = {
				limit = { exists = var:bc_battle_ground }
				var:bc_battle_ground = flag:desert
			}
		}
	}
	text = {
		localization_key = bc_frag_banner_falls_open
		trigger = {
			exists = var:bc_battle_ground
			trigger_if = {
				limit = { exists = var:bc_battle_ground }
				var:bc_battle_ground = flag:open
			}
		}
	}
	text = {
		localization_key = bc_frag_banner_falls_rough
		trigger = {
			exists = var:bc_battle_ground
			trigger_if = {
				limit = { exists = var:bc_battle_ground }
				var:bc_battle_ground = flag:rough
			}
		}
	}
	text = {
		localization_key = bc_frag_banner_falls_forest
		trigger = {
			exists = var:bc_battle_ground
			trigger_if = {
				limit = { exists = var:bc_battle_ground }
				var:bc_battle_ground = flag:forest
			}
		}
	}
	text = {
		localization_key = bc_frag_banner_falls_jungle
		trigger = {
			exists = var:bc_battle_ground
			trigger_if = {
				limit = { exists = var:bc_battle_ground }
				var:bc_battle_ground = flag:jungle
			}
		}
	}
	text = {
		localization_key = bc_frag_banner_falls_winter
		trigger = {
			exists = var:bc_battle_ground
			trigger_if = {
				limit = { exists = var:bc_battle_ground }
				var:bc_battle_ground = flag:winter
			}
		}
	}
	text = {
		localization_key = bc_frag_banner_falls_any
	}
}
```

- [ ] **Step 2: Add the BOM**

```bash
cd /d/ck3 && python -c "import pathlib; p=pathlib.Path('mods/battle_chronicles/common/customizable_localization/bc_flavour.txt'); b=p.read_bytes(); p.write_bytes(b'\xef\xbb\xbf'+b) if not b.startswith(b'\xef\xbb\xbf') else None"
cd /d/ck3 && python -c "import pathlib; print(pathlib.Path('mods/battle_chronicles/common/customizable_localization/bc_flavour.txt').read_bytes()[:3])"
```

Expected: `b'\xef\xbb\xbf'`.

- [ ] **Step 3: Watch the new check fail**

Run `validate` **before** adding the loc keys. This is not a formality: it is the proof that task 1's check is live on real content rather than only on a probe.

```bash
cd /d/ck3 && python tools/ck3.py validate --strict battle_chronicles
```

Expected: **7 errors**, one per arm, each reading `` `localization_key = bc_frag_banner_falls_X` has no loc entry in this mod ``.

- [ ] **Step 4: Add the seven fragments to the loc file**

In `mods/battle_chronicles/localization/english/bc_l_english.yml`, replace line 78:

```
 bc_banner_falls_toast_desc:0 "The standard goes down in the press, and the men nearest it look for it and do not find it."
```

with:

```
 bc_banner_falls_toast_desc:0 "The standard goes down in the press, and the men nearest it look for it and do not find it.[bc_chronicle_subject.Custom('bc_banner_falls_ground')]"

# SPIKE. One fragment set, on one moment, to prove the shape renders before
# ninety-nine more are written. Each BEGINS WITH A SPACE because it is appended
# to a finished sentence - the anchor above deliberately has no space before the
# tag, so that the empty fallback leaves no trailing space. Each is one clause:
# the fragment adds a place to a thing that already happened, it does not
# restate the thing.
 bc_frag_banner_falls_desert:0 " The dust takes it before the sand does."
 bc_frag_banner_falls_open:0 " There is nothing else on that field to look at, and so they all see it go."
 bc_frag_banner_falls_rough:0 " It goes down the slope with the man who carried it."
 bc_frag_banner_falls_forest:0 " The branches have it before the ground does, and it hangs there where no one can reach it."
 bc_frag_banner_falls_jungle:0 " The green closes over it in a moment, as though it had never been raised."
 bc_frag_banner_falls_winter:0 " It lies in the snow, and the snow begins at once to cover it."
 bc_frag_banner_falls_any:0 ""
```

**`bc_chronicle_subject` is the anchor, and the choice is the whole point of the spike.** It is the only scope common to all ten moment call sites — task 5 creates it in `bc_battle_open_effect`, which every phase event calls at the top of its `effect` block. `bc_commander` would render identically here (`bc_commander_phase_events.txt:65` saves it one line above this toast, on the same character) and would prove nothing, because the three `type = knight` events save `bc_knight` instead (`bc_knight_phase_events.txt:80`, `:151`, `:223`) and Plan B's hundred keys all hang off the commander-agnostic anchor. Spiking the wrong scope is a spike that costs a run and answers a question nobody asked. **Do not use `ROOT`** for the same reason: it is the knight in half the families.

`bc_frag_banner_falls_any` is deliberately **empty**. The fallback should add nothing rather than say something vague; the base sentence already stands on its own.

- [ ] **Step 5: Validate**

```bash
cd /d/ck3 && python tools/ck3.py validate --strict battle_chronicles
```

Expected: `0 errors, 2 warnings`. Both new checks are now exercised by real content: seven arms resolve, and one `Custom('bc_banner_falls_ground')` resolves to a definition.

- [ ] **Step 6: Prove the call site would have been caught**

Move the definition out of the mod root — **not** `git stash`, which cannot take an untracked path and would either fail or pop an unrelated stash into the tree:

```bash
cd /d/ck3 && mv mods/battle_chronicles/common/customizable_localization/bc_flavour.txt /tmp/bc_flavour.txt && python tools/ck3.py validate --strict battle_chronicles
```

Expected: **1 error** — `` `Custom('bc_banner_falls_ground')` has no customizable_localization definition in this mod ``. Task 1's check goes quiet with the definition gone (no arms to resolve) and nothing checks for unreferenced loc keys, so this is the only line that moves.

Restore:

```bash
cd /d/ck3 && mv /tmp/bc_flavour.txt mods/battle_chronicles/common/customizable_localization/bc_flavour.txt && python tools/ck3.py validate --strict battle_chronicles
```

Expected: `0 errors, 2 warnings`.

**If the restore fails, the fragments are gone and step 1 has to be redone.** Check the move landed before running anything else:

```bash
cd /d/ck3 && ls -l mods/battle_chronicles/common/customizable_localization/bc_flavour.txt
```

- [ ] **Step 7: Record what the run must show**

Append to `mods/battle_chronicles/README.md`, under its "Not yet verified in game" list:

```markdown
- **The spike fragment.** `bc_banner_falls_ground`, invoked as
  `[bc_chronicle_subject.Custom('bc_banner_falls_ground')]` from
  `bc_banner_falls_toast_desc`. The next run must show a Banner Falls toast
  whose sentence ends with a clause naming the ground, and `probe 'BC: ground'`
  must report a band for the same battle. Read them together:

  | markers | toast | verdict |
  |---|---|---|
  | a band | clause present, matches band | shape proven — Plan B may proceed |
  | a band | no clause at all | either `Custom()` does not render in a toast desc, or `scope:bc_chronicle_subject` is not addressable from loc. Both kill the design as written; before abandoning it, retry once with `bc_commander`, which is saved on the same character fifteen lines above the toast (`bc_commander_phase_events.txt:65`; the toast is at `:80-85`). If that renders, the anchor is the problem and not the mechanism. |
  | a band | clause present, wrong band | the arms read the variable off the wrong character — the anchor resolves but not to the commander who holds the scratch. |
  | `BC: ground missing` | no clause | not a spike failure — `combat.location` did not resolve at a phase event. Fix the read site in `bc_write_ground_effect` and run again. |
```

- [ ] **Step 8: Commit**

```bash
cd /d/ck3/mods/battle_chronicles && git add common/customizable_localization/bc_flavour.txt localization/english/bc_l_english.yml README.md && git commit -m "$(cat <<'EOF'
feat: spike one ground-aware prose fragment on The Banner Falls

The prose design rests on Custom() rendering inside a toast desc with the
arms reading the invoking character's scratch. One fragment set proves or
kills that before the other ninety-nine keys exist. README records what
the next run has to show, per outcome.
EOF
)"
```

---

### Task 8: the eve learns the ground

The opening pop-up renders after its own state may be gone, so it reads saved scopes rather than scratch — the pattern already documented at `bc_scripted_triggers.txt:294-302`: *the freshness comes from the variable, the durability from the scope.*

**Files:**
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_eve_effects.txt`

- [ ] **Step 1: Save the ground scope**

In `bc_eve_offer_effect`, inside the `is_ai = no` gate, directly after the `bc_eve_foe` block and **before** `bc_start_eve_cooldown_effect = yes`:

```
		if = {
			limit = { exists = var:bc_battle_foe }
			var:bc_battle_foe = { save_scope_as = bc_eve_foe }
		}

		# THE EVE READS SCOPES, NOT SCRATCH, and this is the reason. The pop-up
		# is a player event sitting in a queue; its desc renders when the player
		# gets round to it, which can be after the combat has ended and
		# bc_clear_scratch_effect has run. A saved scope is not cleared. The
		# freshness comes from writing it here, one line before the raise; the
		# durability comes from it being a scope.
		#
		# THE HOLE, STATED: a scope IS durable across battles too. A player who
		# leaves one eve unanswered and is offered another would render the
		# second against the first's ground. The eve cooldown makes this rare
		# rather than impossible. `BC: eve ground missing` counting while
		# `BC: eve offered` counts more is what that looks like in the log.
		if = {
			limit = { exists = scope:combat_side.combat.location }
			scope:combat_side.combat.location = { save_scope_as = bc_eve_ground }
		}
		else = {
			debug_log = "BC: eve ground missing"
		}
```

- [ ] **Step 2: Validate**

```bash
cd /d/ck3 && python tools/ck3.py validate --strict battle_chronicles
```

Expected: `0 errors, 2 warnings`.

- [ ] **Step 3: Commit**

```bash
cd /d/ck3/mods/battle_chronicles && git add common/scripted_effects/bc_eve_effects.txt && git commit -m "$(cat <<'EOF'
feat: the eve saves the ground it is fought on

Saved as a scope rather than read from scratch, for the same reason
bc_eve_foe is: the pop-up renders when the player gets round to it, which
can be after the combat ended and scratch was cleared.
EOF
)"
```

---

### Task 9: the `bc_ground_held` modifier

Task 10's new eve option has to apply something, and the file's own header forbids it applying momentum: *"the battle has not started, the eve is about shape, not advantage."* So it applies a family-2 verb modifier, and family 2 has exactly one rule.

**Files:**
- Modify: `mods/battle_chronicles/common/modifiers/bc_battle_modifiers.txt`
- Modify: `mods/battle_chronicles/common/scripted_effects/bc_scripted_effects.txt`
- Modify: `mods/battle_chronicles/localization/english/bc_l_english.yml`

- [ ] **Step 1: Confirm it does not already exist**

```bash
cd /d/ck3 && python tools/ck3.py find bc_ground_held
```

Expected: no definition. If one exists, skip to step 3 and reconcile.

- [ ] **Step 2: Add the modifier**

Append to `mods/battle_chronicles/common/modifiers/bc_battle_modifiers.txt`, after `bc_pursuit`:

```

# Took the broken ground and would not come off it. He cannot be moved and he
# cannot move: a man who has anchored himself to a hillside or a treeline is not
# chasing anybody off it.
#
# BOTH TAGS ARE ALREADY IN USE IN THIS FILE - army_toughness_mult by
# bc_shieldwall, army_pursuit_mult by bc_pursuit - so both are confirmed against
# docs/api/1.19.0.6/modifiers.log by the same evidence the header cites. Nothing
# in this workspace validates a modifier tag; reusing a proven one is the only
# check available.
#
# NOT a second bc_shieldwall. Shieldwall trades damage for toughness and is
# something the line does. This trades PURSUIT for toughness and is something
# the ground does - which is why it is offered only where the ground is worth
# holding.
bc_ground_held = {
	icon = martial_positive
	army_toughness_mult = 0.15
	army_pursuit_mult = -0.15
}
```

- [ ] **Step 3: Correct the header claim this modifier breaks**

`bc_battle_modifiers.txt:8-10` reads:

```
# NO CALL SITE NAMES ONE. They are selected by bc_apply_verb_effect from the
# (KIND, SWING) an event already passes to the seam. If you find yourself adding
# `bc_bloodied` to an event, the KIND table is wrong, not the event.
```

It is already false — the eve's options a and b name `bc_bloodied` and `bc_shieldwall` today, which is what `bc_eve_events.txt:31-37` documents — and tasks 9 and 10 make it falser. Replace those three lines with:

```
# ONE EVENT NAMES THESE DIRECTLY AND IT IS THE ONLY ONE. Everywhere else they
# are selected by bc_apply_verb_effect from the (KIND, SWING) an event already
# passes to the seam. The exception is bc_chronicles.0011, the eve, whose four
# option effects name a modifier because nothing has happened yet - there is no
# moment to route through. See bc_eve_events.txt:31-37, which carries the
# reasoning. If you find yourself naming one from any OTHER event, the KIND
# table is wrong, not the event.
```

- [ ] **Step 4: Register it in `bc_cleanup_effect` — this is the one rule**

`bc_battle_modifiers.txt:28` states it in the imperative: *"EVERY ONE OF THESE MUST APPEAR IN bc_cleanup_effect."* In `mods/battle_chronicles/common/scripted_effects/bc_scripted_effects.txt`, the family-2 block currently ends:

```
	remove_character_modifier = bc_spent_horse
	remove_character_modifier = bc_pursuit
}
```

Change it to:

```
	remove_character_modifier = bc_spent_horse
	remove_character_modifier = bc_pursuit
	remove_character_modifier = bc_ground_held
}
```

**Not** `bc_clear_faltering_effect`, which runs mid-battle from `bc_rally_effect` — the comment five lines above the family-2 block (`bc_scripted_effects.txt`, immediately before `remove_character_modifier = bc_bloodied`) says why, and it applies to this modifier exactly as it does to the other four.

- [ ] **Step 5: Add the loc**

In `bc_l_english.yml`, after `bc_pursuit_desc`:

```
 bc_ground_held:0 "The Ground Is Ours"
 bc_ground_held_desc:0 "They chose the ground and they have not stepped off it. Moving them is a day's work; moving them forward is not happening."
```

- [ ] **Step 6: Verify the modifier resolves and is localized**

`validate` cannot see either of these — `LOC_EXPECTED` (`validate.py:37`) covers only traits, decisions and character interactions, and nothing checks a modifier tag at all. So check both by hand:

```bash
cd /d/ck3 && python tools/ck3.py index -q ; python tools/ck3.py find bc_ground_held ; python tools/ck3.py loc bc_ground_held
```

Separated with `;`, not `&&`, deliberately: `find` exits non-zero when it finds nothing, and chained with `&&` that failure would swallow the `loc` call and read as a quiet pass.

Expected: exactly one definition, in `common/modifiers/bc_battle_modifiers.txt` in this mod, and exactly one loc entry, in this mod. Two of either means a collision with another mod and one of them silently wins. **Zero of either is the failure this step exists to catch** — do not read an empty result as "nothing to report".

- [ ] **Step 7: Verify the cleanup list covers every family-2 modifier**

The one rule, checked mechanically rather than by eye:

```bash
cd /d/ck3/mods/battle_chronicles && python -c "
import re
mods = re.findall(r'^(bc_\w+) = \{', open('common/modifiers/bc_battle_modifiers.txt',encoding='utf-8-sig').read(), re.M)
eff = open('common/scripted_effects/bc_scripted_effects.txt',encoding='utf-8-sig').read()
body = eff[eff.index('bc_cleanup_effect = {'):]
body = body[:body.index('\n}')]
cleared = set(re.findall(r'remove_character_modifier = (bc_\w+)', body))
print('family 2 ', mods)
print('unremoved', [m for m in mods if m not in cleared])
"
```

Expected:

```
family 2  ['bc_bloodied', 'bc_shieldwall', 'bc_spent_horse', 'bc_pursuit', 'bc_ground_held']
unremoved []
```

A non-empty `unremoved` list means a modifier survives combat end for its full 20 days and bleeds into the next battle of the war.

- [ ] **Step 8: Validate**

```bash
cd /d/ck3 && python tools/ck3.py validate --strict battle_chronicles
```

Expected: `0 errors, 2 warnings`.

- [ ] **Step 9: Commit**

```bash
cd /d/ck3/mods/battle_chronicles && git add common/modifiers/bc_battle_modifiers.txt common/scripted_effects/bc_scripted_effects.txt localization/english/bc_l_english.yml && git commit -m "$(cat <<'EOF'
feat: add the bc_ground_held family-2 modifier

Toughness for pursuit: a man anchored to a hillside cannot be moved and
cannot chase. Registered in bc_cleanup_effect in the same commit, which
is the one rule family 2 has, and which nothing in the toolchain can
check for us.
EOF
)"
```

---

### Task 10: the eve says where it is, who is across the field, and offers both

`bc_chronicles.0011` currently branches once (nemesis / stranger) and offers three fixed options. It gains a widened foe paragraph, a new ground paragraph, and two contextual options.

**Two deliberate departures from the spec, recorded here so a later reader does not "fix" them back:**

1. **The eve's foe chain reorders the bond ladder.** It carries all five values, but runs nemesis → kin → **heathen → countryman** → stranger, where `bc_write_bond_effect` runs nemesis → kin → **countryman → heathen** → stranger. Lifting heathen above countryman lets the faith line reach foes who *do* share a culture, which is the more interesting sentence and which the ladder's order makes unreachable. The two orders disagree on purpose: the ladder writes a fact that other systems read, the chain picks a line nobody reads back. Note that this makes the chain's `heathen` a *wider* class than the scratch variable's — do not use one to predict the other.
2. **The ground paragraph names four bands, not six.** `jungle` and `open` collapse into the catch-all. `jungle` is vanishingly rare on the AGOT map outside Sothoryos and the Summer Isles, and the catch-all has to cover an unresolved province anyway, so a band that reads as "the field is what it is" is the honest text for both. The prose fragments (task 7, Plan B) keep all six; this is an eve-only simplification.

**Files:**
- Modify: `mods/battle_chronicles/events/bc_eve_events.txt`
- Modify: `mods/battle_chronicles/localization/english/bc_l_english.yml`
- Modify: `mods/battle_chronicles/README.md`

- [ ] **Step 1: Widen the foe paragraph and add the ground paragraph**

The event's `desc`, **and the three comment lines directly above it at `bc_eve_events.txt:50-52`**, currently read:

```
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
```

Replace **all of it, comment included**, with three assembled paragraphs. The old comment is not preserved: it claims "one desc branch, no new event, no new state", and after this step there are two `first_valid` chains, seven branches, and one new scope (`bc_eve_ground`, task 8). The new comment below says what is true instead.

```
	# THREE PARAGRAPHS, ASSEMBLED: what is happening, who is across the field,
	# what the field is. `desc` blocks concatenate in order; `first_valid` picks
	# exactly one of its children. Each chain ends in a trigger-less child for
	# the same reason the prose fragments have a fallback arm - an eve whose foe
	# or province did not resolve must still render a whole paragraph, not a gap.
	#
	# BOTH NEW CHAINS READ SAVED SCOPES, NOT SCRATCH. See bc_eve_effects.txt: the
	# pop-up renders when the player gets round to it, which can be after the
	# combat ended and bc_clear_scratch_effect ran.
	#
	# THE FOE CHAIN CARRIES THE SAME FIVE VALUES AS THE BOND LADDER BUT IN A
	# DIFFERENT ORDER - nemesis, kin, heathen, countryman, stranger, where the
	# ladder in bc_write_bond_effect runs nemesis, kin, countryman, heathen,
	# stranger. Heathen is lifted above countryman ON PURPOSE: a man of your own
	# people who prays to something else is the more interesting sentence, and
	# under the ladder's order he never gets one. The two orders disagree and
	# that is the intent - the ladder writes a fact, this chain picks a line.
	#
	# THE stranger ARM IS A TRUE FALLBACK AND HAS TO STAY REACHABLE ONLY BY
	# STRANGERS. Its text says "a banner nobody here can name", which is a lie
	# about a countryman. That is why the countryman arm is here and not dropped:
	# without it the largest match-up class on the map falls through to it.
	desc = {
		desc = bc_chronicles.0011.desc_intro
		first_valid = {
			triggered_desc = {
				trigger = { bc_eve_facing_nemesis_trigger = yes }
				desc = bc_chronicles.0011.desc_nemesis
			}
			triggered_desc = {
				trigger = {
					exists = scope:bc_eve_foe
					trigger_if = {
						limit = { exists = scope:bc_eve_foe }
						scope:bc_eve_foe = { is_close_family_of = root }
					}
				}
				desc = bc_chronicles.0011.desc_kin
			}
			triggered_desc = {
				trigger = {
					exists = scope:bc_eve_foe
					trigger_if = {
						limit = { exists = scope:bc_eve_foe }
						NOT = { scope:bc_eve_foe = { faith = root.faith } }
					}
				}
				desc = bc_chronicles.0011.desc_heathen
			}
			triggered_desc = {
				trigger = {
					exists = scope:bc_eve_foe
					trigger_if = {
						limit = { exists = scope:bc_eve_foe }
						scope:bc_eve_foe = { culture = root.culture }
					}
				}
				desc = bc_chronicles.0011.desc_countryman
			}
			desc = bc_chronicles.0011.desc_stranger
		}
		first_valid = {
			triggered_desc = {
				trigger = {
					exists = scope:bc_eve_ground
					trigger_if = {
						limit = { exists = scope:bc_eve_ground }
						scope:bc_eve_ground = { bc_ground_is_rough_trigger = yes }
					}
				}
				desc = bc_chronicles.0011.desc_ground_rough
			}
			triggered_desc = {
				trigger = {
					exists = scope:bc_eve_ground
					trigger_if = {
						limit = { exists = scope:bc_eve_ground }
						scope:bc_eve_ground = { bc_ground_is_forest_trigger = yes }
					}
				}
				desc = bc_chronicles.0011.desc_ground_forest
			}
			triggered_desc = {
				trigger = {
					exists = scope:bc_eve_ground
					trigger_if = {
						limit = { exists = scope:bc_eve_ground }
						scope:bc_eve_ground = { bc_ground_is_winter_trigger = yes }
					}
				}
				desc = bc_chronicles.0011.desc_ground_winter
			}
			triggered_desc = {
				trigger = {
					exists = scope:bc_eve_ground
					trigger_if = {
						limit = { exists = scope:bc_eve_ground }
						scope:bc_eve_ground = { bc_ground_is_desert_trigger = yes }
					}
				}
				desc = bc_chronicles.0011.desc_ground_desert
			}
			desc = bc_chronicles.0011.desc_ground_open
		}
	}
```

Four named bands plus a catch-all, not six plus a fallback: `jungle` is vanishingly rare on the AGOT map outside Sothoryos and the Summer Isles, and `open` is the honest default for both open ground and an unresolved province.

- [ ] **Step 2: Add the two contextual options**

The event currently has three options. Add two more, **after** the existing three so the familiar ones keep their positions:

```
	# TWO CONTEXTUAL OPTIONS. `trigger` on an event option HIDES it when false,
	# which is the behaviour wanted: an option greyed out on every plain would
	# advertise a mechanic the player cannot reach. On open ground against a
	# stranger this event is exactly what it was before.
	#
	# NEITHER APPLIES MOMENTUM. The file header states the rule: the battle has
	# not started, the eve is about shape, not advantage. Both go through
	# bc_add_verb_effect, which is family 2.
	#
	# BOTH TRIGGERS READ SCOPES, so a late-answered eve still renders the same
	# option set it was offered with. That is the whole reason bc_eve_ground is a
	# scope and not scratch.
	#
	# DECISION TABLE for the two markers below. Their denominator is eves
	# ANSWERED, which is neither the moment count nor `BC: eve offered`:
	#   both 0 while `BC: eve offered` counts  the options are never reachable,
	#       or the eve is being dismissed. Not a trigger bug on its own.
	#   `eve option ground` 0 while `BC: eve ground missing` is 0  the ground
	#       scope resolves and the bands still never match: check the trigger.
	#   either counting                        the option was taken. There is no
	#       marker for "offered but not taken"; CK3 gives no hook for it.
	option = {
		name = bc_chronicles.0011.d
		trigger = {
			exists = scope:bc_eve_ground
			trigger_if = {
				limit = { exists = scope:bc_eve_ground }
				scope:bc_eve_ground = {
					OR = {
						bc_ground_is_rough_trigger = yes
						bc_ground_is_forest_trigger = yes
					}
				}
			}
		}
		bc_add_verb_effect = { MODIFIER = bc_ground_held }
		debug_log = "BC: eve option ground"
	}

	# bc_eve_facing_nemesis_trigger already guards its own reads - it is the
	# trigger the desc branch above uses - so this needs no wrapper of its own.
	option = {
		name = bc_chronicles.0011.e
		trigger = { bc_eve_facing_nemesis_trigger = yes }
		bc_add_verb_effect = { MODIFIER = bc_bloodied }
		add_stress = 5
		debug_log = "BC: eve option nemesis"
	}
```

`bc_bloodied` and not a new modifier: going at a man you hate is the same trade the existing option a already makes, and family 2 gains one modifier in this plan, not two.

- [ ] **Step 3: Correct the file header's option count**

The other comment this change falsifies — the one above the `desc` — was already replaced in step 1. This is the remaining one, and it is a load-bearing claim. Comments in this mod are the record; a false one costs a future session a run.

`bc_eve_events.txt:31-37` opens *"TWO OPTIONS APPLY A FAMILY-2 MODIFIER BY NAME, and these are the only call sites in the mod that do."* After step 2 it is four — `.0011.a`, `.b`, `.d`, `.e`. Change the first sentence to:

```
# FOUR OPTIONS APPLY A FAMILY-2 MODIFIER BY NAME, and these are the only call
# sites in the mod that do. Everywhere else the (KIND, SWING) table inside
```

leaving the rest of the paragraph as it stands — the reasoning is unchanged, only the count moved.

- [ ] **Step 4: Add the loc**

Append to `bc_l_english.yml`, in the eve section:

```
 bc_chronicles.0011.desc_kin:0 "The banners across the field are ones he grew up under. Somebody over there taught him to ride."
 bc_chronicles.0011.desc_heathen:0 "They will pray before this, as he will, and not to the same thing."
 bc_chronicles.0011.desc_countryman:0 "The men across the field speak as his do. Whatever is decided here, both sides will tell it in the same tongue."
 bc_chronicles.0011.desc_ground_rough:0 "The ground is broken between here and them. Whoever crosses it will arrive out of order."
 bc_chronicles.0011.desc_ground_forest:0 "The trees begin a hundred paces off and do not end. A line that goes in there stops being a line."
 bc_chronicles.0011.desc_ground_winter:0 "The cold has been in the men since before dawn. It will be in them all day."
 bc_chronicles.0011.desc_ground_desert:0 "There is no water between here and the horizon, and both armies know it."
 bc_chronicles.0011.desc_ground_open:0 "The field is what it is. Nothing on it will decide anything for you."
 bc_chronicles.0011.d:0 "Let the ground fight for us."
 bc_chronicles.0011.e:0 "This time he does not ride away."
```

- [ ] **Step 5: Validate**

```bash
cd /d/ck3 && python tools/ck3.py validate --strict battle_chronicles
```

Expected: `0 errors, 2 warnings`.

- [ ] **Step 6: Check every new key resolves, and resolves only once**

`validate` proves the loc file parses; it does not prove an event's `desc` or `name` points at a key that exists, and a missing one renders as the raw key on screen.

```bash
cd /d/ck3 && python tools/ck3.py index -q ; for k in desc_kin desc_heathen desc_countryman desc_ground_rough desc_ground_forest desc_ground_winter desc_ground_desert desc_ground_open d e; do python tools/ck3.py loc "bc_chronicles.0011.$k"; done
```

`;` and not `&&`, for the reason task 9 gives: `loc` exits non-zero on a miss, and a miss is exactly what this loop is looking for.

Expected: ten results, each with **exactly one** definition, in this mod. A zero means a typo between the event and the loc file; a two means another mod owns the key and one of the two silently wins.

- [ ] **Step 7: Record what the run must show**

Append to `mods/battle_chronicles/README.md`, under its "Not yet verified in game" list:

```markdown
- **The widened eve.** `bc_chronicles.0011` now assembles three paragraphs and
  can offer five options. Nothing static proves a `first_valid` picks the arm
  intended, or that an `option` `trigger` hides rather than greys.

  | markers | screen | verdict |
  |---|---|---|
  | `BC: eve ground <band>` | a third paragraph naming that band | both chains work |
  | `BC: eve ground <band>` | third paragraph reads "The field is what it is" on rough or wooded ground | `scope:bc_eve_ground` is saved but the band triggers do not match through it — check the scope's type, not the triggers |
  | `BC: eve ground missing` | no third paragraph at all | the ground scope never saved. Task 8's insert is in the wrong branch of `bc_eve_offer_effect`. |
  | any | option d visible on open ground | the `trigger` is not gating; every option in the mod is then suspect |
  | `BC: eve option ground` counts | — | the option is reachable and taken. There is no "offered but not taken" marker. |
- **The `bc_ground_held` modifier on a character screen.** It is the fifth
  family-2 modifier and the first added since the cleanup rule was written. The
  run must show it appear when option d is taken and be **gone** by the next
  battle of the same war. If it is still there, `bc_cleanup_effect` did not run
  or did not reach the new line.
```

The award gets its own entry in task 11, not here — it does not exist in the tree yet and the README must not describe code that is not committed.

- [ ] **Step 8: Commit**

```bash
cd /d/ck3/mods/battle_chronicles && git add events/bc_eve_events.txt localization/english/bc_l_english.yml README.md && git commit -m "$(cat <<'EOF'
feat: the eve names the foe and the ground, and offers to use both

The foe paragraph gains kin and faith arms; a third paragraph names one
of four ground bands; two options appear only where they mean something.
Everything reads saved scopes, never scratch, so a late-answered eve
renders the same event it was offered as.
EOF
)"
```

---

### Task 11: the aftermath pays out against the foe

A battle currently leaves momentum, a memory, a counter tick, and sometimes a grudge or a nickname. The one thing missing is that *who you beat* changes what beating him is worth.

**Files:**
- Modify: `mods/battle_chronicles/events/bc_aftermath_events.txt:189-216`
- Modify: `mods/battle_chronicles/README.md`

- [ ] **Step 1: Add the award**

In `bc_chronicles.0091`, inside the `side_commander ?= { if = { limit = { is_alive = yes }` block, after `bc_rivalry_effect = { OUTCOME = win }`:

```
						# WINNER ONLY, .0091 ONLY. There is no symmetric loss
						# term: the loser already pays in the grading, and paying
						# twice for one battle turns a defeat by a heathen into a
						# spiral. Asymmetry here is deliberate and is not an
						# oversight to be tidied up later.
						#
						# TWO FLAGS, READ INDEPENDENTLY. bc_battle_creed picks the
						# CURRENCY; bc_battle_bond = nemesis doubles whichever
						# currency the creed chose.
						#
						# THE CURRENCY QUESTION GOES TO THE CREED AND NOT THE
						# BOND. The bond is an ordered ladder, so a different-
						# faith foe who shares your culture is filed under
						# `countryman` and the bond flag alone cannot answer it.
						# The creed is the orthogonal flag that exists for
						# exactly this read.
						#
						# THE NEMESIS TERM GOES TO THE BOND, because `nemesis`
						# is the top rung of that ladder and the creed knows
						# nothing about grudges. Two questions, two flags, and
						# they are not interchangeable in either direction.
						#
						# NESTED, NOT SIBLING, on both reads. The bond read sits
						# inside its own `if = { limit = { exists = ... } }` and
						# not beside the creed's - they are different variables
						# and `bond` is written on paths where `creed` is not.
						#
						# BEFORE bc_clear_scratch_effect, which removes both.
						# That call is at the bottom of this event and outside
						# this gate; do not move either.
						if = {
							limit = { exists = var:bc_battle_creed }
							if = {
								limit = { var:bc_battle_creed = flag:heathen }
								add_piety = 100
								debug_log = "BC: award piety"
							}
							else = {
								add_prestige = 50
								debug_log = "BC: award prestige"
							}
							if = {
								limit = { exists = var:bc_battle_bond }
								if = {
									limit = { var:bc_battle_bond = flag:nemesis }
									if = {
										limit = { var:bc_battle_creed = flag:heathen }
										add_piety = 100
									}
									else = {
										add_prestige = 50
									}
									debug_log = "BC: award nemesis"
								}
							}
						}
						else = {
							# THE COMMON CASE IS NOT "NO ENEMY COMMANDER". It is
							# a notable battle that produced NO BC MOMENT at all:
							# bc_battle_creed is written by bc_battle_open_effect,
							# which only runs from a phase event, and
							# bc_battle_is_notable_trigger is independent of
							# whether any moment fired. A leaderless enemy side is
							# the OTHER cause and is much rarer.
							#
							# So a large count here is expected and is not a bug.
							# The two causes are separable in the log: cross it
							# against `BC: bond nofoe`, which counts only the
							# leaderless case.
							debug_log = "BC: award no creed"
						}

						# DECISION TABLE for the four award markers, so the next
						# reader does not have to reconstruct it from the plan:
						#
						#   piety + prestige + no creed  = notable wins that
						#       reached here, which is LESS than `BC: win notable`
						#       (that one is logged outside both the
						#       `side_commander ?=` and the `is_alive` gates).
						#   nemesis                      = a SUBSET of piety or
						#       prestige, never a fourth alternative to them.
						#   no creed high, `bond nofoe` low = notable battles with
						#       no moment. Expected.
						#   no creed high, `bond nofoe` high = leaderless enemy
						#       sides. A different question entirely.
						#   piety 0 while `creed heathen` counts = the read is
						#       landing on the wrong character, or this block ran
						#       after bc_clear_scratch_effect.
```

- [ ] **Step 2: Validate**

```bash
cd /d/ck3 && python tools/ck3.py validate --strict battle_chronicles
```

Expected: `0 errors, 2 warnings`.

- [ ] **Step 3: Confirm the award sits before the clear**

```bash
cd /d/ck3 && python -c "
t = open('mods/battle_chronicles/events/bc_aftermath_events.txt',encoding='utf-8-sig').read()
w = t[:t.index('# ---------------------------------------------------------------------------\n# Losing side.')]
print(w.index('BC: award piety'), 'award')
print(w.rindex('bc_clear_scratch_effect'), 'clear')
"
```

Expected: the award index is the smaller number. If it is not, the block landed below `bc_clear_scratch_effect` and reads a variable that has already been removed — which would fire the `BC: award no creed` arm on every single notable win and look like a data problem rather than an ordering one.

- [ ] **Step 4: Record what the run must show**

Append to `mods/battle_chronicles/README.md`, under its "Not yet verified in game" list:

```markdown
- **The foe-relative award.** `probe 'BC: award'` reports which of the two
  currencies paid. The three markers `piety` / `prestige` / `no creed` partition
  the notable wins that reached the award; `nemesis` is a subset of the first
  two. A run where `BC: award no creed` dominates means most notable wins carry
  no BC moment — not that the award is broken. Separate the two causes by
  crossing it against `BC: bond nofoe`, which counts only the leaderless-enemy
  case. `BC: award piety` at zero while `BC: creed heathen` counts is the real
  failure: the read is landing on the wrong character.
```

- [ ] **Step 5: Commit**

```bash
cd /d/ck3/mods/battle_chronicles && git add events/bc_aftermath_events.txt README.md && git commit -m "$(cat <<'EOF'
feat: a notable win pays out against who was beaten

Piety for a foe of another faith, prestige otherwise, doubled against a
nemesis, on the winner only. The currency question goes to
bc_battle_creed because the bond ladder is ordered and swallows the faith
question; the nemesis question goes to bc_battle_bond because the creed
knows nothing about grudges.
EOF
)"
```

---

## The markers this plan adds

**Twenty-three permanent markers.** The spec's §4 table lists the eighteen that instrument classification; this plan adds five more that instrument what is done with it — `BC: award piety`, `BC: award prestige`, `BC: award nemesis`, `BC: eve option ground`, `BC: eve option nemesis`. If the spec's table is ever reconciled against reality, it is the table that is out of date, not the code.

**BUILD CORRECTION (2026-08-15, after implementation).** The table below gives
"moments" as the denominator for the ground, bond and creed markers. **That is
wrong, and the source comments have been corrected; this table has not been
rewritten so the error stays visible.** Those markers are written once per
**phase-event fire**, by `bc_battle_open_effect`. A moment is recorded once per
**seam call**, by `bc_record_moment_effect`. The two differ in *both* directions:

- a phase event that raises a pop-up writes a band and records **no** moment;
- the pop-up option, answered later, records a moment and writes **no** band.

Eight of the eighteen seam call sites are pop-up options, so the offset is not
small. **The correct denominator is the sum of the ten `BC: fired bc_*`
markers.** Read every "moments" in the rows below as "the ten fired". The
`BC: creed` row becomes "the ten fired minus `bond nofoe`". The eve and award
rows are unaffected — their denominators were already right.

See `common/scripted_effects/bc_context_effects.txt:39-49` and `:124-133` for
the corrected statement in the source.

**Four different denominators — do not compare counts across the groups.**

| marker | denominator | what a zero means |
|---|---|---|
| `BC: ground desert` / `open` / `rough` / `forest` / `jungle` / `winter` | moments | that band never came up; jungle and desert legitimately may be zero |
| `BC: ground NONE MATCHED` | moments | should be zero; non-zero means AGOT added a terrain |
| `BC: ground missing` | moments | should be zero; non-zero means `combat.location` does not resolve at a phase event |
| `BC: bond nemesis` / `kin` / `countryman` / `heathen` / `stranger` / `nofoe` | moments | **six disjoint markers, and the six sum to the moment count.** `nofoe` is the leaderless-enemy half of `stranger`, not a subset of it — the outer `else` logs `nofoe` and does *not* also log `stranger` |
| `BC: creed heathen` / `same` | moments minus `bond nofoe` | if the two do not sum to that, the separate-chain shape is wrong |
| `BC: eve ground missing` | **eves offered** | non-zero against a counting `BC: eve offered` is the stale-scope hole |
| `BC: eve option ground` / `eve option nemesis` | **eves answered** | how often the contextual options are even reachable, let alone taken |
| `BC: award piety` / `prestige` / `no creed` | **notable wins with a living, resolvable side commander** | the three sum to *that*, which is **less** than `BC: win notable` |
| `BC: award nemesis` | same | a subset of the piety/prestige firings, not a fourth alternative to them |

The four denominators are: how many moments fired, how many eves were offered, how many eves were answered, and how many notable wins reached the award. In the 44-battle run the first, second and (roughly) fourth were 233, 2 and 36. Comparing a ground count against an eve count says nothing.

**The award denominator is not `BC: win notable`.** That marker is logged at `events/bc_aftermath_events.txt:84`, outside both the `side_commander ?=` and the `is_alive = yes` gates; the award sits inside both. A notable win whose side commander does not resolve, or whose commander died winning, logs `BC: win notable` and none of the award markers. The gap between them is real and is not a bug. (Note the word order of that marker, too — there is no `BC: notable win`.)

---

## Where this plan departs from the spec

Task 10 records its own two departures in its preamble. Two more are global:

- **`bc_ground_held` is a plan invention.** The spec designs the eve's contextual options but names no modifier for the ground option to apply. Family 2 gains exactly one member here, and it reuses two tags already proven in this file rather than introducing a third. If the spec is ever reconciled, this is an addition to it, not a contradiction of it.
- **Task 4 runs after task 3, where spec §8 puts the partition check first.** The check reads `bc_ground_triggers.txt`, and its four deliberate-break steps revert with `git checkout --`, which needs that file committed. Task 3 commits it. Building the check first would mean either an early-return that never exercises, or reverts by hand. The reordering is forced and is not a judgement about which matters more.

## What Plan A does not do

- **The other ninety-nine fragments.** Plan B, gated on task 7's spike rendering.
- **New moment templates.** The spec designs them and defers them: adding call sites moves the realised moment rate, and the tier ladder's thresholds are calibrated against a measured mean that has already drifted once (4.2 → 5.3). New templates land after a run re-measures the rate with the context writes in place.
- **Season, war type, and troop composition.** Designed as inputs, not read by anything in this plan. Ground, foe identity and creed are enough to prove the mechanism; the rest is more of the same shape once it is proven.
- **Anything on the handoff's §3.1 list.** Those are awaiting a run, not awaiting code.

## One thing this plan knowingly leaves ugly

`_check_ground_partition` hardcodes a Battle-Chronicles path into `validate.py`, a module whose docstring says it performs *"static checks for a mod folder"* — any mod folder. It runs on every mod validated and early-returns when the file is absent, so it is harmless, but it is not general and it is not pretending to be. Tasks 1 and 2 are genuinely generic; this one is not.

The alternative — a per-mod check plugin mechanism — is more machinery than one check justifies. If a second mod in this workspace ever needs its own check, that is the moment to build it, and this function is the thing to move.
