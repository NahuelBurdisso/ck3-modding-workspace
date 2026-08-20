import os, re, sys
SCOPE = "Supported Scopes: " + (sys.argv[1] if len(sys.argv)>1 else "character")

txt = open(r"D:/ck3/docs/api/1.19.0.6/triggers.log", encoding="utf-8", errors="replace").read()
blocks = re.split(r"\n(?=[a-z_][a-z_0-9]* - )", txt)

mod = "D:/ck3/mods/battle_chronicles"
blob = ""
for root, dirs, files in os.walk(mod):
    if ".git" in root:
        continue
    for f in files:
        if f.endswith((".txt", ".yml", ".md")):
            blob += open(os.path.join(root, f), encoding="utf-8-sig", errors="replace").read()

out = []
for b in blocks:
    m = re.match(r"([a-z_][a-z_0-9]*) - ", b)
    if not m:
        continue
    name = m.group(1)
    if name in blob:
        continue
    if SCOPE not in b:
        continue
    desc = b.split("\n")[0]
    out.append(desc)
print(len(out))
for d in out:
    print(d[:150])
