"""Check every entry in the live dlc_load.json actually resolves.

`playset audit` reports on version metadata; this answers the cruder question
that decides whether the game starts at all: does each `.mod` pointer exist, does
it carry a `path=`, is that path free of backslashes, and does the folder it
names exist on disk.
"""

import json
import os
import re

USER = "D:/Documents/Paradox Interactive/Crusader Kings III/"

data = json.load(open(USER + "dlc_load.json", encoding="utf-8-sig"))
mods = data["enabled_mods"]
print("entradas: %d | disabled_dlcs: %d" % (len(mods), len(data.get("disabled_dlcs", []))))

problems = []
for i, rel in enumerate(mods, 1):
    p = USER + rel
    if not os.path.exists(p):
        problems.append((i, rel, "falta el archivo .mod"))
        continue
    txt = open(p, encoding="utf-8-sig", errors="replace").read()
    # Anchored to the line start: AGOT alone carries 24 `replace_path=` lines,
    # and an unanchored search reports the first of those as a missing folder.
    m = re.search(r'^path="([^"]+)"', txt, re.M)
    if not m:
        problems.append((i, rel, "sin path="))
        continue
    path = m.group(1)
    if "\\" in path:
        problems.append((i, rel, "backslash en path="))
    if not os.path.isdir(path):
        problems.append((i, rel, "carpeta inexistente: " + path))

print("problemas: %d" % len(problems))
for i, rel, why in problems:
    print("  [%d] %s - %s" % (i, rel, why))

print()
print("cola de la lista (los ultimos ganan):")
for i, rel in enumerate(mods[-5:], len(mods) - 4):
    print("  [%d] %s" % (i, rel))
