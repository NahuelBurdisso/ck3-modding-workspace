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

`validate` is a *syntax and reference* checker. It proves braces balance, that BOMs are present, that loc files parse, and — after tasks 1, 2 and 4 — that custom-loc arms and `Custom()` calls resolve and that the terrain partition is complete. **It cannot prove a trigger evaluates true in game.** It never will. Do not write a step that claims otherwise.

**No step in this plan requires launching CK3.** That is a hard constraint on this plan. Every step's expected output is either a `validate` result, a `git` result, or a `python -c` result. The one thing that genuinely needs a game run is task 7's spike, and task 7 only *writes* the spike — reading its result is Plan B's problem.

**Two git repos.** Docs live in `D:/ck3`. The mod lives in `D:/ck3/mods/battle_chronicles`, which is **its own repository**. `git status` from `D:/ck3` will not show mod changes. Every mod commit in this plan runs with `cd D:/ck3/mods/battle_chronicles` first; every tooling commit runs from `D:/ck3`.

**Every script `.txt` in the mod carries a UTF-8 BOM** (`ef bb bf`). The `Write` tool does not add one. Every task that creates a new `.txt` under `mods/battle_chronicles` has an explicit BOM step, and it is not optional — CK3 does not read the file without it and `validate` will tell you so.

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
| `mods/battle_chronicles/common/scripted_effects/bc_eve_effects.txt` | modify | save `scope:bc_eve_ground` |
| `mods/battle_chronicles/events/bc_eve_events.txt` | modify | ground paragraph + two contextual options |
| `mods/battle_chronicles/events/bc_aftermath_events.txt` | modify | the foe-relative award in `.0091` |
| `mods/battle_chronicles/localization/english/bc_l_english.yml` | modify | fragment keys, eve paragraphs, option text, award reason |

`bc_ground_triggers.txt` is a **new file rather than an append to `bc_scripted_triggers.txt`** for one concrete reason: task 4's validator check counts every `agot_is_*_terrain` mention in the file it reads. A file that contains only the six band triggers makes that check a two-line regex instead of a brace parser. Keep it that way — do not add unrelated triggers to it.

---

### Task 1: validator — custom-loc arms must resolve

`common/customizable_localization/` entries name loc keys with `localization_key = X`. Nothing today checks that `X` exists. This plan is about to create roughly a hundred of them, so the check lands first.

**Files:**
- Modify: `tools/ck3lib/validate.py`

- [ ] **Step 1: Confirm the baseline before touching anything**

Run from `D:/ck3`:

```bash
python tools/ck3.py validate --strict battle_chronicles
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
LOC_ARM_RE = re.compile(r"^\s*localization_key\s*=\s*(\S+)", re.M)
CUSTOM_CALL_RE = re.compile(r"\.Custom2?\(\s*'([^']+)'")
```

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
python tools/ck3.py validate --strict battle_chronicles
```

Expected: `0 errors, 2 warnings` — identical to step 1.

- [ ] **Step 7: Prove the check fires by breaking the mod on purpose**

Create the directory and a deliberately broken definition:

```bash
mkdir -p mods/battle_chronicles/common/customizable_localization
printf '\xef\xbb\xbfbc_probe_check = {\n\ttype = character\n\ttext = {\n\t\tlocalization_key = bc_this_key_does_not_exist\n\t}\n}\n' > mods/battle_chronicles/common/customizable_localization/zz_probe.txt
python tools/ck3.py validate --strict battle_chronicles
```

Expected: exactly one new ERROR, reading

```
ERROR common/customizable_localization/zz_probe.txt:4: `localization_key = bc_this_key_does_not_exist` has no loc entry in this mod
```

If it does not appear, the check is not wired up — most likely the `if relpath.startswith(CUSTOM_LOC_DIR)` block landed outside the `.txt` branch.

- [ ] **Step 8: Remove the probe and confirm the baseline returns**

```bash
rm mods/battle_chronicles/common/customizable_localization/zz_probe.txt
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
python tools/ck3.py validate --strict battle_chronicles
```

Expected: `0 errors, 2 warnings`. The mod's loc contains no `Custom(` calls yet.

- [ ] **Step 4: Prove the check fires**

Append a broken call to the loc file — temporarily:

```bash
printf ' bc_probe_broken_call:0 "[ROOT.Char.Custom('"'"'bc_no_such_fragment'"'"')]"\n' >> mods/battle_chronicles/localization/english/bc_l_english.yml
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
python tools/ck3.py validate --strict battle_chronicles
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
python -c "import pathlib; p=pathlib.Path('mods/battle_chronicles/common/scripted_triggers/bc_ground_triggers.txt'); b=p.read_bytes(); p.write_bytes(b'\xef\xbb\xbf'+b) if not b.startswith(b'\xef\xbb\xbf') else None"
python -c "import pathlib; print(pathlib.Path('mods/battle_chronicles/common/scripted_triggers/bc_ground_triggers.txt').read_bytes()[:3])"
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

The refactor is only safe if the terrain names moved intact. Compare the two sides mechanically:

```bash
cd /d/ck3/mods/battle_chronicles && python -c "
import re, subprocess
old = subprocess.run(['git','show','HEAD:common/scripted_effects/bc_reputation_effects.txt'],capture_output=True,text=True).stdout
new = open('common/scripted_triggers/bc_ground_triggers.txt',encoding='utf-8-sig').read()
body = old[old.index('bc_terrain_bucket_effect'):]
body = body[:body.index('bc_terrain_streak_effect')]
a = re.findall(r'agot_is_(\w+)_terrain', body)
b = re.findall(r'agot_is_(\w+)_terrain', new)
print('old', len(a), 'new', len(b))
print('identical order:', a == b)
"
```

Expected:

```
old 23 new 23
identical order: True
```

Order matters here because the bands are an ordered if/else_if chain: same names in same order means same band assignment for every province.

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

Task 3's partition is only safe while it stays exhaustive. AGOT adds terrains. A helper that falls out of the six bands makes every province on it fall to an `else` and lose its band, silently.

**Files:**
- Modify: `tools/ck3lib/validate.py`

- [ ] **Step 1: Add the expected helper list and the check**

In `tools/ck3lib/validate.py`, after `_scan_matches` (added in task 1 step 3), add:

```python


# The 23 AGOT base terrain helpers, in band order. Held as an explicit list and
# not globbed: the `agot_is_*_terrain` glob matches 26 names, because AGOT also
# ships agot_is_majorroad_terrain, agot_is_minorroad_terrain and
# agot_is_location_valid_vanilla_terrain, which are not bases and must not be
# banded.
BC_GROUND_BASES = [
    "drylands", "desert", "desert_mountains", "oasis", "canyon",
    "farmlands", "plains", "steppe", "floodplains", "urban",
    "hills", "mountains", "wetlands", "the_bog", "taiga_bog", "terraced_hills", "highlands",
    "forest", "taiga",
    "jungle", "cloudforest",
    "frozen_flats", "glacier",
]
BC_GROUND_FILE = "common/scripted_triggers/bc_ground_triggers.txt"
TERRAIN_HELPER_RE = re.compile(r"agot_is_(\w+)_terrain")


def _check_ground_partition(mod_root: Path, issues: list[Issue]) -> None:
    """Mod-specific: the six ground bands must cover every AGOT base once."""
    path = mod_root / BC_GROUND_FILE
    if not path.is_file():
        return
    found = TERRAIN_HELPER_RE.findall(read_text(path))
    missing = [name for name in BC_GROUND_BASES if name not in found]
    extra = [name for name in found if name not in BC_GROUND_BASES]
    dupes = sorted({name for name in found if found.count(name) > 1})
    for name in missing:
        issues.append(Issue(ERROR, BC_GROUND_FILE, None, f"terrain `{name}` is in no ground band"))
    for name in extra:
        issues.append(Issue(ERROR, BC_GROUND_FILE, None, f"`agot_is_{name}_terrain` is not a base terrain helper"))
    for name in dupes:
        issues.append(Issue(ERROR, BC_GROUND_FILE, None, f"terrain `{name}` is in more than one ground band"))
```

- [ ] **Step 2: Call it**

In `validate_mod`, after `_check_structure(mod_root, issues)`, add:

```python
    _check_ground_partition(mod_root, issues)
```

- [ ] **Step 3: Confirm the baseline is unchanged**

```bash
python tools/ck3.py validate --strict battle_chronicles
```

Expected: `0 errors, 2 warnings`. The file task 3 wrote is complete, so the check finds nothing.

- [ ] **Step 4: Prove all three arms fire**

Break the file three ways in turn with `Edit`, running `validate` after each and reverting with `git checkout` from the mod repo between them:

| break | expected new ERROR |
|---|---|
| delete the `agot_is_glacier_terrain = yes` line | `` terrain `glacier` is in no ground band `` |
| change `agot_is_taiga_terrain` to `agot_is_majorroad_terrain` | two errors: `` terrain `taiga` is in no ground band `` and `` `agot_is_majorroad_terrain` is not a base terrain helper `` |
| add `agot_is_hills_terrain = yes` to `bc_ground_is_open_trigger` | `` terrain `hills` is in more than one ground band `` |

Revert after each:

```bash
cd /d/ck3/mods/battle_chronicles && git checkout -- common/scripted_triggers/bc_ground_triggers.txt
```

- [ ] **Step 5: Confirm the baseline returns**

```bash
cd /d/ck3 && python tools/ck3.py validate --strict battle_chronicles
```

Expected: `0 errors, 2 warnings`.

- [ ] **Step 6: Commit**

```bash
cd /d/ck3 && git add tools/ck3lib/validate.py && git commit -m "$(cat <<'EOF'
tools: check the Battle Chronicles ground partition stays complete

A terrain helper that falls out of the six bands loses its band silently,
on every province that carries it. The 23 bases are an explicit list
because the agot_is_*_terrain glob also matches three non-base helpers.
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
python -c "import pathlib; p=pathlib.Path('mods/battle_chronicles/common/scripted_effects/bc_context_effects.txt'); b=p.read_bytes(); p.write_bytes(b'\xef\xbb\xbf'+b) if not b.startswith(b'\xef\xbb\xbf') else None"
python -c "import pathlib; print(pathlib.Path('mods/battle_chronicles/common/scripted_effects/bc_context_effects.txt').read_bytes()[:3])"
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
	# rewritten at the top of every phase event before anything reads it.
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

- [ ] **Step 8: Commit**

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
# MARKERS: five bond values plus two creed values. The five bond markers sum to
# the moment count. The two creed markers sum to the moment count MINUS
# `BC: bond nofoe`, because a battle with no enemy commander has no creed to
# compare.
bc_write_bond_effect = {
	if = {
		limit = { exists = var:bc_battle_foe }

		if = {
			limit = {
				exists = var:bc_nemesis
				var:bc_battle_foe = var:bc_nemesis
			}
			set_variable = { name = bc_battle_bond value = flag:nemesis }
			debug_log = "BC: bond nemesis"
		}
		else_if = {
			limit = { var:bc_battle_foe = { is_close_or_extended_family_of = scope:bc_chronicle_subject } }
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

- [ ] **Step 2: Confirm `is_close_or_extended_family_of` exists in the playset**

```bash
cd /d/ck3 && python tools/ck3.py api is_close_or_extended_family_of
```

Expected: a trigger entry with scope `character` taking a character target. If it is absent, substitute the nearest available relative trigger the `api` dump does list — `is_close_family_of` is the fallback — and update the comment to name the one used. **Do not guess a name that the dump does not contain**; a nonexistent trigger inside a `limit` is not caught by `validate`.

- [ ] **Step 3: Call the bond writer**

In `bc_battle_open_effect`, directly after the `bc_write_ground_effect = yes` line added in task 5:

```
	bc_write_ground_effect = yes

	# AFTER the foe block at the top of this effect - it reads var:bc_battle_foe,
	# which that block writes or removes. AFTER the dead-nemesis housekeeping
	# would be better still, but the housekeeping sits below and moving it is a
	# larger change than this needs: the nemesis arm reads var:bc_nemesis behind
	# an `exists` and a dangling reference simply fails to match, falling through
	# to the next arm. The consequence is one phase event of a dead man's grudge
	# reading as `stranger` rather than `nemesis`, which is the correct answer.
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

- [ ] **Step 7: Commit**

```bash
cd /d/ck3/mods/battle_chronicles && git add common/scripted_effects/bc_context_effects.txt common/scripted_effects/bc_ledger_effects.txt && git commit -m "$(cat <<'EOF'
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
python -c "import pathlib; p=pathlib.Path('mods/battle_chronicles/common/customizable_localization/bc_flavour.txt'); b=p.read_bytes(); p.write_bytes(b'\xef\xbb\xbf'+b) if not b.startswith(b'\xef\xbb\xbf') else None"
python -c "import pathlib; print(pathlib.Path('mods/battle_chronicles/common/customizable_localization/bc_flavour.txt').read_bytes()[:3])"
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
 bc_banner_falls_toast_desc:0 "The standard goes down in the press, and the men nearest it look for it and do not find it. [bc_commander.Custom('bc_banner_falls_ground')]"

# SPIKE. One fragment set, on one moment, to prove the shape renders before
# ninety-nine more are written. Each begins with a space because it is appended
# to a sentence, and each is one clause - the fragment adds a place to a thing
# that already happened, it does not restate the thing.
 bc_frag_banner_falls_desert:0 "The dust takes it before the sand does."
 bc_frag_banner_falls_open:0 "There is nothing else on that field to look at, and so they all see it go."
 bc_frag_banner_falls_rough:0 "It goes down the slope with the man who carried it."
 bc_frag_banner_falls_forest:0 "The branches have it before the ground does, and it hangs there where no one can reach it."
 bc_frag_banner_falls_jungle:0 "The green closes over it in a moment, as though it had never been raised."
 bc_frag_banner_falls_winter:0 "It lies in the snow, and the snow begins at once to cover it."
 bc_frag_banner_falls_any:0 ""
```

`bc_commander` is chosen and not invented: `bc_commander_phase_events.txt:65` saves it in the same `effect` block, one line above the toast. **Do not use `ROOT`** — the moment's desc is rendered from a toast whose root is the phase event's root, which is the knight for `type = knight` events, and using a saved scope keeps one form working for both families when Plan B extends this.

`bc_frag_banner_falls_any` is deliberately **empty**. The fallback should add nothing rather than say something vague; the base sentence already stands on its own.

- [ ] **Step 5: Validate**

```bash
cd /d/ck3 && python tools/ck3.py validate --strict battle_chronicles
```

Expected: `0 errors, 2 warnings`. Both new checks are now exercised by real content: seven arms resolve, and one `Custom('bc_banner_falls_ground')` resolves to a definition.

- [ ] **Step 6: Prove the call site would have been caught**

```bash
cd /d/ck3/mods/battle_chronicles && git stash push common/customizable_localization/bc_flavour.txt && cd /d/ck3 && python tools/ck3.py validate --strict battle_chronicles
```

Expected: **1 error** — `` `Custom('bc_banner_falls_ground')` has no customizable_localization definition in this mod ``.

Restore:

```bash
cd /d/ck3/mods/battle_chronicles && git stash pop && cd /d/ck3 && python tools/ck3.py validate --strict battle_chronicles
```

Expected: `0 errors, 2 warnings`.

- [ ] **Step 7: Record what the run must show**

Append to `mods/battle_chronicles/README.md`, under its "Not yet verified in game" list:

```markdown
- **The spike fragment.** `bc_banner_falls_ground`, invoked as
  `[bc_commander.Custom('bc_banner_falls_ground')]` from
  `bc_banner_falls_toast_desc`. The next run must show a Banner Falls toast
  whose sentence ends with a clause naming the ground, and `probe 'BC: ground'`
  must report a band for the same battle. Read them together:

  | markers | toast | verdict |
  |---|---|---|
  | a band | clause present, matches band | shape proven — Plan B may proceed |
  | a band | no clause at all | `Custom()` does not render here, or the scope is wrong. The design's one unproven premise is false; stop. |
  | a band | clause present, wrong band | the arms read the variable off the wrong character. Check `bc_commander` vs `bc_chronicle_subject`. |
  | `BC: ground missing` | no clause | not a spike failure — `combat.location` did not resolve. Fix the read site, run again. |
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

### Task 9: the eve says where it is and offers the ground

`bc_chronicles.0011` currently branches once (nemesis / stranger) and offers three fixed options. It gains a ground paragraph and one contextual option.

**Files:**
- Modify: `mods/battle_chronicles/events/bc_eve_events.txt`
- Modify: `mods/battle_chronicles/localization/english/bc_l_english.yml`

- [ ] **Step 1: Add the ground paragraph to the desc**

The event's `desc` currently reads:

```
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

Add a third paragraph, appended after the foe paragraph:

```
	# THREE PARAGRAPHS, ASSEMBLED: what is happening, who is across the field,
	# what the field is. `desc` blocks concatenate in order; `first_valid` picks
	# exactly one of its children. The ground block is a `first_valid` with a
	# trigger-less final child for the same reason the fragments have a fallback
	# arm - an eve whose province did not resolve must still render a whole
	# paragraph, not a gap.
	#
	# IT READS scope:bc_eve_ground, NOT scratch. See bc_eve_effects.txt.
	desc = {
		desc = bc_chronicles.0011.desc_intro
		first_valid = {
			triggered_desc = {
				trigger = { bc_eve_facing_nemesis_trigger = yes }
				desc = bc_chronicles.0011.desc_nemesis
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

- [ ] **Step 2: Add the ground option**

The event currently has three options. Add a fourth, **after** the existing three so the familiar ones keep their positions:

```
	# A FOURTH OPTION, GATED ON THE GROUND. It is not offered on open ground -
	# there is nothing there to use - so on most fields this event is unchanged.
	# `trigger` on an option HIDES it when false, which is the behaviour wanted:
	# an option greyed out on every plain would advertise a mechanic the player
	# cannot reach.
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
						bc_ground_is_winter_trigger = yes
					}
				}
			}
		}
		bc_add_verb_effect = { MODIFIER = bc_ground_held }
		debug_log = "BC: eve option ground"
	}
