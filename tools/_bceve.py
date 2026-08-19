"""Pair each eve with the ground band written for the same battle.

open-questions.md's eve verdict table is read by crossing the WRITE-PATH marker
`BC: ground <band>` against what the third paragraph rendered. The write happens
in bc_battle_open_effect, which is also what fires the eve, so the band for a
given eve is the last one logged before its `BC: eve popup 0011`. Anything the
eve itself logged after that line belongs to the same screen.
"""

import re

LOG = "D:/Documents/Paradox Interactive/Crusader Kings III/logs/debug.log"

GROUND = re.compile(r"BC: ground (\w+)")
POPUP = re.compile(r"BC: eve popup 0011")
OFFER = re.compile(r"BC: eve offered")
EVEMISS = re.compile(r"BC: eve ground missing")
OPTION = re.compile(r"BC: eve option (\w+)")
TS = re.compile(r"\[(\d\d:\d\d:\d\d)\]")

last_ground = None
last_ts = "??:??:??"
eves = []

with open(LOG, encoding="utf-8", errors="replace") as fh:
    for line in fh:
        t = TS.search(line)
        if t:
            last_ts = t.group(1)
        if "BC: " not in line:
            continue
        m = GROUND.search(line)
        if m:
            last_ground = m.group(1)
            continue
        if EVEMISS.search(line):
            eves.append(["EVE GROUND MISSING", last_ts, None])
            continue
        if OFFER.search(line):
            eves.append(["offered", last_ts, last_ground])
            continue
        if POPUP.search(line):
            eves.append(["popup shown", last_ts, last_ground])
            continue
        m = OPTION.search(line)
        if m:
            eves.append(["OPTION TAKEN: " + m.group(1), last_ts, last_ground])

print("=== eve timeline (%d entries) ===" % len(eves))
for what, ts, ground in eves:
    print("  [%s]  %-22s  band written for that battle: %s" % (ts, what, ground))
print()
print("Options a, b and c of bc_chronicles.0011 carry NO debug_log, so an eve")
print("with 'popup shown' and no 'OPTION TAKEN' below it means one of those three")
print("was picked, or the screen is still open. It does NOT mean nothing happened.")
