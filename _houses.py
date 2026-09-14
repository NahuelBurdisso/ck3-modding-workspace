import re, sys, pathlib

P = pathlib.Path("D:/ck3/_gamestate")
WANT = set(sys.argv[1:])
id_rx = re.compile(r"^(\d+)=\{\s*$")
kv_rx = re.compile(r"^\t(name|localized_name|dynasty|found_date|prefix)=\"?([^\"\n]+)\"?")

inside = False
cur = None
out = {}
with open(P, "r", encoding="utf-8", errors="replace") as f:
    for line in f:
        if not inside:
            if line.rstrip("\n") == "\tdynasty_house={":
                inside = True
            continue
        if line.rstrip("\n") == "\t}":
            break
        m = id_rx.match(line)
        if m:
            cur = m.group(1) if m.group(1) in WANT else None
            continue
        if not cur:
            continue
        m = kv_rx.match(line)
        if m:
            out.setdefault(cur, {})[m.group(1)] = m.group(2).strip()
for i in sys.argv[1:]:
    print(i, out.get(i))
