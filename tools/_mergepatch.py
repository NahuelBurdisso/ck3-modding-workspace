"""Rebuild agot_conflict_merge's whole-file merges from the CURRENTLY installed mods.

CK3 does not merge files: the last mod in load order replaces the whole file. For a file
several mods each ship, every earlier mod's edits are silently dropped. This regenerates a
3-way merge (base = AGOT, one merge per owning mod in load order) so the patch mod, loaded
late, carries all of them.

Re-run after ANY owning mod updates -- the merge pins their content at build time.

    python tools/_mergepatch.py           # report only
    python tools/_mergepatch.py --write   # write into mods/agot_conflict_merge
"""
import json, re, shutil, subprocess, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DD = Path(r"D:/Documents/Paradox Interactive/Crusader Kings III")
PATCH = Path(r"D:/ck3/mods/agot_conflict_merge")
TMP = Path(r"D:/ck3/_mg")

# Every whole-file collision this patch resolves. The 3-way merge BASE is always the
# FIRST owner in load order (AGOT base, or the earliest submod if AGOT does not ship it) --
# that is the trunk every later mod copied and edited.
TARGETS = [
    "common/scripted_effects/07_dlc_ep3_scripted_effects.txt",
    "gui/hud.gui",
    "common/coat_of_arms/template_lists/color_lists.txt",
    "common/on_action/child_birth_on_actions.txt",
    "common/bookmarks/challenge_characters/00_challenge_characters.txt",
    "gfx/interface/illustrations/scripted_illustrations/ingame.txt",
    "history/titles/agot_d_kingsguard.txt",
    "gui/custom_gui/agot_kingsguard.gui",
]

# Files where a LATER-loading mod ships a stale snapshot of the base and nothing of its
# own. Merging is wrong there: the stale mod's diff-vs-base is a revert, so the merge
# would delete the base's newer content. The patch ships the base verbatim instead.
# The value is the allowlist of structural leftovers the stale copy may still contribute;
# anything else it adds means it is NOT a pure stale copy and the entry is invalid.

# Targets where every owner only APPENDS independent top-level blocks. Their insertions
# land in the same end-of-file region, so a normal merge sees one overlapping hunk and
# --theirs gives the whole region to the latest loader, silently dropping the others'
# entries. --union keeps every side. Only safe because the duplicate-top-level-key check
# below would catch a genuine same-key edit being kept twice.
UNION = {
    # AGOT ships 16 entries; AMSB adds 7, Bookmarked adds 5 (its egg1..egg5 "Main Mod
    # Graveyard" Aegons), A Time for Wolves Fix adds 12. The 16 shared keys are exactly
    # AGOT's, so these three are independent extensions of the base, not of each other.
    "common/bookmarks/challenge_characters/00_challenge_characters.txt",
}

# Per target, owners whose content a LATER owner already contains in full -- purpose-built
# compatches between two other mods. Merging both the inputs and the compatch against the
# base counts every shared addition twice. Skipped as merge inputs, still verified: their
# unique-vs-base lines must reach the output through the compatch.
SUPERSEDED = {
    # Additional Models / AGOT+ Compatch [9] IS AGOT+ [4] + AMSB [8] for this file:
    # 456 + 9 == 465 unique-vs-base lines exactly.
    "gfx/interface/illustrations/scripted_illustrations/ingame.txt": {
        "AGOT+", "AGOT Additional Models and Special Buildings",
    },
}

RESTORE = {
    # Fire and Blood [3] ships a 508-line pre-refactor AGOT copy vs AGOT's 877. AGOT moved
    # the leave-council button into `block "replace_councillor"` inside the councillor
    # template; F&B still carries the 7 old per-slot blockoverrides. Zero fab_/F&B tokens
    # in the file -- it is an accidental leftover, not content.
    "gui/custom_gui/agot_kingsguard.gui": {'blockoverride "replace_councillor"'},
}
WRITE = "--write" in sys.argv


