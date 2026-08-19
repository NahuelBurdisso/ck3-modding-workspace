"""Pair each effective-tier marker with the swing that preceded it.

bc_record_moment_effect logs "BC: moment swing up|down" and then
bc_record_effective_tier_effect logs "BC: moment minor|major|decisive" for the
same moment, so the two are adjacent in the log. bc_wound_effect's first outer
row is `flag:$SWING$ = flag:down`; this says how many major arms could ever have
passed it. Also reports which phase-event file the moment came from, because
knight-scoped moments and commander-scoped ones read different variables.
"""

import re
from collections import Counter

LOG = "D:/Documents/Paradox Interactive/Crusader Kings III/logs/debug.log"

SWING = re.compile(r"BC: moment swing (up|down)")
TIER = re.compile(r"BC: moment (minor|major|decisive)")
MARK = re.compile(r"BC: chronicle mark (commander|knight)")

pairs = Counter()          # (swing, tier) -> n
orphan_tier = Counter()    # tier seen with no swing before it
last_swing = None
recent_mark = None
tier_by_mark = Counter()   # (mark, tier)

with open(LOG, encoding="utf-8", errors="replace") as fh:
    for line in fh:
        if "BC: " not in line:
            continue
        m = MARK.search(line)
        if m:
            recent_mark = m.group(1)
            continue
        m = SWING.search(line)
        if m:
            last_swing = m.group(1)
            continue
        m = TIER.search(line)
        if m:
            tier = m.group(1)
            if last_swing is None:
                orphan_tier[tier] += 1
            else:
                pairs[(last_swing, tier)] += 1
            tier_by_mark[(recent_mark, tier)] += 1
            last_swing = None

print("=== swing x effective tier ===")
for tier in ("minor", "major", "decisive"):
    up = pairs[("up", tier)]
    down = pairs[("down", tier)]
    print("  %-9s  up %5d   down %5d   orphan %d" % (tier, up, down, orphan_tier[tier]))
print()
print("bc_wound_effect is called from the major and decisive arms only.")
reach = pairs[("down", "major")] + pairs[("down", "decisive")]
calls = sum(pairs[(s, t)] for s in ("up", "down") for t in ("major", "decisive"))
print("  calls into bc_wound_effect      : %d" % calls)
print("  of those with SWING = down      : %d   <- max that can pass row 1" % reach)
print()
print("=== nearest preceding 'chronicle mark' x tier ===")
print("(weak: the mark is only written on the commander path, so a knight moment")
print(" inherits whatever mark came last. Read the ratio, not the absolute.)")
for k, v in sorted(tier_by_mark.items(), key=lambda x: -x[1]):
    print("  %6d  mark=%s tier=%s" % (v, k[0], k[1]))
