import re, json, pathlib

P = pathlib.Path("D:/ck3/_gamestate")
PLAYER = "76753"

id_rx = re.compile(r"^(\d+)=\{\s*$")
f_rx = {
    "key": re.compile(r"^\tkey=\"?([a-zA-Z0-9_]+)"),
    "holder": re.compile(r"^\tholder=(\d+)"),
    "djl": re.compile(r"^\tde_jure_liege=(\d+)"),
    "dfl": re.compile(r"^\tde_facto_liege=(\d+)"),
    "claim": re.compile(r"^\tclaim=\{ ([\d ]+)\}"),
    "name": re.compile(r"^\t\t\tname=\"(.+)\"$"),
}

cur = None
T = {}
with open(P, "r", encoding="utf-8", errors="replace") as f:
    for line in f:
        m = id_rx.match(line)
        if m:
            cur = m.group(1)
            continue
        if cur is None:
            continue
        for k, rx in f_rx.items():
            m = rx.match(line)
            if m:
                d = T.setdefault(cur, {})
                if k == "claim":
                    d["claim"] = m.group(1).split()
                elif k not in d:
                    d[k] = m.group(1)
                break

T = {k: v for k, v in T.items() if "key" in v}
json.dump(T, open("D:/ck3/_titles.json", "w"))
print("titles:", len(T))


def name(i):
    d = T.get(i, {})
    return "%s (%s)" % (d.get("name", "?"), d.get("key", i))


print("\n== PLAYER CLAIMS ==")
for i, d in T.items():
    if PLAYER in d.get("claim", []):
        print(" ", name(i), "held by", d.get("holder"))

# de facto realm of player: titles whose dfl chain reaches a player top title
tops = {"10141", "3800"}


def in_realm(i, seen=None):
    seen = seen or set()
    while i and i not in seen:
        if i in tops:
            return True
        seen.add(i)
        i = T.get(i, {}).get("dfl")
    return False


# de jure tree
children = {}
for i, d in T.items():
    if d.get("djl"):
        children.setdefault(d["djl"], []).append(i)


def dejure_counties(root):
    out, stack = [], [root]
    while stack:
        i = stack.pop()
        k = T.get(i, {}).get("key", "")
        if k.startswith("c_"):
            out.append(i)
        stack += children.get(i, [])
    return out


for kingdom in ("10141", "3800"):
    cs = dejure_counties(kingdom)
    missing = [c for c in cs if not in_realm(c)]
    print("\n== DE JURE %s: %d counties, %d NOT in realm ==" % (name(kingdom), len(cs), len(missing)))
    for c in missing:
        h = T.get(c, {}).get("holder")
        dfl = T.get(c, {}).get("dfl")
        print("  ", name(c), "holder", h, "under", name(dfl) if dfl else "-")