def playset():
    dlc = json.loads((DD / "dlc_load.json").read_text(encoding="utf-8-sig"))
    out = []
    for rel in dlc["enabled_mods"]:
        p = DD / rel
        if not p.exists():
            continue
        t = p.read_text(encoding="utf-8-sig", errors="replace")
        n = re.search(r'^name\s*=\s*"([^"]+)"', t, re.M)
        d = re.search(r'^path\s*=\s*"([^"]+)"', t, re.M)
        out.append((n.group(1) if n else rel, Path(d.group(1)) if d else None))
    return out


def norm(p):
    """Read as text, strip BOM, normalise to LF. Returns (text, had_bom)."""
    b = p.read_bytes()
    bom = b.startswith(b"\xef\xbb\xbf")
    if bom:
        b = b[3:]
    return b.decode("utf-8", errors="replace").replace("\r\n", "\n"), bom


def strip_comments(t):
    """Drop `#` line comments, but not a `#` inside a double-quoted string -- CK3 format
    codes look like `default_format = "#high;italic"`."""
    out = []
    for line in t.splitlines():
        q = False
        for j, ch in enumerate(line):
            if ch == '"':
                q = not q
            elif ch == "#" and not q:
                line = line[:j]
                break
        out.append(line)
    return "\n".join(out)


def braces(t):
    # Count only real script braces. Counting them inside comments made every file look
    # unbalanced (AGOT's ingame.txt reads +102 raw, +0 for real) and turned the check into
    # noise -- Bookmarked's commented-out `# 7999.4.1 = {` lines were the classic false hit.
    t = strip_comments(t)
    return t.count("{") - t.count("}")


TMP.mkdir(exist_ok=True)
mods = playset()
rc_total = 0

