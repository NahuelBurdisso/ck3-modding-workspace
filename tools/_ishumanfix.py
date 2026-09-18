"""Rebuild the merged `is_human` scripted trigger for agot_conflict_merge.

Unlike _mergepatch.py's targets this is NOT a whole-file collision. AGOT, DireWolves and
AGOT Great Councils each define `is_human` in a DIFFERENTLY NAMED file under
common/scripted_triggers/, so no file is overwritten and the collision-by-filename scan
sees nothing -- yet CK3 keeps only the LAST definition of a duplicate top-level key, so
whichever mod loads last silently wins and the others' additions die.

Both additions are real:
    DireWolves       NOT = { has_trait = direwolf }              (direwolves aren't people)
    Great Councils   NOT = { has_character_flag = zzz_great_councils_disable }

This extracts each owner's definition, 3-way merges them against AGOT's, and writes the
union as a single definition the patch mod ships. The patch loads last, so its copy wins.

Re-run after ANY owning mod updates -- the merge pins their content at build time.

    python tools/_ishumanfix.py           # report only
    python tools/_ishumanfix.py --write   # write into mods/agot_conflict_merge
"""
import json, re, shutil, subprocess, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DD = Path(r"D:/Documents/Paradox Interactive/Crusader Kings III")
PATCH = Path(r"D:/ck3/mods/agot_conflict_merge")
TMP = Path(r"D:/ck3/_ih")
OUT_REL = "common/scripted_triggers/zzz_merge_is_human.txt"
KEY = "is_human"
SCAN_DIR = "common/scripted_triggers"

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
    b = p.read_bytes()
    if b.startswith(b"\xef\xbb\xbf"):
        b = b[3:]
    return b.decode("utf-8", errors="replace").replace("\r\n", "\n")


def strip_comments(t):
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
    t = strip_comments(t)
    return t.count("{") - t.count("}")


def extract(text, key):
    """Return the full `key = { ... }` top-level block, or None.

    Brace counting ignores comments -- a commented-out brace would end the block early.
    """
    lines = text.split("\n")
    start = None
    for i, ln in enumerate(lines):
        if re.match(rf"^{re.escape(key)}\s*=\s*\{{", strip_comments(ln)):
            start = i
            break
    if start is None:
        return None
    depth = 0
    for i in range(start, len(lines)):
        s = strip_comments(lines[i])
        depth += s.count("{") - s.count("}")
        if depth <= 0 and i > start - 1:
            return "\n".join(lines[start:i + 1])
    return None


TMP.mkdir(exist_ok=True)
owners = []
for idx, (name, root) in enumerate(playset()):
    if not root or not root.exists() or root.resolve() == PATCH.resolve():
        continue
    d = root / SCAN_DIR
    if not d.exists():
        continue
    for f in sorted(d.rglob("*.txt")):
        text = norm(f)
        if not re.search(rf"^{KEY}\s*=\s*\{{", strip_comments(text), re.M):
            continue
        blk = extract(text, KEY)
        if blk is None:
            print(f"  !! [{idx}] {name}: found {KEY} in {f.name} but could not extract it")
            sys.exit(1)
        owners.append((idx, name, f, blk))

print("=" * 78)
print(f"{KEY}  (top-level key defined in {len(owners)} enabled mod(s))")
for i, n, f, blk in owners:
    print(f"  [{i:3}] {n:45} {f.name}  ({len(blk.splitlines())} lines)")

if len(owners) < 2:
    print(f"  only {len(owners)} owner -- no clash, nothing to merge")
    if WRITE and (PATCH / OUT_REL).exists():
        print(f"  STALE FILE IN PATCH: {PATCH / OUT_REL} -- delete it, its inputs are gone")
    shutil.rmtree(TMP, ignore_errors=True)
    sys.exit(0)

base_i, base_n, base_f, base_blk = owners[0]
print(f"  base: [{base_i}] {base_n}   winner today: [{owners[-1][0]}] {owners[-1][1]}")

bp = TMP / "base.txt"
bp.write_text(base_blk + "\n", encoding="utf-8", newline="\n")
cur = TMP / "cur.txt"
cur.write_text(base_blk + "\n", encoding="utf-8", newline="\n")

for i, n, f, blk in owners[1:]:
    op = TMP / "other.txt"
    op.write_text(blk + "\n", encoding="utf-8", newline="\n")
    r = subprocess.run(
        ["git", "merge-file", "-p", "--theirs", "-L", "merged", "-L", base_n, "-L", n,
         str(cur), str(bp), str(op)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode < 0 or r.stdout == "":
        print(f"  !! merge-file failed for {n}: rc={r.returncode} {r.stderr[:200]}")
        sys.exit(1)
    cur.write_text(r.stdout, encoding="utf-8", newline="\n")
    print(f"    merged [{i}] {n:42} overlaps auto-resolved: {r.returncode}")

merged = cur.read_text(encoding="utf-8")

print("  --- checks ---")
ok = True
if "<<<<<<<" in merged or ">>>>>>>" in merged:
    print("  FAIL conflict markers left in output")
    ok = False

bb, bm = braces(base_blk), braces(merged)
print(f"  brace delta: base {bb:+d}  merged {bm:+d}  {'OK' if bb == bm == 0 else 'DIFFERS'}")
if not (bb == bm == 0):
    ok = False

bset = {x.strip() for x in base_blk.splitlines()}
mset = {x.strip() for x in merged.splitlines()}
for i, n, f, blk in owners:
    uniq = [s for l in blk.splitlines() if (s := l.strip()) and s not in bset]
    missing = [l for l in uniq if l not in mset]
    print(f"  [{i:3}] {n[:40]:40} unique-vs-base {len(uniq):3}  missing from merge {len(missing)}")
    for l in uniq:
        print(f"        + {l[:110]}")
    for l in missing[:5]:
        print(f"        - MISSING {l[:110]}")
    if missing:
        ok = False

# The merged block must still be exactly ONE definition of exactly this key: a duplicate
# would mean CK3 keeps only one of them and half the merge is dead on arrival.
tl = re.findall(r"^(\w+)\s*=\s*\{", strip_comments(merged), re.M)
print(f"  top-level keys in output: {tl}")
if tl != [KEY]:
    print(f"  FAIL output must define exactly [{KEY!r}]")
    ok = False

print(f"  lines: base {len(base_blk.splitlines())}  merged {len(merged.splitlines())}")
print("  RESULT:", "PASS" if ok else "FAIL")

if WRITE and ok:
    dst = PATCH / OUT_REL
    dst.parent.mkdir(parents=True, exist_ok=True)
    header = (
        f"# GENERATED by tools/_ishumanfix.py -- do not hand-edit, re-run after any owner updates.\n"
        f"# Merged `{KEY}` from: " + ", ".join(f"[{i}] {n}" for i, n, _, _ in owners) + "\n"
        f"# Each defines {KEY} in its own filename, so nothing collides by file and the last\n"
        f"# mod loaded silently wins the key. This patch loads last and carries every owner's edit.\n"
    )
    # AGOT script files carry a UTF-8 BOM and this block is AGOT-derived; match it.
    dst.write_bytes(b"\xef\xbb\xbf" + (header + merged.rstrip("\n") + "\n").encode("utf-8"))
    print("  WROTE", dst)
elif WRITE:
    print("  NOT WRITTEN (checks failed)")

shutil.rmtree(TMP, ignore_errors=True)
sys.exit(0 if ok else 1)
