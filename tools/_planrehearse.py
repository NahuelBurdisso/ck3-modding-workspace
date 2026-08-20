"""Rehearse the toast-priority plan against scratch copies of the real files.

Parses the plan's Old:/New: fenced pairs in document order, applies each one to a
scratch copy of the file its task names, then runs the plan's own verification
greps against the result. Every assertion the plan makes about a count is checked
here rather than discovered by an implementer mid-task.

Throwaway. Delete after the plan lands.
"""
import re
import sys

PLAN = "D:/ck3/docs/plans/2026-08-20-battle-chronicles-toast-priority.md"
MOD = "D:/ck3/mods/battle_chronicles/"

LEDGER = MOD + "common/scripted_effects/bc_ledger_effects.txt"
TRIGGERS = MOD + "common/scripted_triggers/bc_scripted_triggers.txt"
EFFECTS = MOD + "common/scripted_effects/bc_scripted_effects.txt"
BENCH = "D:/ck3/docs/battle-chronicles/bench.md"

plan = open(PLAN, encoding="utf-8").read()

# Split the plan into task sections so each Old/New pair inherits a target file.
task_targets = {
    "Task 2": LEDGER,
    "Task 3": LEDGER,
    "Task 4": TRIGGERS,
    "Task 5": EFFECTS,
    "Task 6": BENCH,
}

sections = re.split(r"^## (Task \d+)[^\n]*$", plan, flags=re.M)
# sections = [preamble, "Task 1", body, "Task 2", body, ...]
pairs = []
for i in range(1, len(sections), 2):
    name, body = sections[i], sections[i + 1]
    if name not in task_targets:
        continue
    # "Old:" or "Old (...):" then a fence, then "New:" then a fence.
    for m in re.finditer(
        r"^Old[^\n]*:\n\n```\n(.*?)```\n\nNew[^\n]*:\n\n```\n(.*?)```",
        body,
        flags=re.M | re.S,
    ):
        pairs.append((name, task_targets[name], m.group(1), m.group(2)))

print("parsed %d Old/New pairs" % len(pairs))
if len(pairs) != 11:
    print("!! expected 11 pairs (Task2 x6, Task3 x2, Task4, Task5, Task6)")

# Scratch copies, read with utf-8-sig so the BOM is preserved separately.
scratch = {}
boms = {}
for path in (LEDGER, TRIGGERS, EFFECTS, BENCH):
    raw = open(path, "rb").read()
    boms[path] = raw.startswith(b"\xef\xbb\xbf")
    scratch[path] = raw.decode("utf-8-sig")

fails = []
for name, path, old, new in pairs:
    n = scratch[path].count(old)
    if n != 1:
        fails.append("%s: old_string occurs %d times in %s\n---\n%s---"
                     % (name, n, path.rsplit("/", 1)[1], old))
        continue
    scratch[path] = scratch[path].replace(old, new, 1)

# The two insert-only steps the parser cannot pair.
TRIG_HEADER = """# THE SECOND ARM IS A PRIORITY LANE, NOT A SECOND CHANCE."""
if TRIG_HEADER not in plan:
    fails.append("Task 4 Step 2 header text not found in the plan")
# Simulate it: the header goes immediately above the definition.
anchor = "bc_can_toast_trigger = {"
if scratch[TRIGGERS].count(anchor) < 1:
    fails.append("Task 4: no bc_can_toast_trigger definition to insert above")
else:
    hdr = re.search(r"^# THE SECOND ARM IS A PRIORITY LANE.*?^# this codebase\.\n",
                    plan, flags=re.M | re.S)
    if not hdr:
        fails.append("Task 4 Step 2: could not extract the header block from the plan")
    else:
        scratch[TRIGGERS] = scratch[TRIGGERS].replace(
            "bc_can_toast_trigger = {", hdr.group(0) + "bc_can_toast_trigger = {", 1)

# Task 6 Step 2: the bench table row.
row = re.search(r"^\| `bc_toast_cooldown_high` \| <HIGH> \|[^\n]*\n", plan, flags=re.M)
if not row:
    fails.append("Task 6 Step 2: table row not found in the plan")
