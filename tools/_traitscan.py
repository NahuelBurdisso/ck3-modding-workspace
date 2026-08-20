import os
import re
import glob

agot = "D:/SteamLibrary/steamapps/workshop/content/1158310/2962333032/common/traits"
blocks = {}
for f in glob.glob(agot + "/*.txt"):
    txt = open(f, encoding="utf-8-sig", errors="replace").read()
    starts = [(m.start(), m.group(1)) for m in re.finditer(r"^([a-z_][a-z_0-9]*)\s*=\s*\{", txt, re.M)]
    for i, (pos, name) in enumerate(starts):
        endpos = starts[i + 1][0] if i + 1 < len(starts) else len(txt)
        blocks[name] = txt[pos:endpos]

mod = "D:/ck3/mods/battle_chronicles"
blob = ""
for root, dirs, files in os.walk(mod):
    if ".git" in root:
        continue
    for f in files:
        if f.endswith((".txt", ".yml", ".md")):
            blob += open(os.path.join(root, f), encoding="utf-8-sig", errors="replace").read()

skip = re.compile(r"beard_trait|hair|clothes|headgear|_dye$|^archmaester_|dna|eyepatch|portrait")
want = {"personality", "lifestyle", "fame", "health", "commander", "childhood"}
out = []
for name, blk in sorted(blocks.items()):
    if name in blob or skip.search(name):
        continue
    m = re.search(r"^\s*category\s*=\s*(\w+)", blk, re.M)
    cat = m.group(1) if m else "-"
    if cat in want:
        out.append("%-38s %s" % (name, cat))
print(len(out))
print("\n".join(out))