for rel in TARGETS:
    # NEVER treat this patch as an owner of its own target. Feeding last build's output
    # back in is only harmless while the merge is idempotent; the moment a new owning mod
    # appears it duplicates shared hunks and, because the patch loads last, its stale copy
    # wins the overlaps and silently drops the new mod's lines.
    owners = [(i, n, p) for i, (n, p) in enumerate(mods)
              if p and (p / rel).exists() and p.resolve() != PATCH.resolve()]
    verify = owners
    skip = SUPERSEDED.get(rel, set())
    if skip:
        owners = [o for o in owners if o[1] not in skip]
    print("=" * 78)
    print(rel)
    if skip:
        print("  superseded, not merged directly: " + ", ".join(sorted(skip)))
    if len(owners) < 2:
        print(f"  only {len(owners)} owner in the live playset -- no collision, nothing to merge")
        if WRITE and (PATCH / rel).exists():
            print(f"  STALE FILE IN PATCH: {PATCH / rel} -- delete it, its inputs are gone")
        continue
    base = owners[0]
    print("  load order: " + " -> ".join(f"[{i}] {n}" for i, n, _ in owners))
    print(f"  base: [{base[0]}] {base[1]}   winner today: [{owners[-1][0]}] {owners[-1][1]}")

    base_text, base_bom = norm(base[2] / rel)

    if rel in RESTORE:
        allowed = RESTORE[rel]
        bset = {l.strip() for l in base_text.splitlines() if l.strip()}
        ok = True
        for i, n, p in owners[1:]:
            ot, _ = norm(p / rel)
            extra = sorted({l.strip() for l in ot.splitlines() if l.strip()} - bset - allowed)
            print(f"  RESTORE: [{i}] {n[:40]:40} adds {len(extra)} line(s) beyond the allowlist")
            for l in extra[:8]:
                print("        !", l[:120])
            if extra:
                ok = False
        print(f"  lines: base {len(base_text.splitlines())}  "
              f"stale winner {len(norm(owners[-1][2] / rel)[0].splitlines())}")
        print("  RESULT:", "PASS (ship base verbatim)" if ok
              else "FAIL -- not a pure stale copy, remove from RESTORE and merge it")
        rc_total += 0 if ok else 1
        if WRITE and ok:
            dst = PATCH / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            data = base_text.encode("utf-8")
            if norm(owners[-1][2] / rel)[1] or base_bom:
                data = b"\xef\xbb\xbf" + data
            dst.write_bytes(data)
            print("  WROTE", dst)
        elif WRITE:
            print("  NOT WRITTEN (checks failed)")
        continue

    bp = TMP / "base.txt"
    bp.write_text(base_text, encoding="utf-8", newline="\n")

    cur = TMP / "cur.txt"
    cur.write_text(base_text, encoding="utf-8", newline="\n")
    conflicts = {}

    for i, n, p in owners:
        if i == base[0]:
            continue
        other_text, _ = norm(p / rel)
        op = TMP / "other.txt"
        op.write_text(other_text, encoding="utf-8", newline="\n")
        # later loader wins a genuine overlap: --theirs keeps `other`, and we walk
        # owners in ascending load order, so the last writer of an overlap is the
        # latest-loading mod -- identical to what the game does today.
        r = subprocess.run(
            ["git", "merge-file", "-p", "--union" if rel in UNION else "--theirs",
             "-L", "merged", "-L", base[1], "-L", n,
             str(cur), str(bp), str(op)],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode < 0 or r.stdout == "":
            print(f"  !! merge-file failed for {n}: rc={r.returncode} {r.stderr[:200]}")
            sys.exit(1)
        if r.returncode > 0:
            conflicts[n] = r.returncode
        cur.write_text(r.stdout, encoding="utf-8", newline="\n")
        print(f"    merged [{i}] {n:42} overlaps auto-resolved: {r.returncode}")

    merged = cur.read_text(encoding="utf-8")

    # ---- verification -------------------------------------------------------
    print("  --- checks ---")
    ok = True
    if "<<<<<<<" in merged or ">>>>>>>" in merged:
        print("  FAIL conflict markers left in output")
        ok = False
    bb, bm = braces(base_text), braces(merged)
    print(f"  brace delta: base {bb:+d}  merged {bm:+d}  {'OK' if bb == bm else 'DIFFERS'}")
    if bb != bm:
        ok = False
    # every owner's unique lines must survive. Hoist both line-sets out of the loops --
    # rebuilding them per line is O(n^2) and never returns on ingame.txt's 20k lines.
    bset = {x.strip() for x in base_text.splitlines()}
    mset = {x.strip() for x in merged.splitlines()}
    for i, n, p in verify:
        ot, _ = norm(p / rel)
        uniq = [s for l in ot.splitlines() if (s := l.strip()) and s not in bset]
        missing = [l for l in uniq if l not in mset]
        print(f"  [{i}] {n[:40]:40} unique-vs-base {len(uniq):5}  missing from merge {len(missing)}")
        for l in missing[:5]:
            print("        -", l[:120])
        if missing:
            ok = False
    # A duplicated top-level key is the failure mode of an append-heavy merge: CK3 keeps
    # only one definition, so the merge would look complete while half of it is dead.
    # Script databases only -- in .gui, top-level `widget = {}` / `container = {}` are
    # element TYPES and repeat legitimately, so the check is meaningless there.
    if rel.endswith(".txt"):
        tl = re.findall(r"^(\w+)\s*=\s*\{", strip_comments(merged), re.M)
        dupes = sorted({k for k in tl if tl.count(k) > 1})
        print(f"  top-level keys: {len(tl)}  duplicated: {len(dupes)}")
        for k in dupes[:8]:
            print("        !", k)
        if dupes:
            ok = False

    for marker in ("MDE Modified",):
        print(f"  marker {marker!r}: {merged.count(marker)}")
    print(f"  lines: base {len(base_text.splitlines())}  merged {len(merged.splitlines())}")
    print("  RESULT:", "PASS" if ok else "FAIL")
    rc_total += 0 if ok else 1

    if WRITE and ok:
        dst = PATCH / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        data = merged.encode("utf-8")
        # Reproduce the BOM convention of the file the game loads TODAY (the last owner),
        # not the base's -- AGOT ships color_lists.txt without a BOM but House Founders,
        # which currently wins it, ships one, and CK3 logs lexer.cpp:306 without it.
        if norm(owners[-1][2] / rel)[1] or base_bom:
            data = b"\xef\xbb\xbf" + data
        dst.write_bytes(data)
        print("  WROTE", dst)
    elif WRITE:
        print("  NOT WRITTEN (checks failed)")

shutil.rmtree(TMP, ignore_errors=True)
sys.exit(rc_total)