else:
    tr_anchor = "| `bc_toast_cooldown` | 10 | whether the RECIPIENT is shown a toast |\n"
    if tr_anchor not in scratch[BENCH]:
        fails.append("Task 6 Step 2: bc_toast_cooldown table row anchor not in bench.md")
    else:
        scratch[BENCH] = scratch[BENCH].replace(
            tr_anchor, tr_anchor + row.group(0).replace("<HIGH>", "20"), 1)

# Task 5 leaves a placeholder the implementer substitutes.
scratch[EFFECTS] = scratch[EFFECTS].replace("<HIGH>", "20")

if fails:
    print("\n=== EDIT APPLICATION FAILURES ===")
    for f in fails:
        print(f)
    sys.exit(1)
print("all edits applied cleanly\n")


def count(path, needle):
    return sum(1 for line in scratch[path].splitlines() if needle in line)


def ctx(path, needle, after):
    """grep -A<after> <needle> | grep -c <inner>, as the plan runs it."""
    lines = scratch[path].splitlines()
    out = []
    for i, line in enumerate(lines):
        if needle in line:
            out.extend(lines[i:i + after + 1])
    return out


checks = [
    ("T2.6 bc_last_moment_rank lines", count(LEDGER, "bc_last_moment_rank"), 4),
    ("T2.6 'Six of the nine' gone", count(LEDGER, "Six of the nine"), 0),
    ("T3.5 'Eight of the eighteen' gone", count(LEDGER, "Eight of the eighteen"), 0),
    ("T3.5 warning survived (-A8)",
     sum(1 for l in ctx(LEDGER, "THE ABSENT CASE IS REAL", 8) if "bc_battle_size" in l), 1),
    ("T4.3 bc_toast_cooldown_high in triggers", count(TRIGGERS, "bc_toast_cooldown_high"), 2),
    ("T4.3 exists sibling + trigger_if (-A12)",
     sum(1 for l in ctx(TRIGGERS, "bc_can_toast_trigger = {", 12)
         if "exists = var:bc_last_moment_rank" in l), 2),
    ("T5.2 <HIGH> substituted", count(EFFECTS, "<HIGH>"), 0),
    ("T5.2 bc_toast_cooldown_high in effects", count(EFFECTS, "bc_toast_cooldown_high"), 1),
    ("T6.3 bc_toast_cooldown_high in bench", count(BENCH, "bc_toast_cooldown_high"), 2),
    ("T6.3 <HIGH> substituted in bench", count(BENCH, "<HIGH>"), 0),
]

# T5.3: the -B4 window must contain the preemption limit.
lines = scratch[EFFECTS].splitlines()
b4 = []
for i, line in enumerate(lines):
    if "flag = bc_toast_cooldown_high" in line:
        b4.extend(lines[max(0, i - 4):i + 1])
checks.append(("T5.3 high write inside the preempt branch",
               sum(1 for l in b4 if "limit = { has_character_flag = bc_toast_cooldown }" in l), 1))

bad = 0
for label, got, want in checks:
    ok = "ok " if got == want else "FAIL"
    if got != want:
        bad += 1
    print("%s  %-45s got %-3s want %s" % (ok, label, got, want))

# Brace balance on every touched script file, ignoring nothing - the same crude
# measure validate uses, compared before and after.
print()
for path in (LEDGER, TRIGGERS, EFFECTS):
    before = open(path, encoding="utf-8-sig").read()
    d0 = before.count("{") - before.count("}")
    d1 = scratch[path].count("{") - scratch[path].count("}")
    ok = "ok " if d0 == d1 else "FAIL"
    if d0 != d1:
        bad += 1
    print("%s  brace delta %-38s before %+d  after %+d"
          % (ok, path.rsplit("/", 1)[1], d0, d1))

# BOM must survive.
print()
for path, had in boms.items():
    print("    BOM %-40s %s" % (path.rsplit("/", 1)[1], "yes" if had else "no"))

print("\n%d failing check(s)" % bad)
sys.exit(1 if bad else 0)
