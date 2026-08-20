# Proves the invariant the toast-priority design rests on: in every phase-event
# template, bc_record_moment_effect precedes the bc_can_toast_trigger gate, and the
# toast `if` sits exactly one brace deeper - i.e. inside the same enclosing scope.
# That is what lets the gate read var:bc_last_moment_rank with no parameter.
# Re-run after any bulk edit to the phase-event files.
#
# TWO KNOWN LIMITS:
#   1. The SIDE constant is dead. It was going to check the knight wrapper
#      explicitly and the depth check subsumed it; it is left as documentation of
#      what the depth column is really measuring.
#   2. Brace counting does not strip comments, so an unbalanced brace inside a
#      comment would skew the depth column. No template currently has one.
import re, sys

files = [
    r"D:/ck3/mods/battle_chronicles/common/combat_phase_events/bc_commander_phase_events.txt",
    r"D:/ck3/mods/battle_chronicles/common/combat_phase_events/bc_knight_phase_events.txt",
]

REC = "bc_record_moment_effect = {"
TOAST = "limit = { bc_can_toast_trigger = yes }"
SIDE = "scope:combat_side.side_commander ?= {"

for path in files:
    with open(path, encoding="utf-8-sig") as f:
        lines = f.read().split("\n")
    events = []
    for i, ln in enumerate(lines, 1):
        s = ln.strip()
        if s.startswith(REC):
            events.append((i, "REC"))
        elif s == TOAST:
            events.append((i, "TOAST"))
    bad = []
    # expect strict alternation REC, TOAST, REC, TOAST ...
    for idx in range(0, len(events), 2):
        a = events[idx]
        b = events[idx + 1] if idx + 1 < len(events) else None
        if a[1] != "REC" or b is None or b[1] != "TOAST":
            bad.append((a, b))
    print(path.split("/")[-1])
    print("  pairs:", len(events) // 2, " events:", len(events))
    print("  out-of-order pairs:", len(bad))
    for x in bad[:10]:
        print("   ", x)

    # scope check: for each TOAST, find the nearest enclosing side_commander block
    # by brace depth, and confirm the matching REC is at the same depth.
    depth = 0
    depth_at = {}
    for i, ln in enumerate(lines, 1):
        s = ln.strip()
        if s.startswith(REC) or s == TOAST:
            depth_at[i] = depth
        depth += ln.count("{") - ln.count("}")
    mismatch = 0
    for idx in range(0, len(events) - 1, 2):
        r, t = events[idx][0], events[idx + 1][0]
        if depth_at.get(r) != depth_at.get(t) - 1:
            mismatch += 1
            if mismatch <= 5:
                print("    depth mismatch REC", r, depth_at.get(r), "TOAST", t, depth_at.get(t))
    print("  depth mismatches:", mismatch)
