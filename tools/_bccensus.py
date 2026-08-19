"""One pass over debug.log answering the open-questions agenda.

`probe` groups by message, which buries the questions that matter: how many
DISTINCT templates ever fired, and whether the paired markers (deferred vs
deferred-fired) agree. This reads the file once and reports those directly.
"""

import re
from collections import Counter

LOG = "D:/Documents/Paradox Interactive/Crusader Kings III/logs/debug.log"

fired = Counter()          # template key -> hits
fired_file = {}            # template key -> commander|knight
marks = Counter()          # every other BC marker, normalised

FIRED = re.compile(r"BC: fired (\S+)")
BC = re.compile(r"BC: (.+?)\s*$")

lines = 0
with open(LOG, encoding="utf-8", errors="replace") as fh:
    for line in fh:
        if "BC: " not in line:
            continue
        lines += 1
        m = FIRED.search(line)
        if m:
            key = m.group(1)
            fired[key] += 1
            fired_file[key] = "knight" if "bc_knight_phase_events" in line else "commander"
            continue
        m = BC.search(line)
        if m:
            marks[m.group(1)] += 1

cmd = {k: v for k, v in fired.items() if fired_file[k] == "commander"}
kni = {k: v for k, v in fired.items() if fired_file[k] == "knight"}

print("BC lines in debug.log: %d" % lines)
print()
print("=== TEMPLATE CENSUS ===")
print("distinct templates fired : %d   (total fires %d)" % (len(fired), sum(fired.values())))
print("  commander : %3d distinct / 238 shipped   %5d fires" % (len(cmd), sum(cmd.values())))
print("  knight    : %3d distinct / 206 shipped   %5d fires" % (len(kni), sum(kni.values())))
print()
print("top 15 commander:")
for k, v in sorted(cmd.items(), key=lambda x: -x[1])[:15]:
    print("  %5d  %s" % (v, k))
print()
print("top 15 knight:")
for k, v in sorted(kni.items(), key=lambda x: -x[1])[:15]:
    print("  %5d  %s" % (v, k))
print()

print("=== AGENDA MARKERS ===")
AGENDA = [
    "dk deferred", "dk deferred fired", "dk found dead",
    "wound", "wound gates passed",
    "nickname awarded", "nickname style UNMATCHED",
    "nemesis new", "nemesis rung grudge", "nemesis rung rival",
    "ground missing", "eve ground missing", "eve offered", "eve option",
    "moment decisive", "moment major", "moment minor",
    "award piety", "award prestige", "award no creed", "bond nofoe",
    "creed heathen", "ground desert",
]
for want in AGENDA:
    exact = marks.get(want, 0)
    pref = sum(v for k, v in marks.items() if k.startswith(want))
    print("  %-28s exact %6d   with-suffix %6d" % (want, exact, pref))
print()

print("=== ALL NON-TEMPLATE MARKERS ===")
for k, v in sorted(marks.items(), key=lambda x: -x[1]):
    print("  %6d  %s" % (v, k))