```

- [ ] **Step 3: Confirm `bc_ground_held` exists, or add it**

```bash
cd /d/ck3 && python tools/ck3.py find bc_shieldwall
```

Note the file and shape of the `bc_shieldwall` modifier, then confirm whether `bc_ground_held` exists:

```bash
cd /d/ck3 && python tools/ck3.py find bc_ground_held
```

If it does not exist, add it to the same file as `bc_shieldwall`, copying that modifier's shape exactly and changing only the key and its numbers. **Match the existing modifier's magnitude** — this option is a peer of `bc_shieldwall`, not a stronger one.

- [ ] **Step 4: Add the loc**

Append to `bc_l_english.yml`, in the eve section:

```
 bc_chronicles.0011.desc_ground_rough:0 "The ground is broken between here and them. Whoever crosses it will arrive out of order."
 bc_chronicles.0011.desc_ground_forest:0 "The trees begin a hundred paces off and do not end. A line that goes in there stops being a line."
 bc_chronicles.0011.desc_ground_winter:0 "The cold has been in the men since before dawn. It will be in them all day."
 bc_chronicles.0011.desc_ground_desert:0 "There is no water between here and the horizon, and both armies know it."
 bc_chronicles.0011.desc_ground_open:0 "The field is what it is. Nothing on it will decide anything for you."
 bc_chronicles.0011.d:0 "Let the ground fight for us."
