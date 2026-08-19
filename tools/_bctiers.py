"""Static census of what TIER/SWING every template asks for.

The wound only ever fires on the intersection TIER in {major, decisive} AND
SWING = down. This counts how many shipped templates can even request that
combination, split by the file they live in, so a live result of zero can be
told apart from a content gap.
"""

import re
from collections import Counter

FILES = {
    "commander": "D:/ck3/mods/battle_chronicles/common/combat_phase_events/bc_commander_phase_events.txt",
    "knight": "D:/ck3/mods/battle_chronicles/common/combat_phase_events/bc_knight_phase_events.txt",
}

CALL = re.compile(r"bc_record_moment_effect\s*=\s*\{([^}]*)\}", re.S)
TIER = re.compile(r"TIER\s*=\s*(\w+)")
SWING = re.compile(r"SWING\s*=\s*(\w+)")

for label, path in FILES.items():
    text = open(path, encoding="utf-8", errors="replace").read()
    # Strip comments so the prose above a template cannot be counted as a call.
    text = "\n".join(l.split("#")[0] for l in text.splitlines())
    combos = Counter()
    for m in CALL.finditer(text):
        body = m.group(1)
        t = TIER.search(body)
        s = SWING.search(body)
        combos[(t.group(1) if t else "?", s.group(1) if s else "?")] += 1
    total = sum(combos.values())
    print("=== %s (%d call sites) ===" % (label, total))
    for k, v in sorted(combos.items(), key=lambda x: -x[1]):
        star = "   <-- can wound" if k[0] in ("major", "decisive") and k[1] == "down" else ""
        print("  %5d  TIER=%-9s SWING=%s%s" % (v, k[0], k[1], star))
    print()
