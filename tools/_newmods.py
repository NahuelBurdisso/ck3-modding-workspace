"""Collision + on_action check for candidate mods against the live playset.

Reads dlc_load.json for the enabled set, adds the candidate ids on the command
line, and reports (a) relative paths claimed by 2+ sources and (b) on_action
keys that more than one source defines an `effect = {` for, which is the
non-merging case.
"""
import json
import os
import re
import sys
from collections import defaultdict

USER = "D:/Documents/Paradox Interactive/Crusader Kings III"
WS = "D:/SteamLibrary/steamapps/workshop/content/1158310"
LOCAL = {"battle_chronicles": "D:/ck3/mods/battle_chronicles"}

CANDIDATES = sys.argv[1:]

enabled = json.load(open(USER + "/dlc_load.json", encoding="utf-8"))["enabled_mods"]

sources = []  # (label, root)
for entry in enabled:
    slug = os.path.basename(entry)[:-4]
    if slug.startswith("ugc_"):
        wid = slug[4:]
        sources.append((wid, WS + "/" + wid))
    else:
        sources.append((slug, LOCAL.get(slug, USER + "/mod/" + slug)))
for wid in CANDIDATES:
    sources.append((wid + "*NEW", WS + "/" + wid))


def name_of(root):
    for f in os.listdir(root):
        if f.endswith(".mod"):
            m = re.search(r'^name="(.*)"', open(os.path.join(root, f),
                                                encoding="utf-8-sig",
                                                errors="replace").read(), re.M)
            if m:
                return m.group(1)
    return "?"


labels = {}
files = defaultdict(list)
onaction = defaultdict(list)

for label, root in sources:
    if not os.path.isdir(root):
        print("MISSING", label, root)
        continue
    labels[label] = name_of(root)
    for dirpath, dirs, fs in os.walk(root):
        # DireWolves and the local mods are git repos; without this every one of them
        # collides on 20-27 identical .git/hooks/*.sample files and the report is noise.
        dirs[:] = [d for d in dirs if d != ".git"]
        for f in fs:
            if f.endswith((".mod", ".png", ".md", ".py", ".disabled")):
                continue
            if f in ("credits.txt", "LICENSE", ".gitignore"):
                continue
            full = os.path.join(dirpath, f)
            rel = os.path.relpath(full, root).replace("\\", "/")
            files[rel].append(label)
            if "/on_action/" in "/" + rel and rel.endswith(".txt"):
                txt = open(full, encoding="utf-8-sig", errors="replace").read()
                # top-level keys, then whether that block holds an effect = {
                for m in re.finditer(r"^([a-z_][a-z_0-9]*)\s*=\s*\{", txt, re.M):
                    start = m.end()
                    depth, i = 1, start
                    while i < len(txt) and depth:
                        if txt[i] == "{":
                            depth += 1
                        elif txt[i] == "}":
                            depth -= 1
                        i += 1
                    body = txt[start:i]
                    if re.search(r"^\s*effect\s*=\s*\{", body, re.M):
                        onaction[m.group(1)].append((label, rel))

print("sources: %d  (%d candidates)\n" % (len(labels), len(CANDIDATES)))

cand = {c + "*NEW" for c in CANDIDATES}
print("=== file collisions involving a candidate ===")
n = 0
for rel, owners in sorted(files.items()):
    if len(owners) > 1 and cand & set(owners):
        n += 1
        print("  %s" % rel)
        for o in owners:
            print("      %-12s %s" % (o, labels.get(o, "?")))
print("  (%d)\n" % n)

print("=== on_action keys with 2+ competing `effect = {` blocks ===")
n = 0
for key, owners in sorted(onaction.items()):
    if len({o for o, _ in owners}) > 1:
        n += 1
        print("  %s" % key)
        for o, rel in sorted(owners, key=lambda t: os.path.basename(t[1])):
            print("      %-12s %-28s %s" % (o, os.path.basename(rel), labels.get(o, "?")))
print("  (%d)  -- winner is ALPHABETICAL by filename, not load order\n" % n)