```

Plus the modifier's own loc if step 3 created it, in whatever form `bc_shieldwall`'s takes.

- [ ] **Step 5: Validate**

```bash
cd /d/ck3 && python tools/ck3.py validate --strict battle_chronicles
```

Expected: `0 errors, 2 warnings`.

- [ ] **Step 6: Check for a loc key collision across the playset**

```bash
cd /d/ck3 && python tools/ck3.py index -q && python tools/ck3.py loc bc_chronicles.0011.d
```

Expected: exactly one definition, in this mod. A second would mean another mod owns the key and one of the two renders.

- [ ] **Step 7: Commit**

```bash
cd /d/ck3/mods/battle_chronicles && git add events/bc_eve_events.txt localization/english/bc_l_english.yml common/modifiers/ && git commit -m "$(cat <<'EOF'
feat: the eve names the ground and offers to use it

A third assembled paragraph naming one of four bands, and a fourth option
that is hidden on open ground rather than greyed out there. Both read
scope:bc_eve_ground, never scratch.
EOF
)"
```

---

### Task 10: the aftermath pays out against the foe

A battle currently leaves momentum, a memory, a counter tick, and sometimes a grudge or a nickname. The one thing missing is that *who you beat* changes what beating him is worth.

**Files:**
- Modify: `mods/battle_chronicles/events/bc_aftermath_events.txt:189-216`
- Modify: `mods/battle_chronicles/localization/english/bc_l_english.yml`

- [ ] **Step 1: Add the award**

In `bc_chronicles.0091`, inside the `side_commander ?= { if = { limit = { is_alive = yes }` block, after `bc_rivalry_effect = { OUTCOME = win }`:

```
						# WINNER ONLY, .0091 ONLY. There is no symmetric loss
						# term: the loser already pays in the grading, and paying
						# twice for one battle turns a defeat by a heathen into a
						# spiral. Asymmetry here is deliberate and is not an
						# oversight to be tidied up later.
						#
						# IT READS var:bc_battle_creed AND NOT var:bc_battle_bond.
						# The bond is an ordered ladder, so a nemesis of another
						# faith reads `nemesis` and the faith question is
						# unanswerable from it. The creed is the orthogonal flag
						# that exists for exactly this read.
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
						}
						else = {
							# No enemy commander, so nothing to have beaten.
							# Distinguished from the two arms above because a
							# zero here means something different from a zero
							# there.
							debug_log = "BC: award no creed"
						}
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

- [ ] **Step 4: Commit**

```bash
cd /d/ck3/mods/battle_chronicles && git add events/bc_aftermath_events.txt && git commit -m "$(cat <<'EOF'
feat: a notable win pays out against who was beaten

Piety for a foe of another faith, prestige otherwise, on the winner only.
Reads bc_battle_creed rather than bc_battle_bond because the bond ladder
is ordered and swallows the faith question for a nemesis or a kinsman.
EOF
)"
```

---

## The markers this plan adds

Eighteen permanent markers. **Three different denominators — do not compare counts across the groups.**

| marker | denominator | what a zero means |
|---|---|---|
| `BC: ground desert` / `open` / `rough` / `forest` / `jungle` / `winter` | moments | that band never came up; jungle and desert legitimately may be zero |
| `BC: ground NONE MATCHED` | moments | should be zero; non-zero means AGOT added a terrain |
| `BC: ground missing` | moments | should be zero; non-zero means `combat.location` does not resolve at a phase event |
| `BC: bond nemesis` / `kin` / `countryman` / `heathen` / `stranger` | moments | the five sum to the moment count. `stranger` includes the leaderless case |
| `BC: bond nofoe` | moments | a subset of `bond stranger`'s firings, logged separately |
| `BC: creed heathen` / `same` | moments minus `bond nofoe` | if the two do not sum to that, the separate-chain shape is wrong |
| `BC: eve ground missing` | **eves offered**, not moments | non-zero against a counting `BC: eve offered` is the stale-scope hole |
| `BC: award piety` / `prestige` / `no creed` | **notable wins graded**, not moments | the three sum to `BC: notable win` |

The three denominators are, in order: how many moments fired, how many eves were offered, and how many notable wins were graded. In the 44-battle run these were 233, 2 and 36. Comparing a ground count against an eve count says nothing.

---

## What Plan A does not do

- **The other ninety-nine fragments.** Plan B, gated on task 7's spike rendering.
- **New moment templates.** The spec designs them and defers them: adding call sites moves the realised moment rate, and the tier ladder's thresholds are calibrated against a measured mean that has already drifted once (4.2 → 5.3). New templates land after a run re-measures the rate with the context writes in place.
- **Season, war type, and troop composition.** Designed as inputs, not read by anything in this plan. Ground, foe identity and creed are enough to prove the mechanism; the rest is more of the same shape once it is proven.
- **Anything on the handoff's §3.1 list.** Those are awaiting a run, not awaiting code.
