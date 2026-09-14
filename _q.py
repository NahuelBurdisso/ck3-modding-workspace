import json, sys, re

T = json.load(open("D:/ck3/_titles.json"))
PLAYER = "76753"


def name(i):
    d = T.get(str(i), {})
    return "%s [%s]" % (d.get("name", "?"), d.get("key", i))


def show(i):
    d = T.get(str(i), {})
    print(i, d.get("key"), "| name", d.get("name"), "| holder", d.get("holder"),
          "| dfl", name(d.get("dfl")) if d.get("dfl") else "-",
          "| djl", name(d.get("djl")) if d.get("djl") else "-",
          "| claimants", d.get("claim", []))


for arg in sys.argv[1:]:
    if arg.isdigit():
        show(arg)
    else:
        rx = re.compile(arg)
        for i, d in T.items():
            if rx.search(d.get("key", "")):
                show(i)
