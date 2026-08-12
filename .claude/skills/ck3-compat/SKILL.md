---
name: ck3-compat
description: Diagnose and fix Crusader Kings III mod conflicts - two mods overriding the same file, wrong load order, missing dependencies, broken playset. Use when a mod stops working after adding another, or when auditing a playset.
---

# Resolve CK3 mod conflicts

## 1. Audit the playset

    python D:/ck3/tools/ck3.py playset list
    python D:/ck3/tools/ck3.py playset audit

`audit` reports missing content folders, duplicate entries and mods whose
`supported_version` does not match the installed game. Wildcards like `1.*` are
treated as matching.

## 2. Find file collisions

    python D:/ck3/tools/ck3.py conflicts

Each entry lists every mod claiming that path, in load order. **The last one
wins outright** — the others' versions of that file do not load at all.

Vanilla and the configured base mod are filtered out, because a submod
overriding its own base is expected. Add `--include-base` to see those too.

Triage each collision:
- **Patch pairs** (`X` and `X compatch`) are fine as long as the patch loads
  after its target. Fix with `playset move`.
- **Unrelated mods on the same file** are the real risk. They need a merge.

## 3. Inspect a specific file

    python D:/ck3/tools/ck3.py where <relative/path.txt>

Read each version and work out whether the edits are in different regions.

## 4. Merge, when both sets of changes are needed

Use the base mod's copy as the merge base — submods usually copy a file wholesale
and edit different regions, so a 3-way merge comes out clean:

    git merge-file -p <mod_a_copy> <base_copy> <mod_b_copy> > merged.txt

Put the result in a patch mod that loads **last**:

    python D:/ck3/tools/ck3.py new "My Conflict Merge" --agot --deploy
    # place merged files at the same relative paths
    python D:/ck3/tools/ck3.py validate my_conflict_merge
    python D:/ck3/tools/ck3.py playset add my_conflict_merge   # append = last

Verify the merge: brace balance (validate does this) and that each input's
unique lines survived. Note that some mods comment out brace-opening lines, so a
legitimately imbalanced-looking file may be correct — check why before "fixing".

## 5. Reorder rather than merge, when only order is wrong

    python D:/ck3/tools/ck3.py playset move <slug-or-id> --position <n>

Every playset write backs up `dlc_load.json` to `index/playset-backups/` first.
**Confirm reordering with the user** — it changes what their game loads. Warn
them that opening the Paradox launcher regenerates `dlc_load.json` and discards
these edits; launch `binaries/ck3.exe` directly instead.

## 6. Verify

    python D:/ck3/tools/ck3.py launch --clear-logs
    python D:/ck3/tools/ck3.py errors
