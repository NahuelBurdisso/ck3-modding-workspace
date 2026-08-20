import os, re, glob

agot = "D:/SteamLibrary/steamapps/workshop/content/1158310/2962333032/common/scripted_triggers"
names = {}
for f in glob.glob(agot + "/*.txt"):
    txt = open(f, encoding="utf-8-sig", errors="replace").read()
    for m in re.finditer(r"^([a-z_][a-z_0-9]*)\s*=\s*\{", txt, re.M):
        names[m.group(1)] = os.path.basename(f)

mod = "D:/ck3/mods/battle_chronicles"
blob = ""
for root, dirs, files in os.walk(mod):
    if ".git" in root:
        continue
    for f in files:
        if f.endswith((".txt", ".yml", ".md")):
            blob += open(os.path.join(root, f), encoding="utf-8-sig", errors="replace").read()

skip = re.compile(r"dna|portrait|clothes|hair|beard|_gfx|graphical")
out = [(n, f) for n, f in sorted(names.items()) if n not in blob and not skip.search(n)]
print(len(out))
for n, f in out:
    print("%-58s %s" % (n, f))
